.PHONY: deploy sync install test

-include .env

REMOTE_USER ?= dummy
REMOTE_HOST ?= dummy
REMOTE_DIR ?= /home/$(REMOTE_USER)/publicwsgi/ais-app

deploy: test sync install service
	@echo "Deployment to $(REMOTE_HOST) complete!"

test:
	@echo "Running tests locally before deploy..."
	@if [ -f venv/bin/pytest ]; then \
		venv/bin/pytest tests/ ; \
	elif [ -f .venv/bin/pytest ]; then \
		.venv/bin/pytest tests/ ; \
	else \
		python3 -m pytest tests/ ; \
	fi

sync:
	rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='.git' --exclude='*.sqlite' ./ $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)/

install:
	ssh $(REMOTE_USER)@$(REMOTE_HOST) "cd $(REMOTE_DIR) && ( [ -f '.venv/bin/pip' ] || rm -rf .venv ) && [ ! -d '.venv' ] && virtualenv -p python3 --system-site-packages .venv || true && .venv/bin/pip install -r requirements.txt"