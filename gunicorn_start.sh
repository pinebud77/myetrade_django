#!/bin/bash

Xvfb :99&
export DISPLAY=:99

NAME="stock"
DJANGODIR=/home/pi/myetrade_django
SOCKFILE=/home/pi/myetrade_django/run/gunicorn.sock
USER=pi
GROUP=pi
NUM_WORKERS=2
TIME_OUT=300
DJANGO_SETTINGS_MODULE=myetrade_django.settings
DJANGO_WSGI_MODULE=myetrade_django.wsgi

echo "Starting $NAME as `whoami`"

cd $DJANGODIR
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DJANGODIR:$PYTHONPATH

RUNDIR=`dirname $SOCKFILE`
test -d $RUNDIR || mkdir -p $RUNDIR

exec /usr/local/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
	--name $NAME \
	--workers $NUM_WORKERS \
	--user=$USER --group=$GROUP \
	--bind=unix:$SOCKFILE \
	--log-level=debug \
	--timeout=$TIME_OUT \
	--log-file=-
