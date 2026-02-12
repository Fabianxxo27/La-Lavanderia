#!/usr/bin/env python3
"""
Script para ejecutar la migración de notificaciones
Uso: python ejecutar_migracion_notificaciones.py
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
import urllib.parse

# Cargar variables de entorno
load_dotenv()

def conectar_bd():
    """Conectar a la base de datos PostgreSQL"""
    # Intentar con DATABASE_URL primero (Render)
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        # Si no existe, crear desde credentials.py
        try:
            import credentials as cd
            pwd = urllib.parse.quote_plus(cd.password)
            database_url = f"postgresql://{cd.user}:{pwd}@{cd.host}/{cd.db}"
            print(f"ℹ️  Usando credenciales locales de credentials.py")
        except Exception as e:
            print(f"❌ ERROR: No se pudo obtener DATABASE_URL ni credentials.py")
            print(f"   {e}")
            sys.exit(1)
    else:
        print("ℹ️  Usando DATABASE_URL de variables de entorno")
    
    # Convertir postgres:// a postgresql:// si es necesario
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        conn = psycopg2.connect(database_url)
        print("✅ Conexión exitosa a la base de datos")
        return conn
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        print(f"   Verifica que PostgreSQL esté corriendo y que las credenciales sean correctas")
        sys.exit(1)

def verificar_tabla_notificaciones(conn):
    """Verificar si la tabla notificacion existe"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'notificacion'
            )
        """)
        existe = cursor.fetchone()[0]
        cursor.close()
        return existe
    except Exception as e:
        print(f"⚠️ Error al verificar tabla: {e}")
        return False

def ejecutar_migración():
    """Ejecutar la migración de notificaciones"""
    print("=" * 70)
    print("🔔 MIGRACIÓN: SISTEMA DE NOTIFICACIONES EN TIEMPO REAL")
    print("=" * 70)
    print()
    
    # Conectar a la base de datos
    conn = conectar_bd()
    print()
    
    # Verificar si ya existe la tabla
    if verificar_tabla_notificaciones(conn):
        print("ℹ️  ✓ La tabla 'notificacion' ya existe")
        print("✅ Sistema de notificaciones ya está implementado")
        conn.close()
        return True
    
    # Ejecutar el SQL de la migración
    try:
        ruta_migracion = os.path.join(os.path.dirname(__file__), 'migrations', 'create_notificaciones.sql')
        
        if not os.path.exists(ruta_migracion):
            print(f"❌ Archivo no encontrado: {ruta_migracion}")
            conn.close()
            return False
        
        with open(ruta_migracion, 'r', encoding='utf-8') as f:
            sql_contenido = f.read()
        
        cursor = conn.cursor()
        cursor.execute(sql_contenido)
        conn.commit()
        cursor.close()
        
        print("✅ Tabla 'notificacion' creada exitosamente")
        print()
        
        # Verificar la tabla creada
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'notificacion'
            ORDER BY ordinal_position
        """)
        columnas = cursor.fetchall()
        cursor.close()
        
        print("📋 Columnas creadas:")
        for col_name, col_type in columnas:
            print(f"   • {col_name}: {col_type}")
        
        print()
        print("✅ Características del sistema:")
        print("   • Notificaciones en tiempo real para cambios de estado")
        print("   • Badge contador de notificaciones no leídas")
        print("   • Dropdown panel con últimas 20 notificaciones")
        print("   • Timestamps relativos (Ahora, Hace Xmin, Hace Xh, Hace Xd)")
        print("   • Marcado individual y en lote de notificaciones")
        print("   • Auto-refresh cada 30 segundos")
        print()
        print("=" * 70)
        print("🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 70)
        print()
        print("💡 Próximos pasos:")
        print("   1. Reinicia la aplicación para cargar el nuevo código")
        print("   2. Si usas Render, haz un push a GitHub para redeploy automático")
        print("   3. Los clientes verán la campana (🔔) en su navbar")
        print("   4. Los cambios de estado en pedidos crearán notificaciones automáticamente")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error al ejecutar la migración: {e}")
        conn.rollback()
        conn.close()
        return False

if __name__ == "__main__":
    success = ejecutar_migración()
    sys.exit(0 if success else 1)
