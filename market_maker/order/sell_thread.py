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

class SellThread(threading.Thread):
    def __init__(self, custom_strategy):
        logger.info("[SellThread][run] __init__")
        threading.Thread.__init__(self)
        self.custom_strategy = custom_strategy
        singleton_data.instance().setAllowBuy(False)
        singleton_data.instance().setSellThread(True)

        # default(20.0) * (current_quantity / max_order_quantity)
        # The maximum value is the default even if the quantity you have now is greater than max_order.
        # MAX = default(20.0)
        # The more bulk_net_sell orders, the higher the price.
        currentQty = self.custom_strategy.exchange.get_currentQty()
        logger.info("[SellThread][run] MAX_ORDER_QUENTITY : " + str(settings.MAX_ORDER_QUENTITY))

        self.minSellingGap = 3.0
        if currentQty > settings.MAX_ORDER_QUENTITY:
            self.minSellingGap = self.minSellingGap + settings.MIN_SELLING_GAP
        else :
            self.minSellingGap = self.minSellingGap + float(settings.MIN_SELLING_GAP) * float(currentQty / settings.MAX_ORDER_QUENTITY)

        logger.info("[SellThread][run] minSellingGap : " + str(self.minSellingGap))

        self.waiting_sell_order = {}
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
        logger.info("[SellThread][run] " + str('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)))
        execept_logger.info("[SellThread][run] " + str('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)))

    #def retry_sell(self):
    #def ammend_sell(self):

    def run(self):
        logger.info("[SellThread][run]")

        while not singleton_data.instance().getAllowBuy():
            try:
                # realized profit
                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                avgCostPrice = self.custom_strategy.exchange.get_avgCostPrice()
                avgCostPrice_copy = deepcopy(avgCostPrice)
                currentQty = self.custom_strategy.exchange.get_currentQty()

                logger.info("[SellThread][run] [" + str(self.wait_cnt) +"] current_price : " + str(current_price) + ", avgCostPrice : " + str(avgCostPrice) + ", currentQty : " + str(currentQty))

                if len(self.waiting_sell_order) == 0:
                    # selling condition
                    if float(current_price) > float(avgCostPrice) + float(self.minSellingGap):
                        logger.info("[SellThread][run] current_price(" + str(current_price) +") > avgCostPrice(" + str(avgCostPrice) + ") + minSellingGap(" + str(self.minSellingGap) + ")")

                        self.waiting_sell_order = self.make_sell_order()
                        self.waiting_sell_order_copy = deepcopy(self.waiting_sell_order)
                        logger.info("[SellThread][run] NEW : waiting_sell_order : " + str(self.waiting_sell_order))

                    # waiting (default:15) secs condition
                    else:
                        self.wait_cnt += 1

                        if self.wait_cnt > settings.SELLING_WAIT:
                            logger.info("[SellThread][run] stop selling thread because cnt > " + str(settings.SELLING_WAIT))

                            # exit sell thread
                            break

                #check selling order
                elif len(self.waiting_sell_order) > 0:
                    if self.check_sell_order(avgCostPrice):
                        singleton_data.instance().setAllowBuy(True)

                        sleep(5)
                        #report
                        margin = self.custom_strategy.exchange.get_user_margin()
                        margin_str = '수익 정리\n'
                        margin_str += '판매가    : ' + str(self.waiting_sell_order_copy['price']) + '\n'
                        margin_str += '평균가    : ' + str(avgCostPrice_copy) + '\n'
                        margin_str += '수량     : ' + str(self.waiting_sell_order_copy['orderQty']) + '\n'
                        margin_str +=  '실현 수익 : ' + str(margin['prevRealisedPnl']/100000000)[:7] + '\n'
                        singleton_data.instance().sendTelegram(margin_str)

                        break

                sleep(1)
            except Exception as ex:
                self.PrintException()
                break

            sleep(1)

        # Cancel all sell orders
        try:
            self.custom_strategy.exchange.cancel_all_orders('Sell')
        except Exception as ex:
            self.PrintException()
        finally:
            singleton_data.instance().setSellThread(False)

    def make_sell_order(self):
        logger.info("[SellThread][make_sell_order] start")

        # if it couldn't oder, retry it
        cancel_retryCnt = 0
        current_sell_order = {}

        try:

            # buy는 냅두고 sell order만으로 바꿔야한다
            # 그래야지 실패하더라도 buy는 냅둬서 다시 주워담을수 있다
            # 모든걸 취소하게되면 팔리지 않을시 최악의 경우에는 기존 buy는 모두 취소되고 selling만을 기다려야 한다
            self.custom_strategy.exchange.cancel_all_orders('Sell')
            #self.custom_strategy.exchange.cancel_all_orders('All')

            while len(current_sell_order) == 0:
                sell_orders = []
                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                avgCostPrice = self.custom_strategy.exchange.get_avgCostPrice()
                currentQty = self.custom_strategy.exchange.get_currentQty()

                logger.info("[SellThread][make_sell_order] current_price : " + str(current_price) + ", currentQty : " + str(currentQty))

                if currentQty == 0:
                    logger.info("[BuyThread][make_buy_order] The first order was established before the order was cancelled")
                    break

                if cancel_retryCnt < 10:
                    #sell_orders.append({'price': current_price, 'orderQty': currentQty, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})
                    current_sell_order = self.custom_strategy.exchange.create_order('Sell', currentQty, current_price)
                    sleep(0.2)
                else :
                    #sell_orders.append({'price': current_price + 0.5, 'orderQty': currentQty, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})
                    current_sell_order = self.custom_strategy.exchange.create_order('Sell', currentQty, current_price + 0.5)
                    sleep(0.1)

                logger.info("[SellThread][make_sell_order] current_sell_order : " + str(current_sell_order))

                # for remaining buy order
                #for i in range (len(response_order)):
                #    if response_order[i]['side'] == 'Sell':
                #        current_sell_order.append(response_order[i])

                #logger.info("[SellThread][make_sell_order] current_sell_order : " + str(current_sell_order))

                #if len(current_sell_order) == 1:
                if current_sell_order['ordStatus'] == 'Canceled':
                    cancel_retryCnt += 1
                    logger.info("[SellThread][make_sell_order] order Status == Canceled")
                    logger.info("[SellThread][make_sell_order] reason : " + str(current_sell_order['text']))
                    logger.info("[SellThread][make_sell_order] sell order retry : " + str(cancel_retryCnt))
                    current_sell_order = {}
                    sleep(0.5)
                elif current_sell_order['ordStatus'] == 'New':
                    logger.info("[SellThread][make_sell_order] order Status == New")
                    self.expectedProfit = (float(current_price) - float(avgCostPrice)) * float(currentQty)
                    logger.info("[SellThread][make_sell_order] expectedProfit : " + str(self.expectedProfit))

                    break
                else :
                    logger.info("[SellThread][make_sell_order] Abnormal ordStatus : " + str(current_sell_order['ordStatus']))

        except Exception as ex:
            self.PrintException()

        return current_sell_order

    def check_sell_order(self, avgCostPrice):
        # checking whether or not it's sold
        ret = False

        sell_orders = self.custom_strategy.exchange.get_orders('Sell')
        logger.info("[SellThread][check_sell_order] sell_orders : " + str(sell_orders))

        if len(sell_orders) == 0:
            # selling complete
            logger.info("[SellThread][check_sell_order] selling complete!")
            self.custom_strategy.exchange.cancel_all_orders('All')
            singleton_data.instance().setAveDownCnt(0)

            # expectedProfit 수정 필요
            #logger.info("[SellThread][check_sell_order] ######  profit : + " + str(self.expectedProfit) + "$  ######")
            #execute_logger.info("######  profit : + " + str(self.expectedProfit) + "$  ######")

            ret = True
            self.waiting_sell_order = {}

        elif len(sell_orders) == 1:
            current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']

            if not float(current_price) > float(avgCostPrice) + float(self.minSellingGap):
                logger.info("[SellThread][check_sell_order] current_price(" + str(current_price) +") > avgCostPrice(" + str(avgCostPrice) + ") + minSellingGap(" + str(self.minSellingGap) + ")")
                self.waiting_sell_order = {}
                self.custom_strategy.exchange.cancel_all_orders('Sell')
                ret = False

            # 3.0 move to settings
            elif float(sell_orders[0]['price']) - float(current_price) > 3.0:
                # flee away 3$ form first oder_price, amend order
                # reorder
                self.waiting_sell_order = self.make_sell_order()
                logger.info("[SellThread][check_sell_order] reorder current_price - 3$ : waiting_sell_order : " + str(self.waiting_sell_order))
            else :
                logger.info("[SellThread][check_sell_order] The price you ordered has not dropped by more than $ 3 from the current price.")

            logger.info("[SellThread][check_sell_order] not yet selling")

        return ret



