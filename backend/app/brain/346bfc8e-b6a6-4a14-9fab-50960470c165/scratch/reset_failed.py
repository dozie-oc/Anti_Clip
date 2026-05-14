import sqlite3
conn = sqlite3.connect('storage/anticlip.db')
c = conn.cursor()
c.execute("UPDATE projects SET status='pending', progress=0, processing_stage=NULL, error_message=NULL WHERE status IN ('failed','processing')")
c.execute("DELETE FROM jobs WHERE state != 'completed'")
conn.commit()
print("Reset complete.")
conn.close()
