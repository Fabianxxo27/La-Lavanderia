"""
Blueprint de cliente
Rutas del panel de cliente
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from models import run_query, ensure_cliente_exists
from services import limpiar_texto, validar_email, send_email_async
from decorators import login_requerido, admin_requerido
from helpers import admin_only, obtener_esquema_descuento_cliente, ejecutar_sql_file, get_safe_redirect
import datetime

bp = Blueprint('cliente', __name__)


# -----------------------------------------------
# PÁGINA PRINCIPAL DEL PANEL (cliente)
# -----------------------------------------------
@bp.route('/cliente_inicio')
@login_requerido
def cliente_inicio():
    """Dashboard del cliente con estadísticas y próximo nivel de descuento."""
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    
    # Obtener id_usuario (case-insensitive)
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
        {"u": username.lower()},
        fetchone=True
    )
    if not usuario:
        return redirect(url_for('login'))
    
    id_cliente = usuario[0]
    
    # Contar todos los pedidos del cliente (excepto cancelados)
    pedidos_count = run_query(
        "SELECT COUNT(*) FROM pedido WHERE id_cliente = :ic AND estado != 'Cancelado'",
        {"ic": id_cliente},
        fetchone=True
    )[0]
    
    # Calcular nivel de descuento segun esquema configurado
    esquema_cliente = obtener_esquema_descuento_cliente(id_cliente)
    nivel = None
    descuento_porcentaje = 0
    siguiente_nivel = None
    pedidos_faltantes = 0

    for i, nivel_config in enumerate(esquema_cliente):
        min_ped = nivel_config.get("min", 0)
        max_ped = nivel_config.get("max")

        if pedidos_count >= min_ped and (max_ped is None or pedidos_count <= max_ped):
            nivel = nivel_config.get("nivel")
            descuento_porcentaje = nivel_config.get("porcentaje", 0)

            if i + 1 < len(esquema_cliente):
                siguiente_nivel = esquema_cliente[i + 1].get("nivel")
                pedidos_faltantes = esquema_cliente[i + 1].get("min") - pedidos_count
                if pedidos_faltantes < 0:
                    pedidos_faltantes = 0
            else:
                siguiente_nivel = None
                pedidos_faltantes = 0
            break

    if not nivel and esquema_cliente:
        primer_nivel = esquema_cliente[0]
        nivel = "Sin nivel"
        descuento_porcentaje = 0
        siguiente_nivel = primer_nivel.get("nivel")


    iconos = {
        "Bronce": "🥉",
        "Plata": "🥈",
        "Oro": "🥇",
        "Platino": "💎",
        "Diamante": "💎"
    }
    icono = iconos.get(nivel, "⭐")
    
    # Obtener últimos 3 pedidos
    ultimos_pedidos = run_query("""
        SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado,
               (SELECT COUNT(*) FROM prenda WHERE id_pedido = p.id_pedido) as cantidad_prendas,
               ROW_NUMBER() OVER (PARTITION BY p.id_cliente ORDER BY p.fecha_ingreso ASC) as numero_pedido_cliente
        FROM pedido p
        WHERE p.id_cliente = :ic
        ORDER BY p.fecha_ingreso DESC
        LIMIT 3
    """, {"ic": id_cliente}, fetchall=True)
    
    # Calcular dinero ahorrado con descuentos
    recibos = run_query("""
        SELECT r.monto FROM recibo r
        WHERE r.id_cliente = :ic
    """, {"ic": id_cliente}, fetchall=True)
    
    total_gastado = sum(float(r[0]) if r[0] else 0 for r in recibos)
    total_recibos = len(recibos)
    
    # Estimar dinero ahorrado (si cada prenda cuesta 5000)
    # Este es un cálculo aproximado, en producción sería mejor guardarlo en BD
    PRICE_PER_PRENDA = 5000
    prendas_totales = run_query(
        "SELECT COUNT(*) FROM prenda WHERE id_pedido IN (SELECT id_pedido FROM pedido WHERE id_cliente = :ic)",
        {"ic": id_cliente},
        fetchone=True
    )[0]
    
    monto_sin_descuentos = prendas_totales * PRICE_PER_PRENDA
    dinero_ahorrado = monto_sin_descuentos - total_gastado if total_gastado > 0 else 0
    
    return render_template('cliente_inicio.html',
                         nombre_usuario=session.get('nombre', ''),
                         nivel=nivel,
                         icono=icono,
                         descuento_porcentaje=descuento_porcentaje,
                         pedidos_count=pedidos_count,
                         siguiente_nivel=siguiente_nivel,
                         pedidos_faltantes=pedidos_faltantes,
                         ultimos_pedidos=ultimos_pedidos,
                         total_gastado=total_gastado,
                         total_recibos=total_recibos,
                         dinero_ahorrado=dinero_ahorrado,
                         prendas_totales=prendas_totales)


# -----------------------------------------------
# RECIBOS DEL CLIENTE
# -----------------------------------------------
@bp.route('/cliente_recibos')
def cliente_recibos():
    """Ver recibos del cliente actual con estadísticas."""
    username = session.get('username')
    if not username:
        flash("No se pudo identificar al usuario.", "danger")
        return redirect(url_for('login'))
    
    recibos = run_query("""
        SELECT r.id_recibo, r.id_pedido, r.monto, r.fecha,
               ROW_NUMBER() OVER (PARTITION BY r.id_cliente ORDER BY p.fecha_ingreso ASC) as numero_pedido_cliente,
               p.codigo_barras
        FROM recibo r
        LEFT JOIN usuario u ON r.id_cliente = u.id_usuario
        LEFT JOIN pedido p ON r.id_pedido = p.id_pedido
        WHERE LOWER(u.username) = :u
        ORDER BY r.fecha DESC
    """, {"u": username.lower()}, fetchall=True)
    
    # Calcular estadísticas
    total_gastado = sum(float(r[2]) if r[2] else 0 for r in recibos)
    promedio_gasto = total_gastado / len(recibos) if recibos else 0
    
    return render_template('cliente_recibos.html', 
                         recibos=recibos,
                         total_gastado=total_gastado,
                         promedio_gasto=promedio_gasto,
                         total_recibos=len(recibos))


# -----------------------------------------------
# PROMOCIONES DEL CLIENTE
# -----------------------------------------------
@bp.route('/cliente_promociones')
def cliente_promociones():
    """Ver promociones disponibles para el cliente con sistema de lealtad."""
    username = session.get('username')
    if not username:
        flash("No se pudo identificar al usuario.", "danger")
        return redirect(url_for('login'))
    
    # Obtener id_usuario del cliente (case-insensitive)
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
        {"u": username.lower()},
        fetchone=True
    )
    
    if not usuario:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('login'))
    
    id_usuario = usuario[0]
    
    # Contar todos los pedidos del cliente (excepto cancelados)
    pedidos_count = run_query(
        "SELECT COUNT(*) FROM pedido WHERE id_cliente = :id AND estado != 'Cancelado'",
        {"id": id_usuario},
        fetchone=True
    )[0] or 0
    
    # Obtener esquema de descuento del cliente (congelado o actual)
    esquema_cliente = obtener_esquema_descuento_cliente(id_usuario)
    
    # Verificar si tiene esquema congelado
    try:
        esquema_info = run_query("""
            SELECT fecha_inicio FROM cliente_esquema_descuento
            WHERE id_cliente = :id AND activo = true
        """, {"id": id_usuario}, fetchone=True)
        tiene_esquema_congelado = esquema_info is not None
        fecha_inicio_esquema = esquema_info[0] if esquema_info else None
    except:
        tiene_esquema_congelado = False
        fecha_inicio_esquema = None
    
    # Determinar nivel actual del cliente según su esquema
    nivel_actual = None
    descuento_actual = 0
    progreso = 0
    siguiente_nivel = None
    pedidos_faltantes = 0
    
    for i, nivel_config in enumerate(esquema_cliente):
        min_ped = nivel_config.get("min", 0)
        max_ped = nivel_config.get("max")
        
        if pedidos_count >= min_ped and (max_ped is None or pedidos_count <= max_ped):
            nivel_actual = nivel_config.get("nivel")
            descuento_actual = nivel_config.get("porcentaje", 0)
            
            # Calcular progreso
            if max_ped is not None:
                rango = max_ped - min_ped + 1
                en_nivel = pedidos_count - min_ped
                progreso = (en_nivel / rango) * 100
                
                # Siguiente nivel
                if i + 1 < len(esquema_cliente):
                    siguiente_nivel = esquema_cliente[i + 1].get("nivel")
                    pedidos_faltantes = esquema_cliente[i + 1].get("min") - pedidos_count
                else:
                    siguiente_nivel = "Máximo nivel"
                    pedidos_faltantes = 0
            else:
                progreso = 100
                siguiente_nivel = "Máximo nivel"
                pedidos_faltantes = 0
            break
    
    if not nivel_actual and esquema_cliente:
        # Aún no alcanza el primer nivel
        primer_nivel = esquema_cliente[0]
        nivel_actual = "Sin nivel"
        descuento_actual = 0
        siguiente_nivel = primer_nivel.get("nivel")
        pedidos_faltantes = primer_nivel.get("min", 0) - pedidos_count
        if pedidos_faltantes < 0:
            pedidos_faltantes = 0
        progreso = (pedidos_count / primer_nivel.get("min", 1)) * 100 if primer_nivel.get("min", 0) > 0 else 0
    
    # Iconos por nivel
    iconos = {
        "Bronce": "🥉",
        "Plata": "🥈",
        "Oro": "🥇",
        "Platino": "💎",
        "Diamante": "💎"
    }
    icono = iconos.get(nivel_actual, "⭐")
    
    return render_template('cliente_promociones.html', 
                         pedidos_count=pedidos_count,
                         nivel=nivel_actual,
                         descuento_base=descuento_actual,
                         icono=icono,
                         progreso=progreso,
                         siguiente_nivel=siguiente_nivel,
                         pedidos_faltantes=pedidos_faltantes,
                         esquema_descuentos=esquema_cliente,
                         tiene_esquema_congelado=tiene_esquema_congelado,
                         fecha_inicio_esquema=fecha_inicio_esquema)


# -----------------------------------------------
# PEDIDOS DEL cliente
# -----------------------------------------------
@bp.route('/cliente_pedidos')
def cliente_pedidos():
    """Ver pedidos del cliente actual con paginación."""
    # Usar username desde la sesión (más seguro)
    username = session.get('username')
    if not username:
        flash("No se pudo identificar al usuario.", "danger")
        return redirect(url_for('auth.login'))
    
    # Obtener id_usuario (case-insensitive)
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
        {"u": username.lower()},
        fetchone=True
    )
    
    if not usuario:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('auth.login'))
    
    id_usuario = usuario[0]

    # Parámetros de paginación
    pagina = request.args.get('pagina', 1, type=int)
    if pagina < 1:
        pagina = 1
    
    por_pagina = 10  # Mostrar 10 pedidos por página
    offset = (pagina - 1) * por_pagina

    # Contar total de pedidos
    total_count = run_query(
        "SELECT COUNT(*) FROM pedido WHERE id_cliente = :id",
        {"id": id_usuario},
        fetchone=True
    )[0]

    # Obtener pedidos con conteo de prendas (con paginación)
    pedidos = run_query("""
        SELECT 
            p.id_pedido, 
            p.fecha_ingreso, 
            p.fecha_entrega, 
            p.estado,
            COUNT(pr.id_prenda) as total_prendas,
            ROW_NUMBER() OVER (ORDER BY p.fecha_ingreso ASC) as numero_pedido_cliente
        FROM pedido p
        LEFT JOIN prenda pr ON p.id_pedido = pr.id_pedido
        WHERE p.id_cliente = :id
        GROUP BY p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado
        ORDER BY p.fecha_ingreso DESC
        LIMIT :limit OFFSET :offset
    """, {"id": id_usuario, "limit": por_pagina, "offset": offset}, fetchall=True)
    
    # Estadísticas del cliente
    stats = {
        'total_pedidos': total_count,
        'pendientes': run_query(
            "SELECT COUNT(*) FROM pedido WHERE id_cliente = :id AND estado = 'Pendiente'",
            {"id": id_usuario},
            fetchone=True
        )[0],
        'en_proceso': run_query(
            "SELECT COUNT(*) FROM pedido WHERE id_cliente = :id AND estado = 'En proceso'",
            {"id": id_usuario},
            fetchone=True
        )[0],
        'completados': run_query(
            "SELECT COUNT(*) FROM pedido WHERE id_cliente = :id AND estado = 'Completado'",
            {"id": id_usuario},
            fetchone=True
        )[0]
    }

    # Calcular paginación
    total_paginas = (total_count + por_pagina - 1) // por_pagina
    tiene_anterior = pagina > 1
    tiene_siguiente = pagina < total_paginas

    return render_template('cliente_pedidos.html', 
                         pedidos=pedidos, 
                         username=username,
                         stats=stats,
                         pagina=pagina,
                         total_paginas=total_paginas,
                         tiene_anterior=tiene_anterior,
                         tiene_siguiente=tiene_siguiente,
                         total_count=total_count)
