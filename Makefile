.PHONY: deploy sync install test bump_version

-include .env

REMOTE_USER ?= dummy
REMOTE_HOST ?= dummy
REMOTE_DIR ?= /home/$(REMOTE_USER)/publicwsgi/ais-app

deploy: test bump_version sync install
	@echo "Deployment to $(REMOTE_HOST) complete!"

bump_version:
	@python3 -c "import re; fp='app/static/js/config.js'; c=open(fp).read(); m=re.search(r\"const APP_VERSION = '(\d+)\.(\d+)';\", c); \
	ma, mi = (int(m.group(1)), int(m.group(2))) if m else (0,0); \
	v=f'{ma + (mi >= 9)}.{ (mi + 1) % 10 }' if m else None; \
	open(fp, 'w').write(re.sub(r\"const APP_VERSION = '(\d+)\.(\d+)';\", f\"const APP_VERSION = '{v}';\", c)) if v else None; \
	print(f'Bumped version to {v}' if v else 'Version string not found');"

test:
	@echo "Running Python backend tests..."
	@if [ -f venv/bin/pytest ]; then \
		venv/bin/pytest tests/ ; \
	elif [ -f .venv/bin/pytest ]; then \
		.venv/bin/pytest tests/ ; \
	else \
		python3 -m pytest tests/ ; \
	fi
	@echo "Running JavaScript frontend tests..."
	@npm run test:js

sync:
	rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='.git' --exclude='*.sqlite' ./ $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)/

install:
	ssh $(REMOTE_USER)@$(REMOTE_HOST) "cd $(REMOTE_DIR) && ( [ -f '.venv/bin/pip' ] || rm -rf .venv ) && [ ! -d '.venv' ] && virtualenv -p python3 --system-site-packages .venv || true && .venv/bin/pip install -r requirements.txt"