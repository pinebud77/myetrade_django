Django-based MyEtrade
=====================

This is personal test for Django + my trading code.

ToDO :
* think about algorithms now -_-;
* BUGFIX

Done :
* running algorithm on real trading or simulation
* several dummy algorithms (of no practical use)

Installation :
1. generate your own /myetrade_djnago/settings.py : you can refer setting.py.sample
1. $ git clone https://github.com/pinebud77/python_etrade.git
1. create /stock/config.py file for the account (no need if simulation only)
1. $ python3 manage.py migrate
1. $ python3 manage.py makemigrations stock
1. $ python3 manage.py migrate
1. $ python3 manage.py createsuperuser

Setup Account and Stock :
* http://localhost:8000/admin/stock/account/ -> add account and setup stock information
* 'BUDGET RATE IN THE ACCOUNT' means the rate of the stock in the account.<br>
ex) If budget rate is 0.49, and the net value is 1000.0, the budget for the stock is 490.0
* the total of the BUDGET RATE for each stocks should not be over 1.0

Ingesting Stock History Data :
1. locate the csv data to stock/market_history/ as file name of symbol.csv : I downloaded this data from WSJ site
1. $ python3 manage.py runserver
1. open http://localhost:8000/stock/loaddata/ : this will take time
1. ensure that simulation account number is '0'
1. ensure that mode is 'setup'
1. ensure that the stock list has the csv data loaded
1. your initial cash in the account will reset to 100000.0 on execution of simulation
1. open http://localhost:8000/stock/simulate/ : this will take time
1. report csv file will be automatically downloaded

Getting Performance Report after simulation or running the actual :
1. open http://localhost:8000/stock/report/ : this will take time
1. input desired date range for the report
1. click submit and the .csv file will be downloaded
1. example report : monkey is the best !!!<br>
ahnyung alg : https://docs.google.com/spreadsheets/d/1miU30kcAunXzcTWiENtOqByShoXa4KNWKlxZHGRO9to/edit?usp=sharing (huh.. the return is -_-;;)<br>
monkey alg : https://docs.google.com/spreadsheets/d/1Qjo-xpnwApTDFgzEqWoiqVfLXRb1B38BnB0JVpfJeEk/edit?usp=sharing (random buy sell)<br>
trend alg : https://docs.google.com/spreadsheets/d/1mFiiBiKs-IKIHVxng5LP2pLywZSYVNAtqFDZrILjGZ4/edit?usp=sharing

Running the actual daily job :
* open http://127.0.0.1:8000/stock/run/ on the same host as the server
* add cronjob for the user as the following if it works well:<br>
30 6 * * 1-5 /home/pi/myetrade_django/run_cron.sh
* This will run your algorithm every 6:30am (because I am at Western area)

