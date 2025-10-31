SHELL := sh

.PHONY:
run:
	python source/main.py

.PHONY:
test:
	pytest source/modules/version_matcher.py

.PHONY: build
build:
ifeq ($(OS),Windows_NT)
	./scripts/build_win.bat
else
	./scripts/build_linux.sh
endif
