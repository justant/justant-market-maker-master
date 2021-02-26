import linecache
import os
import pathlib
import sys
import threading
import settings

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from market_maker.utils import log
from market_maker.utils.singleton import singleton_data

execept_logger = log.setup_custom_logger('exception')
logger = log.setup_custom_logger('root')

class Telegram(threading.Thread):
    def __init__(self, custom_strategy):
        logger.info("[Telegram] __init__")
        threading.Thread.__init__(self)

        self.custom_strategy = custom_strategy
        self.setApiKey()
        #self.chat_id = '1653838244'

    def run(self):
        """Start the bot."""
        logger.info("[telegram][run]")
        # Create the Updater and pass it your bot's token.
        # Make sure to set use_context=True to use the new context based callbacks
        # Post version 12 this will no longer be necessary

        self.updater = Updater(settings.TELEGRAM_API_KEY, use_context=True)

        # Get the dispatcher to register handlers
        self.dp = self.updater.dispatcher

        # on different commands - answer in Telegram
        self.dp.add_handler(CommandHandler("help", self.help))
        self.dp.add_handler(CommandHandler("mode", self.mode))
        self.dp.add_handler(CommandHandler("margin", self.margin))
        self.dp.add_handler(CommandHandler("signal", self.signal))
        self.dp.add_handler(CommandHandler("btc_price", self.btc_price))
        self.dp.add_handler(CommandHandler("open_position", self.open_position))
        self.dp.add_handler(CommandHandler("order", self.order))

        # on noncommand i.e message - echo the message on Telegram
        self.dp.add_handler(MessageHandler(Filters.text, self.help))

        # log all errors
        self.dp.add_error_handler(self.error)

        # Start the Bot
        self.updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        # updater.idle()

    def PrintException(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        logger.info("[telegram] " + str('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)))
        execept_logger.info("[telegram] " + str('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)))

    def setApiKey(self):
        script_dir = pathlib.Path(__file__).parent.parent.parent

        rel_path = "client_api/telegram_apikey.txt"
        abs_file_path = os.path.join(script_dir, rel_path)

        r = open(abs_file_path, mode='rt', encoding='utf-8')
        list = r.read().splitlines()
        key = list[0]
        logger.info("[telegram][setApiKey] read success")
        settings.TELEGRAM_API_KEY = key

    # Define a few command handlers. These usually take the two arguments update and
    # context. Error handlers also receive the raised TelegramError object in error.
    def help(self, update, context):
        """Send a message when the command /help is issued."""
        update.message.reply_text('/help : Show all command we provide\n'
                                  '/mode : Short or Long currently\n'
                                  '/margin : Show what you have\n'
                                  '/signal : Show Stoch, RSI and Super Trend\n'
                                  '/btc_price : Show current BTC price\n'
                                  '/open_position : Ordered position\n'
                                  '/signal : Show Stoch and RSI\n'
                                  '/order : Show order')

    def mode(self, update, context):
        update.message.reply_text('Mode : ' + str(singleton_data.instance().getMode()))

    def margin(self, update, context):
        margin = self.custom_strategy.exchange.get_user_margin()
        margin_str =  '지갑 잔고      : ' + str(margin['walletBalance']/100000000)[:8] + '\n'
        margin_str += '미실현 손익   : ' + str(margin['unrealisedPnl']/100000000) + '\n'
        margin_str += '마진 밸런스   : ' + str(margin['marginBalance']/100000000)[:8] + '\n'
        margin_str += '포지션 마진   : ' + str(margin['maintMargin']/100000000)[:8] + '\n'
        margin_str += '주문 마진       : ' + str(margin['initMargin']/100000000)[:8] + '\n'
        margin_str += '사용가능 잔고 : ' + str(margin['excessMargin']/100000000)[:8] + '\n'
        margin_str += '마진 사용       : ' + str(margin['marginUsedPcnt'] * 100)[:4] + '\n'
        margin_str += '레버리지        : ' + str(margin['marginLeverage'])[:4] + '\n'

        update.message.reply_text(margin_str)

    def signal(self, update, context):
        signal_str = "[rsi] " + str(self.custom_strategy.analysis_1m['rsi'].values[0])[:5] + " + [stoch_d] " + str(self.custom_strategy.analysis_1m['stoch_d'].values[0])[:5] + " = " + str(self.custom_strategy.analysis_1m['rsi'].values[0] + self.custom_strategy.analysis_1m['stoch_d'].values[0])[:5] + '\n'
        signal_str += "[super_trend] " + str(self.custom_strategy.analysis_15m['SuperTrend'][0])[:7]
        update.message.reply_text(signal_str)

    def order(self, update, context):
        order_dist = settings.CURRENT_ORDER_DIST

        buy_orders = self.custom_strategy.exchange.get_orders('Buy')
        order_str = 'Order List\n' + '================\n ORDER_DIST : ' + str(order_dist) +'\n'
        if len(buy_orders) > 0:
            order_str += 'Buy order list\n'
            for i in buy_orders:
                order_str += '[주문가격] : ' + str(i['price']) + ' [수량] : ' + str(i['orderQty']) + '\n'

        sell_orders = self.custom_strategy.exchange.get_orders('Sell')
        if len(sell_orders) > 0:
            order_str += 'Sell order list\n'
            for i in sell_orders:
                order_str += '[주문가격] : ' + str(i['price']) + ' [수량] : ' + str(i['orderQty']) + '\n'


        update.message.reply_text(order_str)

    def btc_price(self, update, context):
        current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
        update.message.reply_text(str(current_price) + '$')

    def open_position(self, update, context):
        current_price = self.custom_strategy.exchange.get_instrument()['lastPrice']
        avgCostPrice = self.custom_strategy.exchange.get_avgCostPrice()
        currentQty = self.custom_strategy.exchange.get_currentQty()

        position_str =  '현재 가격 : ' + str(current_price) + '$\n'
        position_str +=  '평균 가격 : ' + str(avgCostPrice) + '\n'
        position_str += '수량     : ' + str(currentQty) + '\n'

        update.message.reply_text(position_str)
    '''
    def echo(self, update, context):
        """Echo the user message."""
        update.message.reply_text("You can use /help command")
    '''
    def error(self, update, context):
        """Log Errors caused by Updates."""

        execept_logger.info('[telegram] Update "%s" caused error "%s"', update, context.error)

    def send_msg(self, msg):

        try:
            self.dp.bot.sendMessage('1653838244', msg)
        except Exception as ex:
            self.PrintException()
