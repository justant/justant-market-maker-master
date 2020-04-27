import linecache
import logging
import sys
import threading
from time import sleep

import settings
from market_maker.utils.singleton import singleton_data

logger = logging.getLogger('root')
exe_logger = logging.getLogger('exception')

class SellThread(threading.Thread):
    def __init__(self, custom_strategy):
        logger.info("[SellThread][run] __init__")
        threading.Thread.__init__(self)
        self.custom_strategy = custom_strategy
        singleton_data.getInstance().setAllowBuy(False)
        singleton_data.getInstance().setSellThread(True)

        # 50.0
        self.averagingDownSize = settings.AVERAGING_DOWN_SIZE
        # 10.0
        self.minSellingGap = settings.MIN_SELLING_GAP

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
        exe_logger.info("[SellThread][run] " + str('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)))

    #def retry_sell(self):
    #def ammend_sell(self):

    def run(self):
        logger.info("[SellThread][run]")
        # Cancel all sell orders
        self.custom_strategy.exchange.cancel_all_orders('Sell')
        self.waiting_sell_order = []
        wait_cnt = 0

        while not singleton_data.getInstance().getAllowBuy():
            try:
                # realized profit
                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                avgCostPrice = self.custom_strategy.exchange.get_avgCostPrice()
                currentQty = self.custom_strategy.exchange.get_currentQty()

                logger.info("[SellThread][run] current_price : " + str(current_price))
                logger.info("[SellThread][run] avgCostPrice : " + str(avgCostPrice))
                logger.info("[SellThread][run] currentQty : " + str(currentQty))

                #check selling order
                if len(self.waiting_sell_order) > 0:
                    expectedProfit = (current_price - avgCostPrice) * currentQty
                    if self.check_sell_order(expectedProfit):
                        singleton_data.getInstance().setAllowBuy(True)
                        break
                else :
                    logger.info("[SellThread][run] len(waiting_sell_order) : " + str(len(self.waiting_sell_order)))

                # selling condition
                if float(current_price) > float(avgCostPrice) + float(self.minSellingGap):
                    logger.info("[SellThread][run] current_price > avgCostPrice + " + str(self.minSellingGap))

                    sell_order = self.custom_strategy.exchange.get_orders('Sell')

                    if len(sell_order) > 0:

                        if float(current_price) + 3.0 > float(sell_order['price']):
                            # flee away 3$ form first oder_price, amend order
                            # reorder
                            self.custom_strategy.exchange.cancel_all_orders('Sell')
                            self.waiting_sell_order = self.make_sell_order()
                            logger.info("[SellThread][run] AMEND : waiting_sell_order : " + str(self.waiting_sell_order))
                        else :
                            logger.info("[SellThread][run] The price you ordered has not dropped by more than $ 3 from the current price.")
                            logger.info("[SellThread][run] wait more")
                    elif len(sell_order) == 0:
                        self.waiting_sell_order = self.make_sell_order()
                        logger.info("[SellThread][run] NEW : waiting_sell_order : " + str(self.waiting_sell_order))

                # waiting (default:120) secs condition
                elif float(current_price) > float(avgCostPrice):
                    wait_cnt += 1

                    if wait_cnt > settings.SELLING_WAIT:
                        logger.info("[SellThread][run] stop selling thread because cnt > " + str(settings.SELLING_WAIT))
                        logger.info("[SellThread][run] wait_cnt : " + str(wait_cnt))
                        logger.info("[SellThread][run] current_price : " + str(current_price))
                        logger.info("[SellThread][run] avgCostPrice : " + str(avgCostPrice))
                        logger.info("[SellThread][run] currentQty : " + str(currentQty))

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
                        logger.info("[SellThread][run] current_price : " + str(current_price))
                        logger.info("[SellThread][run] avgCostPrice : " + str(avgCostPrice))

                        self.custom_strategy.exchange.cancel_all_orders('All')
                        singleton_data.getInstance().setAllowBuy(True)

                    else :
                        logger.info("[SellThread][run] Not yet additional buying")

                    break

                sleep(1)
            except Exception as ex:
                self.PrintException()
                break

            logger.info("[SellThread][run] wait_cnt : " + str(wait_cnt))
            sleep(1)

        singleton_data.getInstance().setSellThread(False)

    def make_sell_order(self):
        logger.info("[SellThread][make_sell_order] start")

        current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
        #avgCostPrice = self.custom_strategy.exchange.get_avgCostPrice()
        currentQty = self.custom_strategy.exchange.get_currentQty()

        # if it couldn't oder, retry it
        cancel_retryCnt = 0
        current_order = []

        try:
            while len(current_order) == 0:
                sell_orders = []

                if cancel_retryCnt < 10:
                    sell_orders.append({'price': current_price, 'orderQty': currentQty, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})
                else :
                    sell_orders.append({'price': current_price + 0.5, 'orderQty': currentQty, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})

                logger.info("[SellThread][make_sell_order] current_price : " + str(current_price) + ", currentQty : " + str(currentQty))
                current_order = self.custom_strategy.converge_orders([], sell_orders)

                if len(current_order) == 1:
                    if current_order[0]['ordStatus'] == 'Canceled':
                        cancel_retryCnt += 1
                        logger.info("[SellThread][make_sell_order] order Status == Canceled")
                        logger.info("[SellThread][make_sell_order] reason : " + str(current_order[0]['text']))
                        logger.info("[SellThread][make_sell_order] sell order retry")
                        current_order = []
                    elif current_order[0]['ordStatus'] == 'New':
                        logger.info("[SellThread][make_sell_order] order Status == New")
                        break
                else:
                    logger.info("[SellThread][make_sell_order] Abnormal Selling current_order length: " + str(len(current_order)))
                    logger.info("[SellThread][make_sell_order] Abnormal Selling current_order : " + str(current_order))
                    logger.info("[SellThread][make_sell_order] Abnormal Selling current_order cancel ")
                    self.custom_strategy.exchange.cancel_all_orders('All')
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
            self.custom_strategy.exchange.cancel_all_orders('All')
            ret = True
            self.waiting_sell_order = []

        else :
            logger.info("[SellThread][check_sell_order] not yet selling")

        return ret



