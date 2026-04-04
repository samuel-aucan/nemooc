import sys
import os
import sqlite3

current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "..", "nemo_oc", "nemo_db.sqlite")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM licitaciones_ref WHERE itemcode_sap = 'KNE00107'")
rows = cursor.fetchall()
print(f'Encontradas {len(rows)} filas para KNE00107:')
for r in rows:
    print(dict(r))

cursor.execute("SELECT COUNT(*) FROM licitaciones_ref WHERE descripcion_norm LIKE '%026%' OR descripcion_norm LIKE '%bandeja%' OR descripcion_norm LIKE '%curacion%' OR descripcion_norm LIKE '%anestesia%'")
count = cursor.fetchone()[0]
print(f'Total generic OR matches: {count}')
conn.close()
