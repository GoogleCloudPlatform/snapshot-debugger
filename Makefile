.PHONY: test

test:
	python3 -m unittest discover -s cli_tests -t .
