import os
import pathlib
import sys
from time import sleep
import pandas as pd

#from market_maker import _settings_base
from market_maker.order import net_order
from market_maker.order.buy_thread import BuyThread
from market_maker.order.order_thread import OrderThread
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
        self.analysis_1m = pd.DataFrame()
        self.analysis_30m = pd.DataFrame()

        self.analysis_1m = analysis.get_analysis(True)
        self.analysis_30m = analysis.get_analysis(True, '30m')

        self.user_mode = settings.USER_MODE

        position = self.exchange.get_position()
        currentQty = position['currentQty']

        # default : 0, test : 1~n
        #singleton_data.getInstance().setAveDownCnt(1)

        # 1, 11, 2, 22 condtion is for Testing
        if self.user_mode == 0:
            if (self.analysis_30m['Direction'] == "Long").bool():
                singleton_data.instance().setMode("Buy")
                if abs(currentQty) > 0:
                    singleton_data.getInstance().setAllowBuy(False)
                else :
                    singleton_data.getInstance().setAllowBuy(True)
            elif (self.analysis_30m['Direction'] == "Short").bool():
                singleton_data.instance().setMode("Sell")
                if abs(currentQty) > 0:
                    singleton_data.getInstance().setAllowSell(False)
                else :
                    singleton_data.getInstance().setAllowSell(True)
        # Forced Buying mode
        elif self.user_mode == 1 or self.user_mode == 11:
            logger.info("[strategy] Forced Buying mode")
            singleton_data.instance().setMode("Buy")
            singleton_data.getInstance().setAllowBuy(True)
            singleton_data.getInstance().setAllowSell(False)

        # Forced Selling mode
        elif self.user_mode == 2 or self.user_mode == 22:
            logger.info("[strategy] Forced Selling mode")
            singleton_data.instance().setMode("Sell")
            singleton_data.getInstance().setAllowBuy(False)
            singleton_data.getInstance().setAllowSell(True)


        logger.info("[strategy][__init__] getMode() : " + str(singleton_data.getInstance().getMode()))
        logger.info("[strategy][__init__] getAllowBuy() : " + str(singleton_data.getInstance().getAllowBuy()))
        logger.info("[strategy][__init__] getAllowSell() : " + str(singleton_data.getInstance().getAllowSell()))

    def check_current_strategy(self):
        current_price = self.exchange.get_instrument()['lastPrice']
        avgCostPrice = self.exchange.get_avgCostPrice()
        currentQty = self.exchange.get_currentQty()

        TAG = "[strategy][" + str(singleton_data.instance().getMode()) + "]"

        logger.info(str(TAG) + " current_price : " + str(current_price) + ", avgCostPrice : " + str(avgCostPrice) + ", currentQty : " + str(currentQty))
        logger.info(str(TAG) + " ['rsi'] " + str(self.analysis_1m['rsi'].values[0])[:5] + ", ['stoch_d'] " + str(self.analysis_1m['stoch_d'].values[0])[:5])

        logger.info(str(TAG) + " rsi + stoch_d : " + str(self.analysis_1m['rsi'].values[0] + self.analysis_1m['stoch_d'].values[0])[:5])
        logger.info(str(TAG) + " getAllowBuy() " + str(singleton_data.getInstance().getAllowBuy()) + ", getAllowSell() : " + str(singleton_data.getInstance().getAllowSell()))

        orders = self.exchange.get_orders()
        logger.info(str(TAG) + " len(orders) : " + str(len(orders)))

        # test
        # Sell mode -> Buy mode
        #singleton_data.instance().setSwitchMode(False)
        #singleton_data.instance().setMode("Sell")
        #singleton_data.getInstance().setAllowBuy(True)
        #singleton_data.getInstance().setAllowSell(True)

        if singleton_data.instance().getSwitchMode():
            logger.info("[strategy][switch mode] getSwitchMode : True")
            logger.info("[strategy][switch mode] currentQty : " + str(currentQty))
            if (singleton_data.instance().getMode() == "Buy" and currentQty < 0) or (singleton_data.instance().getMode() == "Sell" and currentQty > 0):
                if singleton_data.getInstance().isOrderThreadRun():
                    logger.info("[strategy][switch mode] isOrderThreadRun : True")
                else :
                    self.exchange.cancel_all_orders('All')

                    singleton_data.getInstance().setAllowOrder(True)
                    order_th = OrderThread(self, singleton_data.instance().getMode())
                    order_th.daemon = True
                    order_th.start()

            else :
                logger.info("[strategy][switch mode] getSwitchMode : True, but Keep going!")
                singleton_data.instance().setSwitchMode(False)

        # Long Mode
        elif singleton_data.instance().getMode() == "Buy":

            ##### Buying Logic #####
            # rsi < 30.0 & stoch_d < 20.0
            if singleton_data.getInstance().getAllowBuy() and len(orders) == 0:
            #if True:
                if self.analysis_1m['rsi'].values[0] < settings.BASIC_DOWN_RSI or self.analysis_1m['stoch_d'].values[0] < settings.BASIC_DOWN_STOCH \
                        or self.analysis_1m['rsi'].values[0] + self.analysis_1m['stoch_d'].values[0] < settings.BASIC_DOWN_RSI + settings.BASIC_DOWN_STOCH\
                        or self.user_mode == 11:

                    logger.info("[Long Mode][buy] rsi < " + str(settings.BASIC_DOWN_RSI) + ", stoch_d < " + str(settings.BASIC_DOWN_STOCH))
                    net_order.net_buy(self)

            ##### Selling Logic #####
            # rsi > 70.0 & stoch_d > 80.0
            elif not singleton_data.getInstance().getAllowBuy():
                if self.analysis_1m['rsi'].values[0] > settings.BASIC_UP_RSI or self.analysis_1m['stoch_d'].values[0] > settings.BASIC_UP_STOCH \
                        or self.analysis_1m['rsi'].values[0] + self.analysis_1m['stoch_d'].values[0] > settings.BASIC_UP_RSI + settings.BASIC_UP_STOCH:
                    logger.info("[Long Mode][sell] rsi > " + str(settings.BASIC_UP_RSI) + ", stoch_d > " + str(settings.BASIC_UP_STOCH))

                    position = self.exchange.get_position()
                    currentQty = position['currentQty']
                    logger.info("[Long Mode][sell] currentQty : " + str(currentQty))
                    logger.info("[Long Mode][sell] isSellThreadRun() : " + str(singleton_data.getInstance().isSellThreadRun()))

                    if currentQty > 0 and not singleton_data.getInstance().isSellThreadRun():
                        sell_th = SellThread(self)
                        sell_th.daemon=True
                        sell_th.start()

                    # even if wait for buying after ordering, it would be no quentity.
                    # swtich to buying mode
                    elif currentQty == 0:
                        logger.info("[Long Mode][sell] currentQty == 0 ")
                        logger.info("[Long Mode][sell] ### switch mode from selling to buying ###")
                        logger.info("[Long Mode][sell] cancel all buying order")
                        self.exchange.cancel_all_orders('All')
                        singleton_data.getInstance().setAllowBuy(True)

        # Short Mode
        elif singleton_data.instance().getMode() == "Sell":
            ##### Buying Logic #####
            # rsi < 30.0 & stoch_d < 20.0
            if not singleton_data.getInstance().getAllowSell():
                if self.analysis_1m['rsi'].values[0] < settings.BASIC_DOWN_RSI or self.analysis_1m['stoch_d'].values[0] < settings.BASIC_DOWN_STOCH \
                    or self.analysis_1m['rsi'].values[0] + self.analysis_1m['stoch_d'].values[0] < settings.BASIC_DOWN_RSI + settings.BASIC_DOWN_STOCH:

                    logger.info("[Short Mode][buy] rsi < " + str(settings.BASIC_DOWN_RSI) + ", stoch_d < " + str(settings.BASIC_DOWN_STOCH))

                    position = self.exchange.get_position()
                    currentQty = position['currentQty']
                    logger.info("[Short Mode][buy] currentQty : " + str(currentQty))
                    logger.info("[Short Mode][buy] isBuyThreadRun() : " + str(singleton_data.getInstance().isBuyThreadRun()))

                    if currentQty < 0 and not singleton_data.getInstance().isBuyThreadRun():
                        buy_th = BuyThread(self)
                        buy_th.daemon=True
                        buy_th.start()

                    # even if wait for buying after ordering, it would be no quentity.
                    # swtich to buying mode
                    elif currentQty == 0:
                        logger.info("[Short Mode][buy] currentQty == 0 ")
                        logger.info("[Short Mode][buy] ### switch mode from buying to selling ###")
                        logger.info("[Short Mode][buy] cancel all selling order")
                        self.exchange.cancel_all_orders('All')
                        singleton_data.getInstance().setAllowSell(True)

            ##### Selling Logic #####p
            # rsi > 70.0 & stoch_d > 80.0
            elif singleton_data.getInstance().getAllowSell() and len(orders) == 0:
                if self.analysis_1m['rsi'].values[0] > settings.BASIC_UP_RSI or self.analysis_1m['stoch_d'].values[0] > settings.BASIC_UP_STOCH \
                        or self.analysis_1m['rsi'].values[0] + self.analysis_1m['stoch_d'].values[0] > settings.BASIC_UP_RSI + settings.BASIC_UP_STOCH\
                        or self.user_mode == 22:
                    logger.info("[Short Mode][sell] rsi > " + str(settings.BASIC_UP_RSI)+", stoch_d > " + str(settings.BASIC_UP_STOCH))
                    net_order.net_sell(self)

    def run_loop(self):
        logger.info("[CustomOrderManager][run_loop]")

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

            update_1m_required = self.exchange.get_tradeBin('1m');

            if update_1m_required:
                logger.info("----------------------------------------------------------------------------")
                logger.info("[CustomOrderManager][run_loop] update_1m_required : " + str(update_1m_required))
                update_5m_required = self.exchange.get_tradeBin('5m');

                if update_5m_required and self.user_mode == 0 :
                    logger.info("[CustomOrderManager][run_loop] update_5m_required : " + str(update_5m_required))

                    self.analysis_30m = analysis.get_analysis(True, '30m')

                    if ((self.analysis_30m['Direction'] == "Long").bool() and singleton_data.instance().getMode() == "Sell")\
                            or ((self.analysis_30m['Direction'] == "Short").bool() and singleton_data.instance().getMode() == "Buy"):
                        singleton_data.instance().setSwitchMode(True)

                        if (self.analysis_30m['Direction'] == "Long").bool():
                            singleton_data.instance().setMode("Buy")
                            singleton_data.getInstance().setAllowBuy(True)
                            singleton_data.getInstance().setAllowSell(False)
                        elif (self.analysis_30m['Direction'] == "Short").bool():
                            singleton_data.instance().setMode("Sell")
                            singleton_data.getInstance().setAllowBuy(False)
                            singleton_data.getInstance().setAllowSell(True)
                    else:
                        singleton_data.instance().setSwitchMode(False)

                if PLOT_RUNNING:
                    self.analysis_1m = bitmex_plot.plot_update()
                else :
                    self.analysis_1m = analysis.get_analysis(True, '1m')

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