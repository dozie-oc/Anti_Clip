
import sqlite3
import os
import json

db_path = r'c:\Users\New\Desktop\Pie\Anti_Clip\storage\anticlip.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, transcript FROM projects WHERE id='f4fb1328-539f-4424-9cba-ef8d5db7181c'")
    row = cursor.fetchone()
    if row:
        transcript = json.loads(row[1]) if row[1] else []
        print(f"Project {row[0]} has {len(transcript)} transcript segments.")
    conn.close()
