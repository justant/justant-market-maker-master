from os.path import join
import logging

########################################################################################################################
# Connection/Auth
########################################################################################################################

# API URL.
#BASE_URL = "https://testnet.bitmex.com/api/v1/"
from market_maker.utils.common_util import calc_max_order

BASE_URL = "https://www.bitmex.com/api/v1/" # Once you're ready, uncomment this.

# The BitMEX API requires permanent API keys. Go to https://testnet.bitmex.com/app/apiKeys to fill these out.
API_KEY = "test2"
API_SECRET = "test2"

# Telegram API Key
TELEGRAM_API_KEY = "test3"

########################################################################################################################
# Target
########################################################################################################################

# Instrument to market make on BitMEX.
SYMBOL = "XBTUSD"


########################################################################################################################
# Order Size & Spread
########################################################################################################################

# How many pairs of buy/sell orders to keep open
ORDER_PAIRS = 100

# ORDER_START_SIZE will be the number of contracts submitted on level 1
# Number of contracts from level 1 to ORDER_PAIRS - 1 will follow the function
# [ORDER_START_SIZE + ORDER_STEP_SIZE (Level -1)]
ORDER_START_SIZE = 100
ORDER_STEP_SIZE = 100

# Distance between successive orders, as a percentage (example: 0.005 for 0.5%)
INTERVAL = 0.005

# Minimum spread to maintain, in percent, between asks & bids
MIN_SPREAD = 0.01

# If True, market-maker will place orders just inside the existing spread and work the interval % outwards,
# rather than starting in the middle and killing potentially profitable spreads.
MAINTAIN_SPREADS = True

# This number defines far much the price of an existing order can be from a desired order before it is amended.
# This is useful for avoiding unnecessary calls and maintaining your ratelimits.
#
# Further information:
# Each order is designed to be (INTERVAL*n)% away from the spread.
# If the spread changes and the order has moved outside its bound defined as
# abs((desired_order['price'] / order['price']) - 1) > settings.RELIST_INTERVAL)
# it will be resubmitted.
#
# 0.01 == 1%
RELIST_INTERVAL = 0.01


########################################################################################################################
# Trading Behavior
########################################################################################################################

# Position limits - set to True to activate. Values are in contracts.
# If you exceed a position limit, the bot will log and stop quoting that side.
CHECK_POSITION_LIMITS = False
MIN_POSITION = -10000
MAX_POSITION = 10000

# If True, will only send orders that rest in the book (ExecInst: ParticipateDoNotInitiate).
# Use to guarantee a maker rebate.
# However -- orders that would have matched immediately will instead cancel, and you may end up with
# unexpected delta. Be careful.
POST_ONLY = False

########################################################################################################################
# Misc Behavior, Technicals
########################################################################################################################

# If true, don't set up any orders, just say what we would do
DRY_RUN = False
# DRY_RUN = False

# How often to re-check and replace orders.
# Generally, it's safe to make this short because we're fetching from websockets. But if too many
# order amend/replaces are done, you may hit a ratelimit. If so, email BitMEX if you feel you need a higher limit.
LOOP_INTERVAL = 5

# Wait times between orders / errors
API_REST_INTERVAL = 0.2
API_ERROR_INTERVAL = 10
TIMEOUT = 7

# If we're doing a dry run, use these numbers for BTC balances
DRY_BTC = 50

# Available levels: logging.(DEBUG|INFO|WARN|ERROR)
LOG_LEVEL = logging.INFO

# To uniquely identify orders placed by this bot, the bot sends a ClOrdID (Client order ID) that is attached
# to each order so its source can be identified. This keeps the market maker from cancelling orders that are
# manually placed, or orders placed by another bot.
#
# If you are running multiple bots on the same symbol, give them unique ORDERID_PREFIXes - otherwise they will
# cancel each others' orders.
# Max length is 13 characters.
ORDERID_PREFIX = "mm_bitmex_"

# If any of these files (and this file) changes, reload the bot.
WATCHED_FILES = [join('market_maker', 'market_maker.py'), join('market_maker', 'bitmex.py'), 'settings.py']


########################################################################################################################
# BitMEX Portfolio
########################################################################################################################

# Specify the contracts that you hold. These will be used in portfolio calculations.
CONTRACTS = ['XBTUSD']

# When current price is lower than the AVERAGING price, additional purchases are made.
AVERAGING_DOWN_SIZE = 10000.0
AVERAGING_UP_SIZE = 10000.0

# rsi, stoch
BASIC_DOWN_RSI = 30.0
BASIC_UP_RSI = 70.0

BASIC_DOWN_STOCH = 20.0
BASIC_UP_STOCH = 80.0

# Sell only when +- 150$ average price
MIN_SELLING_GAP = 50.0
MIN_BUYING_GAP = 50.0

# After capturing the sales signal, wait for the desired price for 2 minutes.
SELLING_WAIT = 60
BUYING_WAIT = 60

# Manual Mode :
# 0  : Auto. It switches direction according to long or short mode.
# 1  : Buying. Maintain long mode regardless of Supertrend and decide Buying, Selling according to RSI and Stoch values
# 11 : Buying without condition. Maintain long mode. No uses Supertrend, RSI, Stoch values.# 111 : Buying except for short mode. It will be no trade during short period.
# 2  : Selling
# 22 : Selling without condition. Maintain short mode. No uses Supertrend, RSI, Stoch values.
# 222 : Selling except for short mode. It will be no trade during long period.
USER_MODE = 0

# first order price. after 10$, order size will be 2 times.
# after 10$, order price will be 3 times... 4times... 5times..
DEFAULT_ORDER_PRICE = 550
DEFAULT_ORDER_COUNT = 32

# will be order from current_price to {current_price +- 30$}
# it should be multiples of 10 (ex: 10, 20, 30 ,,,)
DEFAULT_ORDER_SPAN = 12

MIN_ORDER_DIST = 25.0
CURRENT_ORDER_DIST = 120.0

#MAX_ORDER_QUENTITY = calc_max_order(DEFAULT_ORDER_PRICE, DEFAULT_ORDER_SPAN)
# temp
MAX_ORDER_QUENTITY = 2000

DEFUALT_SWING_ORDER_SIZE = 2000

# Whether to draw a graph or not
PLOT_RUNNING = False
