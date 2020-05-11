#!/usr/bin/env python3

# Owen Kwon, hereby disclaims all copyright interest in the program "myetrade_django" written by Owen (Ohkeun) Kwon.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>

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
