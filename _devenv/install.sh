#!/bin/bash
### This script installs the development version of b2share2.
### It expects python3 and virtualenv to be installed; on macOS:
# brew install python --framework --universal
# pip install virtualenv virtualenvwrapper

if [ -n "$VIRTUAL_ENV" ]; then
	echo "Please deactivate the current virtual environment before running this script"
	echo "Virtual environment detected: $VIRTUAL_ENV"
	exit 1
fi

source /usr/local/bin/virtualenvwrapper.sh

export VIRTUALENV_NAME='b2share-evolution'
workon $VIRTUALENV_NAME
if [ $? -ne 0 ]; then
	echo; echo "### Make virtual env"
	mkvirtualenv --python=/usr/local/bin/python3 $VIRTUALENV_NAME
	workon $VIRTUALENV_NAME
	cdvirtualenv && mkdir src
	pip install --upgrade pip
fi

cdvirtualenv src
if [ ! -d ./b2share ]; then
	echo; echo "### Clone b2share"
	git clone git@github.com:EUDAT-B2SHARE/b2share.git

	echo; echo "### Run pip install b2share"
	cdvirtualenv src/b2share
	pip install -r requirements.txt

	echo; echo "### Run pip install b2share demo"
	cdvirtualenv src/b2share/demo
	pip install -e .

	echo; echo "### Build b2share webui"
	cdvirtualenv src/b2share/webui
	npm install
	node_modules/webpack/bin/webpack.js -p # pack for production
fi

cdvirtualenv src
if [ ! -d ./public-license-selector ]; then
	echo; echo "### Add public-license-selector"
	git clone git@github.com:EUDAT-B2SHARE/public-license-selector.git

	echo; echo "### Build public-license-selector"
	cd public-license-selector
	npm run build

	echo; echo "### Install public-license-selector"
	mkdir -p ../b2share/webui/app/vendors
	cp dist/license-selector.* ../b2share/webui/app/vendors/
fi

echo;
echo "Installation done, now please run:"
echo "./run.sh --reinit"
