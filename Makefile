PORT = 7432
ROOT = $(PWD)

.PHONY: compile validate test serve open install-agent uninstall-agent links links-do harvest-diff backup-progress first-run export-static arxiv-watch eval-slo sync-check

compile:
	python3 scripts/compile_catalog.py

test:
	python3 -m unittest discover -s tests -v

validate: compile test
	python3 scripts/validate.py
	python3 scripts/first_run_check.py
	python3 scripts/sync_check.py

links:
	python3 scripts/check_links.py

links-do:
	python3 scripts/check_links.py --do-only

eval-slo:
	python3 scripts/eval_slo.py

sync-check:
	python3 scripts/sync_check.py

harvest-diff:
	python3 scripts/harvest_diff.py

backup-progress:
	python3 scripts/backup_progress.py

first-run:
	python3 scripts/first_run_check.py

export-static:
	python3 scripts/export_static.py

arxiv-watch:
	python3 scripts/arxiv_watch.py

serve:
	python3 scripts/serve.py

open:
	open http://127.0.0.1:$(PORT)

install-agent:
	bash bin/install-agent.sh

uninstall-agent:
	launchctl unload "$$HOME/Library/LaunchAgents/com.sagar.ai-sme-map.plist" 2>/dev/null || true
	rm -f "$$HOME/Library/LaunchAgents/com.sagar.ai-sme-map.plist"
