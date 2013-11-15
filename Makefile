all: lint test

lint:
	flake8 flask_swagger/*.py tests/*.py

test:
	nosetests
