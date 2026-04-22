import os
import re

DAO_DIR = "src/database/dao"

files_to_fix = {
    "sponsor_dao.py": [
        (r'is_active = 1"""', r'is_active = 1 RETURNING id"""'),
        (r'return cursor.lastrowid', r'row = await cursor.fetchone()\n    return row[0] if row else 0')
    ],
    "reward_dao.py": [
        (r'\) VALUES \(\?, \?, \?, \?, \?, \?, \?\)"', r') VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id"'),
        (r'return cursor.lastrowid', r'row = await cursor.fetchone()\n    return row[0] if row else 0')
    ],
    "quiz_dao.py": [
        (r'\) VALUES \(\?, \?, \?, \?, \?, \?, \?, \?\)"', r') VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id"'),
        (r'\) VALUES \(\?, \?, \?, \?, \?, \?\)"', r') VALUES (?, ?, ?, ?, ?, ?) RETURNING id"'),
        (r'return cursor.lastrowid', r'row = await cursor.fetchone()\n    return row[0] if row else 0')
    ],
    "payment_dao.py": [
        (r'\) VALUES \(\?, \?, \?, \?, \?, \?, \?, \?\)"', r') VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id"'),
        (r'return cursor.lastrowid', r'row = await cursor.fetchone()\n    return row[0] if row else 0')
    ],
    "material_dao.py": [
        (r'\) VALUES \(\?, \?, \?, \?, \?, \?\)"', r') VALUES (?, ?, ?, ?, ?, ?) RETURNING id"'),
        (r'return cursor.lastrowid', r'row = await cursor.fetchone()\n    return row[0] if row else 0')
    ],
    "game_dao.py": [
        (r'\) VALUES \(\?, \?, \?\)"', r') VALUES (?, ?, ?) RETURNING id"'),
        (r'return cursor.lastrowid', r'row = await cursor.fetchone()\n    return row[0] if row else 0')
    ]
}

def main():
    for filename, replacements in files_to_fix.items():
        filepath = os.path.join(DAO_DIR, filename)
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        for old, new in replacements:
            content = re.sub(old, new, content)
            
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"Fixed {filename}")

if __name__ == "__main__":
    main()
