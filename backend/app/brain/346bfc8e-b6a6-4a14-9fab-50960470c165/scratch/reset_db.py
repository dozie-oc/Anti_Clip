
import sqlite3
import os

db_path = r'c:\Users\New\Desktop\Pie\Anti_Clip\storage\anticlip.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Resetting failed and stuck projects...")
    cursor.execute("UPDATE projects SET status='pending', progress=0, processing_stage=NULL WHERE status IN ('failed', 'processing')")
    cursor.execute("DELETE FROM jobs WHERE state IN ('failed', 'running', 'queued')")
    
    conn.commit()
    print("Done. Projects are now 'pending' and jobs are cleared.")
    conn.close()
