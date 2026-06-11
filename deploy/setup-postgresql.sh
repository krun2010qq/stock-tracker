#!/bin/bash
set -euo pipefail

echo "Installing PostgreSQL..."
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y postgresql postgresql-contrib
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y postgresql-server postgresql
  postgresql-setup --initdb || true
fi

systemctl enable postgresql
systemctl start postgresql

DB_USER="stocktracker"
DB_PASS="${POSTGRES_PASSWORD:-stocktracker_prod_2026}"
DB_NAME="stocktracker"

sudo -u postgres psql <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';
  END IF;
END
\$\$;
SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

echo "PostgreSQL ready."
echo "DATABASE_URL=postgresql+psycopg2://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}"
