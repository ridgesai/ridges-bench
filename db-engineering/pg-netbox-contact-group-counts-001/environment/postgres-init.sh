#!/bin/bash
set -euo pipefail

psql --username "$POSTGRES_USER" --dbname postgres --set ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE solver LOGIN PASSWORD 'solver-development-35d886f2'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
REVOKE ALL ON DATABASE postgres FROM PUBLIC;
REVOKE ALL ON DATABASE template0 FROM PUBLIC;
REVOKE ALL ON DATABASE template1 FROM PUBLIC;
SQL

createdb --username "$POSTGRES_USER" --owner solver netbox_dev
createdb --username "$POSTGRES_USER" --owner solver netbox_test

psql --username "$POSTGRES_USER" --dbname postgres --set ON_ERROR_STOP=1 <<'SQL'
REVOKE ALL ON DATABASE netbox_dev FROM PUBLIC;
REVOKE ALL ON DATABASE netbox_test FROM PUBLIC;
GRANT CONNECT ON DATABASE netbox_dev TO solver;
GRANT CONNECT ON DATABASE netbox_test TO solver;
SQL

touch "$PGDATA/TASK_READY"
