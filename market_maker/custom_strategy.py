import os
import pathlib
import sys
from time import sleep
import logging
import pandas as pd

#from market_maker import _settings_base
from market_maker.plot.bitmex_plot import bitmex_plot
from market_maker.market_maker import OrderManager
from market_maker.settings import settings
import threading

LOOP_INTERVAL = 1

logger = logging.getLogger('root')
bitmex_plot = bitmex_plot()

class CustomOrderManager(OrderManager, threading.Thread):
    """A sample order manager for implementing your own custom strategy"""
    def __init__(self):
        super().__init__()
        threading.Thread.__init__(self)
        self.__suspend = False
        self.__exit = False
        self.analysis = pd.DataFrame()
        self.allow_buy = True

    def place_orders(self) -> None:
        # implement your custom strategy here

        buy_orders = []
        sell_orders = []

        # populate buy and sell orders, e.g.
        # buy_orders.append({'price': 999.0, 'orderQty': 100, 'side': "Buy"})
        # sell_orders.append({'price': 1001.0, 'orderQty': 100, 'side': "Sell"})

        self.converge_orders(buy_orders, sell_orders)
    def check_current_strategy(self):
        logger.info("[CustomOrderManager][check_current_strategy] self.analysis['rsi'] " + str(self.analysis['rsi']))
        logger.info("[CustomOrderManager][check_current_strategy] self.analysis['stoch_k'] " + str(self.analysis['stoch_k']))
        logger.info("[CustomOrderManager][check_current_strategy] self.allow_buy " + str(self.allow_buy))
        #self.print_status()

        buy_orders = []
        sell_orders = []

        # buy
        default_Qty = 10
        if self.allow_buy:
            if self.analysis['rsi'][0] < 30.0 and self.analysis['stoch_k'][0] < 30.0:
                logger.info("[CustomOrderManager][check_current_strategy][buy} rsi under 30.0 & stock_k under 30.0")
            #if True:
                current_price = self.exchange.get_instrument()['lastPrice']

                for i in range(1, 21):
                    buy_orders.append({'price': current_price - i + 1, 'orderQty': default_Qty * i, 'side': "Buy"})


                self.converge_orders(buy_orders, [])
                self.allow_buy = False
                logger.info("[CustomOrderManager][check_current_strategy][buy} after self.converge_orders")
                logger.info("[CustomOrderManager][check_current_strategy][buy} self.allow_buy " + str(self.allow_buy))

        # sell # move to thread
        if not self.allow_buy:
            if self.analysis['rsi'][0] > 70.0 and self.analysis['stoch_k'][0] > 70.0:
            #if True:
                logger.info("[CustomOrderManager][check_current_strategy][sell] rsi over 70.0 & stock_k over 70.0")
                self.exchange.cancel_all_orders()

                cnt = 0
                while not self.allow_buy:
                    logger.info("[CustomOrderManager][check_current_strategy][sell] current_price > avgCostPrice")
                    # realized profit
                    current_price = self.exchange.get_instrument()['lastPrice']
                    position = self.exchange.get_position()
                    avgCostPrice = position['avgCostPrice']
                    currentQty = position['currentQty']
                    if current_price > avgCostPrice:
                        logger.info("[CustomOrderManager][check_current_strategy][sell] current_price > avgCostPrice")
                        logger.info("[CustomOrderManager][check_current_strategy][sell] avgCostPrice : " + str(avgCostPrice))
                        logger.info("[CustomOrderManager][check_current_strategy][sell] currentQty : " + str(currentQty))

                        # 주문 모두삭제 & 새로 추가 가 아니라 주문 수정으로 바꿔줄 필요가 있다
                        self.exchange.cancel_all_orders()
                        sell_orders = []
                        sell_orders.append({'price': current_price + 1, 'orderQty': currentQty, 'side': "Sell"})
                        self.converge_orders([], sell_orders)

                        wait = 0
                        while True:
                            wait += 1
                            orders = self.exchange.get_orders()
                            logger.info("[CustomOrderManager][check_current_strategy][sell] orders : " + str(orders))

                            if len(orders) == 0:
                                # 매도 완료!
                                logger.info("[CustomOrderManager][check_current_strategy][sell] len(orders) == 0")
                                self.allow_buy = True
                                break
                            if wait > 10:
                                logger.info("[CustomOrderManager][check_current_strategy][sell] wait > 10")
                                break
                            sleep(1)
                    else :
                        if self.allow_buy:
                            logger.info("[CustomOrderManager][check_current_strategy][sell] else break")
                            break
                        cnt += 1
                        sleep(1)
                        if cnt > 120:
                            logger.info("[CustomOrderManager][check_current_strategy][sell] cnt > 120")
                            self.allow_buy = True
                            break

                self.converge_orders([], sell_orders)

    def run_loop(self):
        logger.info("[CustomOrderManager][run_loop]")

        while True:
            sys.stdout.write("-----\n")
            sys.stdout.flush()

            self.check_file_change()
            sleep(settings.LOOP_INTERVAL)

            # This will restart on very short downtime, but if it's longer,
            # the MM will crash entirely as it is unable to connect to the WS on boot.
            if not self.check_connection():
                logger.error("Realtime data connection unexpectedly closed, restarting.")
                self.restart()

            #self.sanity_check()  # Ensures health of mm - several cut-out points here
            #self.print_status()  # Print skew, delta, etc
            #self.place_orders()  # Creates desired orders and converges to existing orders

            contents = self.exchange.get_instrument()['lastPrice']
            logger.info("[CustomOrderManager][run_loop] test_instrument(lastPrice) : " + str(contents))

            update_required = self.exchange.get_tradeBin1m();
            logger.info("[CustomOrderManager][run_loop] update_required : " + str(update_required))

            if update_required:
                self.analysis = bitmex_plot.plot_update()
                self.check_current_strategy()



    def run(self):
        logger.info("[CustomOrderManager][run]")
        self.run_loop()

def run() -> None:
    order_manager = CustomOrderManager()

    # Try/except just keeps ctrl-c from printing an ugly stacktrace
    try:
        order_manager.start()
        #order_manager.run_loop()
        bitmex_plot.run()

    except (KeyboardInterrupt, SystemExit):
        order_manager.stop()
        sys.exit()

# getApiKey
def setApi():
    script_dir = pathlib.Path(__file__).parent.parent
    #script_dir = os.path.dirname(__file__).parent().parent() #<-- absolute dir the script is in

    rel_path = "client_api\key_secret.txt"
    abs_file_path = os.path.join(script_dir, rel_path)

    r = open(abs_file_path, mode='rt', encoding='utf-8')
    list = r.read().splitlines()
    key = list[0].split('=')[1]
    secret = list[1].split('=')[1]

    #_settings_base.API_KEY = key
    #_settings_base.API_SECRET = secret
    settings.API_KEY = key
    settings.API_SECRET = secret
