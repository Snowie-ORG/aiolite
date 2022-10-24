MODULE_NAME := asyncsqlite
POETRY := $(shell command -v poetry 2> /dev/null)

.PHONY: help
help:
	@echo "Please use 'make <target>', where <target> is one of"
	@echo ""
	@echo "  install     install packages and prepare environment"
	@echo "  lint        run the code linters"
	@echo "  test        run all the tests"
	@echo "  build       build package"
	@echo "  all         install, lint, and test the project"
	@echo "  clean       remove all temporary files listed in .gitignore"
	@echo ""
	@echo "Check the Makefile to know exactly what each target is doing."
	@echo "Most actions are configured in 'pyproject.toml'."

.PHONY: _check_poetry
_check_poetry:
	@if [ -z $(POETRY) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi

.PHONY: all
all: install lint test

.PHONY: install
install: _check_poetry pyproject.toml poetry.lock
	$(POETRY) install

.PHONY: lint
lint: _check_poetry
	$(POETRY) run mypy $(MODULE_NAME)
	$(POETRY) run pylint $(MODULE_NAME)

.PHONY: test
test: _check_poetry
	$(POETRY) run pytest -s --cov $(MODULE_NAME) --asyncio-mode=auto --cov-fail-under=100 --profile --cov-report term-missing tests/

.PHONY: build
build: _check_poetry
	$(POETRY) build

.PHONY: clean
clean:
	git clean -Xdf
