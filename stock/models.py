from django.db import models


class Quote(models.Model):
    id = models.AutoField(primary_key=True)
    symbol = models.CharField(max_length=10)
    date = models.DateTimeField('date of quote')
    price = models.FloatField('price of the symbol at the time')


class Account(models.Model):
    account_id = models.IntegerField(primary_key=True)
    mode = models.CharField(max_length=10, default='setup', blank=True)
    net_value = models.FloatField(null=True, blank=True)
    cash_to_trade = models.FloatField(null=True, blank=True)

    def __str__(self):
        if self.net_value:
            return '%d: %s = %f' % (self.account_id, self.mode, self.net_value)
        else:
            return '%d: %s = 0.0' % (self.account_id, self.mode)


STANCE_CHOICE = (
    (0, 'conservative'),
    (1, 'moderate'),
    (2, 'aggressive'),
)

ALGORITHM_CHOICE = (
    (0, 'fill'),
    (1, 'ahnyung'),
    (2, 'empty'),
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


TRADE_CHOICE = (
    (0, 'buy'),
    (1, 'sell'),
    (2, 'sell_fail'),
    (3, 'sell_fail'),
)


class Trade(models.Model):
    id = models.AutoField(primary_key=True)
    account_id = models.IntegerField()
    symbol = models.CharField(max_length=10)
    date = models.DateTimeField('trade date')
    price = models.FloatField()
    type = models.IntegerField(choices=TRADE_CHOICE)


class OrderIndex(models.Model):
    order_id = models.IntegerField()