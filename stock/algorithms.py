#!/usr/bin/env python3

import logging
import pickle
from . import models
from os.path import realpath, dirname


TREND_CONFIG = dirname(realpath(__file__)) + '/trend_alg_config.pickle'


CONSERVATIVE = 0
MODERATE = 1
AGGRESSIVE = 2          # more frequent trading


def buy_all(stock):
    budget = stock.account.cash_to_trade
    if budget > stock.budget:
        budget = stock.budget

    return int(budget / stock.value)


class TradeAlgorithm:
    def trade_decision(self, stock):
        return 0


trend_variables = [
    {'up_count': 3, 'down_count': 4, 'pause_count': 7},  # conservative
    {'up_count': 2, 'down_count': 3, 'pause_count': 6},  # moderate
    {'up_count': 2, 'down_count': 2, 'pause_count': 5},  # aggressive
]
MIN_HISTORY = 10


class TrendAlgorithm(TradeAlgorithm):
    def __init__(self, dt):
        super(TrendAlgorithm, self).__init__()
        self.dt = dt

    def trade_decision(self, stock):
        try:
            pause_dict = pickle.load(open(TREND_CONFIG, 'rb'))
        except FileNotFoundError:
            pause_dict = {}

        up_count = trend_variables[stock.stance]['up_count']
        down_count = trend_variables[stock.stance]['down_count']
        pause_count = trend_variables[stock.stance]['pause_count']

        quotes = models.Quote.objects.filter(symbol=stock.symbol, date__lte=self.dt).order_by('-date')[:MIN_HISTORY]
        if len(quotes) < MIN_HISTORY:
            return 0

        keep_up = 0
        for n in range(MIN_HISTORY - 1):
            if quotes[n].price < quotes[n+1].price:
                break
            keep_up += 1
        keep_down = 0
        for n in range(MIN_HISTORY - 1):
            if quotes[n].price > quotes[n+1].price:
                break
            keep_down += 1
        logging.debug('%s: keep_up %d keep_down %d' % (stock.symbol, keep_up, keep_down))

        if keep_down >= pause_count:
            pause_dict[stock.symbol] = pause_count
            pickle.dump(pause_dict, open(TREND_CONFIG, 'wb'))
            logging.debug('%s: put in pause_dict' % stock.symbol)
            return -stock.count

        if not stock.count:
            if stock.symbol in pause_dict:
                logging.debug('%s: in pause_dict %d remain' % (stock.symbol, pause_dict[stock.symbol] - 1))
                pause_dict[stock.symbol] -= 1
                if pause_dict[stock.symbol] == 0:
                    del pause_dict[stock.symbol]
                pickle.dump(pause_dict, open(TREND_CONFIG, 'wb'))
                return 0
            if keep_up >= up_count:
                count = buy_all(stock)
                logging.debug('%s: buy %d' % (stock.symbol, count))
                return count
            return 0

        if keep_down >= down_count:
            logging.debug('%s: sell %d' % (stock.symbol, stock.count))
            return -stock.count

        return 0


class FillAlgorithm(TradeAlgorithm):
    def trade_decision(self, stock):
        total_value = stock.get_total_value()
        if total_value is None:
            return 0
        overflow = total_value - stock.budget

        logging.debug('fill: total_value - %f' % total_value)
        logging.debug('fill: overflow - %f' % overflow)

        return -int(overflow / stock.value)


class EmptyAlgorithm(TradeAlgorithm):
    def trade_decision(self, stock):
        return -stock.count


class OverBuyAlgorithm(TradeAlgorithm):
    def trade_decision(self, stock):
        return 10000000000


class OverSellAlgorithm(TradeAlgorithm):
    def trade_decision(self, stock):
        return -10000000000