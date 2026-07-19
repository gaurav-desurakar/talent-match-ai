.PHONY: check-uv install dev api-dev web-dev db-upgrade test lint format clean

UV ?= $(shell command -v uv 2>/dev/null || { test -x "$(HOME)/.local/bin/uv" && printf '%s\n' "$(HOME)/.local/bin/uv"; })
API_DIR := apps/api

check-uv:
	@command -v "$(UV)" >/dev/null 2>&1 || test -x "$(UV)" || { \
		echo "uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/"; \
		exit 1; \
	}

install: check-uv
	$(UV) sync --project $(API_DIR) --locked
	npm ci --prefix apps/web

api-dev: check-uv
	cd $(API_DIR) && $(UV) run --locked uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web-dev:
	npm run dev --prefix apps/web

db-upgrade: check-uv
	cd $(API_DIR) && $(UV) run --locked alembic upgrade head

dev: check-uv
	@trap 'kill 0' INT TERM EXIT; $(MAKE) api-dev & $(MAKE) web-dev & wait

test: check-uv
	cd $(API_DIR) && $(UV) run --locked pytest --cov=app --cov-report=term-missing --cov-fail-under=90
	npm test --prefix apps/web

lint: check-uv
	cd $(API_DIR) && $(UV) run --locked ruff check app tests
	cd $(API_DIR) && $(UV) run --locked mypy app
	npm run lint --prefix apps/web
	npm run typecheck --prefix apps/web

format: check-uv
	cd $(API_DIR) && $(UV) run --locked ruff format app tests
	npx --prefix apps/web prettier --write 'apps/web/**/*.{ts,tsx,css,json,md}'

clean:
	find apps/api -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf apps/web/.next
