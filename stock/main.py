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
import csv
import io
import urllib
import holidays
import python_etrade.client as etclient
import python_simtrade.client as simclient
import python_coinbase.client as coinbase_client
import yfinance as yf
import ssl

from . import models
from django.utils import timezone
from django.db import transaction
from .algorithms import in_algorithm_list, out_algorithm_list
from django.conf import settings
from fake_useragent import UserAgent


logger = logging.getLogger('main_loop')
MIN_HISTORY_DAYS = 120


def load_db_account(db_account, account):
    pass


def store_db_account(db_account, account):
    db_account.net_value = account.net_value
    db_account.cash_to_trade = account.cash_to_trade
    db_account.save()


def load_db_stock(db_stock, stock):
    stock.budget = stock.account.net_value * db_stock.share
    stock.in_algorithm = db_stock.in_algorithm
    stock.in_stance = db_stock.in_stance
    stock.out_algorithm = db_stock.out_algorithm
    stock.out_stance = db_stock.out_stance
    stock.last_count = db_stock.last_count

    if stock.last_count is None:
        stock.last_count = 0.0


def store_db_stock(db_stock, stock):
    db_stock.value = stock.value
    db_stock.count = stock.count
    db_stock.last_count = stock.last_count
    db_stock.save()


def store_day_report(db_account, dt):
    prev_reports = models.DayReport.objects.filter(account=db_account, date=dt.date())
    for prev_report in prev_reports:
        prev_report.delete()

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
        if not quote:
            continue
        prev_quotes = models.Quote.objects.filter(symbol=symbol, dt=dt).order_by('-dt')
        for prev_quote in prev_quotes:
            prev_quote.delete()

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
    try:
        order_id_obj = models.OrderID.objects.all()[0]
    except IndexError:
        order_id_obj = models.OrderID()

    order_id_obj.order_id = order_id
    order_id_obj.save()


def get_in_algorithm(num):
    if num < len(in_algorithm_list):
        return in_algorithm_list[num]()

    print('there is no such in algorithm index %d' % num)

    return None


def get_out_algorithm(num):
    if num < len(out_algorithm_list):
        return out_algorithm_list[num]()

    print('there is no such out algorithm index %d' % num)

    return None


@transaction.atomic
def run(dt=None, client=None):
    if dt is None:
        dt = timezone.now()

    first = True
    need_logout = False
    orig_client = client
    order_id = 0

    for db_account in models.Account.objects.all():
        if not orig_client:
            if client:
                client.logout()

            if db_account.account_type == models.ACCOUNT_ETRADE:
                client = etclient.Client()
                result = client.login(
                    getattr(settings, 'ETRADE_KEY', ''),
                    getattr(settings, 'ETRADE_SECRET', ''),
                    getattr(settings, 'ETRADE_USERNAME', ''),
                    getattr(settings, 'ETRADE_PASSWORD', ''))
            elif db_account.account_type == models.ACCOUNT_COINBASE:
                client = coinbase_client.Client()
                result = client.login(
                    getattr(settings, 'COINBASE_KEY', ''),
                    getattr(settings, 'COINBASE_SECRET', '')
                    )

            if first:
                store_quotes(client, dt)
                order_id = get_order_id()
                first = False

            if not result:
                logger.error('login failed')
                return False
            logger.debug('logged in')
            need_logout = True

        account = client.get_account(db_account.account_id)
        if account is None:
            logger.error('getting account failed: wrong account_id?')
            continue

        load_db_account(db_account, account)

        logger.debug('account id:%d mode: %s' % (account.id, account.mode))

        trade_failed = False
        for db_stock in models.Stock.objects.filter(account=db_account):

            us_holidays = holidays.UnitedStates()
            if dt.date() in us_holidays and db_stock.symbol != 'BTC':
                logger.info('skipping sim: US holiday')
                continue

            stock = account.get_stock(db_stock.symbol)
            if not stock:
                stock = account.new_stock(db_stock.symbol)
            if stock is None:
                logger.error('new stock is None %s' % db_stock.symbol)
                continue

            load_db_stock(db_stock, stock)

            if stock.count:
                alg = get_out_algorithm(stock.out_algorithm)
                if not alg:
                    continue
            else:
                alg = get_in_algorithm(stock.in_algorithm)
                if not alg:
                    continue

            logger.debug('run algorithm: %s' % alg.__class__.name)
            decision = alg.trade_decision(stock)

            if not stock.float_trade:
                decision = int(decision)

            logger.info('%s: decision=%f' % (stock.symbol, decision))

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
        logger.debug('logged out')

    return True


