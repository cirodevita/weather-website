build:
	docker build app/

test:
	docker compose -f /home/ccmmma/prometeo/opt/docker/docker-compose.yml up --build web

run:
	docker compose -f /home/ccmmma/prometeo/opt/docker/docker-compose.yml up -d --build web

backup:
	docker exec postgres pg_dump -U user -d cnmost | gzip > backup_mydb_$(date +%F).sql.gz

restore:
	gunzip -c backup_mydb_2025-09-05.sql.gz | docker exec -i postgres psql -U user -d cnmost