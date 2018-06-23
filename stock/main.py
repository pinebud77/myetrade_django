#!/usr/bin/env python3

import logging
import csv
import io
import urllib
from . import models
from .algorithms import FillAlgorithm, TrendAlgorithm
from .algorithms import MonkeyAlgorithm, EmptyAlgorithm
from django.utils import timezone
from django.db import transaction
import python_etrade.client as etclient
import python_simtrade.client as simclient
import holidays

try:
    from .config import *
except ModuleNotFoundError:
    pass

try:
    from .private_algorithms import DayTrendAlgorithm, OpenCloseAlgorithm, TrendTrendAlgorithm
except ModuleNotFoundError:
    from .algorithms import TrendAlgorithm as DayTrendAlgorithm

LOG_FORMAT = '%(asctime)-15s %(message)s'
MIN_HISTORY_DAYS = 20


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
    stock.last_count = db_stock.last_count

    if stock.last_count is None:
        stock.last_count = 0.0


def store_db_stock(db_stock, stock):
    db_stock.value = stock.value
    db_stock.count = stock.count
    db_stock.last_count = stock.last_count
    db_stock.save()


def store_day_report(db_account, dt):
    try:
        t_dt = timezone.datetime(year=dt.year, month=dt.month, day=dt.day)
        prev_report = models.DayReport.objects.filter(account=db_account, date=t_dt.date())[0]
        prev_report.delete()
    except IndexError:
        pass
    day_report = models.DayReport()
    day_report.date = dt
    day_report.account = db_account
    day_report.net_value = db_account.net_value
    day_report.cash_to_trade = db_account.cash_to_trade
    day_report.save()


def store_order(stock, dt, decision, failed, failure_reason):
    reasons = models.FailureReason.objects.filter(message=failure_reason)
    if not reasons:
        reason = models.FailureReason()
        reason.message = failure_reason
        reason.save()
    else:
        reason = reasons[0]

    order = models.Order()
    order.dt = dt
    order.symbol = stock.symbol
    order.account_id = stock.account.id
    order.count = abs(decision)
    order.price = stock.value
    order.failure_reason = reason
    if decision > 0 and not failed:
        order.action = models.ACTION_BUY
    elif decision > 0:
        order.action = models.ACTION_BUY_FAIL
    elif decision < 0 and not failed:
        order.action = models.ACTION_SELL
    else:
        order.action = models.ACTION_SELL_FAIL
    order.save()


def store_quotes(client, dt):
    symbol_list = []
    for stock in models.Stock.objects.all():
        if str(stock.symbol) not in symbol_list:
            symbol_list.append(str(stock.symbol))

    for symbol in symbol_list:
        quote = client.get_quote(symbol)
        if quote is None:
            continue
        try:
            prev_quote = models.Quote.objects.filter(symbol=symbol, dt=dt).order_by('-dt')[0]
            prev_quote.delete()
        except IndexError:
            pass

        db_quote = models.Quote()
        db_quote.dt = dt
        db_quote.symbol = symbol
        db_quote.ask = quote.ask
        db_quote.bid = quote.bid
        db_quote.save()


def get_order_id():
    order_ids = models.OrderID.objects.all()
    if not order_ids:
        order_id_obj = models.OrderID()
        order_id_obj.order_id = 500
        order_id_obj.save()
        order_ids = models.OrderID.objects.all()

    order_id_obj = order_ids[0]
    order_id = order_id_obj.order_id

    return order_id


def store_order_id(order_id):
    order_id_obj = models.OrderID.objects.all()[0]
    order_id_obj.order_id = order_id
    order_id_obj.save()


alg_fill = FillAlgorithm()
alg_empty = EmptyAlgorithm()
alg_trend = TrendAlgorithm()
alg_day_trend = DayTrendAlgorithm()
alg_monkey = MonkeyAlgorithm()
alg_open_close = OpenCloseAlgorithm()
alg_trend_trend = TrendTrendAlgorithm()


@transaction.atomic
def run(dt=None, client=None):
    logging.basicConfig(level=logging.DEBUG)
    if dt is None:
        dt = timezone.now()

    need_logout = False
    if client is None:
        if etrade_consumer_key is None:
            logging.error('no key defined')
            return False
        client = etclient.Client()
        result = client.login(etrade_consumer_key,
                              etrade_consumer_secret,
                              etrade_username,
                              etrade_passwd)
        if not result:
            logging.error('login failed')
            return False
        logging.debug('logged in')
        need_logout = True

    store_quotes(client, dt)
    order_id = get_order_id()

    for db_account in models.Account.objects.all():
        account = client.get_account(db_account.account_id)
        if account is None:
            logging.error('getting account failed: wrong account_id?')
            continue
        load_db_account(db_account, account)

        logging.debug('account id:%d mode: %s' % (account.id, account.mode))

        trade_failed = False
        for db_stock in models.Stock.objects.filter(account=db_account):
            stock = account.get_stock(db_stock.symbol)
            if not stock:
                stock = account.new_stock(db_stock.symbol)
            if stock is None:
                logging.error('new stock is None %s' % db_stock.symbol)
                continue

            load_db_stock(db_stock, stock)

            decision = 0
            if account.mode == 'setup':
                logging.debug('run algorithm: fill')
                decision = alg_fill.trade_decision(stock)
            elif account.mode == 'run':
                logging.debug('run algorithm: %s' % stock.algorithm_string)
                if stock.algorithm_string == 'trend':
                    decision = alg_trend.trade_decision(stock)
                elif stock.algorithm_string == 'day_trend':
                    decision = alg_day_trend.trade_decision(stock)
                elif stock.algorithm_string == 'monkey':
                    decision = alg_monkey.trade_decision(stock)
                elif stock.algorithm_string == 'empty':
                    decision = alg_empty.trade_decision(stock)
                elif stock.algorithm_string == 'open_close':
                    decision = alg_open_close.trade_decision(stock)
                elif stock.algorithm_string == 'trend_trend':
                    decision = alg_trend_trend.trade_decision(stock)

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
                store_order(stock, dt, decision, trade_failed, stock.get_failure_reason())

            store_db_stock(db_stock, stock)

        if not trade_failed and account.mode == 'setup':
            account.mode = 'run'
        account.update()
        store_db_account(db_account, account)
        store_day_report(db_account, dt)

    store_order_id(order_id)

    if need_logout:
        client.logout()
        logging.debug('logged out')

    return True


