#!/bin/bash

# Clear Database Script (Shell version)
# This script clears all data from the message_logs table

echo "============================================================"
echo "  DATABASE CLEANUP"
echo "============================================================"

# Check if PostgreSQL container is running
if ! docker ps | grep -q logger_db; then
    echo ""
    echo "❌ PostgreSQL container (logger_db) is not running!"
    echo "   Start it with: docker compose up postgres -d"
    exit 1
fi

echo ""
echo "🔌 Connecting to database..."

# Get current row count
ROW_COUNT=$(docker exec -t logger_db psql -U iot -d iotlab -t -c "SELECT COUNT(*) FROM message_logs" | tr -d '[:space:]')

echo "✅ Connected successfully"
echo ""
echo "📊 Current records in database: $ROW_COUNT"

if [ "$ROW_COUNT" -eq 0 ]; then
    echo ""
    echo "✨ Database is already empty. Nothing to clear."
    exit 0
fi

echo ""
echo "⚠️  WARNING: This will delete ALL data from message_logs table!"
read -p "   Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" = "yes" ] || [ "$CONFIRM" = "y" ]; then
    echo ""
    echo "🗑️  Clearing database..."
    
    # Clear the table
    docker exec -t logger_db psql -U iot -d iotlab -c "TRUNCATE TABLE message_logs RESTART IDENTITY"
    
    # Verify deletion
    NEW_COUNT=$(docker exec -t logger_db psql -U iot -d iotlab -t -c "SELECT COUNT(*) FROM message_logs" | tr -d '[:space:]')
    
    echo "✅ Database cleared successfully!"
    echo "   Deleted: $ROW_COUNT records"
    echo "   Remaining: $NEW_COUNT records"
else
    echo ""
    echo "❌ Operation cancelled. No data was deleted."
fi

echo ""
echo "============================================================"
