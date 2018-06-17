#!/usr/bin/env python3


import csv
from os import listdir
from os.path import isfile, join, splitext, realpath, dirname
from .models import QuoteName, Quote
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
def load_csv(quote_name):
    Quote.objects.all().delete()

    csv_file = open(join(DATA_PATH, quote_name.symbol + '.csv'))
    reader = csv.reader(csv_file)

    for row in reader:
        if row[0] == 'Date':
            continue
        else:
            quote = Quote()
            quote.name = quote_name

            dates = row[0].split('/')
            quote.date = datetime(year=int(dates[2])+2000, month=int(dates[0]), day=int(dates[1]))
            quote.price = float(row[1])

            quote.save()

    csv_file.close()


def load_data():
    symbols = get_symbol_list()

    for symbol in symbols:
        quote_name = QuoteName.objects.filter(symbol=symbol)[0]
        if not quote_name:
            quote_name = QuoteName()
            quote_name.symbol = symbol
            quote_name.save()

        load_csv(quote_name)
