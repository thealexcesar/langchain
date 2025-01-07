default:
	make build
	make run

up:
	docker-compose up

down:
	docker-compose down

shell:
	docker exec -it langchain-app /bin/sh

clean:
	docker-compose down --volumes --rmi all

build:
	@if [ ! -f .env ]; then \
		echo "Moving .env-example to .env"; \
		cp .env-example .env; \
	fi
	docker-compose build

logs:
	docker-compose logs -f

restart:
	make down
	make up

test-interactive:
	python3 src/main.py

run:
	docker-compose run --rm app
