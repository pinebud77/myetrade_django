from datetime import datetime
import stock.models as models
import logging


TRANSACTION_FEE = 6.95


class Quote:
    def __init__(self, symbol):
        self.symbol = symbol
        self.ask = None

    def update(self, cur_time):
        dt = datetime(year=cur_time.year,
                      month=cur_time.month,
                      day=cur_time.day,
                      hour=23,
                      minute=59,
                      second=59)
        try:
            quote = models.SimQuote.objects.filter(symbol=self.symbol, date__lt=dt).order_by('-date')[0]
        except IndexError:
            return False
        self.ask = quote.price

        logging.debug('quote: %s' % self.symbol)
        logging.debug('price: %f' % self.ask)
        return True


class Stock:
    def __init__(self, symbol, account):
        self.symbol = symbol
        self.account = account
        self.count = None
        self.value = None
        self.last_value = 0.0
        self.last_sell_price = 0.0
        self.last_buy_price = 0.0
        self.last_count = 0
        self.budget = 0.0
        self.algorithm_string = 'ahnyung'
        self.stance = 1
        self.valid = True

    def update(self, dt):
        quote = Quote(self.symbol)
        res = quote.update(dt)
        if not res:
            self.valid = False
            return False
        self.value = quote.ask
        logging.debug('stock: %s' % self.symbol)
        logging.debug('price: %f' % self.value)

        return True

    def market_order(self, count, order_id):
        if not self.valid:
            return False
        if count < 0 and -count > self.count:
            logging.error('market_order: no enough stock count')
            return False
        if count > 0 and count * self.value > self.account.cash_to_trade:
            logging.error('market_order: no enough cash')
            return False

        self.count += count
        self.account.cash_to_trade -= count * self.value
        self.account.cash_to_trade -= TRANSACTION_FEE

        logging.debug('trade complete: %s %d' % (self.symbol, count))

        return True

    def get_total_value(self):
        if not self.valid:
            return None
        if self.count is None:
            logging.error('get_total_value: count is None')
            return None
        if self.value is None:
            logging.error('get_total_value: value is None')
            return None

        return self.count * self.value
