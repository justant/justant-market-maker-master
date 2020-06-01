import numpy as np
import pandas as pd

#SuperTrend
def getSuperTrend(df, f, n): #df is the dataframe, n is the period, f is the factor; f=3, n=7 are commonly used.
    df = df.reset_index()

    #Calculation of ATR
    df['H-L']=abs(df['High']-df['Low'])
    df['H-PC']=abs(df['High']-df['Close'].shift(1))
    df['L-PC']=abs(df['Low']-df['Close'].shift(1))
    df['TR']=df[['H-L','H-PC','L-PC']].max(axis=1)
    df['ATR']=np.nan
    df.loc[df.index[n-1],'ATR']=df['TR'][:df.index[n-1]].mean()

    for i in range(n, len(df)):
        df['ATR'][i]=(df['ATR'][i-1]*(n-1)+ df['TR'][i])/n
        #df['ATR'][i] = 1.0

    #Calculation of SuperTrend
    df['Upper Basic']=(df['High']+df['Low'])/2+(f*df['ATR'])
    df['Lower Basic']=(df['High']+df['Low'])/2-(f*df['ATR'])
    df['Upper Band']=df['Upper Basic']
    df['Lower Band']=df['Lower Basic']

    for i in range(n,len(df)):
        if df['Close'][i - 1] <= df['Upper Band'][i - 1]:
            df['Upper Band'][i]=min(df['Upper Basic'][i],df['Upper Band'][i - 1])
        else:
            df['Upper Band'][i]=df['Upper Basic'][i]
    for i in range(n,len(df)):
        if df['Close'][i - 1] >= df['Lower Band'][i - 1]:
            df['Lower Band'][i] = max(df['Lower Basic'][i], df['Lower Band'][i - 1])
        else:
            df['Lower Band'][i] = df['Lower Basic'][i]

    df['SuperTrend'] = np.nan

    for i in range (1, len(df['SuperTrend'])):
        if df['Close'][n - 1] <= df['Upper Band'][n - 1]:
            df['SuperTrend'][n - 1] = df['Upper Band'][n - 1]
        elif df['Close'][n - 1] > df['Upper Band'][i]:
            df = df.fillna(0)
            df['SuperTrend'][n - 1] = df['Lower Band'][n - 1]


    df['Direction'] = np.nan
    df['PreDirection'] = np.nan

    for i in range(n, len(df)):
        # Short
        if df['SuperTrend'][i - 1] == df['Upper Band'][i - 1]:
            if df['Close'][i] <= df['Upper Band'][i]:
                df['SuperTrend'][i] = df['Upper Band'][i]
                df['Direction'][i] = 'Short'
                df['PreDirection'][i] = df['Direction'][i - 1]
            elif df['Close'][i] >= df['Upper Band'][i]:
                df['SuperTrend'][i] = df['Lower Band'][i]
                df['Direction'][i] = 'Long'
                df['PreDirection'][i] = df['Direction'][i - 1]
        # Long
        elif df['SuperTrend'][i - 1] == df['Lower Band'][i - 1]:
            if df['Close'][i] >= df['Lower Band'][i]:
                df['SuperTrend'][i] = df['Lower Band'][i]
                df['Direction'][i] = 'Long'
                df['PreDirection'][i] = df['Direction'][i - 1]
            elif df['Close'][i] <= df['Lower Band'][i]:
                df['SuperTrend'][i] = df['Upper Band'][i]
                df['Direction'][i] = 'Short'
                df['PreDirection'][i] = df['Direction'][i - 1]

    df = df.set_index(pd.DatetimeIndex(pd.to_datetime(df["index"])))
    return df