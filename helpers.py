"""
Funciones auxiliares reutilizables
"""
import os
import json
from flask import session, request, url_for
from models import run_query


def admin_only():
    """
    Verifica si el usuario actual es administrador.
    
    Returns:
        bool: True si es administrador, False en caso contrario
    """
    rol = session.get('rol')
    if not rol:
        return False
    return str(rol).strip().lower() == 'administrador'


def tabla_descuento_existe():
    """
    Verifica si la tabla descuento_config existe en la base de datos.
    
    Returns:
        bool: True si existe, False en caso contrario
    """
    try:
        result = run_query(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'descuento_config')",
            fetchone=True
        )
        return bool(result[0]) if result else False
    except Exception:
        return False


def parse_sql_statements(sql_text):
    """
    Parsea un archivo SQL en statements individuales.
    
    Args:
        sql_text: texto SQL completo
        
    Returns:
        lista de statements SQL
    """
    statements = []
    cleaned_lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('--'):
            continue
        if '--' in line:
            line = line.split('--', 1)[0]
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)
    for stmt in cleaned.split(';'):
        stmt = stmt.strip()
        if stmt:
            statements.append(stmt)
    return statements


def ejecutar_sql_file(nombre_archivo):
    """
    Ejecuta un archivo SQL desde la carpeta migrations.
    
    Args:
        nombre_archivo: nombre del archivo SQL
        
    Returns:
        tupla (éxito, error)
    """
    ruta = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations', nombre_archivo)
    if not os.path.exists(ruta):
        return False, 'Archivo no encontrado'
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
        statements = parse_sql_statements(contenido)
        for stmt in statements:
            run_query(stmt, commit=True)
        return True, None
    except Exception as e:
        return False, str(e)


