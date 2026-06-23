DATE := $(shell date +%Y-%m-%d)

.PHONY: setup test probe eval report dry

setup:
	uv sync

test:
	uv run pytest -q

probe:
	uv run python -m econ_eval probe

dry:
	uv run python -m econ_eval --date $(DATE) eval --dry-run

eval:
	uv run python -m econ_eval --date $(DATE) eval -n 5

report:
	uv run python -m econ_eval --date $(DATE) report
