import logging
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

        #self.allow_stop_loss = False
        #self.exchange = ExchangeInterface(settings.DRY_RUN)

    def run(self):
        logger.info("[SellThread][run]")
        #logger.info("[SellThread][run] rsi over 70.0 & stock_k over 70.0")

        wait_cnt = 0
        while not singleton_data.getInstance().getAllowBuy():
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

                current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                sell_orders = []
                sell_orders.append({'price': current_price, 'orderQty': currentQty, 'side': "Sell"})
                logger.info("[SellThread][run] sell order current_price : " + str(current_price) + ", currentQty : " + str(currentQty))

                ret = self.custom_strategy.converge_orders([], sell_orders)
                logger.info("[SellThread][run] sell order result : " + str(ret))
                orders = self.custom_strategy.exchange.get_orders()
                logger.info("[SellThread][run] orders information right after execution : " + str(orders))

                # if not order, retry
                '''
                while True:
                    orders = self.custom_strategy.exchange.get_orders()
                    if len(orders) > 0:
                        logger.info("[SellThread][run] selling order complete : " + str(orders))
                        break

                    current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
                    sell_orders = []
                    sell_orders.append({'price': current_price, 'orderQty': currentQty, 'side': "Sell"})
                    logger.info("[SellThread][run] if not order, retry, current_price : " + str(current_price) + ", currentQty : " + str(currentQty))
                    logger.info("[SellThread][run] before retry orders : " + str(orders))
                    ret = self.custom_strategy.converge_orders([], sell_orders)
                    logger.info("[SellThread][run] ret : " + str(ret))
                    sleep(1)
                '''

                # monitoring and waiting until selling
                sleep(20)
                orders = self.custom_strategy.exchange.get_orders()
                logger.info("[SellThread][run] start monitoring orders : " + str(orders))

                if len(orders) == 0:
                    # selling complete
                    logger.info("[SellThread][run] selling complete, len(orders) == 0")
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

            if wait_cnt > 120 or current_price > avgCostPrice + 100:
                logger.info("[SellThread][run] stop selling thread because cnt > 120 or current_price > avgCostPrice + 100")
                logger.info("[SellThread][run] stop selling thread wait_cnt : " + str(wait_cnt))
                logger.info("[SellThread][run] stop selling thread current_price > avgCostPrice + 100 : " + str(current_price > avgCostPrice + 100))
                singleton_data.getInstance().setAllowBuy(True)
                break

            logger.info("[SellThread][run] wait_cnt : " + str(wait_cnt))
            sleep(1)

        singleton_data.getInstance().setSellThread(False)




