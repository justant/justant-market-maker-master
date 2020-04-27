import logging

import settings
import math
from market_maker.utils.singleton import singleton_data

logger = logging.getLogger('root')

def net_buy(custom_strategy):
    current_price = custom_strategy.exchange.get_instrument()['lastPrice']
    logger.info("[net_order][normal_buy] current_price(2) : " + str(current_price))
    default_Qty = settings.DEFAULT_ORDER_SIZE
    buy_level = math.ceil(settings.DEFAULT_ORDER_SPAN / 10)
    buy_orders = []

    for i in range(1, buy_level + 1):
        for j in range(1, 21):
            buy_orders.append({'price': current_price - ((j * 0.5) + (i - 1) * 10), 'orderQty': default_Qty * i, 'side': "Buy", 'execInst': "ParticipateDoNotInitiate"})

    ret = custom_strategy.converge_orders(buy_orders, [])
    logger.info("[net_order][normal_buy] order length : " + str(len(ret)))

    singleton_data.getInstance().setAllowBuy(False)
    logger.info("[net_order][normal_buy] after self.converge_orders")
    logger.info("[net_order][normal_buy] getAllowBuy() " + str(singleton_data.getInstance().getAllowBuy()))

#def net_buy(custom_strategy):
