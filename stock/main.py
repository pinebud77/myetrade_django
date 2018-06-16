#!/usr/bin/env python3

import logging
from . import algorithms
from .config import *
from python_etrade.client import Client
from .algorithms import AhnyungAlgorithm, FillAlgorithm
from datetime import datetime

from .models import *


LOG_FORMAT = '%(asctime)-15s %(message)s'


def load_db_account(db_account, account):
    account.mode = db_account.mode


def store_db_account(db_account, account):
    db_account.mode = account.mode
    db_account.net_value = account.net_value
    db_account.cash_to_trade = account.cash_to_trade
    db_account.save()


def load_db_stock(db_stock, stock):
    stock.budget = stock.account.net_value * db_stock.share
    stock.algorithm_string = db_stock.algorithm
    if db_stock.stance == 'moderate':
        stock.stance = algorithms.MODERATE
    elif db_stock.stance == 'aggressive':
        stock.stance = algorithms.AGGRESSIVE
    else:
        stock.stance = algorithms.CONSERVATIVE

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


def run():
    client = Client()
    result = client.login(etrade_consumer_key,
                          etrade_consumer_secret,
                          etrade_username,
                          etrade_passwd)
    if not result:
        logging.error('login failed')
        exit(-1)
    logging.debug('logged in')

    alg_ahnyung = AhnyungAlgorithm()
    alg_fill = FillAlgorithm()

    order_ids = OrderIndex.objects.all()
    if not order_ids:
        order_id_obj = OrderIndex()
        order_id_obj.order_id = 200
        order_id_obj.save()
        order_ids = OrderIndex.objects.all()

    order_id_obj = order_ids[0]
    order_id = order_id_obj.order_id

    for db_account in Account.objects.all():
        account = client.get_account(db_account.account_id)
        load_db_account(db_account, account)

        trade_failed = False

        for db_stock in Stock.objects.filter(account=db_account):
            stock = account.get_stock(db_stock.symbol)
            if not stock:
                quote = client.get_quote(db_stock.symbol)
                stock = Stock(quote.symbol, account, account.session)
                stock.value = quote.ask
                stock.count = 0
                account.add_empty_stock(stock)

            load_db_stock(db_stock, stock)

            #execute main algorithms
            decision = 0
            if account.mode == 'setup':
                decision = alg_fill.trade_decision(stock)
            if account.mode == 'run':
                if stock.algorithm_string == 'ahnyung':
                    decision = alg_ahnyung.trade_decision(stock)

            #execute decision
            if decision != 0:
                stock.last_count = stock.count

                trade = Trade()
                trade.account_id = account.id
                trade.symbol = stock.symbol
                trade.date = datetime.now()
                trade.price = stock.value

            if decision > 0:
                if stock.market_order(decision, order_id):
                    trade.type = 'buy'
                else:
                    trade.type = 'buy_fail'
                    trade_failed = True
            elif decision < 0:
                if stock.market_order(decision, order_id):
                    trade.type = 'sell'
                else:
                    trade.type = 'sell_fail'
                    trade_failed = True


            if decision != 0:
                order_id += 1
                trade.save()

            if not trade_failed and account.mode == 'setup':
                stock.last_buy_price = stock.value
                stock.last_sell_price = stock.value
                stock.last_value = stock.value

            store_db_stock(db_stock, stock)

        if not trade_failed and account.mode == 'setup':
            account.mode = 'run'

        store_db_account(db_account, account)

    order_id_obj.order_id = order_id
    order_id_obj.save()

    client.logout()
    logging.debug('logged out')


