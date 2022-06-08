.PHONY: test

test:
	python3 -m unittest discover -s snapshot_dbg_cli_tests -t .
