import pandas as pd
from market_maker.utils import log

logger = log.setup_custom_logger('root')

class singleton_data:
    _instance = None

    @classmethod
    def getInstance(cls):
        return cls._instance

    @classmethod
    def instance(cls, *args, **kargs):
        cls._instance = cls(*args, **kargs)
        cls.instance = cls.getInstance
        return cls._instance

    def __init__(self):
        self.ohld_data = pd.DataFrame
        self.allow_buy = True
        self.is_sell_thread_run = False
        self.is_buy_thread_run = False

    def setOHLC_data(self, newData):
        self.ohld_data = newData

    def getOHLC_data(self):
        return self.ohld_data

    def appendOHLC_data(self, bin1m):
        #logger.info("[ohlc_data][appendData]")

        update_required = False
        # max data len = 120
        MAX_DATA_LEN = 120
        pre_cnt = len(self.ohld_data)
        self.ohld_data = self.ohld_data.append(bin1m).drop_duplicates()
        post_cnt = len(self.ohld_data)

        if post_cnt > pre_cnt :
            #logger.info("[ohlc_data][appendData] post_cnt > pre_cnt")
            update_required = True

        if post_cnt > MAX_DATA_LEN :
            #logger.info("[ohlc_data][appendData] post_cnt > MAX_DATA_LEN, delete first row of data")
            self.ohld_data = self.ohld_data.iloc[1:]

        return update_required

    def setAllowBuy(self, value):
        self.allow_buy = value

    def getAllowBuy(self):
        return self.allow_buy

    def isSellThreadRun(self):
        return self.is_sell_thread_run

    def setSellThread(self, value):
        self.is_sell_thread_run = value

    def isBuyThreadRun(self):
        return self.is_buy_thread_run

    def setBuyThread(self, value):
        self.is_buy_thread_run = value