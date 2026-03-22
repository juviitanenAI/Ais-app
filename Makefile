.PHONY: deploy sync install test dev bump_version calculate-views build-frontend fetch-db

-include .env

REMOTE_USER ?= dummy
REMOTE_HOST ?= dummy
REMOTE_DIR ?= /home/$(REMOTE_USER)/publicwsgi/ais-app

deploy: test bump_version build-frontend sync install
	@echo "Triggering remote service restart..."
	-@ssh $(REMOTE_USER)@$(REMOTE_HOST) "pkill -f 'uvicorn main:app' || true"
	@echo "Deployment to $(REMOTE_HOST) complete!"

build-frontend:
	@echo "Building Svelte frontend..."
	@cd frontend && npm install && npm run build

calculate-views:
	ssh $(REMOTE_USER)@$(REMOTE_HOST) "cd $(REMOTE_DIR) && .venv/bin/python main.py --calculate-views"

bump_version:
	@python3 scripts/bump_version.py

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
	@cd frontend && npm run test

dev:
	@echo "Starting FastAPI backend and Vite Svelte dev server..."
	@trap 'kill %1' EXIT; python3 main.py & cd frontend && npm run dev

sync:
	rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='.git' --exclude='*.sqlite*' --exclude='frontend/node_modules' ./ $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)/

fetch-db:
	@echo "Fetching remote database..."
	@mkdir -p remote_db
	scp $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)/vessels.sqlite remote_db/

install:
	ssh $(REMOTE_USER)@$(REMOTE_HOST) "cd $(REMOTE_DIR) && ( [ -f '.venv/bin/pip' ] || rm -rf .venv ) && [ ! -d '.venv' ] && virtualenv -p python3 --system-site-packages .venv || true && .venv/bin/pip install -r requirements.txt"