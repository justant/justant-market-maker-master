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
        singleton_data.getInstance().setAllowBuy(False)
        singleton_data.getInstance().setSellThread(True)

        # 50.0
        self.averagingDownSize = settings.AVERAGING_DOWN_SIZE

        # default(20.0) * (current_quantity / max_order_quantity)
        # The maximum value is the default even if the quantity you have now is greater than max_order.
        # MAX = default(20.0)
        # The more net_buying orders, the higher the price.
        currentQty = self.custom_strategy.exchange.get_currentQty()
        logger.info("[SellThread][run] MAX_ORDER_QUENTITY : " + str(settings.MAX_ORDER_QUENTITY))
        if currentQty > settings.MAX_ORDER_QUENTITY:
            self.minSellingGap = settings.MIN_SELLING_GAP
        else :
            self.minSellingGap = float(settings.MIN_SELLING_GAP) * float(currentQty / settings.MAX_ORDER_QUENTITY)

        logger.info("[SellThread][run] minSellingGap : " + str(self.minSellingGap))

        self.waiting_sell_order = []
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
        # Cancel all sell orders
        self.custom_strategy.exchange.cancel_all_orders('Sell')


        while not singleton_data.getInstance().getAllowBuy():
            try:
                # realized profit
                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                avgCostPrice = self.custom_strategy.exchange.get_avgCostPrice()
                currentQty = self.custom_strategy.exchange.get_currentQty()

                logger.info("[SellThread][run] current_price : " + str(current_price) + ", avgCostPrice : " + str(avgCostPrice) + ", currentQty : " + str(currentQty))

                #check selling order
                if len(self.waiting_sell_order) > 0:
                    expectedProfit = (float(current_price) - float(avgCostPrice)) * float(currentQty)
                    if self.check_sell_order(expectedProfit):
                        singleton_data.getInstance().setAllowBuy(True)
                        break
                else :
                    logger.info("[SellThread][run] len(waiting_sell_order) : " + str(len(self.waiting_sell_order)))

                # selling condition
                if float(current_price) > float(avgCostPrice) + float(self.minSellingGap):
                    logger.info("[SellThread][run] current_price > avgCostPrice + " + str(self.minSellingGap))

                    sell_order = self.custom_strategy.exchange.get_orders('Sell')

                    if len(sell_order) == 1:
                        # 3.0 move to settings
                        if float(current_price) + 3.0 > float(sell_order[0]['price'] + float(self.minSellingGap)):
                            # flee away 3$ form first oder_price, amend order
                            # reorder
                            self.waiting_sell_order = self.make_sell_order()
                            logger.info("[SellThread][run] AMEND : waiting_sell_order : " + str(self.waiting_sell_order))
                        else :
                            logger.info("[SellThread][run] The price you ordered has not dropped by more than $ 3 from the current price.")
                    elif len(sell_order) == 0:
                        self.waiting_sell_order = self.make_sell_order()
                        logger.info("[SellThread][run] NEW : waiting_sell_order : " + str(self.waiting_sell_order))

                    elif len(sell_order) > 0:
                        logger.info("[SellThread][run] Abnormal len(sell_order): " + str(len(sell_order)))
                        logger.info("[SellThread][run] Abnormal sell_order: " + str(sell_order))

                # waiting (default:120) secs condition
                elif float(current_price) > float(avgCostPrice):
                    self.wait_cnt += 1

                    if self.wait_cnt > settings.SELLING_WAIT:
                        logger.info("[SellThread][run] stop selling thread because cnt > " + str(settings.SELLING_WAIT))
                        logger.info("[SellThread][run] wait_cnt : " + str(self.wait_cnt))
                        logger.info("[SellThread][run] current_price : " + str(current_price) + ", avgCostPrice : " + str(avgCostPrice) + ", currentQty : " + str(currentQty))

                        break

                # exit sell thread
                else :
                    # check Additional buying #
                    # even though buying in not allow,
                    # ave_price largger that cur_price + averagingDownSize(default : 50$), making ave_down
                    #logger.info("[SellThread][run] current_price + averagingDownSize < avgCostPrice : " + str(float(current_price) + float(self.averagingDownSize) < float(avgCostPrice)))
                    if float(current_price) + float(self.averagingDownSize) < float(avgCostPrice):

                        logger.info("[SellThread][run] ### Additional buying ###")
                        logger.info("[SellThread][run] current_price + averagingDownSize("+str(self.averagingDownSize)+") > avgCostPrice")
                        logger.info("[SellThread][run] current_price : " + str(current_price) + ", avgCostPrice : " + str(avgCostPrice))

                        self.custom_strategy.exchange.cancel_all_orders('All')
                        singleton_data.getInstance().setAllowBuy(True)

                    else :
                        logger.info("[SellThread][run] Not yet additional buying")

                    break

                sleep(1)
            except Exception as ex:
                self.PrintException()
                break

            logger.info("[SellThread][run] wait_cnt : " + str(self.wait_cnt))
            sleep(1)

        self.custom_strategy.exchange.cancel_all_orders('Sell')
        singleton_data.getInstance().setSellThread(False)

    def make_sell_order(self):
        logger.info("[SellThread][make_sell_order] start")

        # if it couldn't oder, retry it
        cancel_retryCnt = 0
        current_order = []

        try:
            while len(current_order) == 0:
                sell_orders = []
                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                #avgCostPrice = self.custom_strategy.exchange.get_avgCostPrice()
                currentQty = self.custom_strategy.exchange.get_currentQty()

                # buy는 냅두고 sell order만으로 바꿔야한다
                # 그래야지 실패하더라도 buy는 냅둬서 다시 주워담을수 있다
                # 모든걸 취소하게되면 팔리지 않을시 최악의 경우에는 기존 buy는 모두 취소되고 selling만을 기다려야 한다
                #self.custom_strategy.exchange.cancel_all_orders('Sell')
                self.custom_strategy.exchange.cancel_all_orders('All')

                if cancel_retryCnt < 10:
                    sell_orders.append({'price': current_price, 'orderQty': currentQty, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})
                else :
                    sell_orders.append({'price': current_price + 0.5, 'orderQty': currentQty, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})

                logger.info("[SellThread][make_sell_order] current_price : " + str(current_price) + ", currentQty : " + str(currentQty))
                current_order = self.custom_strategy.converge_orders([], sell_orders)
                logger.info("[SellThread][make_sell_order] current_order : " + str(current_order))

                # buy는 냅두고 sell order만으로 바꿔야한다
                current_sell_order = self.custom_strategy.exchange.get_orders('Sell')
                logger.info("[SellThread][make_sell_order] current_sell_order : " + str(current_sell_order))

                if len(current_order) == 1:
                    if current_order[0]['ordStatus'] == 'Canceled':
                        cancel_retryCnt += 1
                        logger.info("[SellThread][make_sell_order] order Status == Canceled")
                        logger.info("[SellThread][make_sell_order] reason : " + str(current_order[0]['text']))
                        logger.info("[SellThread][make_sell_order] sell order retry : " + str(cancel_retryCnt))
                        current_order = []
                        sleep(0.2)
                    elif current_order[0]['ordStatus'] == 'New':
                        logger.info("[SellThread][make_sell_order] order Status == New")
                        break
                else:
                    logger.info("[SellThread][make_sell_order] Abnormal Selling current_order length: " + str(len(current_order)))
                    logger.info("[SellThread][make_sell_order] Abnormal Selling current_order : " + str(current_order))
                    logger.info("[SellThread][make_sell_order] Abnormal Selling current_order cancel ")
                    self.custom_strategy.exchange.cancel_all_orders('Sell')
                    logger.info("[SellThread][make_sell_order] retry after Abnormal Selling order")
                    current_order = []

        except Exception as ex:
            self.PrintException()

        return current_order

    def check_sell_order(self, expectedProfit):
        # checking whether or not it's sold
        ret = False

        orders = self.custom_strategy.exchange.get_orders('Sell')
        logger.info("[SellThread][check_sell_order] orders : " + str(orders))

        if len(orders) == 0:
            # selling complete
            logger.info("[SellThread][check_sell_order] selling complete!")
            logger.info("[SellThread][check_sell_order] ######  profit : + " + str(expectedProfit) + "$  ######")
            execute_logger.info("######  profit : + " + str(expectedProfit) + "$  ######")

            self.custom_strategy.exchange.cancel_all_orders('All')
            ret = True
            self.waiting_sell_order = []

        else :
            logger.info("[SellThread][check_sell_order] not yet selling")

        return ret



