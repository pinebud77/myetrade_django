#!/usr/bin/env python3

import logging
import pickle
from . import models
from os.path import realpath, dirname


TREND_CONFIG = dirname(realpath(__file__)) + '/trend_alg_config.pickle'


CONSERVATIVE = 0
MODERATE = 1
AGGRESSIVE = 2          # more frequent trading


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
        super(TradeAlgorithm, self).__init__()
        self.dt = dt

    def trade_decision(self, stock):
        try:
            pause_dict = pickle.load(open(TREND_CONFIG, 'rb'))
        except FileNotFoundError:
            pause_dict = {}

        up_count = trend_variables[stock.stance]['up_count']
        down_count = trend_variables[stock.stance]['down_count']
        pause_count = trend_variables[stock.stance]['pause_count']

        quotes = models.Quote.objects.filter(symbol=stock.symbol, date__lt=self.dt).order_by('-date')[:MIN_HISTORY]
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
                budget = stock.account.cash_to_trade
                if budget > stock.budget:
                    budget = stock.budget
                count = int(budget / stock.value)
                logging.debug('%s: buy %d' % (stock.symbol, count))
                return count
            return 0

        if keep_down >= down_count:
            logging.debug('%s: sell %d' % (stock.symbol, stock.count))
            return -stock.count

        return 0


ahnyung_variables = [
    {'day_low': -0.01, 'overall_low': -0.02, 'buy_again': -0.05, 'over_sell': 0.04},
    {'day_low': -0.01, 'overall_low': -0.015, 'buy_again': -0.04, 'over_sell': 0.03},
    {'day_low': -0.01, 'overall_low': -0.01, 'buy_again': -0.03, 'over_sell': 0.02},
]


class AhnyungAlgorithm(TradeAlgorithm):
    def trade_decision(self, stock):
        budget = stock.account.cash_to_trade
        if budget > stock.budget:
            budget = stock.budget

        logging.debug('ahnyung: budget %f' % stock.budget)

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
        if total_value is None:
            return 0
        overflow = total_value - stock.budget

        logging.debug('fill: total_value - %f' % total_value)
        logging.debug('fill: overflow - %f' % overflow)

        return -int(overflow / stock.value)


class EmptyAlgorithm(TradeAlgorithm):
    def trade_decision(self, stock):
        return -stock.count
