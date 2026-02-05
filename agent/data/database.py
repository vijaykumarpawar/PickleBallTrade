import sqlite3
import pandas as pd
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='agent/data/leads.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.initialize_db()

    def initialize_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT,
                city TEXT,
                state TEXT,
                website TEXT,
                email TEXT,
                phone TEXT,
                whatsapp TEXT,
                contact_person TEXT,
                address TEXT,
                priority TEXT,
                source TEXT,
                email_sent INTEGER DEFAULT 0,
                whatsapp_sent INTEGER DEFAULT 0,
                email_sent_at TEXT,
                whatsapp_sent_at TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("CREATE TABLE IF NOT EXISTS proposals (id INTEGER PRIMARY KEY, entity_id INTEGER, proposal_type TEXT, content TEXT, created_at TEXT)")
        
        # Migration: Add new columns if they don't exist
        try:
            cursor.execute("ALTER TABLE entities ADD COLUMN email_sent INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            cursor.execute("ALTER TABLE entities ADD COLUMN whatsapp_sent INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE entities ADD COLUMN email_sent_at TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE entities ADD COLUMN whatsapp_sent_at TEXT")
        except sqlite3.OperationalError:
            pass
            
        conn.commit()
        conn.close()

    def store_entity(self, entity):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO entities (name, type, city, state, website, email, phone, whatsapp, 
                contact_person, address, priority, source, email_sent, whatsapp_sent, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,0,?)
        """, (
            entity.get("name",""), entity.get("type",""), entity.get("city",""), 
            entity.get("state",""), entity.get("website",""), entity.get("email",""), 
            entity.get("phone",""), entity.get("whatsapp",""), entity.get("contact_person",""), 
            entity.get("address",""), entity.get("priority","medium"), entity.get("source",""),
            datetime.now().isoformat()
        ))
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

    def get_entity_by_id(self, entity_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def mark_email_sent(self, entity_id):
        """Mark an entity as having received an email."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE entities SET email_sent = 1, email_sent_at = ? WHERE id = ?",
            (datetime.now().isoformat(), entity_id)
        )
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def mark_whatsapp_sent(self, entity_id):
        """Mark an entity as having received a WhatsApp message."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE entities SET whatsapp_sent = 1, whatsapp_sent_at = ? WHERE id = ?",
            (datetime.now().isoformat(), entity_id)
        )
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def reset_sent_status(self, entity_id, channel=None):
        """Reset sent status for an entity. channel can be 'email', 'whatsapp', or None for both."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if channel == 'email':
            cursor.execute("UPDATE entities SET email_sent = 0, email_sent_at = NULL WHERE id = ?", (entity_id,))
        elif channel == 'whatsapp':
            cursor.execute("UPDATE entities SET whatsapp_sent = 0, whatsapp_sent_at = NULL WHERE id = ?", (entity_id,))
        else:
            cursor.execute("UPDATE entities SET email_sent = 0, whatsapp_sent = 0, email_sent_at = NULL, whatsapp_sent_at = NULL WHERE id = ?", (entity_id,))
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def get_stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT type, COUNT(*) FROM entities GROUP BY type")
        by_type = dict(cursor.fetchall())
        cursor.execute("SELECT COUNT(*) FROM entities WHERE email_sent = 1")
        emails_sent = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM entities WHERE whatsapp_sent = 1")
        whatsapp_sent = cursor.fetchone()[0]
        conn.close()
        return {
            "total_entities": total,
            "by_type": by_type,
            "emails_sent": emails_sent,
            "whatsapp_sent": whatsapp_sent
        }

    def export_entities(self, path="exports/leads.csv"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        entities = self.get_all_entities()
        df = pd.DataFrame(entities)
        df.to_csv(path, index=False)
        return path
