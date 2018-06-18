#!/usr/bin/env python3

import logging
from . import models
from .config import *
from .algorithms import AhnyungAlgorithm, FillAlgorithm, TrendAlgorithm
from datetime import date, datetime, timedelta
from python_simtrade.client import reset_sim_config
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


def store_day_report(db_account, dt):
    try:
        prev_report = models.DayReport.objects.filter(account=db_account, date__lte=dt).order_by('-date')[0]
        if prev_report.date.year == dt.year and prev_report.date.month == dt.month and prev_report.date.day == dt.day:
            prev_report.delete()
    except IndexError:
        pass
    day_report = models.DayReport()
    day_report.date = dt
    day_report.account = db_account
    day_report.net_value = db_account.net_value
    day_report.cash_to_trade = db_account.cash_to_trade
    day_report.save()


def store_trade(stock, dt, decision, failed):
    trade = models.Trade()

    trade.date = dt
    trade.symbol = stock.symbol
    trade.account_id = stock.account.id
    trade.count = abs(decision)
    trade.price = stock.value

    if decision > 0 and not failed:
        trade.action = models.ACTION_BUY
    elif decision > 0:
        trade.action = models.ACTION_BUY_FAIL
    elif decision < 0 and not failed:
        trade.action = models.ACTION_SELL
    else:
        trade.action = models.ACTION_SELL_FAIL

    trade.save()


def get_quotes(client, dt):
    symbol_list = []
    for stock in models.Stock.objects.all():
        if str(stock.symbol) not in symbol_list:
            symbol_list.append(str(stock.symbol))

    for symbol in symbol_list:
        quote = client.get_quote(symbol)
        if quote is None:
            continue
        try:
            prev_quote = models.Quote.objects.filter(symbol=symbol, date__lt=dt).order_by('-date')[0]
            day_start = datetime(year=dt.year, month=dt.month, day=dt.day,
                                 hour=0, minute=0, second=0)
            if day_start < prev_quote.date:
                continue
        except IndexError:
            pass

        db_quote = models.Quote()
        db_quote.date = dt
        db_quote.symbol = symbol
        db_quote.price = quote.ask
        db_quote.save()


alg_ahnyung = AhnyungAlgorithm()
alg_fill = FillAlgorithm()
alg_trend = TrendAlgorithm(None)


def run(dt=None, client=None):
    if dt is None:
        dt = datetime.now()

    need_logout = False
    if client is None:
        client = etclient.Client()
        result = client.login(etrade_consumer_key,
                              etrade_consumer_secret,
                              etrade_username,
                              etrade_passwd)
        if not result:
            logging.error('login failed')
            return
        logging.debug('logged in')
        need_logout = True

    alg_trend.dt = dt

    get_quotes(client, dt)

    order_ids = models.OrderID.objects.all()
    if not order_ids:
        order_id_obj = models.OrderID()
        order_id_obj.order_id = 200
        order_id_obj.save()
        order_ids = models.OrderID.objects.all()

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
            if stock is None:
                continue

            load_db_stock(db_stock, stock)

            decision = 0
            if account.mode == 'setup':
                logging.debug('run algorithm: fill')
                decision = alg_fill.trade_decision(stock)
            elif account.mode == 'run':
                logging.debug('run algorithm: %s' % stock.algorithm_string)
                if stock.algorithm_string == 'ahnyung':
                    decision = alg_ahnyung.trade_decision(stock)
                elif stock.algorithm_string == 'trend':
                    decision = alg_trend.trade_decision(stock)

            logging.debug('decision=%d' % decision)

            if decision != 0:
                stock.last_count = stock.count

                if decision > 0:
                    if not stock.market_order(decision, order_id):
                        trade_failed = True
                elif decision < 0:
                    if not stock.market_order(decision, order_id):
                        trade_failed = True

                order_id += 1
                store_trade(stock, dt, decision, trade_failed)

            if not trade_failed and account.mode == 'setup':
                stock.last_buy_price = stock.value
                stock.last_sell_price = stock.value
                stock.last_value = stock.value

            store_db_stock(db_stock, stock)

        if not trade_failed and account.mode == 'setup':
            account.mode = 'run'
        account.update()
        store_db_account(db_account, account)
        store_day_report(db_account, dt)

    order_id_obj.order_id = order_id
    order_id_obj.save()

    if need_logout:
        client.logout()
        logging.debug('logged out')


def simulate():
    #logging.basicConfig(level=logging.DEBUG)

    reset_sim_config()

    models.Trade.objects.all().delete()
    models.Quote.objects.all().delete()
    models.DayReport.objects.all().delete()

    for db_account in models.Account.objects.all():
        db_account.mode = models.MODE_SETUP
        db_account.save()

        for db_stock in models.Stock.objects.filter(account=db_account):
            db_stock.count = 0
            db_stock.save()

    first_quote = models.SimQuote.objects.all().order_by('date')[0]
    last_quote = models.SimQuote.objects.all().order_by('-date')[0]

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

    client = simclient.Client()
    client.login(cur_dt)
    while cur_dt < last_dt:
        if cur_dt.weekday() == 5 or cur_dt.weekday() == 6:
            cur_dt += day_delta
            continue
        if cur_dt in us_holidays:
            cur_dt += day_delta
            continue
        print('running: ' + str(cur_dt))
        client.update(cur_dt)
        run(dt=cur_dt, client=client)
        cur_dt += day_delta

    client.logout()

