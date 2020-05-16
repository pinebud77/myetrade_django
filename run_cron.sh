#!/bin/bash

export DJANGO_BASE=/home/pinebud/myetrade_django

cd ${DJANGO_BASE}/logs
wget --timeout=5000 --no-check-certificate https://127.0.0.1/stock/run/ -O run.log
