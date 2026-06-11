#!/bin/bash
set -euo pipefail

DB_USER="stocktracker"
DB_PASS="${POSTGRES_PASSWORD:-stocktracker_prod_2026}"
DB_NAME="stocktracker"

PG_HBA="$(sudo -u postgres psql -tAc "SHOW hba_file;")"
echo "Updating $PG_HBA"

cp "$PG_HBA" "${PG_HBA}.bak.$(date +%s)"

# Replace ident/peer with password auth for local connections.
sed -i 's/ident/scram-sha-256/g' "$PG_HBA"
sed -i 's/peer/scram-sha-256/g' "$PG_HBA"

sudo -u postgres psql <<SQL
ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

systemctl reload postgresql
echo "PostgreSQL authentication updated"
