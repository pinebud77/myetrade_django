#!/bin/bash

export DJANGO_BASE=/home/pi/myetrade_django

cd ${DJANGO_BASE}
if /usr/bin/python3 is_holiday.py; then
	exit 0
fi


cd ${DJANGO_BASE}/logs
wget -q --no-check-certificate -O run https://127.0.0.1/stock/run
