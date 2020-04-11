import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np
import talib as ta
from matplotlib.dates import date2num
from mpl_finance import candlestick_ohlc as candlestick
import logging
import time
import threading
from pandas_datareader import data
from datetime import datetime, timedelta

sec_id = pd.DataFrame
flag = False
logger = logging.getLogger('root')
ticker = 'BTC-USD'

temp_cnt = 0


def data_listener(bin1m):
    logger.info("[plotThread][data_listener]")
    time.sleep(1)
    global flag
    global sec_id
    global temp_cnt

    sec_id = bin1m

    sec_id["open"] = sec_id["open"].astype(float)
    sec_id["high"] = sec_id["high"].astype(float)
    sec_id["close"] = sec_id["close"].astype(float)
    sec_id["trades"] = sec_id["trades"].astype(float)
    sec_id["volume"] = sec_id["volume"].astype(float)
    sec_id["vwap"] = sec_id["vwap"].astype(float)
    sec_id["lastSize"] = sec_id["lastSize"].astype(float)
    sec_id["turnover"] = sec_id["turnover"].astype(float)
    sec_id["homeNotional"] = sec_id["homeNotional"].astype(float)
    sec_id["foreignNotional"] = sec_id["foreignNotional"].astype(float)

    flag = True

class plotThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.__suspend = False
        self.__exit = False


    def run(self):
        logger.info("[plotThread][run]")
        global sec_id
        global flag

        SMA_FAST = 50
        SMA_SLOW = 200
        RSI_PERIOD = 14
        RSI_AVG_PERIOD = 15
        MACD_FAST = 12
        MACD_SLOW = 26
        MACD_SIGNAL = 9
        STOCH_K = 14
        STOCH_D = 3
        SIGNAL_TOL = 3
        Y_AXIS_SIZE = 12

        while self.__suspend:
            time.sleep(0.5)

        # Prepare plot
        #fig, (ax1) = plt.subplots(1, 1, sharex=True)
        #ax1.set_ylabel(ticker, size=20)
        #plt.ion()
        #plt.show()

        #size plot
        #fig.set_size_inches(15,30)

        fig = plt.figure(figsize=(8, 5))
        fig.set_facecolor('w')
        gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
        axes = []
        axes.append(plt.subplot(gs[0]))
        axes.append(plt.subplot(gs[1], sharex=axes[0]))
        #axes[0].get_xaxis().set_visible(False)
        axes[0].xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M:%S'))
        plt.ion()
        plt.show()

        cnt = 0
        while True:

            if flag:
                cnt += 1
                logger.info("[plotThread][run] cnt " + str(cnt))

                sec_id_ochl = np.array(pd.DataFrame({'0':date2num(sec_id.index.to_pydatetime()),
                                                     '1':sec_id.open,
                                                     '2':sec_id.close,
                                                     '3':sec_id.high,
                                                     '4':sec_id.low}))

                #logger.info("[plotThread][run] sec_id_ochl " + sec_id_ochl)

                analysis = pd.DataFrame(index = sec_id.index)

                analysis['sma_f'] = sec_id.close.rolling(SMA_FAST).mean()
                analysis['sma_s'] = sec_id.close.rolling(SMA_SLOW).mean()

                # Plot candles
                candlestick(axes[0], sec_id_ochl, width=.6/(24*60), colorup='r', colordown='b', alpha =.4)

                # Draw Moving Averages
                #analysis.sma_f.plot(ax=ax1, c='r')
                #analysis.sma_s.plot(ax=ax1, c='g')

                plt.pause(0.02)

            flag = False
            time.sleep(1)


    def mySuspend(self):
        self.__suspend = True

    def myResume(self):
        self.__suspend = False

    def myExit(self):
        self.__exit = True




