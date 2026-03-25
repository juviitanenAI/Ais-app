.PHONY: deploy sync install test dev bump_version calculate-views build-frontend fetch-db backup-db

ifneq (,$(wildcard ./.env))
    include .env
    export
    $(info .env file found and loaded.)
else
    $(info Warning: .env file not found. Using default or environment variables.)
endif

REMOTE_USER ?= dummy
REMOTE_HOST ?= dummy
REMOTE_DIR ?= /home/$(REMOTE_USER)/publicwsgi/ais-app

deploy: test
	@python3 scripts/bump_version.py
	@$(MAKE) build-frontend
	@$(MAKE) sync
	@$(MAKE) install
	@echo "Triggering graceful remote shutdown..."
	-@ssh $(REMOTE_USER)@$(REMOTE_HOST) "curl -f -X POST http://localhost:$(APP_PORT)/api/admin/shutdown || pkill -f 'uvicorn main:app'"
	@$(MAKE) backup-db
	@echo "Deployment to $(REMOTE_HOST) complete!"

build-frontend:
	@echo "Building Svelte frontend..."
	@cd frontend && npm install && npm run build

calculate-views:
	ssh $(REMOTE_USER)@$(REMOTE_HOST) "cd $(REMOTE_DIR) && .venv/bin/python main.py --calculate-views"

bump_version:
	@python3 scripts/bump_version.py

test: build-frontend
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
	ssh $(REMOTE_USER)@$(REMOTE_HOST) "cd $(REMOTE_DIR) && .venv/bin/python -c 'from app import db; db.shutdown()'"
	rsync -avz $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)/vessels.sqlite* remote_db/

backup-db:
	@echo "Backing up remote database..."
	-@ssh $(REMOTE_USER)@$(REMOTE_HOST) "cp $(REMOTE_DIR)/vessels.sqlite $(REMOTE_DIR)/vessels.sqlite.bak"

push-db:
	@echo "Pushing local database to remote..."
	-@ssh $(REMOTE_USER)@$(REMOTE_HOST) "curl -f -X POST http://localhost:$(APP_PORT)/api/admin/shutdown || pkill -f 'uvicorn main:app'"
	@sleep 2
	ssh $(REMOTE_USER)@$(REMOTE_HOST) "rm -f $(REMOTE_DIR)/vessels.sqlite $(REMOTE_DIR)/vessels.sqlite-wal $(REMOTE_DIR)/vessels.sqlite-shm"
	scp vessels.sqlite* $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)/
	@echo "Database push complete."

install:
	ssh $(REMOTE_USER)@$(REMOTE_HOST) "cd $(REMOTE_DIR) && ( [ -f '.venv/bin/pip' ] || rm -rf .venv ) && [ ! -d '.venv' ] && virtualenv -p python3 --system-site-packages .venv || true && .venv/bin/pip install -r requirements.txt"