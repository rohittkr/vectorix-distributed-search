-- Runs once, on first container startup (docker-entrypoint-initdb.d).
-- Table creation itself is handled by Alembic migrations, not here --
-- this file is only for one-time database-level setup.

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
