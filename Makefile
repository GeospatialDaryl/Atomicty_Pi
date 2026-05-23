PYTHON  := python3
TRACKER := $(PYTHON) tools/pr_tracker.py
DB      ?= data/project_updates.db

.PHONY: prdb-init prdb-report prdb-report-json prdb-list-open test help

help:
	@echo "prdb-init        Initialise / migrate the database"
	@echo "prdb-report      Print full project state report"
	@echo "prdb-report-json Report as JSON"
	@echo "prdb-list-open   List open PRs"
	@echo "test             Run pytest suite"

prdb-init:
	$(TRACKER) --db $(DB) init

prdb-report:
	$(TRACKER) --db $(DB) report

prdb-report-json:
	$(TRACKER) --db $(DB) report --json

prdb-list-open:
	$(TRACKER) --db $(DB) list-prs --state open

test:
	$(PYTHON) -m pytest tests/ -v
