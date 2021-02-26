from copy import deepcopy
import linecache
import sys
import threading
from time import sleep

import settings
from market_maker.utils.singleton import singleton_data
from market_maker.utils import log

logger = log.setup_custom_logger('root')
execept_logger = log.setup_custom_logger('exception')
execute_logger = log.setup_custom_logger('order')

class BuyThread(threading.Thread):
    def __init__(self, custom_strategy):
        logger.info("[BuyThread][run] __init__")
        threading.Thread.__init__(self)
        self.custom_strategy = custom_strategy
        singleton_data.instance().setAllowSell(False)
        singleton_data.instance().setBuyThread(True)

        # default(20.0) * (current_quantity / max_order_quantity)
        # The maximum value is the default even if the quantity you have now is greater than max_order.
        # MAX = default(20.0)
        # The more bulk_net_buy orders, the higher the price.
        currentQty = self.custom_strategy.exchange.get_currentQty()
        logger.info("[BuyThread][run] MAX_ORDER_QUENTITY : " + str(settings.MAX_ORDER_QUENTITY))

        self.minBuyingGap = 3.0
        if abs(currentQty) >= settings.MAX_ORDER_QUENTITY:
            self.minBuyingGap = self.minBuyingGap + settings.MIN_SELLING_GAP
        else :
            self.minBuyingGap = self.minBuyingGap + float(settings.MIN_SELLING_GAP) * float(abs(currentQty) / settings.MAX_ORDER_QUENTITY)

        logger.info("[BuyThread][run] minBuyingGap : " + str(self.minBuyingGap))

        self.waiting_buy_order = {}
        self.wait_cnt = 0
        #self.allow_stop_loss = False
        #self.exchange = ExchangeInterface(settings.DRY_RUN)


    def PrintException(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        logger.info("[BuyThread][run] " + str('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)))
        execept_logger.info("[BuyThread][run] " + str('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)))

    #def retry_buy(self):
    #def ammend_buy(self):

    def run(self):
        logger.info("[BuyThread][run]")

        while not singleton_data.instance().getAllowBuy():
            try:
                # realized profit
                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                avgCostPrice = self.custom_strategy.exchange.get_avgCostPrice()
                avgCostPrice_copy = deepcopy(avgCostPrice)
                currentQty = self.custom_strategy.exchange.get_currentQty()

                logger.info("[BuyThread][run] [" + str(self.wait_cnt) +"] current_price : " + str(current_price) + ", avgCostPrice : " + str(avgCostPrice) + ", currentQty : " + str(currentQty))

                if len(self.waiting_buy_order) == 0:
                    # buying condition
                    if float(current_price) < float(avgCostPrice) - float(self.minBuyingGap):
                        logger.info("[BuyThread][run] current_price(" + str(current_price) +") < avgCostPrice(" + str(avgCostPrice) + ") - minBuyingGap(" + str(self.minBuyingGap) + ")")

                        self.waiting_buy_order = self.make_buy_order()
                        self.waiting_buy_order_copy = deepcopy(self.waiting_buy_order)
                        logger.info("[BuyThread][run] NEW : waiting_buy_order : " + str(self.waiting_buy_order))

                    # waiting (default:15) secs condition
                    else:
                        self.wait_cnt += 1

                        if self.wait_cnt > settings.SELLING_WAIT:
                            logger.info("[BuyThread][run] stop buying thread because cnt < " + str(settings.SELLING_WAIT))

                            # exit buy thread
                            break

                #check buying order
                elif len(self.waiting_buy_order) > 0:
                    if self.check_buy_order(avgCostPrice):
                        singleton_data.instance().setAllowSell(True)

                        sleep(5)
                        #report
                        margin = self.custom_strategy.exchange.get_user_margin()
                        margin_str = '수익 정리\n'
                        margin_str += '판매가    : ' + str(self.waiting_buy_order_copy['price']) + '\n'
                        margin_str += '평균가    : ' + str( ) + '\n'
                        margin_str += '수량     : ' + str(self.waiting_buy_order_copy['orderQty']) + '\n'
                        margin_str +=  '실현 수익 : ' + str(margin['prevRealisedPnl']/100000000)[:7] + '\n'
                        singleton_data.instance().sendTelegram(margin_str)

                        break

                sleep(1)
            except Exception as ex:
                self.PrintException()
                break

            sleep(1)

        # Cancel all buy orders
        try:
            self.custom_strategy.exchange.cancel_all_orders('Buy')
        except Exception as ex:
            self.PrintException()
        finally:
            singleton_data.instance().setBuyThread(False)

    def make_buy_order(self):
        logger.info("[BuyThread][make_buy_order] start")

        # if it couldn't oder, retry it
        cancel_retryCnt = 0
        current_buy_order = {}

        try:

            # buy는 냅두고 buy order만으로 바꿔야한다
            # 그래야지 실패하더라도 buy는 냅둬서 다시 주워담을수 있다
            # 모든걸 취소하게되면 팔리지 않을시 최악의 경우에는 기존 buy는 모두 취소되고 buying만을 기다려야 한다
            self.custom_strategy.exchange.cancel_all_orders('Buy')
            #self.custom_strategy.exchange.cancel_all_orders('All')

            while len(current_buy_order) == 0:
                buy_orders = []
                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                avgCostPrice = self.custom_strategy.exchange.get_avgCostPrice()
                currentQty = abs(self.custom_strategy.exchange.get_currentQty())

                logger.info("[BuyThread][make_buy_order] current_price : " + str(current_price) + ", currentQty : " + str(currentQty))

                if currentQty == 0:
                    logger.info("[BuyThread][make_buy_order] The first order was established before the order was cancelled")
                    break

                if cancel_retryCnt < 10:
                    #buy_orders.append({'price': current_price, 'orderQty': currentQty, 'side': "Buy", 'execInst': "ParticipateDoNotInitiate"})
                    current_buy_order = self.custom_strategy.exchange.create_order('Buy', currentQty, current_price)
                    sleep(0.2)
                else :
                    #buy_orders.append({'price': current_price + 0.5, 'orderQty': currentQty, 'side': "Buy", 'execInst': "ParticipateDoNotInitiate"})
                    current_buy_order = self.custom_strategy.exchange.create_order('Buy', currentQty, current_price - 0.5)
                    sleep(0.1)

                logger.info("[BuyThread][make_buy_order] current_buy_order : " + str(current_buy_order))

                # for remaining buy order
                #for i in range (len(response_order)):
                #    if response_order[i]['side'] == 'Buy':
                #        current_buy_order.append(response_order[i])

                #logger.info("[BuyThread][make_buy_order] current_buy_order : " + str(current_buy_order))

                #if len(current_buy_order) == 1:
                if current_buy_order['ordStatus'] == 'Canceled':
                    cancel_retryCnt += 1
                    logger.info("[BuyThread][make_buy_order] order Status == Canceled")
                    logger.info("[BuyThread][make_buy_order] reason : " + str(current_buy_order['text']))
                    logger.info("[BuyThread][make_buy_order] buy order retry : " + str(cancel_retryCnt))
                    current_buy_order = {}
                    sleep(0.5)
                elif current_buy_order['ordStatus'] == 'New':
                    logger.info("[BuyThread][make_buy_order] order Status == New")
                    self.expectedProfit = (float(current_price) - float(avgCostPrice)) * float(currentQty)
                    logger.info("[BuyThread][make_buy_order] expectedProfit : " + str(self.expectedProfit))

                    break
                else :
                    logger.info("[BuyThread][make_buy_order] Abnormal ordStatus : " + str(current_buy_order['ordStatus']))

        except Exception as ex:
            self.PrintException()

        return current_buy_order

    def check_buy_order(self, avgCostPrice):
        # checking whether or not it's sold
        ret = False

        buy_orders = self.custom_strategy.exchange.get_orders('Buy')
        logger.info("[BuyThread][check_buy_order] buy_orders : " + str(buy_orders))

        if len(buy_orders) == 0:
            # buying complete
            logger.info("[BuyThread][check_buy_order] buying complete!")
            self.custom_strategy.exchange.cancel_all_orders('All')
            singleton_data.instance().setAveDownCnt(0)

            # expectedProfit 수정 필요
            #logger.info("[BuyThread][check_buy_order] ######  profit : + " + str(self.expectedProfit) + "$  ######")
            #execute_logger.info("######  profit : + " + str(self.expectedProfit) + "$  ######")

            ret = True
            self.waiting_buy_order = {}

        elif len(buy_orders) == 1:
            current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']

            if not float(current_price) < float(avgCostPrice) - float(self.minBuyingGap):
                logger.info("[BuyThread][check_buy_order] current_price(" + str(current_price) +") < avgCostPrice(" + str(avgCostPrice) + ") - minBuyingGap(" + str(self.minBuyingGap) + ")")
                self.waiting_buy_order = {}
                self.custom_strategy.exchange.cancel_all_orders('Buy')
                ret = False

            # 3.0 move to settings
            elif float(current_price) - float(buy_orders[0]['price']) > 3.0:
                # flee away 3$ form first oder_price, amend order
                # reorder
                self.waiting_buy_order = self.make_buy_order()
                logger.info("[BuyThread][check_buy_order] reorder current_price + 3$ : waiting_buy_order : " + str(self.waiting_buy_order))
            else :
                logger.info("[BuyThread][check_buy_order] The price you ordered has not dropped by more than $ 3 from the current price.")

            logger.info("[BuyThread][check_buy_order] not yet buying")

        return ret



