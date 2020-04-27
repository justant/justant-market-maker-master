import os
import pathlib
import sys
from time import sleep
import pandas as pd

#from market_maker import _settings_base
from market_maker.order import net_order
from market_maker.order.sell_thread import SellThread
from market_maker.plot import analysis
from market_maker.plot.bitmex_plot import bitmex_plot
from market_maker.market_maker import OrderManager
from market_maker.settings import settings
import threading
from market_maker.utils.singleton import singleton_data
from market_maker.utils import log

LOOP_INTERVAL = 1

logger = log.setup_custom_logger('root')

bitmex_plot = bitmex_plot()

PLOT_RUNNING = settings.PLOT_RUNNING

class CustomOrderManager(OrderManager, threading.Thread):
    """A sample order manager for implementing your own custom strategy"""
    def __init__(self):
        super().__init__()
        threading.Thread.__init__(self)
        self.__suspend = False
        self.__exit = False
        self.analysis = pd.DataFrame()

        position = self.exchange.get_position()
        currentQty = position['currentQty']

        # False condtion is for Testing
        if(True):
            if currentQty > 0:
                singleton_data.getInstance().setAllowBuy(False)
                logger.info("[strategy] init setAllowBuy : False")
            else :
                singleton_data.getInstance().setAllowBuy(True)
                logger.info("[strategy] init setAllowBuy : True")
        else :
            singleton_data.getInstance().setAllowBuy(True)

    def check_current_strategy(self):
        current_price = self.exchange.get_instrument()['lastPrice']
        avgCostPrice = self.exchange.get_avgCostPrice()
        currentQty = self.exchange.get_currentQty()

        logger.info("[strategy] current_price(1) : " + str(current_price))
        logger.info("[strategy] avgCostPrice : " + str(avgCostPrice))
        logger.info("[strategy] currentQty : " + str(currentQty))

        logger.info("[strategy] ['rsi'] " + str(self.analysis['rsi'].values[0])[:5])
        #logger.info("[strategy] ['stoch_k'] " + str(self.analysis['stoch_k'].values[0]))
        logger.info("[strategy] ['stoch_d'] " + str(self.analysis['stoch_d'].values[0])[:5])
        logger.info("[strategy] rsi + stoch_d : " + str(self.analysis['rsi'].values[0] + self.analysis['stoch_d'].values[0])[:5])
        logger.info("[strategy] getAllowBuy() " + str(singleton_data.getInstance().getAllowBuy()))

        orders = self.exchange.get_orders()
        #logger.info("[CustomOrderManager] before buying orders : " + str(orders))
        logger.info("[strategy] len(orders) : " + str(len(orders)))

        ##### Buying Logic #####
        # rsi < 30.0 & stoch_d < 20.0
        if singleton_data.getInstance().getAllowBuy() and len(orders) == 0:
            if self.analysis['rsi'].values[0] < 30.0 or self.analysis['stoch_d'].values[0] < 20.0 or self.analysis['rsi'].values[0] + self.analysis['stoch_d'].values[0] < 50.0:
            #if True: # for test
                logger.info("[strategy][buy] rsi < 30.0, stoch_d < 20.0")
                net_order.net_buy(self)

        ##### Selling Logic #####
        # rsi > 70.0 & stoch_d > 80.0
        if not singleton_data.getInstance().getAllowBuy():
            if self.analysis['rsi'].values[0] > 70.0 or self.analysis['stoch_d'].values[0] > 80.0 or self.analysis['rsi'].values[0] + self.analysis['stoch_d'].values[0] > 150.0:
            #if True: # for test
                logger.info("[strategy][sell] rsi > 70.0, stoch_d > 80.0")

                position = self.exchange.get_position()
                currentQty = position['currentQty']
                logger.info("[strategy][sell] currentQty : " + str(currentQty))
                logger.info("[strategy][sell] isSellThreadRun() : " + str(singleton_data.getInstance().isSellThreadRun()))

                #test
                #if(not singleton_data.getInstance().isSellThreadRun()):
                if currentQty > 0 and not singleton_data.getInstance().isSellThreadRun():
                    sell_th = SellThread(self)
                    sell_th.daemon=True
                    sell_th.start()

                # even if wait for buying after ordering, it would be no quentity.
                # swtich to buying mode
                elif currentQty == 0:
                    logger.info("[strategy][sell] currentQty == 0 ")
                    logger.info("[strategy][sell] ### switch mode from selling to buying ###")
                    logger.info("[strategy][sell] cancel all buying order")
                    self.exchange.cancel_all_orders('All')
                    singleton_data.getInstance().setAllowBuy(True)

    def run_loop(self):
        logger.info("[CustomOrderManager][run_loop]")

        self.analysis = analysis.get_analysis(True)
        self.check_current_strategy()

        while True:

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

            update_required = self.exchange.get_tradeBin1m();

            if update_required:
                logger.info("----------------------------------------------------------------------------")
                #logger.info("[CustomOrderManager][run_loop] update_required : " + str(update_required))

                if PLOT_RUNNING:
                    self.analysis = bitmex_plot.plot_update()
                else :
                    self.analysis = analysis.get_analysis(True)
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
        logger.info("[CustomOrderManager][run] PLOT_RUNNING : " + str(PLOT_RUNNING))
        if PLOT_RUNNING:
            bitmex_plot.run()

    except (KeyboardInterrupt, SystemExit):
        order_manager.stop()
        sys.exit()