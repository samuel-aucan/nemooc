import sys
import os
import logging
from datetime import datetime

# Agregar la raíz del backend al path para poder importar módulos de 'app'
# Estamos asumiendo que el script se corre desde la carpeta 'nemo_oc' o 'nemo_oc_web'
# Nos aseguramos de añadir la ruta correcta a PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(current_dir, "..")
sys.path.append(app_dir)

from app.db import get_connection
from app.services.licitaciones_service import get_licitaciones_service

def auto_assign():
    print("Iniciando auto-asignación retroactiva para OCs NO-CM...")
    lics_svc = get_licitaciones_service()
    conn = get_connection()
    
    # Buscar todas las líneas NO-CM que no tienen itemcode_sap asignado
    cursor = conn.execute("""
        SELECT l.codigo_oc, l.correlativo, l.especificacion_comprador, l.producto, c.rut_unidad
        FROM oc_detalle l
        JOIN oc_cabecera c ON l.codigo_oc = c.codigo_oc
        WHERE c.tipo_oc != 'CM' 
          AND (l.itemcode_sap IS NULL OR l.itemcode_sap = '')
    """)
    rows = cursor.fetchall()
    print(f"Encontradas {len(rows)} líneas NO-CM sin asignar.")
    
    updated = 0
    now = datetime.now().isoformat()
    
    for row in rows:
        cod_oc, corr, esp, prod, rut_unidad = row
        query = str(esp) if esp else str(prod)
        sugs = lics_svc.buscar_sugerencias(query, rut_oc=rut_unidad, max_results=1)
        
        if sugs and sugs[0].score >= 0.35:
            sug = sugs[0]
            conn.execute("""
                UPDATE oc_detalle
                SET itemcode_sap = ?, descripcion_sap = ?, estado_homologacion = 'asignado_auto', updated_at = ?
                WHERE codigo_oc = ? AND correlativo = ?
            """, (sug.itemcode_sap, sug.descripcion_sap, now, cod_oc, corr))
            updated += 1
            print(f" -> Asignado {sug.itemcode_sap} a línea {corr} de OC {cod_oc} (Score: {sug.score:.2f})")
    
    conn.commit()
    conn.close()
    print(f"Completado. {updated} líneas actualizadas retroactivamente.")

if __name__ == "__main__":
    auto_assign()
