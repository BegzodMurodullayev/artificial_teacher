import asyncio
import json
import sqlite3
from pathlib import Path
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "engbot.db"  # Check config if it's different. In run.py/config it might be something else
KUTUBXONA_FILE = BASE_DIR / "bolimlar    test" / "kutubxona" / "kitob_baza.json"
EVRIKA_FILE = BASE_DIR / "bolimlar    test" / "evrika" / "evrika.json"
ZAKOVAT_OCHIQ_FILE = BASE_DIR / "bolimlar    test" / "zakovat" / "zakovat_ochiq.json"

def seed_materials():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table if not exists (in case it wasn't created yet)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_type TEXT NOT NULL,
            category TEXT,
            title TEXT NOT NULL,
            author TEXT,
            description TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Check if we already have seeded items
    cursor.execute("SELECT COUNT(*) FROM materials")
    if cursor.fetchone()[0] > 0:
        print("Materials already seeded. Run DELETE FROM materials if you want to reseed.")
        # Optional: delete and re-seed? No, just clear for safe measure for this script
        cursor.execute("DELETE FROM materials")
        print("Cleared materials table.")

    count = 0
    
    # 1. Kutubxona
    if KUTUBXONA_FILE.exists():
        with open(KUTUBXONA_FILE, 'r', encoding='utf-8') as f:
            books = json.load(f)
            for b in books:
                cursor.execute(
                    "INSERT INTO materials (material_type, category, title, author, description, content) VALUES (?, ?, ?, ?, ?, ?)",
                    ('book', b.get('janr'), b.get('nom'), b.get('yozuvchi'), b.get('tavsif'), json.dumps(b))
                )
                count += 1
        print(f"Seeded {len(books)} books.")

    # 2. Evrika
    if EVRIKA_FILE.exists():
        with open(EVRIKA_FILE, 'r', encoding='utf-8') as f:
            facts = json.load(f)
            for fct in facts:
                cursor.execute(
                    "INSERT INTO materials (material_type, category, title, author, description, content) VALUES (?, ?, ?, ?, ?, ?)",
                    ('fact', fct.get('category'), fct.get('title'), fct.get('author'), fct.get('summary'), json.dumps(fct))
                )
                count += 1
        print(f"Seeded {len(facts)} facts.")

    # 3. Zakovat (Ochiq)
    if ZAKOVAT_OCHIQ_FILE.exists():
        with open(ZAKOVAT_OCHIQ_FILE, 'r', encoding='utf-8') as f:
            quizzes = json.load(f)
            for q in quizzes:
                cursor.execute(
                    "INSERT INTO materials (material_type, category, title, author, description, content) VALUES (?, ?, ?, ?, ?, ?)",
                    ('quiz', q.get('mavzu'), "Zakovat Savoli: " + str(q.get('id')), None, q.get('savol'), json.dumps(q))
                )
                count += 1
        print(f"Seeded {len(quizzes)} quizzes.")

    conn.commit()
    conn.close()
    print(f"Total seeded: {count}")

if __name__ == '__main__':
    seed_materials()
