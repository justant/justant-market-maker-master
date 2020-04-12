import matplotlib.pyplot as plt
import matplotlib.dates as dates
import matplotlib.ticker as ticker
import matplotlib.animation as animation
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np
from matplotlib.dates import date2num
from matplotlib import style
from mpl_finance import candlestick_ohlc as candlestick
from market_maker.utils import log
import time

from market_maker.utils.singleton import ohlc_data

logger = log.setup_custom_logger('root')

flag = False
ticker = 'BTC-USD'
temp_cnt = 0


style.use('fivethirtyeight')

class bitmex_plot():

    def __init__(self):
        logger.info("[bitmex_plot][__init__]")

        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(1, 1, 1)
        self.current_data_cnt = 0;

        self.SMA_FAST = 50
        self.SMA_SLOW = 200
        self.RSI_PERIOD = 14
        self.RSI_AVG_PERIOD = 15
        self.MACD_FAST = 12
        self.MACD_SLOW = 26
        self.MACD_SIGNAL = 9
        self.STOCH_K = 14
        self.STOCH_D = 3
        self.SIGNAL_TOL = 3
        self.Y_AXIS_SIZE = 12

    def run(self):
        logger.info("[bitmex_plot][run]")
        flag = True

        # Prepare plot
        self.fig, (self.ax1) = plt.subplots(1, 1, sharex=True)
        self.ax1.set_ylabel(ticker, size=20)

        #size plot
        self.fig.set_size_inches(15,30)

        self.ani = animation.FuncAnimation(self.fig, self.animate, interval=1000)
        plt.show()

    def animate(self, i):
        cnt = ohlc_data._getInstance().getDataCnt()
        logger.info("[plotThread][animate] cnt " + str(cnt))

        if cnt > self.current_data_cnt:
            self.current_data_cnt = cnt
            logger.info("[plotThread][animate] current_data_cnt " + str(self.current_data_cnt))

            sec_id = ohlc_data._getInstance().getData()

            sec_id_ochl = np.array(pd.DataFrame({'0':date2num(sec_id.index.to_pydatetime()),
                                                 '1':sec_id.open,
                                                 '2':sec_id.close,
                                                 '3':sec_id.high,
                                                 '4':sec_id.low}))
            logger.info("[plotThread][animate] sec_id_ochl " + str(sec_id_ochl))
            analysis = pd.DataFrame(index = sec_id.index)

            #analysis['sma_f'] = sec_id.close.rolling(SMA_FAST).mean()
            #analysis['sma_s'] = sec_id.close.rolling(SMA_SLOW).mean()

            # Plot candles
            self.ax1.clear()
            logger.info("[plotThread][animate] clear")
            candlestick(self.ax1, sec_id_ochl, width=.6/(24*60), colorup='g', colordown='r', alpha=1)

            # Draw Moving Averages
            #analysis.sma_f.plot(ax=ax1, c='r')
            #analysis.sma_s.plot(ax=ax1, c='g')

    def data_listener(self):
        logger.info("[bitmex_plot][data_listener]")
        df = ohlc_data._getInstance().getData()

        logger.info("[plotThread][data_listener] df.to_string() " + df.to_string())