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

class OrderThread(threading.Thread):
    def __init__(self, custom_strategy, order_type):
        logger.info("[OrderThread][run] __init__")
        threading.Thread.__init__(self)
        self.custom_strategy = custom_strategy
        self.order_type = order_type
        self.lastClosePrice = self.custom_strategy.analysis_15m['Close']

        singleton_data.instance().setOrderThread(True)

        currentQty = self.custom_strategy.exchange.get_currentQty()
        logger.info("[OrderThread][run] currentQty : " + str(currentQty))

        self.waiting_order = {}

    def PrintException(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        logger.info("[OrderThread][run] " + str('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)))
        execept_logger.info("[OrderThread][run] " + str('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)))

    def run(self):
        logger.info("[OrderThread][run]")

        while singleton_data.instance().getAllowOrder():
            try:
                # realized profit
                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                avgCostPrice = self.custom_strategy.exchange.get_avgCostPrice()
                currentQty = self.custom_strategy.exchange.get_currentQty()

                logger.info("[OrderThread][run] current_price : " + str(current_price) + ", avgCostPrice : " + str(avgCostPrice) + ", currentQty : " + str(currentQty))

                if len(self.waiting_order) == 0:
                    # ordering condition
                    self.waiting_order = self.make_order()
                    logger.info("[OrderThread][run] NEW : waiting_order : " + str(self.waiting_order))

                #check ordering
                elif len(self.waiting_order) > 0:
                    if self.check_order():
                        singleton_data.instance().setAllowOrder(False)
                        break

                else :
                    logger.info("[OrderThread][run] len(waiting_order) : " + str(len(self.waiting_order)))
                    logger.info("[OrderThread][run] waiting_order : " + str(self.waiting_order))

                sleep(1)
            except Exception as ex:
                self.PrintException()
                break

            sleep(1)

        # Cancel all orders
        try:
            self.custom_strategy.exchange.cancel_all_orders('All')
        except Exception as ex:
            self.PrintException()
        finally:
            singleton_data.instance().setOrderThread(False)
            singleton_data.instance().setSwitchMode(False)

    def make_order(self):
        logger.info("[OrderThread][make_order] start")

        # if it couldn't oder, retry it
        cancel_retryCnt = 0
        current_order = {}

        try:
            #self.custom_strategy.exchange.cancel_all_orders('All')

            while len(current_order) == 0:
                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                avgCostPrice = self.custom_strategy.exchange.get_avgCostPrice()
                currentQty = abs(self.custom_strategy.exchange.get_currentQty())

                logger.info("[OrderThread][make_order] current_price : " + str(current_price) + ", currentQty : " + str(currentQty))
                if cancel_retryCnt < 3:
                    current_order = self.custom_strategy.exchange.create_order(self.order_type, currentQty, current_price)
                else :
                    #orders.append({'price': current_price + 0.5, 'orderQty': currentQty, 'side': "Buy", 'execInst': "ParticipateDoNotInitiate"})
                    if self.order_type == 'Buy':
                        current_order = self.custom_strategy.exchange.create_order(self.order_type, currentQty, current_price - 0.5)
                    elif self.order_type == 'Sell':
                        current_order = self.custom_strategy.exchange.create_order(self.order_type, currentQty, current_price + 0.5)

                logger.info("[OrderThread][make_order] current_order : " + str(current_order))

                if current_order['ordStatus'] == 'Canceled':
                    cancel_retryCnt += 1
                    logger.info("[OrderThread][make_order] order Status == Canceled")
                    logger.info("[OrderThread][make_order] reason : " + str(current_order['text']))
                    logger.info("[OrderThread][make_order] order retry : " + str(cancel_retryCnt))
                    current_order = {}
                    sleep(0.5)

                elif current_order['ordStatus'] == 'New':
                    logger.info("[OrderThread][make_order] order Status == New")

                    break
                else :
                    logger.info("[OrderThread][make_order] Abnormal ordStatus : " + str(current_order['ordStatus']))

        except Exception as ex:
            self.PrintException()

        return current_order

    def check_order(self):
        # checking whether or not it's sold
        ret = False

        orders = self.custom_strategy.exchange.get_orders('All')
        logger.info("[OrderThread][check_order] orders : " + str(orders))

        if len(orders) == 0:
            # ordering complete
            logger.info("[OrderThread][check_order] ordering complete!")
            self.custom_strategy.exchange.cancel_all_orders('All')

            ret = True
            self.waiting_order = {}

        elif len(orders) == 1:
            current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
            logger.info("[OrderThread][check_order] orders : " + str(orders))

            if abs(float(current_price) - float(orders[0]['price'])) > 3.0:
                logger.info("[OrderThread][check_order] current_price(" + str(current_price) +") - order_price(" + str(orders[0]['price']) + " plus minus 3")
                self.waiting_order = {}
                self.custom_strategy.exchange.cancel_all_orders('All')
                ret = False

            else :
                logger.info("[OrderThread][check_order] The price you ordered has not dropped by more than $ 3 from the current price.")

            logger.info("[OrderThread][check_order] not yet ordering")

        return ret



