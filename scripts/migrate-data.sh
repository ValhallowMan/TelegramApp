#!/bin/bash
# migrate-data.sh

# Backup from old server
docker compose exec postgres pg_dump -U $DB_USER -d $DB_NAME -Fc > backup.dump

# Copy backup to new server (scp/rsync)
scp backup.dump user@new-server:/path

# On new server: Restore
docker compose exec postgres pg_restore -U $DB_USER -d $DB_NAME -c backup.dump

# Apply migrations after restore
docker compose exec app alembic upgrade head