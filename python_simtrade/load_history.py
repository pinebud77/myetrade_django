#!/usr/bin/env python3
import csv
import urllib
import io
import logging
import os
from os.path import join, realpath, dirname
from stock.models import SimHistory, Stock
from django.utils import timezone
from django.db import transaction


DATA_PATH = dirname(realpath(__file__)) + '/market_history'


def get_symbol_list():
    result = list()
    for file in os.listdir(DATA_PATH):
        spl = file.split('.')
        if spl[1] == 'csv':
            result.append(spl[0])

    return result


@transaction.atomic
def load_csv(symbol):
    csv_file = open(join(DATA_PATH, symbol + '.csv'))
    reader = csv.reader(csv_file)

    for row in reader:
        if row[0] == 'Date':
            continue
        else:
            history = SimHistory()
            history.symbol = symbol

            dates = row[0].split('/')
            history.date = timezone.datetime(year=int(dates[2]) + 2000, month=int(dates[0]), day=int(dates[1])).date()
            history.open = float(row[1])
            history.high = float(row[2])
            history.low = float(row[3])
            history.close = float(row[4])
            history.volume = int(float(row[5]))
            history.save()

    csv_file.close()


@transaction.atomic
def load_web(symbol):
    today = timezone.datetime.now().today()
    start_dt = timezone.datetime(year=2002, month=1, day=1)
    url = 'http://quotes.wsj.com/%s/historical-prices/download?MOD_VIEW=page&' \
          'num_rows=1000000&range_days=1000000&endDate=%2.2d/%2.2d/%4.4d&' \
          'startDate=%2.2d/%2.2d/%4.4d'\
          % (symbol, today.month, today.day, today.year, start_dt.month, start_dt.day, start_dt.year)
    page = urllib.request.urlopen(url, None, 100000)
    reader = csv.reader(io.TextIOWrapper(page))

    for row in reader:
        if row[0] == 'Date':
            continue
        dates = row[0].split('/')
        t_dt = timezone.datetime(year=int(dates[2]) + 2000, month=int(dates[0]), day=int(dates[1]))

        day_history = SimHistory()
        day_history.symbol = symbol
        day_history.date = t_dt.date()
        day_history.open = float(row[1])
        day_history.high = float(row[2])
        day_history.low = float(row[3])
        day_history.close = float(row[4])
        day_history.volume = int(row[5])
        day_history.save()


def load_data():
    SimHistory.objects.all().delete()

    symbols = get_symbol_list()
    #sleep(2)

    for symbol in symbols:
        logging.info(symbol)
        #load_web(symbol)
        #sleep(2)
        load_csv(symbol)
