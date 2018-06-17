#!/usr/bin/env python3

import logging
from . import algorithms
from . import models
from .config import *
from .algorithms import AhnyungAlgorithm, FillAlgorithm
from datetime import datetime, timedelta
import python_etrade.client as etclient
import python_simtrade.client as simclient
import holidays


LOG_FORMAT = '%(asctime)-15s %(message)s'


def load_db_account(db_account, account):
    account.mode = models.MODE_CHOICE[db_account.mode][1]


def store_db_account(db_account, account):
    for en in models.MODE_CHOICE:
        if en[1] == account.mode:
            db_account.mode = en[0]
    db_account.net_value = account.net_value
    db_account.cash_to_trade = account.cash_to_trade
    db_account.save()


def load_db_stock(db_stock, stock):
    stock.budget = stock.account.net_value * db_stock.share
    stock.algorithm_string = models.ALGORITHM_CHOICE[db_stock.algorithm][1]

    stock.stance = db_stock.stance
    stock.last_sell_price = db_stock.last_sell_price
    stock.last_buy_price = db_stock.last_buy_price
    stock.last_value = db_stock.last_value
    stock.last_count = db_stock.last_count

    if stock.last_sell_price is None:
        stock.last_sell_price = 0
    if stock.last_buy_price is None:
        stock.last_buy_price = 0
    if stock.last_value is None:
        stock.last_value = 0
    if stock.last_count is None:
        stock.last_count = 0


def store_db_stock(db_stock, stock):
    db_stock.value = stock.value
    db_stock.count = stock.count
    db_stock.last_sell_price = stock.last_sell_price
    db_stock.last_buy_price = stock.last_buy_price
    db_stock.last_value = stock.last_value
    db_stock.last_count = stock.last_count
    db_stock.save()


def run(dt=None):
    if dt is None:
        client = etclient.Client()
        result = client.login(etrade_consumer_key,
                              etrade_consumer_secret,
                              etrade_username,
                              etrade_passwd)
    else:
        client = simclient.Client()
        result = client.login(dt)
    if not result:
        logging.error('login failed')
        exit(-1)
    logging.debug('logged in')

    alg_ahnyung = AhnyungAlgorithm()
    alg_fill = FillAlgorithm()

    order_ids = models.OrderIndex.objects.all()
    if not order_ids:
        order_id_obj = models.OrderIndex()
        order_id_obj.order_id = 200
        order_id_obj.save()
        order_ids = models.OrderIndex.objects.all()

    order_id_obj = order_ids[0]
    order_id = order_id_obj.order_id

    for db_account in models.Account.objects.all():
        account = client.get_account(db_account.account_id)
        load_db_account(db_account, account)

        logging.debug('account mode: %s' % account.mode)

        trade_failed = False

        for db_stock in models.Stock.objects.filter(account=db_account):
            stock = account.get_stock(db_stock.symbol)
            if not stock:
                stock = account.new_stock(db_stock.symbol)

            load_db_stock(db_stock, stock)

            decision = 0
            if account.mode == 'setup':
                logging.debug('run algorithm: fill')
                decision = alg_fill.trade_decision(stock)
            elif account.mode == 'run':
                logging.debug('run algorithm: %s' % stock.algorithm_string)
                if stock.algorithm_string == 'ahnyung':
                    decision = alg_ahnyung.trade_decision(stock)

            logging.debug('decision=%d' % decision)

            if decision != 0:
                stock.last_count = stock.count

                trade = models.Trade()
                trade.account_id = account.id
                trade.symbol = stock.symbol
                if not dt:
                    trade.date = datetime.now()
                else:
                    trade.date = dt
                trade.price = stock.value

                if decision > 0:
                    if stock.market_order(decision, order_id):
                        trade.type = models.TRADE_BUY
                    else:
                        trade.type = models.TRADE_BUY_FAIL
                        trade_failed = True
                elif decision < 0:
                    if stock.market_order(decision, order_id):
                        trade.type = models.TRADE_SELL
                    else:
                        trade.type = models.TRADE_SELL_FAIL
                        trade_failed = True

                order_id += 1
                trade.save()

            if not trade_failed and account.mode == 'setup':
                stock.last_buy_price = stock.value
                stock.last_sell_price = stock.value
                stock.last_value = stock.value

            store_db_stock(db_stock, stock)

        if not trade_failed and account.mode == 'setup':
            account.mode = 'run'
        account.update()

        store_db_account(db_account, account)

    order_id_obj.order_id = order_id
    order_id_obj.save()

    client.logout()
    logging.debug('logged out')


def simulate():
    logging.basicConfig(level=logging.DEBUG)

    models.Trade.objects.all().delete()

    for db_account in models.Account.objects.all():
        db_account.mode = models.MODE_SETUP
        db_account.save()

        for db_stock in models.Stock.objects.filter(account=db_account):
            db_stock.count = 0
            db_stock.save()

    first_quote = models.Quote.objects.all().order_by('date')[0]
    last_quote = models.Quote.objects.all().order_by('-date')[0]

    cur_dt = datetime(year=first_quote.date.year,
                      month=first_quote.date.month,
                      day=first_quote.date.day,
                      hour=8,
                      minute=0,
                      second=0)

    last_dt = datetime(year=last_quote.date.year,
                       month=last_quote.date.month,
                       day=last_quote.date.day,
                       hour=23,
                       minute=59,
                       second=59)

    day_delta = timedelta(1)
    us_holidays = holidays.UnitedStates()

    while cur_dt < last_dt:
        if cur_dt in us_holidays:
            cur_dt += day_delta
            continue
        print('running: ' + str(cur_dt))
        run(cur_dt)
        cur_dt += day_delta

