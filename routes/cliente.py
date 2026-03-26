"""
Blueprint de cliente
Rutas del panel de cliente
"""
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import run_query, ensure_cliente_exists
from services import limpiar_texto, validar_email, validar_contrasena, send_email_async
from decorators import login_requerido, admin_requerido
from helpers import admin_only, obtener_esquema_descuento_cliente, ejecutar_sql_file, get_safe_redirect
import datetime

bp = Blueprint('cliente', __name__)


@bp.route('/cliente_perfil', methods=['GET', 'POST'])
@login_requerido
def cliente_perfil():
    """Ver y actualizar perfil del cliente autenticado."""
    username = session.get('username')
    if not username:
        flash('Debes iniciar sesión para ver tu perfil.', 'danger')
        return redirect(url_for('auth.login'))

    cliente = run_query(
        """
        SELECT u.id_usuario, u.nombre, u.username, u.email,
               COALESCE(c.telefono, '') AS telefono,
               COALESCE(c.direccion, '') AS direccion
        FROM usuario u
        LEFT JOIN cliente c ON c.id_cliente = u.id_usuario
        WHERE LOWER(u.username) = :u AND u.rol = 'cliente'
        """,
        {"u": username.lower()},
        fetchone=True
    )

    if not cliente:
        flash('No se encontró la información del perfil.', 'danger')
        return redirect(url_for('auth.login'))

    perfil = {
        'id_cliente': cliente[0],
        'nombre': cliente[1] or '',
        'username': cliente[2] or '',
        'email': cliente[3] or '',
        'telefono': cliente[4] or '',
        'direccion': cliente[5] or '',
    }

    if request.method == 'POST':
        telefono = limpiar_texto(request.form.get('telefono', ''), 40)
        direccion = limpiar_texto(request.form.get('direccion', ''), 220)

        errores = []

        if telefono and not re.match(r'^[0-9+()\-\s]{7,20}$', telefono):
            errores.append('El teléfono solo puede tener números, espacios y los símbolos + ( ) -.')

        if direccion and len(direccion) < 5:
            errores.append('La dirección debe tener al menos 5 caracteres.')

        if errores:
            for error in errores:
                flash(error, 'warning')
            perfil['telefono'] = telefono
            perfil['direccion'] = direccion
            return render_template('cliente_perfil.html', perfil=perfil)

        try:
            ensure_cliente_exists(cliente[0])

            # Detectar qué campos cambiaron
            cambio_telefono = telefono != perfil['telefono']
            cambio_direccion = direccion != perfil['direccion']

            run_query(
                """
                INSERT INTO cliente (id_cliente, nombre, email, telefono, direccion)
                VALUES (:id, :n, :e, :t, :d)
                ON CONFLICT (id_cliente)
                DO UPDATE SET
                    telefono = EXCLUDED.telefono,
                    direccion = EXCLUDED.direccion
                """,
                {
                    "id": cliente[0],
                    "n": cliente[1],
                    "e": cliente[3],
                    "t": telefono,
                    "d": direccion,
                },
                commit=True
            )

            # Enviar correo de confirmación si hubo cambios en teléfono o dirección
            if (cambio_telefono or cambio_direccion) and perfil['email']:
                cambios_html = ""
                if cambio_telefono:
                    cambios_html += f'<p style="margin: 10px 0;"><strong>📱 Teléfono:</strong> {telefono or "<em>sin definir</em>"}</p>'
                if cambio_direccion:
                    cambios_html += f'<p style="margin: 10px 0;"><strong>📍 Dirección:</strong> {direccion or "<em>sin definir</em>"}</p>'

                html_confirmacion = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #a6cc48 0%, #8fb933 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                            <h1 style="color: white; margin: 0;">Datos Actualizados</h1>
                        </div>
                        <div style="padding: 30px; background: #f9f9f9;">
                            <h2 style="color: #1a4e7b;">Hola {perfil['nombre']},</h2>
                            <p style="font-size: 16px; line-height: 1.6;">
                                Te confirmamos que los siguientes datos de tu perfil han sido actualizados exitosamente:
                            </p>
                            <div style="background: white; border-left: 4px solid #a6cc48; padding: 20px; margin: 20px 0; border-radius: 5px;">
                                <h3 style="color: #1a4e7b; margin-top: 0;">📋 Datos actualizados:</h3>
                                {cambios_html}
                            </div>
                            <div style="background: #fff3cd; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #ffc107;">
                                <p style="margin: 0; font-size: 14px;">
                                    ⚠️ Si tú no realizaste estos cambios, por favor cambia tu contraseña inmediatamente
                                    e infórmanos.
                                </p>
                            </div>
                        </div>
                        <div style="background: #1a4e7b; padding: 20px; text-align: center; border-radius: 0 0 10px 10px;">
                            <p style="color: #a6cc48; margin: 0; font-size: 14px;">
                                La Lavandería - Tu servicio de confianza 🧺
                            </p>
                        </div>
                    </body>
                </html>
                """
                send_email_async(
                    perfil['email'],
                    'Confirmación de actualización de perfil - La Lavandería',
                    html_confirmacion
                )

            flash('Perfil actualizado correctamente.', 'success')
            return redirect(url_for('cliente.cliente_perfil'))
        except Exception as e:
            print(f"[ERROR] Actualizando perfil cliente: {e}")
            flash('No fue posible actualizar tu perfil. Intenta nuevamente.', 'danger')
            perfil['telefono'] = telefono
            perfil['direccion'] = direccion
            return render_template('cliente_perfil.html', perfil=perfil)

    return render_template('cliente_perfil.html', perfil=perfil)


@bp.route('/cliente_cambiar_contrasena', methods=['GET', 'POST'])
@login_requerido
def cliente_cambiar_contrasena():
    """Cambiar contraseña del cliente autenticado."""
    username = session.get('username')
    if not username:
        flash('Debes iniciar sesión para cambiar tu contraseña.', 'danger')
        return redirect(url_for('auth.login'))

    usuario = run_query(
        """
        SELECT u.id_usuario, u.nombre, u.username, u.email, u.password
        FROM usuario u
        WHERE LOWER(u.username) = :u AND u.rol = 'cliente'
        """,
        {"u": username.lower()},
        fetchone=True
    )

    if not usuario:
        flash('No se encontró el usuario.', 'danger')
        return redirect(url_for('auth.login'))

    perfil_seguridad = {
        'id_usuario': usuario[0],
        'nombre': usuario[1] or '',
        'username': usuario[2] or '',
        'email': usuario[3] or '',
    }

    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        errores = []

        if not current_password:
            errores.append('Debes ingresar tu contraseña actual.')
        elif not check_password_hash(usuario[4], current_password):
            errores.append('La contraseña actual no es correcta.')

        if not new_password:
            errores.append('Debes ingresar una nueva contraseña.')
        else:
            valida_password, mensaje_password = validar_contrasena(new_password)
            if not valida_password:
                errores.append(mensaje_password)

        if new_password != confirm_password:
            errores.append('La confirmación de la nueva contraseña no coincide.')

        if new_password and check_password_hash(usuario[4], new_password):
            errores.append('La nueva contraseña debe ser diferente a la actual.')

        if errores:
            for error in errores:
                flash(error, 'warning')
            return render_template('cliente_cambiar_contrasena.html', perfil_seguridad=perfil_seguridad)

        try:
            new_hashed_password = generate_password_hash(new_password)
            run_query(
                "UPDATE usuario SET password = :p WHERE id_usuario = :id",
                {"p": new_hashed_password, "id": usuario[0]},
                commit=True
            )

            flash('Contraseña actualizada correctamente.', 'success')
            return redirect(url_for('cliente.cliente_perfil'))
        except Exception as e:
            print(f"[ERROR] Cambiando contraseña cliente: {e}")
            flash('No fue posible actualizar tu contraseña. Intenta nuevamente.', 'danger')
            return render_template('cliente_cambiar_contrasena.html', perfil_seguridad=perfil_seguridad)

    return render_template('cliente_cambiar_contrasena.html', perfil_seguridad=perfil_seguridad)


# -----------------------------------------------
# PÁGINA PRINCIPAL DEL PANEL (cliente)
# -----------------------------------------------
@bp.route('/cliente_inicio')
@login_requerido
def cliente_inicio():
    """Dashboard del cliente con estadísticas y próximo nivel de descuento."""
    username = session.get('username')
    if not username:
        return redirect(url_for('auth.login'))
    
    # Obtener id_usuario (case-insensitive)
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
        {"u": username.lower()},
        fetchone=True
    )
    if not usuario:
        return redirect(url_for('auth.login'))
    
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
        pedidos_faltantes = primer_nivel.get("min", 0) - pedidos_count
        if pedidos_faltantes < 0:
            pedidos_faltantes = 0


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
        return redirect(url_for('auth.login'))
    
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
        return redirect(url_for('auth.login'))
    
    # Obtener id_usuario del cliente (case-insensitive)
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
        {"u": username.lower()},
        fetchone=True
    )
    
    if not usuario:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('auth.login'))
    
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
