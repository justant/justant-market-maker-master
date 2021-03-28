from time import sleep

import settings
import math
from market_maker.utils.singleton import singleton_data
from market_maker.utils import log

logger = log.setup_custom_logger('root')

def bulk_net_buy(custom_strategy):
    current_price = custom_strategy.exchange.get_instrument()['lastPrice'] - 0.5
    logger.info("[net_order][normal_buy] current_price(2) : " + str(current_price))

    buy_orders = []

    super_trend = custom_strategy.analysis_15m['SuperTrend'][0]
    order_cnt = settings.DEFAULT_ORDER_COUNT
    order_dist = get_order_dist(current_price, super_trend, order_cnt)

    default_Qty = get_qty(95, current_price)
    #default_Qty = settings.DEFAULT_ORDER_PRICE
    logger.info("[net_order][bulk_net_buy] default_Qty : " + str(default_Qty))

    # manual
    #current_price = 9400.0

    total_qty = 0

    for i in range(1, order_cnt + 1):
        if current_price - ((i - 1) * order_dist) < super_trend:
            break

        if i == 1:
            buy_orders.append({'price': current_price + order_dist * 10, 'orderQty': default_Qty * 2, 'side': "Buy"})
            buy_orders.append({'price': current_price - ((i - 1) * order_dist), 'orderQty': default_Qty * 2, 'side': "Buy", 'execInst': "ParticipateDoNotInitiate"})
        else:
            buy_orders.append({'price': current_price - ((i - 1) * order_dist), 'orderQty': default_Qty, 'side': "Buy", 'execInst': "ParticipateDoNotInitiate"})

        total_qty = total_qty + default_Qty

    ret = custom_strategy.converge_orders(buy_orders, [])
    check_caceled_order(custom_strategy, ret, 'Buy')
    logger.info("[net_order][bulk_net_buy] order length : " + str(len(ret)))
    logger.info("[net_order][bulk_net_buy] order : " + str(ret))

    settings.MAX_ORDER_QUENTITY = total_qty
    logger.info("[net_order][bulk_net_buy] MAX_ORDER_QUENTITY : " + str(settings.MAX_ORDER_QUENTITY))

    singleton_data.instance().setAllowBuy(False)
    logger.info("[net_order][bulk_net_buy] getAllowBuy() " + str(singleton_data.instance().getAllowBuy()))

def bulk_net_sell(custom_strategy):
    current_price = custom_strategy.exchange.get_instrument()['lastPrice'] + 0.5
    logger.info("[net_order][normal_sell] current_price(2) : " + str(current_price))

    sell_orders = []

    #order_cnt = round(settings.DEFAULT_ORDER_COUNT * 4 / 7)
    super_trend = custom_strategy.analysis_15m['SuperTrend'][0]
    order_cnt = settings.DEFAULT_ORDER_COUNT
    order_dist = get_order_dist(current_price, super_trend, order_cnt)

    default_Qty = get_qty(99, current_price + (order_cnt - 1) * order_dist)
    #default_Qty = settings.DEFAULT_ORDER_PRICE
    logger.info("[net_order][bulk_net_sell] default_Qty : " + str(default_Qty))
    # manual
    #current_price = 9400.0

    total_qty = 0

    for i in range(1, order_cnt + 1):
        if current_price + ((i - 1) * order_dist) > super_trend:
            break

        if i == 1:
            sell_orders.append({'price': current_price - order_dist * 10, 'orderQty': default_Qty * 2, 'side': "Sell"})
            sell_orders.append({'price': current_price + ((i - 1) * order_dist), 'orderQty': default_Qty * 2, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})
        else:
            sell_orders.append({'price': current_price + ((i - 1) * order_dist), 'orderQty': default_Qty, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})

        total_qty = total_qty + default_Qty

    ret = custom_strategy.converge_orders(sell_orders, [])
    check_caceled_order(custom_strategy, ret, 'Sell')
    logger.info("[net_order][bulk_net_sell] order length : " + str(len(ret)))
    logger.info("[net_order][bulk_net_sell] order : " + str(ret))

    settings.MAX_ORDER_QUENTITY = total_qty
    logger.info("[net_order][bulk_net_sell] MAX_ORDER_QUENTITY : " + str(settings.MAX_ORDER_QUENTITY))

    singleton_data.instance().setAllowSell(False)
    logger.info("[net_order][bulk_net_sell] getAllowSell() " + str(singleton_data.instance().getAllowSell()))

# MIN_ORDER_DIST를 슈퍼트랜드의 bottom 라인과 연계해서 넣기
#    (ex : 가격이 50000 이고 슈트 bottom이 49000을 가르킨다면, (50000-49000) * 1.3 = 1300 =? 50000~48700 구간을 {order갯수}로 나눈다음에 Oder간 DIST를 구한다. DIST가 40보다 좁다면 40으로 고정)

def get_order_dist(current_price, super_trend, order_cnt):
    logger.info("[net_order][get_order_dist] order_cnt " + str(order_cnt))

    order_cnt = order_cnt - 1
    dist = round((abs(current_price - super_trend) * 1.0) / order_cnt)

    if dist < settings.MIN_ORDER_DIST:
        dist = settings.MIN_ORDER_DIST

    logger.info("[net_order][get_order_dist] dist " + str(dist))
    settings.CURRENT_ORDER_DIST = dist

    return dist

def check_caceled_order(custom_strategy, order_ret, order_type):

    add_price = 0
    if order_type == 'Buy':
        add_price = -0.5
    elif order_type == 'Sell':
        add_price = 0.5

    if len(order_ret) > 0 and order_ret[0]['ordStatus'] == 'Canceled' :
        logger.info("[net_order][check_caceled_order] Canceled")

        for i in range(1, 11):
            current_price = custom_strategy.exchange.get_instrument()['lastPrice'] + add_price
            current_order = custom_strategy.exchange.create_order(order_type, order_ret[0]['orderQty'], current_price)
            sleep(0.2)

            if current_order['ordStatus'] == 'New':
                logger.info("[net_order][check_caceled_order] current_order['ordStatus'] : New")
                break
            else :
                logger.info("[net_order][check_caceled_order] current_order['ordStatus'] : " + str(current_order['ordStatus']))

def get_qty(ratio, max_price):
    logger.info("[net_order][get_qty] order max price : " + str(max_price))
    return round(max_price / ratio)