def simulate(start_date=None, end_date=None):
    logging.basicConfig(level=logging.DEBUG)

    models.Order.objects.all().delete()
    models.Quote.objects.all().delete()
    models.DayReport.objects.all().delete()
    models.DayHistory.objects.all().delete()

    for db_account in models.Account.objects.all():
        db_account.mode = models.MODE_SETUP
        db_account.save()

        for db_stock in models.Stock.objects.filter(account=db_account):
            db_stock.count = 0
            db_stock.save()

    if start_date is None:
        first_quote = models.SimHistory.objects.all().order_by('date')[0]
    else:
        try:
            first_quote = models.SimHistory.objects.filter(date__gte=start_date).order_by('date')[0]
        except IndexError:
            return False

    cur_dt = timezone.datetime(year=first_quote.date.year, month=first_quote.date.month, day=first_quote.date.day,
                               hour=9, minute=31, second=0, tzinfo=timezone.get_default_timezone())

    if end_date is None:
        last_quote = models.SimHistory.objects.all().order_by('-date')[0]
    else:
        try:
            last_quote = models.SimHistory.objects.filter(date__lte=end_date).order_by('-date')[0]
        except IndexError:
            return False

    last_dt = timezone.datetime(year=last_quote.date.year, month=last_quote.date.month, day=last_quote.date.day,
                                hour=23, minute=59, second=59, tzinfo=timezone.get_default_timezone())

    day_delta = timezone.timedelta(1)
    us_holidays = holidays.UnitedStates()

    simclient.reset_sim_config()
    client = simclient.Client()
    client.login(cur_dt)
    while cur_dt <= last_dt:
        if cur_dt.weekday() == 5 or cur_dt.weekday() == 6:
            logging.info('skipping sim: Saturday or Sunday')
            cur_dt += day_delta
            continue
        if cur_dt in us_holidays:
            logging.info('skipping sim: US holiday')
            cur_dt += day_delta
            continue
        print('running sim: ' + str(cur_dt))
        client.update(cur_dt)
        run(dt=cur_dt, client=client)
        load_history_sim(cur_dt.date())
        cur_dt += day_delta

    client.logout()

    return True


def load_history_sim(cur_date):
    symbol_list = []

    for stock in models.Stock.objects.all():
        if str(stock.symbol) not in symbol_list:
            symbol_list.append(str(stock.symbol))

    for symbol in symbol_list:
        sim_histories = models.SimHistory.objects.filter(symbol=symbol, date__lte=cur_date).order_by('-date')[:MIN_HISTORY_DAYS]
        if len(sim_histories) == 0:
            continue

        for sim_history in sim_histories:
            try:
                prev_history = models.DayHistory.objects.filter(symbol=symbol, date=sim_history.date)[0]
                break
            except IndexError:
                pass

            day_history = models.DayHistory()
            day_history.symbol = sim_history.symbol
            day_history.date = sim_history.date
            day_history.open = sim_history.open
            day_history.high = sim_history.high
            day_history.low = sim_history.low
            day_history.close = sim_history.close
            day_history.volume = sim_history.volume
            day_history.save()


def load_history_wsj(today):
    symbol_list = []

    for stock in models.Stock.objects.all():
        if str(stock.symbol) not in symbol_list:
            symbol_list.append(str(stock.symbol))
    for symbol in symbol_list:
        try:
            today_history = models.DayHistory.objects.filter(symbol=symbol, date=today)[0]
            if today_history:
                continue
        except IndexError:
            pass

    td = timezone.timedelta(MIN_HISTORY_DAYS)
    start_date = today - td

    for symbol in symbol_list:
        try:
            today_history = models.DayHistory.objects.filter(symbol=symbol, date=today)[0]
            if today_history:
                continue
        except IndexError:
            pass

        url = 'http://quotes.wsj.com/%s/historical-prices/download?MOD_VIEW=page&' \
              'num_rows=100&range_days=100&endDate=%2.2d/%2.2d/%4.4d&' \
              'startDate=%2.2d/%2.2d/%4.4d' \
              % (symbol, today.month, today.day, today.year, start_date.month, start_date.day, start_date.year)
        page = urllib.request.urlopen(url)
        reader = csv.reader(io.TextIOWrapper(page))

        for row in reader:
            print(row)
            if row[0] == 'Date':
                continue
            dates = row[0].split('/')
            t_dt = timezone.datetime(year=int(dates[2])+2000, month=int(dates[0]), day=int(dates[1]))
            try:
                t_history = models.DayHistory.objects.filter(symbol=symbol, date=t_dt.date())[0]
                break
            except IndexError:
                pass

            day_history = models.DayHistory()
            day_history.symbol = symbol
            day_history.date = t_dt.date()
            day_history.open = float(row[1])
            day_history.high = float(row[2])
            day_history.low = float(row[3])
            day_history.close = float(row[4])
            day_history.volume = int(row[5])
            day_history.save()

    return True
