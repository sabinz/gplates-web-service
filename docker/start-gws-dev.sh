#!/usr/bin/env bash

BASEDIR=$(dirname "$0")
echo "$BASEDIR"
cd $BASEDIR  
docker-compose run --rm --service-ports gws /bin/bash -c "cd /gws/django/GWS && python3 manage.py runserver 0.0.0.0:80"