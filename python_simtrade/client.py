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

import json
import logging
from .accounts import Account
from .stocks import Stock, Quote
from os.path import dirname, realpath, join


SIM_CONFIG_FILE = join(dirname(realpath(__file__)), 'sim_config.json')
SIM_INITIAL_VALUE = 100000.0


def reset_sim_config():
    config = dict()
    config['accounts'] = [
        {'id': 0, 'cash_to_trade': SIM_INITIAL_VALUE, 'stocks': []},
        {'id': 1, 'cash_to_trade': SIM_INITIAL_VALUE, 'stocks': []},
        {'id': 2, 'cash_to_trade': SIM_INITIAL_VALUE, 'stocks': []},
        {'id': 3, 'cash_to_trade': SIM_INITIAL_VALUE, 'stocks': []},
        {'id': 4, 'cash_to_trade': SIM_INITIAL_VALUE, 'stocks': []},
        {'id': 5, 'cash_to_trade': SIM_INITIAL_VALUE, 'stocks': []},
        {'id': 6, 'cash_to_trade': SIM_INITIAL_VALUE, 'stocks': []},
        {'id': 7, 'cash_to_trade': SIM_INITIAL_VALUE, 'stocks': []},
        {'id': 8, 'cash_to_trade': SIM_INITIAL_VALUE, 'stocks': []},
        {'id': 9, 'cash_to_trade': SIM_INITIAL_VALUE, 'stocks': []},
    ]

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

        self.current_time = dt

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

    def update(self, dt):
        self.current_time = dt
        for account_id in self.account_dict:
            account = self.account_dict[account_id]
            account.update(dt)
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

        logging.debug('\nlogout sim client')
        logging.debug('config' + str(self.config))

        with open(SIM_CONFIG_FILE, 'w') as outfile:
            json.dump(self.config, outfile, indent=2, sort_keys=False)
        return True

    def get_account(self, account_id):
        return self.account_dict[account_id]

    def get_quote(self, symbol):
        quote = Quote(symbol)
        if not quote.update(self.current_time):
            return None

        if quote.ask is None:
            return None
        return quote
