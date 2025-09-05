DATE := $(shell date +%F)

build:
	docker build app/

test:
	docker compose -f /home/ccmmma/prometeo/opt/docker/docker-compose.yml up --build web

run:
	docker compose -f /home/ccmmma/prometeo/opt/docker/docker-compose.yml up -d --build web

backup:
	docker exec postgres pg_dump -U user -d cnmost -Fc \
	| gzip > backup_mydb_$(DATE).dump.gz

restore-%:
	gunzip -c $* \
	| docker exec -i postgres pg_restore -U user \
		--clean --if-exists --no-owner --no-privileges \
		-d cnmost
