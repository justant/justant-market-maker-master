import pandas as pd

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

    def getDataCnt(self):
        return self.data_cnt

    def appendData(self, bin1m):
        self.data = self.data.append(bin1m).drop_duplicates()
        self.data_cnt = len(self.data)