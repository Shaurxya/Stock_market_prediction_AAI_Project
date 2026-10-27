.PHONY: run install clean analytics-install analytics-demo analytics-ingest analytics-process analytics-benchmark analytics-test check

PYTHON ?= python3.11
ANALYTICS_PYTHON = analytics/.venv/bin/python
ARGS ?=

# Default target
all: run

# Run both frontend and backend
run:
	@echo "Starting the application..."
	@bash ./start.sh

# Install all dependencies for both frontend and backend
install:
	@echo "Installing backend dependencies..."
	@$(PYTHON) -m venv backend/venv
	@backend/venv/bin/python -m pip install -r backend/requirements-dev.txt
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "Installation complete!"

analytics-install:
	@$(PYTHON) -m venv analytics/.venv
	@$(ANALYTICS_PYTHON) -m pip install -r analytics/requirements.txt

analytics-demo:
	@$(ANALYTICS_PYTHON) -m analytics.cli demo $(ARGS)

analytics-ingest:
	@$(ANALYTICS_PYTHON) -m analytics.cli ingest $(ARGS)

analytics-process:
	@$(ANALYTICS_PYTHON) -m analytics.cli process $(ARGS)

analytics-benchmark:
	@$(ANALYTICS_PYTHON) -m analytics.cli benchmark $(ARGS)

analytics-test:
	@$(ANALYTICS_PYTHON) -m unittest discover -s analytics/tests -v

check:
	@backend/venv/bin/python -m unittest discover -s backend/tests -v
	@cd frontend && npm run build

# Clean up build artifacts and virtual environments
clean:
	@echo "Cleaning up..."
	@rm -rf backend/venv
	@rm -rf frontend/node_modules
	@rm -rf frontend/dist
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Clean complete!"
