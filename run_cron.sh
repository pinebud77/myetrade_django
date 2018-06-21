#!/bin/bash

cd /home/pi/myetrade_django

if /usr/bin/python3 is_holiday.py; then
	exit 0
fi


cd /home/pi/myetrade_django/logs
wget -q --no-check-certificate -O run https://127.0.0.1/stock/run