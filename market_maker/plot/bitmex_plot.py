import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as dates
import matplotlib.ticker as ticker
import matplotlib.animation as animation
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np
import talib as ta
from matplotlib.dates import date2num
from matplotlib import style
from mpl_finance import candlestick_ohlc as candlestick
from market_maker.utils import log
import time

from market_maker.utils.singleton import singleton_data

logger = log.setup_custom_logger('root')

ticker = 'BTC-USD'

style.use('fivethirtyeight')

class bitmex_plot():

    def __init__(self):
        for i in range(0, 5):
            logger.info("==============================================================================================================")
        logger.info("[bitmex_plot][__init__]")

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
        self.LINE_WIDTH = 1

        self.update_flag = False

    def run(self):
        logger.info("[bitmex_plot][run]")

        sec_id = singleton_data.getInstance().getOHLC_data()

        self.sec_id_ochl = np.array(pd.DataFrame({'0':date2num(sec_id.index),#.to_pydatetime()),
                                             '1':sec_id.open,
                                             '2':sec_id.close,
                                             '3':sec_id.high,
                                             '4':sec_id.low}))

        #self.analysis = pd.DataFrame(index = sec_id.index)
        self.analysis = pd.DataFrame(index = date2num(sec_id.index))
        #self.analysis.Date.dt.tz_localize('UTC')

        self.analysis['sma_f'] = sec_id.close.rolling(self.SMA_FAST).mean()
        self.analysis['sma_s'] = sec_id.close.rolling(self.SMA_SLOW).mean()
        self.analysis['rsi'] = ta.RSI(sec_id.close.to_numpy(), self.RSI_PERIOD)
        self.analysis['sma_r'] = self.analysis.rsi.rolling(self.RSI_PERIOD).mean()
        self.analysis['macd'], self.analysis['macdSignal'], self.analysis['macdHist'] = ta.MACD(sec_id.close.to_numpy(), fastperiod=self.MACD_FAST, slowperiod=self.MACD_SLOW, signalperiod=self.MACD_SIGNAL)
        self.analysis['stoch_k'], self.analysis['stoch_d'] = ta.STOCH(sec_id.high.to_numpy(), sec_id.low.to_numpy(), sec_id.close.to_numpy(), fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0) #slowk_period=self.STOCH_K, slowd_period=self.STOCH_D)

        self.analysis['sma'] = np.where(self.analysis.sma_f > self.analysis.sma_s, 1, 0)
        #self.analysis['macd_test'] = np.where((self.analysis.macd > self.analysis.macdSignal), 1, 0)
        #self.analysis['stoch_k_test'] = np.where((self.analysis.stoch_k < 50) & (self.analysis.stoch_k > self.analysis.stoch_k.shift(1)), 1, 0)
        #self.analysis['rsi_test'] = np.where((self.analysis.rsi < 50) & (self.analysis.rsi > self.analysis.rsi.shift(1)), 1, 0)

        # Prepare plot
        self.fig, (self.ax1, self.ax2, self.ax3, self.ax4) = plt.subplots(4, 1, sharex=True)
        self.ax1.set_ylabel(ticker, size=20)

        self.ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M:%S'))

        #size plot
        self.fig.set_size_inches(15,30)

        # Plot candles width=.6/(24*60)
        candlestick(self.ax1, self.sec_id_ochl, width=.6/(24*60), colorup='g', colordown='r', alpha=1)

        # Draw Moving Averages
        self.analysis.sma_f.plot(ax=self.ax1, c='r', linewidth=self.LINE_WIDTH)
        self.analysis.sma_s.plot(ax=self.ax1, c='g', linewidth=self.LINE_WIDTH)
        handles, labels = self.ax1.get_legend_handles_labels()
        self.ax1.legend(handles, labels)


        #RSI
        self.ax2.set_ylabel('RSI', size=self.Y_AXIS_SIZE)
        self.analysis.rsi.plot(ax = self.ax2, c='g', label = 'Period: ' + str(self.RSI_PERIOD), linewidth=self.LINE_WIDTH)
        self.analysis.sma_r.plot(ax = self.ax2, c='r', label = 'MA: ' + str(self.RSI_AVG_PERIOD), linewidth=self.LINE_WIDTH)
        self.ax2.axhline(y=30, c='b', linewidth=self.LINE_WIDTH)
        #self.ax2.axhline(y=50, c='black', linewidth=self.LINE_WIDTH)
        self.ax2.axhline(y=70, c='b', linewidth=self.LINE_WIDTH)
        self.ax2.set_ylim([0,100])
        handles, labels = self.ax2.get_legend_handles_labels()
        self.ax2.legend(handles, labels)

        # Draw MACD computed with Talib
        self.ax3.set_ylabel('MACD: '+ str(self.MACD_FAST) + ', ' + str(self.MACD_SLOW) + ', ' + str(self.MACD_SIGNAL), size=self.Y_AXIS_SIZE)
        self.analysis.macd.plot(ax=self.ax3, color='b', label='Macd', linewidth=self.LINE_WIDTH)
        self.analysis.macdSignal.plot(ax=self.ax3, color='g', label='Signal', linewidth=self.LINE_WIDTH)
        self.analysis.macdHist.plot(ax=self.ax3, color='r', label='Hist', linewidth=self.LINE_WIDTH)
        self.ax3.axhline(0, lw=2, color='0', linewidth=self.LINE_WIDTH)
        handles, labels = self.ax3.get_legend_handles_labels()
        self.ax3.legend(handles, labels)

        # Stochastic plot
        self.ax4.set_ylabel('Stoch (k,d)', size=self.Y_AXIS_SIZE)
        self.analysis.stoch_k.plot(ax=self.ax4, label='stoch_k:'+ str(self.STOCH_K), color='r', linewidth=self.LINE_WIDTH)
        self.analysis.stoch_d.plot(ax=self.ax4, label='stoch_d:'+ str(self.STOCH_D), color='g', linewidth=self.LINE_WIDTH)
        handles, labels = self.ax4.get_legend_handles_labels()
        self.ax4.legend(handles, labels)
        self.ax4.axhline(y=20, c='b', linewidth=self.LINE_WIDTH)
        self.ax4.axhline(y=50, c='black', linewidth=self.LINE_WIDTH)
        self.ax4.axhline(y=80, c='b', linewidth=self.LINE_WIDTH)

        self.ani = animation.FuncAnimation(self.fig, self.animate, interval=5000)

        plt.show()

    def animate(self, i):
        #logger.info("[plotThread][animate] self.update_flag " + str(self.update_flag))

        if self.update_flag:
            sec_id = singleton_data.getInstance().getOHLC_data()

            sec_id_ochl = np.array(pd.DataFrame({'0':date2num(sec_id.index),
                                                 '1':sec_id.open,
                                                 '2':sec_id.close,
                                                 '3':sec_id.high,
                                                 '4':sec_id.low}))

            #logger.info("[plotThread][animate] sec_id_ochl " + str(sec_id_ochl))

            self.analysis = pd.DataFrame(index = sec_id.index)

            self.analysis['sma_f'] = sec_id.close.rolling(self.SMA_FAST).mean()
            self.analysis['sma_s'] = sec_id.close.rolling(self.SMA_SLOW).mean()
            self.analysis['rsi'] = ta.RSI(sec_id.close.to_numpy(), self.RSI_PERIOD)
            self.analysis['sma_r'] = self.analysis.rsi.rolling(self.RSI_PERIOD).mean()
            self.analysis['macd'], self.analysis['macdSignal'], self.analysis['macdHist'] = ta.MACD(sec_id.close.to_numpy(), fastperiod=self.MACD_FAST, slowperiod=self.MACD_SLOW, signalperiod=self.MACD_SIGNAL)
            self.analysis['stoch_k'], self.analysis['stoch_d'] = ta.STOCH(sec_id.high.to_numpy(), sec_id.low.to_numpy(), sec_id.close.to_numpy(), fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)#slowk_period=self.STOCH_K, slowd_period=self.STOCH_D)

            self.analysis['sma'] = np.where(self.analysis.sma_f > self.analysis.sma_s, 1, 0)

            # Plot candles width=.6/(24*60)
            candlestick(self.ax1, sec_id_ochl, width=.6/(24*60), colorup='g', colordown='r', alpha=1)

            # Draw Moving Averages
            self.analysis['sma_f'] = sec_id.close.rolling(self.SMA_FAST).mean()
            self.analysis['sma_s'] = sec_id.close.rolling(self.SMA_SLOW).mean()

            self.analysis.sma_f.plot(ax=self.ax1, c='r', linewidth=self.LINE_WIDTH)
            self.analysis.sma_s.plot(ax=self.ax1, c='g', linewidth=self.LINE_WIDTH)

            self.analysis.rsi.plot(ax = self.ax2, c='g', label = 'Period: ' + str(self.RSI_PERIOD), linewidth=self.LINE_WIDTH)
            self.analysis.sma_r.plot(ax = self.ax2, c='r', label = 'MA: ' + str(self.RSI_AVG_PERIOD), linewidth=self.LINE_WIDTH)

            self.analysis.macd.plot(ax=self.ax3, color='b', label='Macd', linewidth=self.LINE_WIDTH)
            self.analysis.macdSignal.plot(ax=self.ax3, color='g', label='Signal', linewidth=self.LINE_WIDTH)
            self.analysis.macdHist.plot(ax=self.ax3, color='r', label='Hist', linewidth=self.LINE_WIDTH)

            self.analysis.stoch_k.plot(ax=self.ax4, label='stoch_k:'+ str(self.STOCH_K), color='r', linewidth=self.LINE_WIDTH)
            self.analysis.stoch_d.plot(ax=self.ax4, label='stoch_d:'+ str(self.STOCH_D), color='g', linewidth=self.LINE_WIDTH)

            self.update_flag = False

    def plot_update(self):
        logger.info("[bitmex_plot][plot_update]")
        self.update_flag = True

        wait_plotupdate = 0
        while self.update_flag :
            wait_plotupdate += 1
            #logger.info("[bitmex_plot][plot_update] wait_plotupdate " + str(wait_plotupdate))
            time.sleep(0.1)

        return self.analysis.iloc[-1:]


