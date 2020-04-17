import os
import pathlib
import sys
from time import sleep
import logging

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

    def place_orders(self) -> None:
        # implement your custom strategy here

        buy_orders = []
        sell_orders = []

        # populate buy and sell orders, e.g.
        # buy_orders.append({'price': 999.0, 'orderQty': 100, 'side': "Buy"})
        # sell_orders.append({'price': 1001.0, 'orderQty': 100, 'side': "Sell"})

        self.converge_orders(buy_orders, sell_orders)

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
                bitmex_plot.data_listener()

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
