# Microservicio Anime (Frontend + Backend + DB)

Tres contenedores interconectados:
- **db**: Postgres 16
- **backend**: FastAPI + SQLAlchemy (sin async), expone `http://localhost:8000`
- **frontend**: Nginx sirviendo `index.html`, expone `http://localhost:8080`

## Cómo ejecutar con Docker Compose

```bash
docker compose up -d --build
```

- Abre `http://localhost:8080` (frontend)
- La API responde en `http://localhost:8000/docs` (Swagger)

## Variables y conexiones
- El backend usa `DATABASE_URL=postgresql+psycopg2://anime_user:anime_pass@db:5432/anime_db`
- Postgres se inicializa con `db/init.sql` y persiste en el volumen `db_data`.

## Endpoints clave
- `GET /animes` listar
- `POST /animes` crear
- `GET /animes/{id}` obtener
- `PUT /animes/{id}` actualizar
- `DELETE /animes/{id}` eliminar

> La app crea la tabla y hace un seed automático si está vacía.
