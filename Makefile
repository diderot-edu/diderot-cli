.PHONY: test clean

default: dist

dist:
	python setup.py bdist_wheel

install:
	pip install .

test:
	python -m unittest test -v

coverage:
	coverage run --source='.' ./test.py
	coverage report

clean:
	rm -rf dist
