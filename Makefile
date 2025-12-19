SHELL := sh

.PHONY:
run:
	python build_style.py
	python source/main.py

.PHONY:
test:
	pytest source/modules/version_matcher.py

.PHONY: build
build:
	python build_style.py
ifeq ($(OS),Windows_NT)
	./scripts/build_win.bat
else
	./scripts/build_linux.sh
endif
