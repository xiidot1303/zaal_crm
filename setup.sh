#!/bin/bash

# Exit if any command fails
set -e

printf "Enter DB user:\n"
read DB_USER
printf "Enter DB password:\n"
read DB_PASS

echo "=== Updating system packages ==="
sudo apt update && sudo apt upgrade -y

echo "=== Installing required packages ==="
sudo apt install -y \
    nginx \
    supervisor \
    postgresql postgresql-contrib \
    redis-server \
    python3-certbot-nginx \
    python3-pip \
    python3-venv


echo "=== Configuring PostgreSQL user ==="
# Switch to postgres user to run SQL commands
sudo -u postgres psql <<EOF
-- Create user if not exists
DO
\$do\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
      CREATE USER "${DB_USER}" WITH PASSWORD '${DB_PASS}';
   END IF;
END
\$do\$;

-- Grant superuser privileges
ALTER ROLE "${DB_USER}" WITH SUPERUSER;
EOF

echo "=== Updating pg_hba.conf for Django connections ==="
PG_HBA_FILE=$(sudo -u postgres psql -t -P format=unaligned -c "SHOW hba_file;")

# Backup before editing
sudo cp "$PG_HBA_FILE" "${PG_HBA_FILE}.bak"

# Ensure md5 authentication for local connections
if ! grep -q "${DB_USER}" "$PG_HBA_FILE"; then
    echo "host    all    ${DB_USER}    127.0.0.1/32    md5" | sudo tee -a "$PG_HBA_FILE"
    echo "host    all    ${DB_USER}    ::1/128        md5" | sudo tee -a "$PG_HBA_FILE"
fi

echo "=== Restarting PostgreSQL ==="
sudo systemctl restart postgresql

echo "=== PostgreSQL setup completed ==="
echo "User: $DB_USER"
echo "Password: $DB_PASS"
echo "Role: SUPERUSER"

# Install pgbouncer if needed
if [[ "$answer" != "yes" ]]; then
    echo "=== Installation finished successfully! ==="
    exit 0
fi

echo "Installing PgBouncer..."

# ====== INSTALL ======
sudo apt install -y pgbouncer

# ====== STOP SERVICE BEFORE CONFIG ======
sudo systemctl stop pgbouncer

# ====== CONFIGURE pgbouncer.ini ======
sudo bash -c "cat > /etc/pgbouncer/pgbouncer.ini" <<EOF
[databases]
* = host=127.0.0.1 port=5432

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
admin_users = $DB_USER
pool_mode = transaction
max_client_conn = 100
default_pool_size = 20
EOF

# ====== GENERATE MD5 PASSWORD ======
MD5_PASS=$(echo -n "${DB_PASS}${DB_USER}" | md5sum | awk '{print $1}')

# ====== CREATE userlist.txt ======
echo "\"$DB_USER\" \"md5$MD5_PASS\"" | sudo tee /etc/pgbouncer/userlist.txt

sudo chown postgres:postgres /etc/pgbouncer/userlist.txt
sudo chmod 600 /etc/pgbouncer/userlist.txt

# ====== START SERVICE ======
sudo systemctl enable pgbouncer
sudo systemctl start pgbouncer

echo "PgBouncer installation and configuration completed."
echo "Listening on port 6432"

echo "=== Installation finished successfully! ==="
