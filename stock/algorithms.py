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
import pickle
import random
from . import models
from os.path import realpath, dirname, join


logger = logging.getLogger('algorithms')

in_algorithm_list = []
out_algorithm_list = []


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


in_algorithm_list.append(MonkeyAlgorithm)
out_algorithm_list.append(MonkeyAlgorithm)


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

in_algorithm_list.append(FillAlgorithm)


class EmptyAlgorithm(TradeAlgorithm):
    name = 'Empty'

    def trade_decision(self, stock):
        if stock.count:
            return sell_all(stock)

        return 0

out_algorithm_list.append(EmptyAlgorithm)


class HoldAlgorithm(TradeAlgorithm):
    name = 'Hold'

    def trade_decision(self, stock):
        return 0

in_algorithm_list.append(HoldAlgorithm)
out_algorithm_list.append(HoldAlgorithm)


up_variables = (
    {'consecutive_up': 5},      #conservative
    {'consecutive_up': 3},
    {'consecutive_up': 2},
)

class UpAlgorithm(TradeAlgorithm):
    name = 'ConsecutiveUp'

    def trade_decision(self, stock):
        if stock.count:
            return 0

        consecutive_up = up_variables[stock.in_stance]['consecutive_up']

        logger.debug('evaluating: %s' % stock.symbol)

        histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[0:consecutive_up]

        if len(histories) < consecutive_up:
            logger.info('not enough history yet')
            return 0

        for i in range(len(histories) - 1):
            if histories[i].open < histories[i+1].open:
                return 0

        return buy_all(stock)

in_algorithm_list.append(UpAlgorithm)


ahnyung_variable = (
    {'out_rate': 1.200, 'emergency_rate': 0.6},        #conservative
    {'out_rate': 1.100, 'emergency_rate': 0.7},
    {'out_rate': 1.030, 'emergency_rate': 0.8},
)

class AhnyungAlgorithm(TradeAlgorithm):
    name = 'Anhyung'

    def trade_decision(self, stock):
        if not stock.count:
            return 0

        out_rate = ahnyung_variable[stock.out_stance]['out_rate']
        emergency_rate = ahnyung_variable[stock.out_stance]['emergency_rate']

        logger.debug('evaluating: %s' % stock.symbol)

        try:
            order = models.Order.objects.filter(
                symbol=stock.symbol,
                account_id=stock.account.id,
                action=models.ACTION_BUY).order_by('-dt')[0]
        except IndexError:
            logger.info('there is no order information yet')
            return 0

        print('value=%f, prev_buy=%f' % (stock.value, order.price))

        if (order.price * out_rate) < stock.value:
            return sell_all(stock)

        if (order.price * emergency_rate) > stock.value:
            return sell_all(stock)

        return 0

out_algorithm_list.append(AhnyungAlgorithm)


vertex_variable = (
    {'period': 5},      #conservative
    {'period': 4},
    {'period': 3},
)

class VertexAlgorithm(TradeAlgorithm):
    name = 'Vertex'

    def trade_decision(self, stock):
        if stock.count:
            period = vertex_variable[stock.out_stance]['period']
        else:
            period = vertex_variable[stock.in_stance]['period']

        logger.debug('evaluating: %s' % stock.symbol)

        histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[0:period]

        if len(histories) < period:
            logger.info('not enough history yet')
            return 0

        old_rate = 0
        new_rate = stock.value - histories[0].open
        for i in range(len(histories) - 1):
            old_rate += histories[i].open - histories[i+1].open

            if i == len(histories) - 1:
                continue

            new_rate += histories[i].open - histories[i+1].open

        if stock.count and old_rate > 0  and new_rate < 0:
            return sell_all(stock)
        elif not stock.count and old_rate < 0 and new_rate > 0:
            return buy_all(stock)

        return 0

in_algorithm_list.append(VertexAlgorithm)
out_algorithm_list.append(VertexAlgorithm)
