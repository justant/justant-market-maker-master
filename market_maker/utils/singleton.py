import pandas as pd
from market_maker.utils import log

logger = log.setup_custom_logger('root')
#log.setup_custom_logger('order')

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
        self.mode = None
        self.switch_mode = False

        self.ohld_1m_data = pd.DataFrame
        self.ohld_5m_data = pd.DataFrame

        self.allow_buy = False
        self.allow_sell = False
        self.allow_order = False

        self.is_order_thread_run = False
        self.is_sell_thread_run = False
        self.is_buy_thread_run = False

        self.aveDownCnt = 0
    def setMode(self, mode):
        logger.info("[setMode] : " + str(mode))
        self.mode = mode

    def getMode(self):
        return self.mode

    def getSwitchMode(self):
        return self.switch_mode

    def setSwitchMode(self, bool):
        logger.info("[setSwitchMode] : " + str(bool))
        self.switch_mode = bool

    def setOHLC_1m_data(self, newData):
        self.ohld_1m_data = newData

    def getOHLC_1m_data(self):
        return self.ohld_1m_data

    def setOHLC_5m_data(self, newData):
        self.ohld_5m_data = newData

    def getOHLC_5m_data(self):
        return self.ohld_5m_data

    def appendOHLC_data(self, bin_data, bidSize):
        #logger.info("[ohlc_data][appendOHLC_15m_data]")

        update_required = False
        # max data len = 120
        MAX_DATA_LEN = 120

        pre_cnt = 0
        post_cnt = 0

        if bidSize == '1m':
                if self.ohld_1m_data['timestamp'][len(self.ohld_1m_data) - 1] != bin_data['timestamp']:
                    self.ohld_1m_data = self.ohld_1m_data.append(bin_data, ignore_index=True)
                    update_required = True

                    for i in range(0, len(self.ohld_1m_data) - 1):
                        self.ohld_1m_data.iloc[i] = self.ohld_1m_data.iloc[i + 1]
                    self.ohld_1m_data = self.ohld_1m_data.iloc[:len(self.ohld_1m_data) - 1]

        elif bidSize == '5m':
            if self.ohld_5m_data['timestamp'][len(self.ohld_5m_data) - 1] != bin_data['timestamp']:
                self.ohld_5m_data = self.ohld_5m_data.append(bin_data, ignore_index=True)
                update_required = True

                for i in range(0, len(self.ohld_5m_data) - 1):
                    self.ohld_5m_data.iloc[i] = self.ohld_5m_data.iloc[i + 1]
                self.ohld_5m_data = self.ohld_5m_data.iloc[:len(self.ohld_5m_data) - 1]

        return update_required

    def setAllowBuy(self, value):
        logger.info("[setAllowBuy] : " + str(value))
        self.allow_buy = value

    def getAllowBuy(self):
        return self.allow_buy

    def setAllowSell(self, value):
        logger.info("[setAllowSell] : " + str(value))
        self.allow_sell = value

    def getAllowSell(self):
        return self.allow_sell

    def setAllowOrder(self, value):
        logger.info("[setAllowOrder] : " + str(value))
        self.allow_order = value

    def getAllowOrder(self):
        return self.allow_order

    def isSellThreadRun(self):
        return self.is_sell_thread_run

    def setSellThread(self, value):
        logger.info("[setSellThread] : " + str(value))
        self.is_sell_thread_run = value

    def isBuyThreadRun(self):
        return self.is_buy_thread_run

    def setBuyThread(self, value):
        logger.info("[setBuyThread] : " + str(value))
        self.is_buy_thread_run = value

    def isOrderThreadRun(self):
        return self.is_order_thread_run

    def setOrderThread(self, value):
        logger.info("[setOrderThread] : " + str(value))
        self.is_order_thread_run = value

    def getAveDownCnt(self):
        return self.aveDownCnt

    def setAveDownCnt(self, value):
        logger.info("[setAveDownCnt] :" + str(value))
        self.aveDownCnt = value
