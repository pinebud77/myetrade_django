import json
import logging
from .accounts import Account
from .stocks import Stock, Quote
from os.path import dirname, realpath
from datetime import datetime


SIM_CONFIG_FILE = dirname(realpath(__file__)) + '/sim_config.json'


def reset_sim_config():
    config = dict()
    config['accounts'] = [{'id': 0, 'cash_to_trade': 100000.0, 'stocks':[]}]

    with open(SIM_CONFIG_FILE, 'w') as outfile:
        json.dump(config, outfile, indent=2, sort_keys=False)


class Client:
    def __init__(self):
        self.current_time = None
        self.config = None
        self.account_dict = {}

    def login(self, dt):
        try:
            with open(SIM_CONFIG_FILE) as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = dict()
            self.config['accounts'] = []

            with open(SIM_CONFIG_FILE, 'w') as outfile:
                json.dump(self.config, outfile, indent=2, sort_keys=False)

        self.current_time = datetime(year=dt.year,
                                     month=dt.month,
                                     day=dt.day,
                                     hour=8,
                                     minute=0,
                                     second=0)

        for json_account in self.config['accounts']:
            account = Account(json_account['id'], self.current_time)
            self.account_dict[account.id] = account
            account.cash_to_trade = json_account['cash_to_trade']

            for json_stock in json_account['stocks']:
                stock = Stock(json_stock['symbol'], account)
                quote = Quote(stock.symbol)
                quote.update(dt)
                stock.value = quote.ask
                stock.count = json_stock['count']

                account.stock_list.append(stock)
            account.update()
        return True

    def renew_connection(self):
        return True

    def logout(self):
        old_config = self.config
        self.config = dict()
        self.config['accounts'] = []
        for old_account in old_config['accounts']:
            account = self.get_account(old_account['id'])
            account.update()
            new_json_account = {'id': old_account['id'],
                                'cash_to_trade': account.cash_to_trade,
                                'net_value': account.net_value,
                                'stocks': []}
            self.config['accounts'].append(new_json_account)

            for stock in account.stock_list:
                new_json_stock = {'symbol': stock.symbol,
                                  'count': stock.count}
                new_json_account['stocks'].append(new_json_stock)

        logging.debug(self.config)

        with open(SIM_CONFIG_FILE, 'w') as outfile:
            json.dump(self.config, outfile, indent=2, sort_keys=False)
        return True

    def get_account(self, id):
        return self.account_dict[id]

    def get_quote(self, symbol):
        quote = Quote(symbol)
        if not quote.update(self.current_time):
            return None

        if quote.ask is None:
            return None
        return quote
