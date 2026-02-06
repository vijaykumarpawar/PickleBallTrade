import sqlite3
import pandas as pd
import os
from datetime import datetime
from typing import Optional, Dict, Any

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
                enriched INTEGER DEFAULT 0,
                enriched_at TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("CREATE TABLE IF NOT EXISTS proposals (id INTEGER PRIMARY KEY, entity_id INTEGER, proposal_type TEXT, content TEXT, created_at TEXT)")
        
        # Migration: Add new columns if they don't exist
        migrations = [
            "ALTER TABLE entities ADD COLUMN email_sent INTEGER DEFAULT 0",
            "ALTER TABLE entities ADD COLUMN whatsapp_sent INTEGER DEFAULT 0",
            "ALTER TABLE entities ADD COLUMN email_sent_at TEXT",
            "ALTER TABLE entities ADD COLUMN whatsapp_sent_at TEXT",
            "ALTER TABLE entities ADD COLUMN enriched INTEGER DEFAULT 0",
            "ALTER TABLE entities ADD COLUMN enriched_at TEXT",
        ]
        
        for migration in migrations:
            try:
                cursor.execute(migration)
            except sqlite3.OperationalError:
                pass  # Column already exists
            
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
        entity_id = cursor.lastrowid
        conn.close()
        return entity_id

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

    def update_entity(self, entity_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update an entity with new data.
        
        Args:
            entity_id: The entity ID to update
            updates: Dictionary of fields to update (only non-None values will be updated)
            
        Returns:
            True if entity was updated, False otherwise
        """
        # Filter out None values - only update fields with actual values
        filtered_updates = {k: v for k, v in updates.items() if v is not None}
        
        if not filtered_updates:
            return False
        
        # Build update query dynamically
        set_clause = ", ".join([f"{key} = ?" for key in filtered_updates.keys()])
        values = list(filtered_updates.values())
        values.append(entity_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = f"UPDATE entities SET {set_clause} WHERE id = ?"
        cursor.execute(query, values)
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        return affected > 0

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

    def mark_enriched(self, entity_id):
        """Mark an entity as having been enriched with scraped data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE entities SET enriched = 1, enriched_at = ? WHERE id = ?",
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

    def get_entities_needing_enrichment(self, limit: int = 50):
        """Get entities with website but missing email or phone."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM entities 
            WHERE website IS NOT NULL AND website != ''
            AND (email IS NULL OR email = '' OR phone IS NULL OR phone = '')
            AND (enriched IS NULL OR enriched = 0)
            LIMIT ?
        """, (limit,))
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
        cursor.execute("SELECT COUNT(*) FROM entities WHERE email_sent = 1")
        emails_sent = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM entities WHERE whatsapp_sent = 1")
        whatsapp_sent = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM entities WHERE enriched = 1")
        enriched = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM entities WHERE email IS NOT NULL AND email != ''")
        with_email = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM entities WHERE phone IS NOT NULL AND phone != ''")
        with_phone = cursor.fetchone()[0]
        conn.close()
        return {
            "total_entities": total,
            "by_type": by_type,
            "emails_sent": emails_sent,
            "whatsapp_sent": whatsapp_sent,
            "enriched": enriched,
            "with_email": with_email,
            "with_phone": with_phone
        }

    def search_entities(self, query: str, limit: int = 20):
        """Search entities by name, city, or type."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM entities 
            WHERE name LIKE ? OR city LIKE ? OR type LIKE ?
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def delete_entity(self, entity_id: int) -> bool:
        """Delete an entity by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def export_entities(self, path="exports/leads.csv"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        entities = self.get_all_entities()
        df = pd.DataFrame(entities)
        df.to_csv(path, index=False)
        return path
