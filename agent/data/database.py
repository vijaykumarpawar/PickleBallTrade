import sqlite3
import pandas as pd
import os

class DatabaseManager:
    def __init__(self, db_path='agent/data/leads.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.initialize_db()

    def initialize_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS entities (id INTEGER PRIMARY KEY, name TEXT, type TEXT, city TEXT, state TEXT, website TEXT, email TEXT, phone TEXT, whatsapp TEXT, contact_person TEXT, address TEXT, priority TEXT, source TEXT, created_at TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS proposals (id INTEGER PRIMARY KEY, entity_id INTEGER, proposal_type TEXT, content TEXT, created_at TEXT)")
        conn.commit()
        conn.close()

    def store_entity(self, entity):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO entities (name, type, city, state, website, email, phone, whatsapp, contact_person, address, priority, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (entity.get("name",""), entity.get("type",""), entity.get("city",""), entity.get("state",""), entity.get("website",""), entity.get("email",""), entity.get("phone",""), entity.get("whatsapp",""), entity.get("contact_person",""), entity.get("address",""), entity.get("priority","medium"), entity.get("source","")))
        conn.commit()
        conn.close()

    def get_all_entities(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM entities")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT type, COUNT(*) FROM entities GROUP BY type")
        by_type = dict(cursor.fetchall())
        conn.close()
        return {"total_entities": total, "by_type": by_type}

    def export_entities(self, path="exports/leads.csv"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        entities = self.get_all_entities()
        df = pd.DataFrame(entities)
        df.to_csv(path, index=False)
        return path
