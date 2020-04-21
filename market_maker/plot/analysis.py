from market_maker.utils.singleton import singleton_data
import logging
import pandas as pd
import numpy as np
import talib as ta
from matplotlib.dates import date2num

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
LINE_WIDTH = 1

logger = logging.getLogger('root')

def get_analysis(getOnlyLast = False):
    sec_id = singleton_data.getInstance().getOHLC_data()
    analysis = pd.DataFrame(index = date2num(sec_id.index))
    ret = []

    #analysis['sma_f'] = sec_id.close.rolling(SMA_FAST).mean()
    #analysis['sma_s'] = sec_id.close.rolling(SMA_SLOW).mean()
    analysis['rsi'] = ta.RSI(sec_id.close.to_numpy(), RSI_PERIOD)
    #analysis['sma_r'] = analysis.rsi.rolling(RSI_PERIOD).mean()
    #analysis['macd'], analysis['macdSignal'], analysis['macdHist'] = ta.MACD(sec_id.close.to_numpy(), fastperiod=MACD_FAST, slowperiod=MACD_SLOW, signalperiod=MACD_SIGNAL)
    analysis['stoch_k'], analysis['stoch_d'] = ta.STOCH(sec_id.high.to_numpy(), sec_id.low.to_numpy(), sec_id.close.to_numpy(), fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0) #slowk_period=self.STOCH_K, slowd_period=self.STOCH_D)

    #analysis['sma'] = np.where(analysis.sma_f > analysis.sma_s, 1, 0)

    if(getOnlyLast):
        ret = analysis.iloc[-1:]
    else :
        ret = analysis
    return ret
