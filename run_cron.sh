#!/bin/bash

export DJANGO_BASE=/home/pinebud/myetrade_django

cd ${DJANGO_BASE}
if /usr/bin/python3 is_holiday.py; then
	echo "holiday"
	exit 0
fi


echo "non-holiday"
cd ${DJANGO_BASE}/logs
wget --timeout=1000 --no-check-certificate -O get_history.log https://127.0.0.1/stock/get_history
wget --timeout=1000 --no-check-certificate -O run.log https://127.0.0.1/stock/run
