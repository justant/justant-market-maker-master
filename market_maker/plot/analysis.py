from market_maker.utils.singleton import singleton_data
import logging
import pandas as pd
import numpy as np
import talib as ta
from matplotlib.dates import date2num
from market_maker.order.super_trend import getSuperTrend
from dateutil.parser import parse

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

def trim_30m(bin5m_data):
    first_idx = 0
    last_idx = len(bin5m_data) - 1
    for i in range(0, len(bin5m_data)):
        temp_time = bin5m_data['timestamp'][i]
        dt = parse(temp_time)
        if dt.time().minute == 5 or dt.time().minute == 35:
            first_idx = i
            break

    for i in range(len(bin5m_data) - 10, len(bin5m_data)):
        temp_time = bin5m_data['timestamp'][i]
        dt = parse(temp_time)

        if dt.time().minute == 0 or dt.time().minute == 30:
            last_idx = i

    return first_idx, last_idx


def get_analysis(getOnlyLast = False, bidSize = '1m'):
    sec_id = None

    if bidSize == '1m':
        sec_id = singleton_data.getInstance().getOHLC_1m_data()
    elif bidSize == '5m':
        sec_id = singleton_data.getInstance().getOHLC_5m_data()
    elif bidSize == '30m':
        bin5m_data = singleton_data.getInstance().getOHLC_5m_data()

        first_idx, last_idx = trim_30m(bin5m_data)

        logger.info("[get_analysis] len(bin5m_data) " + str(len(bin5m_data)))

        temp_list = []
        for i in range(first_idx, last_idx + 1):
            if not i % 6 == first_idx:
                continue

            temp_map = {}
            temp_map['trades'] = 0
            temp_map['volume'] = 0
            temp_map['high'] = bin5m_data['high'][i]
            temp_map['low'] = bin5m_data['low'][i]
            temp_map['timestamp'] = bin5m_data['timestamp'][i]
            temp_map['symbol'] = bin5m_data['symbol'][i]
            temp_map['open'] = bin5m_data['open'][i]
            temp_map['close'] = bin5m_data['close'][i + 5]

            for j in range(i, i + 6):
                if temp_map['high'] < bin5m_data['high'][j]:
                    temp_map['high'] = bin5m_data['high'][j]

                if temp_map['low'] > bin5m_data['low'][j]:
                    temp_map['low'] = bin5m_data['low'][j]

                temp_map['trades'] = temp_map['trades'] + bin5m_data['trades'][j]
                temp_map['volume'] = bin5m_data['volume'][i] + bin5m_data['volume'][j]

            temp_list.append(temp_map)

        cnt = int((last_idx + 1 - first_idx) / 6)

        df = pd.DataFrame({
            'timestamp' : [temp_list[i]['timestamp'] for i in range(0, cnt)],
            'symbol' : [temp_list[i]['symbol'] for i in range(0, cnt)],
            'open' : [temp_list[i]['open'] for i in range(0, cnt)],
            'high' : [temp_list[i]['high'] for i in range(0, cnt)],
            'low' : [temp_list[i]['low'] for i in range(0, cnt)],
            'close' : [temp_list[i]['close'] for i in range(0, cnt)],
            'trades' : [temp_list[i]['trades'] for i in range(0, cnt)],
            'volume' : [temp_list[i]['volume'] for i in range(0, cnt)],

        },
            index=pd.to_datetime([temp_list[i]['timestamp'] for i in range(0, cnt)]))

        sec_id = df

    #analysis = pd.DataFrame(index = date2num(sec_id.index))
    analysis = pd.DataFrame()

    ret = []
    analysis['timestamp'] = sec_id.timestamp
    analysis['Open'] = sec_id.open.to_numpy()
    analysis['High'] = sec_id.high.to_numpy()
    analysis['Low'] = sec_id.low.to_numpy()
    analysis['Close'] = sec_id.close.to_numpy()

    analysis = getSuperTrend(analysis, 2, 16)

    #analysis['sma_f'] = sec_id.close.rolling(SMA_FAST).mean()
    #analysis['sma_s'] = sec_id.close.rolling(SMA_SLOW).mean()
    analysis['rsi'] = ta.RSI(sec_id.close.to_numpy(), RSI_PERIOD)
    #analysis['sma_r'] = analysis.rsi.rolling(RSI_PERIOD).mean()
    #analysis['macd'], analysis['macdSignal'], analysis['macdHist'] = ta.MACD(sec_id.close.to_numpy(), fastperiod=MACD_FAST, slowperiod=MACD_SLOW, signalperiod=MACD_SIGNAL)
    analysis['stoch_k'], analysis['stoch_d'] = ta.STOCH(sec_id.high.to_numpy(), sec_id.low.to_numpy(), sec_id.close.to_numpy(), fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0) #slowk_period=self.STOCH_K, slowd_period=self.STOCH_D)
    #analysis['sma'] = np.where(analysis.sma_f > analysis.sma_s, 1, 0)

    ret = analysis

    if(getOnlyLast):
        ret = analysis.iloc[-1:]

    return ret
