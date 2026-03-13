.PHONY: run test

run:
	python3 main.py

test:
	python3 -m unittest discover -s tests -p 'test_*.py'
