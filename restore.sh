#!/bin/bash

# Ledger Database Restore Script

BACKUP_DIR="./backups"

echo "📂 Available backups:"
echo ""

# List available backups
ls -lh "$BACKUP_DIR"/ledger_backup_*.sql 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ No backups found in $BACKUP_DIR"
    exit 1
fi

echo ""
echo "Enter the backup filename to restore (e.g., ledger_backup_20240101_120000.sql):"
read BACKUP_FILE

BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"

if [ ! -f "$BACKUP_PATH" ]; then
    echo "❌ Backup file not found: $BACKUP_PATH"
    exit 1
fi

echo ""
echo "⚠️  WARNING: This will overwrite your current database!"
echo "📁 Restoring from: $BACKUP_PATH"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Restore cancelled"
    exit 0
fi

echo ""
echo "🔄 Restoring database..."

# Restore backup
docker exec -i ledger_db mysql -u ledger_user -pledger_pass ledger_db < "$BACKUP_PATH"

if [ $? -eq 0 ]; then
    echo "✅ Database restored successfully!"
    echo ""
    echo "🔄 Restarting backend service..."
    docker-compose restart backend
    echo "✅ Backend restarted"
else
    echo "❌ Restore failed!"
    exit 1
fi
