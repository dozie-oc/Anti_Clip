
import sqlite3
import os

db_path = r'c:\Users\New\Desktop\Pie\Anti_Clip\storage\anticlip.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Projects ---")
    cursor.execute("SELECT id, name, status, progress, processing_stage, error_message FROM projects")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- Jobs ---")
    cursor.execute("SELECT id, project_id, state, stage, progress, error FROM jobs")
    for row in cursor.fetchall():
        print(row)
    
    conn.close()
