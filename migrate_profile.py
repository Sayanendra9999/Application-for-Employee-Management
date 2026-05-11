"""Add rejection_reason column to profile_update_requests table."""
import sqlite3

conn = sqlite3.connect('enterprise_portal.db')
cursor = conn.cursor()

# Check if column already exists
columns = [row[1] for row in cursor.execute('PRAGMA table_info(profile_update_requests)').fetchall()]
if 'rejection_reason' not in columns:
    cursor.execute("ALTER TABLE profile_update_requests ADD COLUMN rejection_reason TEXT DEFAULT ''")
    conn.commit()
    print('SUCCESS: Added rejection_reason column to profile_update_requests')
else:
    print('Column rejection_reason already exists, skipping.')

# Verify
columns_after = cursor.execute('PRAGMA table_info(profile_update_requests)').fetchall()
for col in columns_after:
    print(f'  {col}')

conn.close()
