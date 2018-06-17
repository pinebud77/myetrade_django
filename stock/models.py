from django.db import models


class QuoteName(models.Model):
    symbol = models.CharField(max_length=10, primary_key=True)

    def __str__(self):
        return str(self.symbol)


class Quote(models.Model):
    class Meta:
        indexes = [models.Index(fields=['name', '-date',]),]

    id = models.AutoField(primary_key=True)
    name = models.ForeignKey(QuoteName, on_delete=models.CASCADE)
    date = models.DateTimeField('date of quote')
    price = models.FloatField('price of the symbol at the time')

    def __str__(self):
        return '%d/%d/%d: %s - %f' % (self.date.month, self.date.day, self.date.year, self.name.symbol, self.price)


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
        if self.net_value:
            return '%d: %s = %f' % (self.account_id, self.mode, self.net_value)
        else:
            return '%d: %s = 0.0' % (self.account_id, self.mode)


STANCE_CONSERVATIVE =0
STANCE_MODERATE =1
STANCE_AGGRESSIVE =2

STANCE_CHOICE = (
    (STANCE_CONSERVATIVE, 'conservative'),
    (STANCE_MODERATE, 'moderate'),
    (STANCE_AGGRESSIVE, 'aggressive'),
)

ALGORITHM_FILL = 0
ALGORITHM_AHNYUNG = 1
ALGORITHM_EMPTY = 2

ALGORITHM_CHOICE = (
    (ALGORITHM_FILL, 'fill'),
    (ALGORITHM_AHNYUNG, 'ahnyung'),
    (ALGORITHM_EMPTY, 'empty'),
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


TRADE_BUY = 0
TRADE_SELL = 1
TRADE_BUY_FAIL = 2
TRADE_SELL_FAIL = 3

TRADE_CHOICE = (
    (TRADE_BUY, 'buy'),
    (TRADE_SELL, 'sell'),
    (TRADE_BUY_FAIL, 'buy_fail'),
    (TRADE_SELL_FAIL, 'sell_fail'),
)


class Trade(models.Model):
    class Meta:
        indexes = [models.Index(fields=['account_id', 'symbol', '-date',]),]

    id = models.AutoField(primary_key=True)
    account_id = models.IntegerField()
    symbol = models.CharField(max_length=10)
    date = models.DateTimeField('trade date')
    price = models.FloatField()
    type = models.IntegerField(choices=TRADE_CHOICE)


class OrderIndex(models.Model):
    order_id = models.IntegerField()
