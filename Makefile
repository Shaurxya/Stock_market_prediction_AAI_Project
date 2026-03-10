.PHONY: run install clean

# Default target
all: run

# Run both frontend and backend
run:
	@echo "Starting the application..."
	@bash ./start.sh

# Install all dependencies for both frontend and backend
install:
	@echo "Installing backend dependencies..."
	@cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "Installation complete!"

# Clean up build artifacts and virtual environments
clean:
	@echo "Cleaning up..."
	@rm -rf backend/venv
	@rm -rf frontend/node_modules
	@rm -rf frontend/dist
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Clean complete!"
