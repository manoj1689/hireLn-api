.PHONY: install dev migrate reset-db test lint format

# Install dependencies
install:
	pip install -r requirements.txt
	prisma generate

# Run development server
dev:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run database migrations
migrate:
	prisma db push

# Reset database
reset-db:
	prisma db push --force-reset

# Seed database
seed:
	python scripts/seed.py

# Run tests
test:
	pytest

# Lint code
lint:
	flake8 .
	black --check .

# Format code
format:
	black .
	isort .

# Start with Docker
docker-up:
	docker-compose up -d

# Stop Docker containers
docker-down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f api
