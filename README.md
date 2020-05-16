Django-based MyEtrade
=====================

This is personal test for Django + my trading code. However, this looks like not a good approach at all..<br>
There is no gurantee on your data and integrity. If you try this, it is on your own risk. You'd better not to try this SW. :)

ToDO :
* think more about algorithms now -_-;
* bugfix : there are plenty of bugs yet.. (too many bugs!!! too many bugs!! don't try this program!!)

Done :
* running algorithm on real trading
* simulation based on daily history
* several dummy algorithms (of no practical use)
* graph and report generation
* BTC : trading through coinbase API (wrapper to coinbase public python lib)
* stocks : trading through E*TRADE API (my private python API)

Installation :
1. Required libraries : django requests requests_oauth holidays fake_useragent matplotlib mpld3 requests_oauthlib jinja2 coinbase yfinance
1. generate your own /myetrade_django/settings.py : you can refer setting.py.sample
1. $ cd myetrade_django
1. $ git clone https://github.com/pinebud77/python_etrade.git
1. $ git clone https://github.com/pinebud77/python_coinbase.git
1. $ python3 manage.py migrate
1. $ python3 manage.py makemigrations stock
1. $ python3 manage.py migrate
1. $ python3 manage.py createsuperuser

Required Variables in settings.py if you want to try coinbase
* COINBASE_KEY
* COINBASE_SECRET

Required Variables in settings.py if you want to trid E*TRADE
* ETRADE_KEY
* ETRADE_SECRET
* ETRADE_USERNAME
* ETRADE_PASSWORD

Setting up Account and Stock :
* http://localhost:8000/admin/stock/account/ -> add account and setup stock information
* 
* 'BUDGET RATE IN THE ACCOUNT' means the rate of the stock in the account.<br>
ex) If budget rate is 0.49, and the net value is 1000.0, the budget for the stock is 490.0
* the total of the BUDGET RATE for each stocks should not be over 1.0 <br>
ex) you have to consider the trading fee. so, using total 0.95 of tradable money is recommended considering the trading fee
* Account type and Account id need to be set <br>
account id can be anyvalue for coinbase account <br>
account id need to be 0 for simulation account
* Net value and Cash to trade will be filled when the daily run is called, or when simulation starts
* stocks need to set if you want to try simulation

Ingesting Stock History Data (for simulation):
1. $ python3 manage.py runserver
1. open http://localhost:8000/stock/loaddata/ : this will load daily history data from yahoo finance (stock) or other server (BTC)
1. your initial cash in the account will reset to 100000.0 on execution of simulation
1. open http://localhost:8000/stock/simulate/

Getting Performance Graph for the actual run :
* open http://localhsot:8000/stock/graph/ <br>
ex) 2018-2019 coin : https://docs.google.com/spreadsheets/d/1psDI7E3vNqV-z9qAqHGL73fkA84iFn98z_onY7jTJ_E/edit?usp=sharing (-\_-)

Getting Performance Report for the actual run :
1. open http://localhost:8000/stock/report/
1. input desired date range for the report
1. click submit and the .csv file will be downloaded
1. example report : monkey is the best !!!<br>

Deploying the server with nginx + gunicorn
* https://docs.gunicorn.org/en/stable/deploy.html
* gunicorn_start.sh was prepared for the gunicorn deployment
* logrotate may need to be setup on logs directory

Running the actual daily job :
* open http://127.0.0.1:8000/stock/run/ on the same host as the server : this page will return error if the client is not on the same server
* add cronjob for the user as the following if it works well:<br>
30 6 * * 1-5 /home/${your_account}/myetrade_django/run_cron.sh
* This will run your algorithm every 6:30am (because I am at Western area)

