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

from django.db import models
from .algorithms import in_algorithm_list, out_algorithm_list


class Quote(models.Model):
    class Meta:
        unique_together = (('symbol', 'dt'),)

    symbol = models.CharField(max_length=10)
    dt = models.DateTimeField('date of quote')
    ask = models.FloatField('ask of the symbol at the time')
    bid = models.FloatField('bid of the symbol at the time')

    def __str__(self):
        return '%s: %s - ask %f bid %f' % (str(self.dt), self.symbol, self.ask, self.bid)


class DayHistory(models.Model):
    class Meta:
        unique_together = (('symbol', 'date'),)

    symbol = models.CharField(max_length=10)
    date = models.DateField('date of the history')
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField()

    def __str__(self):
        return '%2.2d/%2.2d/%4.4d - %s: open %f high %f low %f close %f volume %f' \
               % (self.date.month, self.date.day, self.date.year, self.symbol,
                  self.open, self.high, self.low, self.close, self.volume)


class SimHistory(models.Model):
    class Meta:
        unique_together = (('symbol', 'date'),)

    date = models.DateField('date of quote')
    symbol = models.CharField(max_length=10)
    open = models.FloatField('open of the symbol at the time')
    high = models.FloatField('high of the symbol at the time')
    low = models.FloatField('low of the symbol at the time')
    close = models.FloatField('close of the symbol at the time')
    volume = models.FloatField('volume of the symbol at the time')

    def __str__(self):
        return '%2.2d/%2.2d/%4.4d - %s: open %f high %f low %f close %f volume %d' \
               % (self.date.month, self.date.day, self.date.year, self.symbol,
                  self.open, self.high, self.low, self.close, self.volume)


ACCOUNT_ETRADE = 0
ACCOUNT_COINBASE = 1
ACCOUNT_SIMULATION = 2
ACCOUNT_CHOICE = (
    (ACCOUNT_ETRADE, 'E*TRADE'),
    (ACCOUNT_COINBASE, 'Coinbase'),
    (ACCOUNT_SIMULATION, 'Simulation'),
)

class Account(models.Model):
    account_type = models.IntegerField(choices=ACCOUNT_CHOICE)
    account_id = models.IntegerField(primary_key=True)
    net_value = models.FloatField(null=True, blank=True)
    cash_to_trade = models.FloatField(null=True, blank=True)

    def __str__(self):
        if self.net_value:
            return '%d: %f' % (self.account_id, self.net_value)
        else:
            return '%d: 0.0' % (self.account_id)


class DayReport(models.Model):
    class Meta:
        unique_together = (('date', 'account'),)

    date = models.DateField()
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    net_value = models.FloatField()
    cash_to_trade = models.FloatField()

    def __str__(self):
        return '%d/%d/%d - %d: net %f (cash %f, equity %f)' % (self.date.month, self.date.day, self.date.year,
                                                               self.account.account_id,
                                                               self.net_value,
                                                               self.cash_to_trade,
                                                               self.net_value - self.cash_to_trade)


STANCE_CONSERVATIVE = 0
STANCE_MODERATE = 1
STANCE_AGGRESSIVE = 2
STANCE_CHOICE = (
    (STANCE_CONSERVATIVE, 'conservative'),
    (STANCE_MODERATE, 'moderate'),
    (STANCE_AGGRESSIVE, 'aggressive'),
)


def get_alg_choice():
    in_alg_choice = []
    out_alg_choice = []

    num = 0
    for alg in in_algorithm_list:
        in_alg_choice.append((num, alg.name))
        num += 1

    num = 0
    for alg in out_algorithm_list:
        out_alg_choice.append((num, alg.name))
        num += 1

    return in_alg_choice, out_alg_choice


class Stock(models.Model):
    class Meta:
        unique_together = (('account', 'symbol'),)

    in_alg_choice, out_alg_choice = get_alg_choice()

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    share = models.FloatField('budget rate in the account')
    in_algorithm = models.IntegerField(choices=in_alg_choice)
    in_stance = models.IntegerField(choices=STANCE_CHOICE)
    out_algorithm = models.IntegerField(choices=out_alg_choice)
    out_stance = models.IntegerField(choices=STANCE_CHOICE)
    count = models.FloatField(null=True, default=0, blank=True)
    last_count = models.FloatField(null=True, blank=True)

    def __str__(self):
        return '%s - count %f' % (self.symbol, self.count)


class FailureReason(models.Model):
    message = models.CharField(primary_key=True, max_length=300)

    def __str__(self):
        return str(self.message)


ACTION_BUY = 0
ACTION_SELL = 1
ACTION_BUY_FAIL = 2
ACTION_SELL_FAIL = 3
ACTION_CHOICE = (
    (ACTION_BUY, 'buy'),
    (ACTION_SELL, 'sell'),
    (ACTION_BUY_FAIL, 'buy_fail'),
    (ACTION_SELL_FAIL, 'sell_fail'),
)


class Order(models.Model):
    class Meta:
        unique_together = (('account_id', 'symbol', 'dt'),)

    account_id = models.IntegerField()
    symbol = models.CharField(max_length=10)
    dt = models.DateTimeField('order date')
    price = models.FloatField()
    count = models.FloatField()
    action = models.IntegerField(choices=ACTION_CHOICE)
    failure_reason = models.ForeignKey(FailureReason, on_delete=models.CASCADE)

    def __str__(self):
        action_string = 'unknown'
        for en in ACTION_CHOICE:
            if en[0] == self.action:
                action_string = en[1]
        return '%s - %d: %s %s %f %s' % (str(self.dt), self.account_id, self.symbol, action_string,
                                         self.price * self.count, self.failure_reason.message)


class OrderID(models.Model):
    order_id = models.IntegerField()
