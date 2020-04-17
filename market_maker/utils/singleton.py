import pandas as pd
from market_maker.utils import log

logger = log.setup_custom_logger('root')

class ohlc_data:
    _instance = None

    @classmethod
    def _getInstance(cls):
        return cls._instance

    @classmethod
    def instance(cls, *args, **kargs):
        cls._instance = cls(*args, **kargs)
        cls.instance = cls._getInstance
        return cls._instance

    def __init__(self):
        self.data = pd.DataFrame
        self.data_cnt = 0;

    def setData(self, newData):
        self.data = newData
        self.data_cnt = len(self.data)

    def getData(self):
        return self.data

    def appendData(self, bin1m):
        logger.info("[ohlc_data][appendData]")

        update_required = False
        # max data len = 120
        MAX_DATA_LEN = 120
        pre_cnt = len(self.data)
        self.data = self.data.append(bin1m).drop_duplicates()
        post_cnt = len(self.data)

        if post_cnt > pre_cnt :
            logger.info("[ohlc_data][appendData] post_cnt > pre_cnt")
            update_required = True

        if post_cnt > MAX_DATA_LEN :
            logger.info("[ohlc_data][appendData] post_cnt > MAX_DATA_LEN, delete first row of data")
            self.data = self.data.iloc[1:]

        return update_required