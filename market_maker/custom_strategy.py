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
from market_maker.utils.telegram import Telegram

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
        self.analysis_15m = pd.DataFrame()
        #self.analysis_30m = pd.DataFrame()

        self.analysis_1m = analysis.get_analysis(True)
        #self.analysis_15m = analysis.get_analysis(True, '5m')
        self.analysis_15m = analysis.get_analysis(True, '15m')
        #self.analysis_30m = analysis.get_analysis(True, '30m')

        self.user_mode = settings.USER_MODE

        #self.telegram = Telegram(self)
        self.telegram_th = Telegram(self)
        self.telegram_th.daemon=True
        self.telegram_th.start()
        singleton_data.instance().setTelegramThread(self.telegram_th)


        position = self.exchange.get_position()

        currentQty = position['currentQty']

        # default : 0, test : 1~n
        #singleton_data.instance().setAveDownCnt(1)

        # 1, 11, 2, 22 condtion is for Testing
        if self.user_mode == 0 or self.user_mode == 111 or self.user_mode == 222:
            if (self.analysis_15m['Direction'] == "Long").bool():
                singleton_data.instance().setMode("Long")
                if abs(currentQty) > 0:
                    singleton_data.instance().setAllowBuy(False)
                else :
                    singleton_data.instance().setAllowBuy(True)
            elif (self.analysis_15m['Direction'] == "Short").bool():
                singleton_data.instance().setMode("Short")
                if abs(currentQty) > 0:
                    singleton_data.instance().setAllowSell(False)
                else :
                    singleton_data.instance().setAllowSell(True)
        # Forced Buying mode
        elif self.user_mode == 1 or self.user_mode == 11:
            logger.info("[strategy] Forced Buying mode")
            singleton_data.instance().setMode("Long")
            singleton_data.instance().setAllowBuy(True)
            singleton_data.instance().setAllowSell(False)

        # Forced Selling mode
        elif self.user_mode == 2 or self.user_mode == 22:
            logger.info("[strategy] Forced Selling mode")
            singleton_data.instance().setMode("Short")
            singleton_data.instance().setAllowBuy(False)
            singleton_data.instance().setAllowSell(True)


        logger.info("[strategy][__init__] getMode() : " + str(singleton_data.instance().getMode()))
        logger.info("[strategy][__init__] getAllowBuy() : " + str(singleton_data.instance().getAllowBuy()))
        logger.info("[strategy][__init__] getAllowSell() : " + str(singleton_data.instance().getAllowSell()))


    def check_addtional_buy(self):
        #should be executed when it is in the normal state
        # 300.0 *  2^n
        p = 2 ** int(singleton_data.instance().getAveDownCnt())
        self.averagingDownSize = settings.AVERAGING_DOWN_SIZE * p

        # check Additional buying #
        current_price = self.exchange.get_instrument()['lastPrice']
        avg_cost_price = self.exchange.get_avgCostPrice()

        if avg_cost_price is None:
            return False

        logger.info("[check_addtional_buy] should be current_price(" + str(current_price) + ") + averagingDownSize(" + str(self.averagingDownSize) + ") < avgCostPrice(" + str(avg_cost_price) + ")")
        if float(current_price) + float(self.averagingDownSize) < float(avg_cost_price):
            logger.info("[check_addtional_buy] Additional buying")

            buy_orders = self.exchange.get_orders('Buy')
            if len(buy_orders) > 0:
                logger.info("[check_addtional_buy] Additional buying fail because remaining buy orders : " + str(buy_orders))

            else :
                aveCnt = singleton_data.instance().getAveDownCnt() + 1
                singleton_data.instance().setAveDownCnt(aveCnt)
                logger.info("[check_addtional_buy] aveCnt : " + str(aveCnt))

                singleton_data.instance().setAllowBuy(True)

                return True

        return False

    def check_addtional_sell(self):
        #should be executed when it is in the normal state
        # 300.0 *  2^n
        p = 2 ** int(singleton_data.instance().getAveDownCnt())
        self.averagingUpSize = settings.AVERAGING_UP_SIZE * p

        # check Additional selling #
        current_price = self.exchange.get_instrument()['lastPrice']
        avg_cost_price = self.exchange.get_avgCostPrice()

        if avg_cost_price is None:
            return False

        logger.info("[check_addtional_sell] should be current_price(" + str(current_price) + ") > avgCostPrice(" + str(avg_cost_price) + ") + avgCostPrice(" + str(self.averagingUpSize) + ")")
        if float(current_price) > float(avg_cost_price) + float(self.averagingUpSize):
            logger.info("[check_addtional_sell] Additional selling")

            sell_orders = self.exchange.get_orders('Sell')
            if len(sell_orders) > 0:
                logger.info("[check_addtional_sell] Additional selling fail because remaining sell orders : " + str(sell_orders))

            else :
                aveCnt = singleton_data.instance().getAveDownCnt() + 1
                singleton_data.instance().setAveDownCnt(aveCnt)
                logger.info("[check_addtional_sell] aveCnt : " + str(aveCnt))

                singleton_data.instance().setAllowSell(True)

                return True

        return False

    def check_current_strategy(self):
        current_price = self.exchange.get_instrument()['lastPrice']
        avgCostPrice = self.exchange.get_avgCostPrice()
        currentQty = self.exchange.get_currentQty()
        orders = self.exchange.get_orders()

        TAG = "[strategy][" + str(singleton_data.instance().getMode()) + "]"

        logger.info(str(TAG) + " current_price : " + str(current_price) + ", avgCostPrice : " + str(avgCostPrice) + ", currentQty : " + str(currentQty))
        logger.info(str(TAG) + " ['rsi'] " + str(self.analysis_1m['rsi'].values[0])[:5] + " + ['stoch_d'] " + str(self.analysis_1m['stoch_d'].values[0])[:5] + " = " + str(self.analysis_1m['rsi'].values[0] + self.analysis_1m['stoch_d'].values[0])[:5])
        logger.info(str(TAG) + " getAllowBuy() " + str(singleton_data.instance().getAllowBuy()) + ", getAllowSell() : " + str(singleton_data.instance().getAllowSell()) + ", len(orders) : " + str(len(orders)))

        # test
        # Short mode -> Long mode
        #singleton_data.instance().setSwitchMode(True)
        #singleton_data.instance().setMode("Long")
        #singleton_data.instance().setAllowBuy(True)
        #singleton_data.instance().setAllowSell(False)

        if singleton_data.instance().getSwitchMode():
            logger.info("[strategy][switch mode] getSwitchMode : True")
            logger.info("[strategy][switch mode] currentQty : " + str(currentQty))
            if (singleton_data.instance().getMode() == "Long" and currentQty < 0) or (singleton_data.instance().getMode() == "Short" and currentQty > 0):
                if singleton_data.instance().isOrderThreadRun():
                    logger.info("[strategy][switch mode] isOrderThreadRun : True")
                else :
                    self.exchange.cancel_all_orders('All')

                    singleton_data.instance().setAllowOrder(True)

                    order_th = None
                    if singleton_data.instance().getMode() == "Long":
                        order_th = OrderThread(self, 'Buy')
                    elif  singleton_data.instance().getMode() == "Short":
                        order_th = OrderThread(self, 'Sell')

                    order_th.daemon = True
                    order_th.start()

            else :
                logger.info("[strategy][switch mode] getSwitchMode : True, but Keep going!")
                singleton_data.instance().setSwitchMode(False)

        # Long Mode
        elif singleton_data.instance().getMode() == "Long":
            if self.user_mode == 222:
                logger.info("[Long Mode] Skip Long Mode, Trading only for Short Mode")
                return

            ##### Buying Logic #####
            # rsi < 30.0 & stoch_d < 20.0
            if self.analysis_1m['rsi'].values[0] < settings.BASIC_DOWN_RSI or self.analysis_1m['stoch_d'].values[0] < settings.BASIC_DOWN_STOCH \
                    or self.analysis_1m['rsi'].values[0] + self.analysis_1m['stoch_d'].values[0] < settings.BASIC_DOWN_RSI + settings.BASIC_DOWN_STOCH \
                    or self.user_mode == 11:

                    if singleton_data.instance().getAllowBuy() and len(orders) == 0:
                        logger.info("[Long Mode][buy] rsi < " + str(settings.BASIC_DOWN_RSI) + ", stoch_d < " + str(settings.BASIC_DOWN_STOCH))
                        net_order.bulk_net_buy(self)
            else:
                ##### Selling Logic #####
                # rsi > 70.0 & stoch_d > 80.0
                if not singleton_data.instance().getAllowBuy():
                    ##### Check Addtional Buy ####
                    if self.check_addtional_buy():
                        return

                    if self.analysis_1m['rsi'].values[0] > settings.BASIC_UP_RSI or self.analysis_1m['stoch_d'].values[0] > settings.BASIC_UP_STOCH \
                            or self.analysis_1m['rsi'].values[0] + self.analysis_1m['stoch_d'].values[0] > settings.BASIC_UP_RSI + settings.BASIC_UP_STOCH:

                        if not self.user_mode == 11:
                            logger.info("[Long Mode][sell] rsi > " + str(settings.BASIC_UP_RSI) + ", stoch_d > " + str(settings.BASIC_UP_STOCH))

                            position = self.exchange.get_position()
                            currentQty = position['currentQty']
                            logger.info("[Long Mode][sell] currentQty : " + str(currentQty))
                            logger.info("[Long Mode][sell] isSellThreadRun() : " + str(singleton_data.instance().isSellThreadRun()))

                            if currentQty > 0 and not singleton_data.instance().isSellThreadRun():
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
                                singleton_data.instance().setAllowBuy(True)

        # Short Mode
        elif singleton_data.instance().getMode() == "Short":
            if self.user_mode == 111:
                logger.info("[Short Mode] Skip Short Mode, Trading only for Long Mode")
                return

            ##### Selling Logic #####
            # rsi > 70.0 & stoch_d > 80.0
            if singleton_data.instance().getAllowSell() and len(orders) == 0:
                if self.analysis_1m['rsi'].values[0] > settings.BASIC_UP_RSI or self.analysis_1m['stoch_d'].values[0] > settings.BASIC_UP_STOCH \
                        or self.analysis_1m['rsi'].values[0] + self.analysis_1m['stoch_d'].values[0] > settings.BASIC_UP_RSI + settings.BASIC_UP_STOCH \
                        or self.user_mode == 22:
                    logger.info("[Short Mode][sell] rsi > " + str(settings.BASIC_UP_RSI)+", stoch_d > " + str(settings.BASIC_UP_STOCH))
                    net_order.bulk_net_sell(self)

            else :
                ##### Buying Logic #####
                # rsi < 30.0 & stoch_d < 20.0

                if not singleton_data.instance().getAllowSell():
                    ##### Check Addtional Sell ####
                    if self.check_addtional_sell():
                        return

                    if self.analysis_1m['rsi'].values[0] < settings.BASIC_DOWN_RSI or self.analysis_1m['stoch_d'].values[0] < settings.BASIC_DOWN_STOCH \
                            or self.analysis_1m['rsi'].values[0] + self.analysis_1m['stoch_d'].values[0] < settings.BASIC_DOWN_RSI + settings.BASIC_DOWN_STOCH:

                            if not self.user_mode == 22:
                                logger.info("[Short Mode][buy] rsi < " + str(settings.BASIC_DOWN_RSI) + ", stoch_d < " + str(settings.BASIC_DOWN_STOCH))

                                position = self.exchange.get_position()
                                currentQty = position['currentQty']
                                logger.info("[Short Mode][buy] currentQty : " + str(currentQty))
                                logger.info("[Short Mode][buy] isBuyThreadRun() : " + str(singleton_data.instance().isBuyThreadRun()))

                                if currentQty < 0 and not singleton_data.instance().isBuyThreadRun():
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
                                    singleton_data.instance().setAllowSell(True)



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

            update_1m_required = self.exchange.get_tradeBin('1m')

            if update_1m_required:
                logger.info("----------------------------------------------------------------------------")
                logger.info("[CustomOrderManager][run_loop] update_1m_required : " + str(update_1m_required))
                update_5m_required = self.exchange.get_tradeBin('5m')

                #if update_5m_required and (self.user_mode == 0 or self.user_mode == 111 or self.user_mode == 222):
                # TEST
                if update_1m_required and (self.user_mode == 0 or self.user_mode == 111 or self.user_mode == 222):
                    logger.info("[CustomOrderManager][run_loop] update_5m_required : " + str(update_5m_required))

                    #self.analysis_15m = analysis.get_analysis(True, '5m')
                    self.analysis_15m = analysis.get_analysis(True, '15m')

                    if ((self.analysis_15m['Direction'] == "Long").bool() and singleton_data.instance().getMode() == "Short")\
                            or ((self.analysis_15m['Direction'] == "Short").bool() and singleton_data.instance().getMode() == "Long"):
                        singleton_data.instance().setSwitchMode(True)

                        if (self.analysis_15m['Direction'] == "Long").bool():
                            singleton_data.instance().setMode("Long")
                            singleton_data.instance().setAllowBuy(True)
                            singleton_data.instance().setAllowSell(False)
                            singleton_data.instance().sendTelegram("Switch from Short to Long")

                        elif (self.analysis_15m['Direction'] == "Short").bool():
                            singleton_data.instance().setMode("Short")
                            singleton_data.instance().setAllowBuy(False)
                            singleton_data.instance().setAllowSell(True)
                            singleton_data.instance().sendTelegram("Switch from Long to Short")
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
        logger.info("[CustomOrderManager][run] except")

        singleton_data.instance().sendTelegram("오류로 인해 시스템 종료!!")
        #order_manager.stop()
        sys.exit()