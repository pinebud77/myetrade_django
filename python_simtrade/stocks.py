from django.utils import timezone
import stock.models as models
import logging


TRANSACTION_FEE = 6.95


class Quote:
    def __init__(self, symbol):
        self.symbol = symbol
        self.ask = None
        self.bid = None

    def update(self, cur_time):
        try:
            history = models.SimHistory.objects.filter(symbol=self.symbol, date__lte=cur_time.date()).order_by('-date')[0]
        except IndexError:
            return False
        self.ask = history.open
        self.bid = history.open

        logging.debug('quote: %s' % self.symbol)
        logging.debug('ask: %f' % self.ask)
        logging.debug('bid: %f' % self.bid)

        return True


class Stock:
    def __init__(self, symbol, account):
        self.symbol = symbol
        self.account = account
        self.count = None
        self.value = None
        self.last_count = 0
        self.budget = 0.0
        self.algorithm = 0
        self.stance = 0
        self.valid = True
        self.failure_reason = 'success'

    def update(self, dt):
        quote = Quote(self.symbol)
        res = quote.update(dt)
        if not res:
            self.valid = False
            return False
        self.value = (quote.ask + quote.bid) / 2
        logging.debug('\nupdating stock')
        logging.debug('stock: %s' % self.symbol)
        logging.debug('ask: %f' % self.value)

        return True

    def get_failure_reason(self):
        return self.failure_reason

    def market_order(self, count, order_id):
        if not self.valid:
            logging.error('no such stock yet :)')
            return False
        if count < 0 and -count > self.count:
            logging.error('market_order: not enough stock count')
            self.failure_reason = 'not enough stock count'
            return False
        if count > 0 and count * self.value > self.account.cash_to_trade:
            logging.error('market_order: not enough cash')
            self.failure_reason = 'not enough cash'
            return False

        self.failure_reason = 'success'

        self.count += count
        self.account.cash_to_trade -= count * self.value
        self.account.cash_to_trade -= TRANSACTION_FEE

        logging.debug('trade complete: %s %d' % (self.symbol, count))

        return True

    def get_total_value(self):
        if not self.valid:
            logging.error('no such stock yet :)')
            return None
        if self.count is None:
            logging.error('get_total_value: count is None')
            return None
        if self.value is None:
            logging.error('get_total_value: value is None')
            return None

        return self.count * self.value
