"""
Clear Database Script

This script clears all data from the message_logs table in the PostgreSQL database.
Use this before running new experiments to start with a clean slate.

Usage:
    python clear_database.py
"""

import os
import sys
import psycopg2

def connect_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            database=os.getenv("DB_NAME", "iotlab"),
            user=os.getenv("DB_USER", "iot"),
            password=os.getenv("DB_PASSWORD", "iot"),
            port=os.getenv("DB_PORT", "5433")
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nMake sure PostgreSQL container is running:")
        print("  docker compose up postgres -d")
        sys.exit(1)

def get_row_count(conn):
    """Get current row count"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM message_logs")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def clear_table(conn):
    """Clear all data from message_logs table"""
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE message_logs RESTART IDENTITY")
    conn.commit()
    cursor.close()

def main():
    print("=" * 60)
    print("  DATABASE CLEANUP")
    print("=" * 60)
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    conn = connect_db()
    print("✅ Connected successfully")
    
    # Get current row count
    row_count = get_row_count(conn)
    print(f"\n📊 Current records in database: {row_count:,}")
    
    if row_count == 0:
        print("\n✨ Database is already empty. Nothing to clear.")
        conn.close()
        return
    
    # Confirm deletion
    print("\n⚠️  WARNING: This will delete ALL data from message_logs table!")
    response = input("   Are you sure you want to continue? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        print("\n🗑️  Clearing database...")
        clear_table(conn)
        
        # Verify deletion
        new_count = get_row_count(conn)
        print(f"✅ Database cleared successfully!")
        print(f"   Deleted: {row_count:,} records")
        print(f"   Remaining: {new_count:,} records")
    else:
        print("\n❌ Operation cancelled. No data was deleted.")
    
    conn.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
