.PHONY: build run test clean lint

# Build Docker image
build:
    docker-compose build

# Run the game engine
run:
    docker-compose up mahjong-engine

# Run web server
web:
    docker-compose up mahjong-web

# Run tests
test:
    docker-compose run --rm mahjong-engine python -m pytest tests/ -v

# Run tests with coverage
test-coverage:
    docker-compose run --rm mahjong-engine python -m pytest tests/ --cov=src --cov-report=html

# Lint code
lint:
    docker-compose run --rm mahjong-engine flake8 src/
    docker-compose run --rm mahjong-engine mypy src/

# Format code
format:
    docker-compose run --rm mahjong-engine black src/ tests/

# Clean up
clean:
    docker-compose down
    docker system prune -f

# Interactive shell
shell:
    docker-compose run --rm mahjong-engine bash

# Run a quick game demo
demo:
    docker-compose run --rm mahjong-engine python src/main.py
