#!/bin/bash

# Ledger Database Backup Script

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/ledger_backup_$TIMESTAMP.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "📦 Creating database backup..."
echo "Backup file: $BACKUP_FILE"
echo ""

# Create backup
docker exec ledger_db mysqldump -u ledger_user -pledger_pass ledger_db > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Backup completed successfully!"
    echo "📁 Saved to: $BACKUP_FILE"
    
    # Get file size
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "📊 Backup size: $SIZE"
    
    # Keep only last 7 backups
    echo ""
    echo "🧹 Cleaning old backups (keeping last 7)..."
    ls -t "$BACKUP_DIR"/ledger_backup_*.sql | tail -n +8 | xargs -r rm
    
    echo "✅ Cleanup complete!"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/ledger_backup_*.sql
else
    echo "❌ Backup failed!"
    exit 1
fi