def obtener_esquema_descuento_cliente(id_cliente):
    """
    Obtiene el esquema de descuento para un cliente específico.
    - Si tiene pedidos activos (Pendiente/En proceso), usa esquema congelado
    - Si NO tiene pedidos activos, usa esquema actual (actualizado)
    - Si completó el último nivel, actualiza al esquema actual
    
    Args:
        id_cliente: ID del cliente
        
    Returns:
        lista de dicts con nivel, porcentaje, min, max
    """
    # Obtener configuración actual
    config_actual = run_query("""
        SELECT nivel, porcentaje, pedidos_minimos, pedidos_maximos
        FROM descuento_config
        WHERE activo = true
        ORDER BY pedidos_minimos ASC
    """, fetchall=True)
    
    if not config_actual:
        # Valores por defecto si no hay configuración
        return [
            {"nivel": "Bronce", "porcentaje": 5, "min": 0, "max": 2},
            {"nivel": "Plata", "porcentaje": 10, "min": 3, "max": 5},
            {"nivel": "Oro", "porcentaje": 15, "min": 6, "max": 9},
            {"nivel": "Platino", "porcentaje": 20, "min": 10, "max": None}
        ]
    
    esquema_actual = [
        {
            "nivel": c[0],
            "porcentaje": int(c[1]),
            "min": int(c[2]),
            "max": int(c[3]) if c[3] is not None else None
        }
        for c in config_actual
    ]
    
    # Verificar si tiene pedidos activos (NO completados)
    pedidos_activos = run_query("""
        SELECT COUNT(*) FROM pedido 
        WHERE id_cliente = :id AND estado IN ('Pendiente', 'En proceso')
    """, {"id": id_cliente}, fetchone=True)[0] or 0
    
    # Si NO tiene pedidos activos, usar SIEMPRE el esquema actual
    if pedidos_activos == 0:
        # Desactivar cualquier esquema congelado anterior
        try:
            run_query("""
                UPDATE cliente_esquema_descuento
                SET activo = false
                WHERE id_cliente = :id AND activo = true
            """, {"id": id_cliente}, commit=True)
        except:
            pass
        
        return esquema_actual
    
    # Tiene pedidos activos - verificar si tiene esquema congelado
    try:
        esquema_guardado = run_query("""
            SELECT id_esquema, esquema_json, fecha_inicio
            FROM cliente_esquema_descuento
            WHERE id_cliente = :id AND activo = true
        """, {"id": id_cliente}, fetchone=True)
    except:
        esquema_guardado = None
    
    if esquema_guardado:
        # Tiene esquema congelado - verificar si completó TODOS los niveles
        try:
            esquema_json = json.loads(esquema_guardado[1])
            
            # Contar todos los pedidos del cliente (excepto cancelados)
            pedidos_count = run_query(
                "SELECT COUNT(*) FROM pedido WHERE id_cliente = :id AND estado != 'Cancelado'",
                {"id": id_cliente},
                fetchone=True
            )[0] or 0
            
            # Verificar si completó el último nivel del esquema
            # Solo actualizar si el último nivel tiene máximo definido Y lo superó
            ultimo_nivel = esquema_json[-1] if esquema_json else None
            if ultimo_nivel:
                max_ultimo = ultimo_nivel.get("max")
                # Si el último nivel es ilimitado (None), NUNCA actualizar
                # Si tiene máximo y lo superó, actualizar al esquema actual
                if max_ultimo is not None and pedidos_count > max_ultimo:
                    # Desactivar esquema anterior
                    run_query("""
                        UPDATE cliente_esquema_descuento
                        SET activo = false
                        WHERE id_esquema = :id
                    """, {"id": esquema_guardado[0]}, commit=True)
                    
                    # Crear nuevo esquema con config actual
                    run_query("""
                        INSERT INTO cliente_esquema_descuento (id_cliente, esquema_json, activo)
                        VALUES (:id, :json, true)
                    """, {"id": id_cliente, "json": json.dumps(esquema_actual)}, commit=True)
                    
                    return esquema_actual
            
            # Mantener esquema congelado (tiene pedidos activos)
            return esquema_json
        except:
            # Error parseando JSON, usar actual
            return esquema_actual
    else:
        # Tiene pedidos activos pero NO tiene esquema congelado - congelar el actual
        try:
            run_query("""
                INSERT INTO cliente_esquema_descuento (id_cliente, esquema_json, activo)
                VALUES (:id, :json, true)
            """, {"id": id_cliente, "json": json.dumps(esquema_actual)}, commit=True)
        except:
            # Si falla (tabla no existe), continuar sin guardar
            pass
        
        return esquema_actual


def get_safe_redirect():
    """
    Obtiene una URL segura para redireccionar, priorizando el referrer.
    
    Returns:
        URL de redirección segura
    """
    referrer = request.referrer
    # Verificar que el referrer sea de la misma aplicación
    if referrer and request.host_url in referrer:
        return referrer
    # Fallback basado en el rol
    rol = session.get('rol', '').strip().lower()
    if rol == 'administrador':
        return url_for('admin.pedidos')
    else:
        return url_for('cliente.cliente_pedidos')


def crear_notificacion(id_usuario, titulo, mensaje, tipo='info', url=None):
    """
    Crea una notificación para un usuario.
    
    Args:
        id_usuario: ID del usuario destinatario
        titulo: título de la notificación
        mensaje: mensaje de la notificación
        tipo: tipo de notificación (info, warning, error, success)
        url: URL opcional para acción relacionada
        
    Returns:
        bool: True si se creó correctamente, False en caso contrario
    """
    try:
        run_query("""
            INSERT INTO notificacion (id_usuario, titulo, mensaje, tipo, url)
            VALUES (:id_usuario, :titulo, :mensaje, :tipo, :url)
        """, {
            'id_usuario': id_usuario,
            'titulo': titulo,
            'mensaje': mensaje,
            'tipo': tipo,
            'url': url
        }, commit=True)
        return True
    except Exception as e:
        print(f"[ERROR] crear_notificacion: {e}")
        return False