def simulate(start_date=None, end_date=None):
    models.Order.objects.all().delete()
    models.Quote.objects.all().delete()
    models.DayReport.objects.all().delete()
    models.DayHistory.objects.all().delete()

    for db_account in models.Account.objects.all():
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

    simclient.reset_sim_config()
    client = simclient.Client()
    client.login(cur_dt)
    while cur_dt <= last_dt:
        logger.info('running sim: ' + str(cur_dt))
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
            prev_histories = models.DayHistory.objects.filter(symbol=symbol, date=sim_history.date)
            if prev_histories:
                break

            day_history = models.DayHistory()
            day_history.symbol = sim_history.symbol
            day_history.date = sim_history.date
            day_history.open = sim_history.open
            day_history.high = sim_history.high
            day_history.low = sim_history.low
            day_history.close = sim_history.close
            day_history.volume = sim_history.volume
            day_history.save()

def load_stock_symbol(symbol, today, simulate):
    today_histories = models.DayHistory.objects.filter(symbol=symbol, date=today)
    if today_histories:
        return

    if not simulate:
        td = timezone.timedelta(day=MIN_HISTORY_DAYS)
        start_date = today - td
    else:
        start_date = timezone.datetime(year=2002, month=1, day=1)

    data = yf.download(symbol,
        start='%4.4d-%2.2d-%2.2d' % (start_date.year, start_date.month, start_date.day),
        end='%4.4d-%2.2d-%2.2d' % (today.year, today.month, today.day))

    data.sort_index(axis=0, ascending=False, inplace=True)

    for index, row in data.iterrows():
        if not simulate:
            t_histories = models.DayHistory.objects.filter(symbol=symbol, date=index.date())
        else:
            t_histories = models.SimHistory.objects.filter(symbol=symbol, date=index.date())

        if t_histories:
            break

        if not simulate:
            day_history = models.DayHistory()
        else:
            day_history = models.SimHistory()
        day_history.symbol = symbol
        day_history.date = index.date()
        day_history.open = float(row[0])
        day_history.high = float(row[1])
        day_history.low = float(row[2])
        day_history.close = float(row[3])
        day_history.volume = int(row[4])
        day_history.save()

    return True


def load_coin_symbol(symbol, today, simulate):
    today_histories = models.DayHistory.objects.filter(symbol=symbol, date=today)
    if today_histories:
        return

    ssl._create_default_https_context = ssl._create_unverified_context

    url = 'https://www.cryptodatadownload.com/cdd/Coinbase_BTCUSD_d.csv'
    page = urllib.request.urlopen(url)
    reader = csv.reader(io.TextIOWrapper(page))

    for row in reader:
        if 'Created' in row[0]:
            continue
        if 'Date' in row[0]:
            continue

        d_digit = row[0].split('-')
        t_dt = timezone.datetime(year=int(d_digit[0]), month=int(d_digit[1]), day=int(d_digit[2]))

        if not simulate:
            t_histories = models.DayHistory.objects.filter(symbol=symbol, date=t_dt.date())
        else:
            t_histories = models.SimHistory.objects.filter(symbol=symbol, date=t_dt.date())
        if t_histories:
            break

        if not simulate:
            day_history = models.DayHistory()
        else:
            day_history = models.SimHistory()
        day_history.symbol = symbol
        day_history.date = t_dt.date()
        day_history.open = float(row[2])
        day_history.high = float(row[3])
        day_history.low = float(row[4])
        day_history.close = float(row[5])
        day_history.volume = float(row[6])
        day_history.save()

    return True

@transaction.atomic
def load_history(simulate=False):
    today = timezone.now().date()
    symbol_list = []

    if simulate:
        models.SimHistory.objects.all().delete()

    for stock in models.Stock.objects.all():
        if str(stock.symbol) not in symbol_list:
            symbol_list.append(str(stock.symbol))
    for symbol in symbol_list:
        today_histories = models.DayHistory.objects.filter(symbol=symbol, date=today)
        if today_histories:
            continue

    ret = True
    for symbol in symbol_list:
        if symbol != 'BTC':
            ret = load_stock_symbol(symbol, today, simulate)
        else:
            ret = load_coin_symbol(symbol, today, simulate)

    return True

def learn(start_date, end_date):
    tf_learn(start_date, end_date)

