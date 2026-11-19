# skill-gate-lab — the gate is stdlib Python, so "no API key, no network" is a property
# of the code, not a promise in the README.
SHELL := /bin/bash
export PYTHONPATH := $(CURDIR)

.PHONY: help test gate smoke run report baseline compose clean

help:
	@echo "make test          unit tests (offline, no key)"
	@echo "make gate          tier 1 + tier 2 + the routing floor — the CI check"
	@echo "make smoke         gate + a tier-3 replay run + report.html (offline)"
	@echo "make run           tier 3 against a real executor: make run EXECUTOR_CMD='model-cli'"
	@echo "make report        rebuild out/report.html from the last run (free)"
	@echo "make baseline      write the routing floor to config/routing-baseline.json"
	@echo "make compose       run the gate inside the image that ships (needs docker)"
	@echo "make clean         remove out/ and bytecode"

test:
	python3 -m unittest discover -s tests -t . -v 2>&1 | tail -20

gate:
	python3 -m gate.cli gate

smoke:
	python3 -m gate.cli smoke

run:
	python3 -m gate.cli run --runs 3 $(if $(EXECUTOR_CMD),--executor-cmd "$(EXECUTOR_CMD)")

report:
	python3 -m gate.cli report

baseline:
	python3 -m gate.cli baseline $(if $(MIN),--min $(MIN))

compose:
	bash scripts/compose_smoke.sh

clean:
	rm -rf out/runs out/report.html out/report.json
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
