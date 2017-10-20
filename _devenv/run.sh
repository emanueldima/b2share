#!/bin/bash
### This script runs the development version of b2share2.

# customize this line to point to the correct IP
DOCKER_HOST=b2share.local

if [ "$1" = "--reinit" ]; then
	REINIT=1
fi

if [ -n "$VIRTUAL_ENV" ]; then
	echo "Please deactivate the current virtual environment before running this script"
	echo "Virtual environment detected: $VIRTUAL_ENV"
	exit 1
fi

source /usr/local/bin/virtualenvwrapper.sh
workon b2share-evolution
cdvirtualenv

DEVENV=src/b2share/_devenv

set -o allexport;
source $DEVENV/.env;
set +o allexport

export B2SHARE_BROKER_URL="amqp://${B2SHARE_RABBITMQ_USER}:${B2SHARE_RABBITMQ_PASS}@${DOCKER_HOST}:5672"
export B2SHARE_CELERY_BROKER_URL="amqp://${B2SHARE_RABBITMQ_USER}:${B2SHARE_RABBITMQ_PASS}@${DOCKER_HOST}:5672"
export B2SHARE_CELERY_RESULT_BACKEND="redis://${DOCKER_HOST}:6379/2"
export B2SHARE_ACCOUNTS_SESSION_REDIS_URL="redis://${DOCKER_HOST}:6379/0"
export B2SHARE_CACHE_REDIS_URL="redis://${DOCKER_HOST}:6379/0"
export B2SHARE_CACHE_REDIS_HOST="${DOCKER_HOST}"

export B2SHARE_SEARCH_ELASTIC_HOSTS="${DOCKER_HOST}:9200"
export B2SHARE_JSONSCHEMAS_HOST="${DOCKER_HOST}"

export B2SHARE_PREFERRED_URL_SCHEME=https
export B2SHARE_FAKE_EPIC_PID=1
export B2SHARE_FAKE_DOI=1
export USE_STAGING_B2ACCESS=1
export B2SHARE_UI_PATH=`pwd`/src/b2share/webui/app

if [ -n "$REINIT" ]; then
	echo; echo "### Remove docker containers"
	cdvirtualenv $DEVENV
	docker-compose down --remove-orphans
	docker-compose down --remove-orphans

	echo; echo "### Remove instance data"
	cdvirtualenv var
	rm -rf ./b2share-instance
fi

echo; echo "### Run docker-compose detached mode"
cdvirtualenv $DEVENV
docker-compose up -d

cdvirtualenv src/b2share
ps aux | grep -v grep | grep celeryd >/dev/null
if [ $? -ne 0 ]; then
	echo; echo "### Run celeryd in background"
	nohup celery worker -E -A b2share.celery -l INFO --workdir=$VIRTUAL_ENV &
fi

echo; echo "### Waiting for services to start"
until lsof -n -P | grep LISTEN | grep 5432 >/dev/null; do printf '_'; sleep 2; done
cdvirtualenv $DEVENV
until docker-compose logs postgres | grep "init process complete" >/dev/null; do printf '.'; sleep 2; done

echo; env | grep B2SHARE

cdvirtualenv src/b2share
if [ -n "$REINIT" ]; then
	echo; echo "### Initialize database"
    b2share db init

	echo; echo "### Run upgrade"
    b2share upgrade run -v
    # b2share index queue init
	# b2share index init
	# b2share schemas init

	echo; echo "### Add demo config and objects"
	b2share demo load_config -f
	b2share demo load_data -v
fi

if [ -z "$B2ACCESS_CONSUMER_KEY" -o -z "$B2ACCESS_SECRET_KEY" ]; then
	echo "*** Warning: B2ACCESS_CONSUMER_KEY / B2ACCESS_SECRET_KEY are NOT configured"
fi

echo; echo "### Run b2share"
export SSL_CERT_FILE="staging_b2access.pem"
export FLASK_DEBUG=1
b2share run -h 0.0.0.0
