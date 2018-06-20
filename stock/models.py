from django.db import models


class Quote(models.Model):
    class Meta:
        unique_together = (('symbol', 'date'),)

    symbol = models.CharField(max_length=10)
    date = models.DateTimeField('date of quote')
    price = models.FloatField('price of the symbol at the time')

    def __str__(self):
        return '%d/%d/%d: %s - %f' % (self.date.month, self.date.day, self.date.year, self.symbol, self.price)


class DayHistory(models.Model):
    class Meta:
        unique_together = (('symbol', 'date'),)

    symbol = models.CharField(max_length=10)
    date = models.DateField('date of the history')
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()

    def __str__(self):
        return '%2.2d/%2.2d/%4.4d - %s: open %f high %f low %f close %f volume %d' \
               % (self.date.month, self.date.day, self.date.year, self.symbol,
                  self.open, self.high, self.low, self.close, self.volume)


class SimHistory(models.Model):
    class Meta:
        unique_together = (('symbol', 'date'),)

    date = models.DateTimeField('date of quote')
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


MODE_SETUP = 0
MODE_RUN = 1
MODE_STOP = 2
MODE_CHOICE = (
    (MODE_SETUP, 'setup'),
    (MODE_RUN, 'run'),
    (MODE_STOP, 'stop'),
)


class Account(models.Model):
    account_id = models.IntegerField(primary_key=True)
    mode = models.IntegerField(default='setup', choices=MODE_CHOICE)
    net_value = models.FloatField(null=True, blank=True)
    cash_to_trade = models.FloatField(null=True, blank=True)

    def __str__(self):
        mode_string = 'unknown'
        for en in MODE_CHOICE:
            if en[0] == self.mode:
                mode_string = en[1]
        if self.net_value:
            return '%d: %s = %f' % (self.account_id, mode_string, self.net_value)
        else:
            return '%d: %s = 0.0' % (self.account_id, mode_string)


class DayReport(models.Model):
    class Meta:
        unique_together = (('date', 'account'),)

    date = models.DateField()
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    net_value = models.FloatField()
    cash_to_trade = models.FloatField()

    def __str__(self):
        return '%d/%d/%d - %d: net %f (cash %f, equity %f)' % (self.date.month,
                                                               self.date.day,
                                                               self.date.year,
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

ALGORITHM_FILL = 0
ALGORITHM_AHNYUNG = 1
ALGORITHM_EMPTY = 2
ALGORITHM_TREND = 3
ALGORITHM_DAY_TREND = 4
ALGORITHM_CHOICE = (
    (ALGORITHM_FILL, 'fill'),
    (ALGORITHM_AHNYUNG, 'ahnyung'),
    (ALGORITHM_EMPTY, 'empty'),
    (ALGORITHM_TREND, 'trend'),
    (ALGORITHM_DAY_TREND, 'day_trend'),
)


class Stock(models.Model):
    class Meta:
        unique_together = (('account', 'symbol'),)

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    share = models.FloatField('budget rate in the account')
    algorithm = models.IntegerField(choices=ALGORITHM_CHOICE)
    stance = models.IntegerField(choices=STANCE_CHOICE)
    count = models.IntegerField(null=True, default=0, blank=True)
    last_value = models.FloatField(null=True, blank=True)
    last_count = models.FloatField(null=True, blank=True)
    last_sell_price = models.FloatField(null=True, blank=True)
    last_buy_price = models.FloatField(null=True, blank=True)

    def __str__(self):
        return '%d: %s - count %d' % (self.account.account_id,
                                      self.symbol,
                                      self.count)


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


class Trade(models.Model):
    class Meta:
        unique_together = (('account_id', 'symbol', 'date'),)

    account_id = models.IntegerField()
    symbol = models.CharField(max_length=10)
    date = models.DateTimeField('trade date')
    price = models.FloatField()
    count = models.IntegerField()
    action = models.IntegerField(choices=ACTION_CHOICE)

    def __str__(self):
        action_string = 'unknown'
        for en in ACTION_CHOICE:
            if en[0] == self.action:
                action_string = en[1]
        return '%d/%d/%d - %d: %s %s %f' % (self.date.month,
                                            self.date.day,
                                            self.date.year,
                                            self.account_id,
                                            self.symbol,
                                            action_string,
                                            self.price * self.count)


class OrderID(models.Model):
    order_id = models.IntegerField()
