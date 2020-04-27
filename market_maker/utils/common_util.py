import math

def calc_max_order(order_size, order_span):
    buy_level = math.ceil(order_span / 10)
    sum = 0
    for i in range(1, buy_level + 1):
        sum += i;

    ave = float(sum / buy_level)

    max_order_size = order_size * ave * order_span * 2;

    return max_order_size