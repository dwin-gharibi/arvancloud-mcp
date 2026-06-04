.PHONY: install lint type test cov smoke check run serve docker clean

install:
	pip install -e ".[dev]"

lint:
	ruff check src tests

format:
	ruff check --fix src tests
	ruff format src tests

type:
	mypy

test:
	pytest -q

cov:
	pytest -q --cov --cov-report=term-missing

smoke:
	python scripts/smoke_test.py

check: lint type test smoke

run:
	arvancloud-mcp

serve:
	ARVAN_TRANSPORT=streamable-http ARVAN_HOST=0.0.0.0 arvancloud-mcp

docker:
	docker build -t arvancloud-mcp:latest .

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
