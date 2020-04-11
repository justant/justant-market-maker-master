import datetime

#2020-04-05T12:21:00.000Z
def coonvertDateFormat(date_str):
    #ret = datetime.datetime(2011, 7, 2, 0, 0)
    ret = datetime.datetime(int(date_str[0:4]), int(date_str[5:7]), int(date_str[8:10]), int(date_str[11:13]), int(date_str[14:16]))

    return ret;