#!/usr/bin/env python3

import sqlite3


CONSERVATIVE = 0
MODERATE = 1
AGGRESSIVE = 2          # more frequent trading


class TradeAlgorithm:
    def trade_decision(self, stock):
        return 0


ahnyung_variables = [
    {"day_low": -0.01, "overall_low": -0.02, "buy_again": -0.05, "over_sell": 0.04},
    {"day_low": -0.01, "overall_low": -0.015, "buy_again": -0.04, "over_sell": 0.03},
    {"day_low": -0.01, "overall_low": -0.01, "buy_again": -0.03, "over_sell": 0.02},
]


class AhnyungAlgorithm(TradeAlgorithm):
    def trade_decision(self, stock):
        total_value = stock.get_total_value()
        if total_value is None:
            return 0

        budget = stock.account.cash_to_trade
        if budget > stock.budget:
            budget = stock.budget

        if not stock.count:
            decrease_rate = (stock.last_sell_price - stock.value) / stock.value
            if decrease_rate < ahnyung_variables[stock.stance]['buy_again']:
                return int(budget / stock.value)
        else:
            day_change_rate = (stock.value - stock.last_value) / stock.value
            if day_change_rate < ahnyung_variables[stock.stance]['day_low']:
                return -stock.count

            overall_change_rate = (stock.last_buy_price - stock.value) / stock.value
            if overall_change_rate < ahnyung_variables[stock.stance]['overall_low']:
                return -stock.count

            if overall_change_rate > ahnyung_variables[stock.stance]['over_sell']:
                return -stock.count

        return 0


class FillAlgorithm(TradeAlgorithm):
    def trade_decision(self, stock):
        total_value = stock.get_total_value()
        overflow = total_value - stock.budget

        return -int(overflow / stock.value)


class EmptyAlgorithm(TradeAlgorithm):
    def trade_decision(self, stock):
        return -stock.count


class UpDownAlgorithm(TradeAlgorithm):
    def __init__(self, account=None):
        super(UpDownAlgorithm, self).__init__()
        self.account = account
        self.conn = sqlite3.connect('updown_quotes.db')

        self.ensure_table()

    def ensure_table(self):
        c = self.conn.cursor()
        if not c.execute('''SELECT name FROM sqlite_master WHERE type='table' AND name='quotes';'''):
            c.execute('''CREATE TABLE quotes (date text, symbol text, price real)''')
            self.conn.commit()
