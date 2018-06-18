#!/usr/bin/env python3


import csv
from os import listdir
from os.path import isfile, join, splitext, realpath, dirname
from .models import SimQuote
from datetime import datetime
from django.db import transaction


DATA_PATH = dirname(realpath(__file__)) + '/market_history'


def get_symbol_list():
    result = []
    for file in listdir(DATA_PATH):
        if isfile(join(DATA_PATH, file)):
            result.append(splitext(file)[0])

    return result


@transaction.atomic
def load_csv(symbol):
    csv_file = open(join(DATA_PATH, symbol + '.csv'))
    reader = csv.reader(csv_file)

    for row in reader:
        if row[0] == 'Date':
            continue
        else:
            quote = SimQuote()
            quote.symbol = symbol

            dates = row[0].split('/')
            quote.date = datetime(year=int(dates[2])+2000, month=int(dates[0]), day=int(dates[1]),
                                  hour=0, minute=0, second=0)
            quote.price = float(row[1])

            quote.save()

    csv_file.close()


def load_data():
    SimQuote.objects.all().delete()

    symbols = get_symbol_list()

    for symbol in symbols:
        load_csv(symbol)
