#!/bin/bash

export DJANGO_BASE=/home/pi/myetrade_django

cd ${DJANGO_BASE}
if /usr/bin/python3 is_holiday.py; then
	echo "holiday"
	exit 0
fi


echo "non-holiday"
cd ${DJANGO_BASE}/logs
wget -q --no-check-certificate -O ${1}.log https://127.0.0.1/stock/${1}
