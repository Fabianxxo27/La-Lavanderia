"""
Script para ejecutar migraciones de base de datos automáticamente
Ejecutar desde la terminal: python ejecutar_migraciones.py
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

# Cargar variables de entorno
load_dotenv()

def conectar_bd():
    """Conectar a la base de datos PostgreSQL"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL no encontrado en variables de entorno")
        print("Configura DATABASE_URL en tu archivo .env o variables de entorno")
        sys.exit(1)
    
    # Convertir postgres:// a postgresql:// si es necesario
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        conn = psycopg2.connect(database_url)
        print("✅ Conexión exitosa a la base de datos")
        return conn
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        sys.exit(1)

def ejecutar_sql_file(conn, archivo_sql):
    """Ejecutar un archivo SQL"""
    ruta_completa = os.path.join(os.path.dirname(__file__), 'migrations', archivo_sql)
    
    if not os.path.exists(ruta_completa):
        print(f"❌ Archivo no encontrado: {ruta_completa}")
        return False
    
    try:
        with open(ruta_completa, 'r', encoding='utf-8') as f:
            sql_contenido = f.read()
        
        cursor = conn.cursor()
        cursor.execute(sql_contenido)
        conn.commit()
        cursor.close()
        print(f"✅ Migración ejecutada: {archivo_sql}")
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Error al ejecutar {archivo_sql}: {e}")
        return False

def verificar_migracion_direcciones(conn):
    """Verificar si las columnas de dirección existen"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'pedido' 
            AND column_name IN ('direccion_recogida', 'direccion_entrega')
        """)
        columnas = cursor.fetchall()
        cursor.close()
        return len(columnas) == 2
    except Exception as e:
        print(f"⚠️ Error al verificar columnas: {e}")
        return False

def verificar_tabla_descuentos(conn):
    """Verificar si la tabla descuento_config existe"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'descuento_config'
            )
        """)
        existe = cursor.fetchone()[0]
        cursor.close()
        return existe
    except Exception as e:
        print(f"⚠️ Error al verificar tabla: {e}")
        return False

def verificar_columnas_descuento_pedido(conn):
    """Verificar si las columnas de descuento en pedido existen"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'pedido' 
            AND column_name IN ('porcentaje_descuento', 'nivel_descuento')
        """)
        columnas = cursor.fetchall()
        cursor.close()
        return len(columnas) == 2
    except Exception as e:
        print(f"⚠️ Error al verificar columnas: {e}")
        return False

def verificar_tabla_esquema_cliente(conn):
    """Verificar si la tabla cliente_esquema_descuento existe"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'cliente_esquema_descuento'
            )
        """)
        existe = cursor.fetchone()[0]
        cursor.close()
        return existe
    except Exception as e:
        print(f"⚠️ Error al verificar tabla: {e}")
        return False

def main():
    print("=" * 70)
    print("🚀 EJECUTANDO MIGRACIONES DE BASE DE DATOS")
    print("=" * 70)
    print()
    
    # Conectar a la base de datos
    conn = conectar_bd()
    
    print("\n📋 Verificando estado actual...")
    
    # Verificar migración 1: Direcciones
    tiene_direcciones = verificar_migracion_direcciones(conn)
    if tiene_direcciones:
        print("ℹ️  Las columnas de dirección ya existen, se omitirá esta migración")
    else:
        print("📝 Ejecutando migración: add_direcciones_to_pedido.sql")
        if ejecutar_sql_file(conn, 'add_direcciones_to_pedido.sql'):
            print("   ✓ Campos direccion_recogida y direccion_entrega agregados")
        else:
            print("   ✗ Falló la migración de direcciones")
    
    print()
    
    # Verificar migración 2: Tabla de descuentos
    tiene_descuentos = verificar_tabla_descuentos(conn)
    if tiene_descuentos:
        print("ℹ️  La tabla descuento_config ya existe, se omitirá esta migración")
    else:
        print("📝 Ejecutando migración: create_descuento_config.sql")
        if ejecutar_sql_file(conn, 'create_descuento_config.sql'):
            print("   ✓ Tabla descuento_config creada con datos iniciales")
            print("   ✓ Niveles: Bronce (5%), Plata (10%), Oro (15%), Platino (20%)")
        else:
            print("   ✗ Falló la migración de descuentos")
    
    print()
    
    # Verificar migración 3: Columnas de descuento en pedido
    tiene_descuento_pedido = verificar_columnas_descuento_pedido(conn)
    if tiene_descuento_pedido:
        print("ℹ️  Las columnas de descuento en pedido ya existen, se omitirá esta migración")
    else:
        print("📝 Ejecutando migración: add_descuento_to_pedido.sql")
        if ejecutar_sql_file(conn, 'add_descuento_to_pedido.sql'):
            print("   ✓ Columnas porcentaje_descuento y nivel_descuento agregadas a pedido")
            print("   ✓ Ahora los descuentos se guardan al crear el pedido")
        else:
            print("   ✗ Falló la migración de descuento en pedido")
    
    print()
    
    # Verificar migración 4: Tabla de esquema de cliente
    tiene_esquema_cliente = verificar_tabla_esquema_cliente(conn)
    if tiene_esquema_cliente:
        print("ℹ️  La tabla cliente_esquema_descuento ya existe, se omitirá esta migración")
    else:
        print("📝 Ejecutando migración: create_cliente_esquema_descuento.sql")
        if ejecutar_sql_file(conn, 'create_cliente_esquema_descuento.sql'):
            print("   ✓ Tabla cliente_esquema_descuento creada")
            print("   ✓ Ahora los clientes mantienen su esquema de promociones hasta completar el ciclo")
        else:
            print("   ✗ Falló la migración de esquema cliente")
    
    print()
    print("=" * 70)
    print("🎉 PROCESO COMPLETADO")
    print("=" * 70)
    
    # Verificación final
    print("\n🔍 Verificación final:")
    if verificar_migracion_direcciones(conn):
        print("   ✅ Columnas de dirección: OK")
    else:
        print("   ❌ Columnas de dirección: FALTAN")
    
    if verificar_columnas_descuento_pedido(conn):
        print("   ✅ Columnas de descuento en pedido: OK")
    else:
        print("   ❌ Columnas de descuento en pedido: FALTAN")
    
    if verificar_tabla_esquema_cliente(conn):
        print("   ✅ Tabla cliente_esquema_descuento: OK")
    else:
        print("   ❌ Tabla cliente_esquema_descuento: FALTA")
    
    if verificar_tabla_descuentos(conn):
        print("   ✅ Tabla descuento_config: OK")
        
        # Mostrar configuración actual
        cursor = conn.cursor()
        cursor.execute("SELECT nivel, porcentaje, pedidos_minimos, pedidos_maximos FROM descuento_config ORDER BY pedidos_minimos")
        descuentos = cursor.fetchall()
        cursor.close()
        
        if descuentos:
            print("\n   📊 Niveles de descuento configurados:")
            for d in descuentos:
                max_ped = d[3] if d[3] else "∞"
                print(f"      • {d[0]}: {d[1]}% ({d[2]}-{max_ped} pedidos)")
    else:
        print("   ❌ Tabla descuento_config: FALTA")
    
    conn.close()
    print("\n✅ Conexión cerrada")
    print("\n💡 Próximo paso: Configurar variables de entorno para el correo")
    print("   Ver instrucciones en MIGRACIONES.md")

if __name__ == "__main__":
    main()
