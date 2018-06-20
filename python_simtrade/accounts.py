import logging
from . import stocks


class Account:
    def __init__(self, id, dt):
        self.id = id
        self.net_value = None
        self.cash_to_trade = None
        self.stock_list = []
        self.mode = 'setup'
        self.dt = dt

    def update(self, dt=None):
        if dt:
            self.dt = dt

        self.net_value = self.cash_to_trade
        for stock in self.stock_list:
            res = stock.update(self.dt)
            if not res:
                continue
            self.net_value += stock.value * stock.count

        logging.debug('\nupdating account')
        logging.debug('Account: %d' % self.id)
        logging.debug('Net value: %f' % self.net_value)
        logging.debug('cash to trade: %f' % self.cash_to_trade)
        logging.debug('Stocks: ' + str(self.stock_list))

        return True

    def get_stock(self, symbol):
        for stock in self.stock_list:
            if stock.symbol == symbol:
                return stock

        return None

    def new_stock(self, symbol):
        stock = stocks.Stock(symbol, self)
        if not stock.update(self.dt):
            return None
        stock.count = 0
        self.stock_list.append(stock)

        return stock
