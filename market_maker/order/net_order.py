
import settings
import math
from market_maker.utils.singleton import singleton_data
from market_maker.utils import log

logger = log.setup_custom_logger('root')

def net_buy(custom_strategy):
    current_price = custom_strategy.exchange.get_instrument()['lastPrice'] + 0.5
    logger.info("[net_order][normal_buy] current_price(2) : " + str(current_price))
    default_Qty = settings.DEFAULT_ORDER_SIZE
    buy_level = math.ceil(settings.DEFAULT_ORDER_SPAN / 10)
    buy_orders = []


    # manual
    #current_price = 9400.0

    total_qty = 0

    for i in range(1, buy_level + 1):
        for j in range(1, 21):
            buy_orders.append({'price': current_price - ((j * 1.0) + (i - 1) * 20), 'orderQty': default_Qty * i, 'side': "Buy", 'execInst': "ParticipateDoNotInitiate"})
            total_qty = total_qty + default_Qty * i
    ret = custom_strategy.converge_orders(buy_orders, [])
    logger.info("[net_order][normal_buy]1 order length : " + str(len(ret)))

    buy_orders = []
    for i in range(1 + 5, buy_level + 1 + 5):
        for j in range(1, 21):
            buy_orders.append({'price': current_price - ((j * 1.0) + (i - 1) * 20), 'orderQty': default_Qty * i, 'side': "Buy", 'execInst': "ParticipateDoNotInitiate"})
            total_qty = total_qty + default_Qty * i

    ret = custom_strategy.converge_orders(buy_orders, [])
    logger.info("[net_order][normal_buy]2 order length  : " + str(len(ret)))
    settings.MAX_ORDER_QUENTITY = total_qty
    logger.info("[net_order][normal_buy] MAX_ORDER_QUENTITY : " + str(settings.MAX_ORDER_QUENTITY))

    singleton_data.getInstance().setAllowBuy(False)
    logger.info("[net_order][normal_buy] getAllowBuy() " + str(singleton_data.getInstance().getAllowBuy()))

def net_sell(custom_strategy):
    current_price = custom_strategy.exchange.get_instrument()['lastPrice'] - 0.5
    logger.info("[net_order][normal_sell] current_price(2) : " + str(current_price))
    default_Qty = settings.DEFAULT_ORDER_SIZE
    sell_level = math.ceil(settings.DEFAULT_ORDER_SPAN / 10)
    sell_orders = []


    # manual
    #current_price = 9400.0

    total_qty = 0

    for i in range(1, sell_level + 1):
        for j in range(1, 21):
            sell_orders.append({'price': current_price + ((j * 1.0) + (i - 1) * 20), 'orderQty': default_Qty * i, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})
            total_qty = total_qty + default_Qty * i

    ret = custom_strategy.converge_orders(sell_orders, [])
    logger.info("[net_order][normal_sell]1 order length : " + str(len(ret)))

    sell_orders = []
    for i in range(1 + 5, sell_level + 1 + 5):
        for j in range(1, 21):
            sell_orders.append({'price': current_price + ((j * 1.0) + (i - 1) * 20), 'orderQty': default_Qty * i, 'side': "Sell", 'execInst': "ParticipateDoNotInitiate"})
            total_qty = total_qty + default_Qty * i

    ret = custom_strategy.converge_orders(sell_orders, [])
    logger.info("[net_order][normal_sell]2 order length : " + str(len(ret)))

    settings.MAX_ORDER_QUENTITY = total_qty
    logger.info("[net_order][normal_sell] MAX_ORDER_QUENTITY : " + str(settings.MAX_ORDER_QUENTITY))

    singleton_data.getInstance().setAllowSell(False)
    logger.info("[net_order][normal_sell] getAllowSell() " + str(singleton_data.getInstance().getAllowSell()))