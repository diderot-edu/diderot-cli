.PHONY: test clean

default: dist

dist:
	python setup.py bdist_wheel

install:
	pip install .

setup:
	pip install -r requirements.txt

test:
	nosetests test.py --logging-level=ERROR

coverage:
	coverage run --source='.' ./test.py
	coverage report

clean:
	rm -rf dist build *.egg-info
