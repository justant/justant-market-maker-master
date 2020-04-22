import linecache
import logging
import sys
import threading
from time import sleep

import settings
from market_maker.market_maker import ExchangeInterface
from market_maker.utils.singleton import singleton_data

logger = logging.getLogger('root')

class SellThread(threading.Thread):
    def __init__(self, custom_strategy):
        logger.info("[SellThread][run] __init__")
        threading.Thread.__init__(self)
        self.custom_strategy = custom_strategy
        singleton_data.getInstance().setAllowBuy(False)
        singleton_data.getInstance().setSellThread(True)

        # move to setting value
        self.averagingDownSize = 50.0
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

    #def retry_sell(self):
    #def ammend_sell(self):

    def run(self):
        logger.info("[SellThread][run]")
        #logger.info("[SellThread][run] rsi over 70.0 & stock_k over 70.0")

        wait_cnt = 0
        while not singleton_data.getInstance().getAllowBuy():
            try:
                # realized profit
                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                position = self.custom_strategy.exchange.get_position()
                avgCostPrice = position['avgCostPrice']
                currentQty = position['currentQty']

                if current_price > avgCostPrice:
                    logger.info("[SellThread][run] current_price > avgCostPrice")
                    logger.info("[SellThread][run] avgCostPrice : " + str(avgCostPrice))
                    logger.info("[SellThread][run] currentQty : " + str(currentQty))

                    # 주문 모두삭제 & 새로 추가 가 아니라 주문 수정으로 바꿔줄 필요가 있다
                    self.custom_strategy.exchange.cancel_all_orders()

                    # if it couldn't oder, retry it
                    self.cancel_retryCnt = 0
                    self.ret = []
                    while len(self.ret) == 0:
                        current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                        sell_orders = []

                        if(self.cancel_retryCnt < 10):
                            sell_orders.append({'price': current_price, 'orderQty': currentQty, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})
                        else :
                            sell_orders.append({'price': current_price + 0.5, 'orderQty': currentQty, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})

                        logger.info("[SellThread][run] sell order current_price : " + str(current_price) + ", currentQty : " + str(currentQty))
                        self.ret = self.custom_strategy.converge_orders([], sell_orders)

                        if len(self.ret) == 1:
                            if self.ret[0]['ordStatus'] == 'Canceled':
                                self.cancel_retryCnt += 1
                                logger.info("[SellThread][run] order Status == Canceled")
                                logger.info("[SellThread][run] reason : " + str(self.ret[0]['text']))
                                logger.info("[SellThread][run] sell order retry")
                                self.ret = []
                            elif self.ret[0]['ordStatus'] == 'New':
                                logger.info("[SellThread][run] order Status == New")
                                break
                        else:
                            logger.info("[SellThread][run] Abnormal Selling order length: " + str(len(self.ret)))
                            logger.info("[SellThread][run] Abnormal Selling order : " + str(self.ret))
                            logger.info("[SellThread][run] Abnormal Selling order cancel ")
                            self.custom_strategy.exchange.cancel_all_orders()
                            logger.info("[SellThread][run] retry after Abnormal Selling order")
                            self.ret = []

                        sleep(0.1)

                    # monitoring and waiting until selling
                    # flee away 3$ form first oder_price, amend order
                    #order_price = float(self.ret[0]['price'])
                    #current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']

                    logger.info("[SellThread][run] waiting 20 secs")
                    sleep(20)
                    orders = self.custom_strategy.exchange.get_orders()
                    logger.info("[SellThread][run] start monitoring orders : " + str(orders))

                    if len(orders) == 0:
                        # selling complete
                        logger.info("[SellThread][run] selling complete, len(orders) == 0")
                        logger.info("[SellThread][run] ###### price : " + str(current_price) + ",avgCostPrice, : + " + str(avgCostPrice) + ",quantity : " + str(currentQty) + " ######")
                        singleton_data.getInstance().setAllowBuy(True)
                        break
                    else :
                        logger.info("[SellThread][run] not selling after monitoring 10 seconds, order : " + str(orders))
                        self.custom_strategy.exchange.cancel_all_orders()
                        logger.info("[SellThread][run] not selling after monitoring 10 seconds, cancel order ")


                wait_cnt += 1
                # 1) current price is more than average prive + 100$
                # 2) after 2mins
                # break
                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                position = self.custom_strategy.exchange.get_position()
                avgCostPrice = position['avgCostPrice']


                if wait_cnt > 120:
                    logger.info("[SellThread][run] stop selling thread because cnt > 120")
                    logger.info("[SellThread][run] wait_cnt : " + str(wait_cnt))
                    logger.info("[SellThread][run] current_price : " + str(current_price))
                    logger.info("[SellThread][run] avgCostPrice : " + str(avgCostPrice))
                    logger.info("[SellThread][run] currentQty : " + str(position['currentQty']))

                    break

                # Additional buying #
                # even though buying in not allow,
                # ave_price largger that cur_price + averagingDownSize(default : 100$), making ave_down
                elif float(current_price) > float(avgCostPrice) + self.averagingDownSize:

                    logger.info("[SellThread][run] ### Additional buying ###")
                    logger.info("[SellThread][run] current_price > avgCostPrice + averagingDownSize("+str(self.averagingDownSize)+")")
                    logger.info("[SellThread][run] current_price : " + str(current_price))
                    logger.info("[SellThread][run] avgCostPrice : " + str(avgCostPrice))

                    singleton_data.getInstance().setAllowBuy(True)

                    break
            except Exception as ex:
                self.PrintException()
                break

            logger.info("[SellThread][run] wait_cnt : " + str(wait_cnt))
            sleep(1)

        singleton_data.getInstance().setSellThread(False)




