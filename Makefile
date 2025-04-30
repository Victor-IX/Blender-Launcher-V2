SHELL := sh

.PHONY:
run:
	python source/main.py

.PHONY:
test:
	pytest source/modules/version_matcher.py
