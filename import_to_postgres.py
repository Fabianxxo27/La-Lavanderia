#!/usr/bin/env python3
"""
Script para importar datos a PostgreSQL en Render
Ejecuta: python import_to_postgres.py
"""

import psycopg2
import os

# URL de PostgreSQL (Render)
DATABASE_URL = "postgresql://fabianmedina:4ESJDVBJTp98LkbyzjmfJkrmRViCVnNf@dpg-d5t69vm3jp1c73b2u2j0-a.oregon-postgres.render.com/lalavanderia"

print("=" * 70)
print("📊 IMPORTANDO DATOS A PostgreSQL (Render)")
print("=" * 70)

try:
    # Conectar a PostgreSQL
    print("\n🔗 Conectando a PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("✅ Conectado a PostgreSQL")
    
    # Leer el archivo SQL
    print("\n📖 Leyendo archivo SQL...")
    with open('fabianmedina_miapp_postgres.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Ejecutar el SQL
    print("⏳ Ejecutando SQL...")
    cursor.execute(sql_content)
    conn.commit()
    
    print("✅ Datos importados exitosamente")
    
    # Verificar que se importaron
    cursor.execute("SELECT COUNT(*) FROM usuario")
    count = cursor.fetchone()[0]
    print(f"\n📈 Total de usuarios: {count}")
    
    cursor.execute("SELECT COUNT(*) FROM cliente")
    count = cursor.fetchone()[0]
    print(f"📈 Total de clientes: {count}")
    
    cursor.execute("SELECT COUNT(*) FROM pedido")
    count = cursor.fetchone()[0]
    print(f"📈 Total de pedidos: {count}")
    
    cursor.execute("SELECT COUNT(*) FROM prenda")
    count = cursor.fetchone()[0]
    print(f"📈 Total de prendas: {count}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ IMPORTACIÓN COMPLETADA")
    print("=" * 70)
    print("\nPróximos pasos:")
    print("1. Sube los cambios a GitHub (git push)")
    print("2. En Render, actualiza DATABASE_URL en tu servicio web")
    print("3. Redeploy tu aplicación")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
