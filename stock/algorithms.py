#!/usr/bin/env python3
import logging
import pickle
import random
from . import models
from os.path import realpath, dirname, join


logger = logging.getLogger('algorithms')
TREND_CONFIG = join(dirname(realpath(__file__)),'trend_alg_config.pickle')


algorithm_list = []


CONSERVATIVE = 0
MODERATE = 1
AGGRESSIVE = 2          # more frequent trading


def buy_all(stock):
    budget = stock.account.cash_to_trade
    if budget > stock.budget:
        budget = stock.budget

    return budget / stock.value


def sell_all(stock):
    return -stock.count


class TradeAlgorithm:
    name = None

    def trade_decision(self, stock, time_now=None):
        return 0


trend_variables = [
    {'up_count': 4, 'down_count': 4, 'pause_count': 5},  # conservative
    {'up_count': 3, 'down_count': 3, 'pause_count': 4},  # moderate
    {'up_count': 2, 'down_count': 2, 'pause_count': 3},  # aggressive
]
MIN_HISTORY = 10


class MonkeyAlgorithm(TradeAlgorithm):
    name = 'Monkey'

    def trade_decision(self, stock):
        logger.debug('kikikik')
        val = random.random()
        if not stock.count and val > 0.85:
            logger.debug('buy all')
            return buy_all(stock)

        if stock.count and val > 0.85:
            logger.debug('sell all')
            return -stock.count

        return 0


class FillAlgorithm(TradeAlgorithm):
    name = 'Fill'

    def trade_decision(self, stock):
        total_value = stock.get_total_value()
        if total_value is None:
            logger.error('huh total value of stock is None : symbol %s' % stock.symbol)
            return 0
        overflow = total_value - stock.budget

        logger.debug('fill: total_value - %f' % total_value)
        logger.debug('fill: overflow - %f' % overflow)

        return -overflow / stock.value


class EmptyAlgorithm(TradeAlgorithm):
    name = 'Empty'

    def trade_decision(self, stock):
        return -stock.count


class HoldAlgorithm(TradeAlgorithm):
    name = 'Hold'

    def trade_decision(self, stock):
        return 0


algorithm_list.append(FillAlgorithm)
algorithm_list.append(EmptyAlgorithm)
algorithm_list.append(HoldAlgorithm)
algorithm_list.append(MonkeyAlgorithm)

