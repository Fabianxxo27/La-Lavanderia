"""
Blueprint de admin
Rutas del panel de administración
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, Response, jsonify
from werkzeug.security import generate_password_hash
from models import run_query, ensure_cliente_exists
from services import limpiar_texto, validar_email, send_email_async
from decorators import login_requerido, admin_requerido
from helpers import admin_only, obtener_esquema_descuento_cliente, ejecutar_sql_file, get_safe_redirect
from io import BytesIO
import pandas as pd
import datetime
import barcode
from barcode.writer import ImageWriter
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from pyzbar.pyzbar import decode
from PIL import Image as PILImage
import cv2
import numpy as np
import os
import json
import secrets
import string

bp = Blueprint('admin', __name__)


# -----------------------------------------------
# FUNCIONES AUXILIARES
# -----------------------------------------------
def tabla_descuento_existe():
    """Verifica si la tabla descuento_config existe."""
    try:
        result = run_query(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'descuento_config')",
            fetchone=True
        )
        return bool(result[0]) if result else False
    except Exception:
        return False


def parse_sql_statements(sql_text):
    """Parsea un archivo SQL en sentencias individuales."""
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


def ejecutar_sql_file_local(nombre_archivo):
    """Ejecuta un archivo SQL desde la carpeta migrations."""
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


def validar_contrasena(password):
    """Valida que la contraseña cumpla con los requisitos de seguridad."""
    import re
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not re.search(r'[A-Z]', password):
        return "La contraseña debe contener al menos una letra mayúscula."
    if not re.search(r'[a-z]', password):
        return "La contraseña debe contener al menos una letra minúscula."
    if not re.search(r'[0-9]', password):
        return "La contraseña debe contener al menos un número."
    return True


def crear_notificacion(id_usuario, titulo, mensaje, tipo='info', url=None):
    """Crea una notificación para un usuario."""
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


# -----------------------------------------------
# PÁGINA PRINCIPAL DEL PANEL (administrador)
# -----------------------------------------------
@bp.route('/inicio')
@login_requerido
@admin_requerido
def inicio():
    return render_template('inicio.html')


# -----------------------------------------------
# LISTAR PEDIDOS
# -----------------------------------------------
@bp.route('/pedidos')
@login_requerido
@admin_requerido
def pedidos():
    """Mostrar todos los pedidos con búsqueda, filtrado y paginación (para administrador)."""
    if not admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('auth.index'))
    
    # Obtener parámetros de filtrado y paginación
    cliente_filter = request.args.get('cliente', '').strip()
    estado_filter = request.args.get('estado', '').strip()
    fecha_desde = request.args.get('desde', '').strip()
    fecha_hasta = request.args.get('hasta', '').strip()
    orden = request.args.get('orden', 'desc').strip().lower()
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 10
    
    # Construir query base para contar
    count_query = """
        SELECT COUNT(*) FROM pedido p
        LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE 1=1
    """
    
    # Construir query base para datos
    query = """
        SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre, p.codigo_barras
        FROM pedido p
        LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE 1=1
    """
    params = {}
    
    # Agregar filtros dinámicamente
    filtro_where = ""
    if cliente_filter:
        filtro_where += " AND (LOWER(c.nombre) LIKE LOWER(:cliente) OR c.id_cliente = :cliente_id)"
        params['cliente'] = f"%{cliente_filter}%"
        try:
            params['cliente_id'] = int(cliente_filter)
        except:
            params['cliente_id'] = -1
    
    if estado_filter:
        filtro_where += " AND p.estado = :estado"
        params['estado'] = estado_filter
    
    if fecha_desde:
        filtro_where += " AND DATE(p.fecha_ingreso) >= :desde"
        params['desde'] = fecha_desde
    
    if fecha_hasta:
        filtro_where += " AND DATE(p.fecha_ingreso) <= :hasta"
        params['hasta'] = fecha_hasta
    
    # Aplicar filtros a ambas queries
    count_query += filtro_where
    query += filtro_where
    
    # Contar total de registros
    total_result = run_query(count_query, params, fetchall=True)
    total_count = total_result[0][0] if total_result else 0
    total_paginas = (total_count + por_pagina - 1) // por_pagina if total_count > 0 else 1
    
    # Ajustar página si está fuera de rango
    if pagina < 1:
        pagina = 1
    if pagina > total_paginas and total_paginas > 0:
        pagina = total_paginas
    
    # Agregar orden y paginación
    orden_sql = "DESC" if orden == 'desc' else "ASC"
    query += f" ORDER BY p.fecha_ingreso {orden_sql} LIMIT {por_pagina} OFFSET {(pagina - 1) * por_pagina}"
    
    # Ejecutar query
    data = run_query(query, params, fetchall=True)
    
    return render_template('pedidos.html',
                         pedidos=data,
                         cliente_filter=cliente_filter,
                         estado_filter=estado_filter,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta,
                         orden=orden,
                         pagina=pagina,
                         total_paginas=total_paginas)


# -----------------------------------------------
# CALENDARIO DE PEDIDOS
# -----------------------------------------------
@bp.route('/calendario-pedidos')
@login_requerido
@admin_requerido
def calendario_pedidos():
    """Mostrar calendario interactivo de pedidos."""
    # Obtener todos los pedidos para el calendario
    pedidos_raw = run_query("""
        SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, u.nombre
        FROM pedido p
        LEFT JOIN usuario u ON p.id_cliente = u.id_usuario
        ORDER BY p.fecha_ingreso
    """, fetchall=True)
    
    # Convertir Row objects a diccionarios para serialización JSON
    pedidos_calendario = []
    for row in pedidos_raw:
        pedidos_calendario.append({
            'id_pedido': row[0],
            'fecha_ingreso': row[1].isoformat() if row[1] else None,
            'fecha_entrega': row[2].isoformat() if row[2] else None,
            'estado': row[3],
            'nombre_cliente': row[4] or 'Sin nombre'
        })
    
    return render_template('calendario_pedidos.html', pedidos_calendario=pedidos_calendario)


# -----------------------------------------------
# ACTUALIZAR PEDIDO
# -----------------------------------------------
@bp.route('/actualizar_pedido/<int:id_pedido>', methods=['POST'])
def actualizar_pedido(id_pedido):
    """Actualizar estado de un pedido."""
    if not admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('auth.index'))
    
    estado = request.form.get('estado')
    
    try:
        # Obtener datos del pedido y cliente antes de actualizar
        pedido_data = run_query("""
            SELECT p.id_pedido, p.codigo_barras, p.fecha_entrega, c.nombre, c.email, p.id_cliente, p.estado
            FROM pedido p
            LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
            WHERE p.id_pedido = :id
        """, {"id": id_pedido}, fetchone=True)
        
        if not pedido_data:
            flash('Pedido no encontrado.', 'danger')
            return redirect(url_for('admin.pedidos'))
        
        estado_anterior = pedido_data[6]
        id_cliente = pedido_data[5]
        codigo = pedido_data[1] or f"#{id_pedido}"
        nombre_cliente = pedido_data[3]
        
        # Actualizar estado
        run_query(
            "UPDATE pedido SET estado = :e WHERE id_pedido = :id",
            {"e": estado, "id": id_pedido},
            commit=True
        )
        
        # Crear notificación para el cliente si el estado cambió
        if id_cliente and estado != estado_anterior:
            titulo = ""
            mensaje = ""
            tipo = "info"
            
            if estado == "En proceso":
                titulo = f"🔄 Pedido {codigo} en Proceso"
                mensaje = "Tu pedido está siendo procesado. Estamos lavando tu ropa con el mayor cuidado."
                tipo = "info"
            elif estado == "Completado":
                titulo = f"✅ Pedido {codigo} Completado"
                mensaje = "¡Tu pedido está listo! Tu ropa está limpia y lista para ser entregada."
                tipo = "success"
            elif estado == "Cancelado":
                titulo = f"❌ Pedido {codigo} Cancelado"
                mensaje = "Tu pedido ha sido cancelado. Si tienes dudas, contacta con nosotros."
                tipo = "error"
            elif estado == "Pendiente":
                titulo = f"🕐 Pedido {codigo} Pendiente"
                mensaje = "Tu pedido está registrado y pronto será procesado."
                tipo = "warning"
            
            if titulo:
                crear_notificacion(
                    id_usuario=id_cliente,
                    titulo=titulo,
                    mensaje=mensaje,
                    tipo=tipo,
                    url=f'/cliente_pedidos'
                )
        
        # Enviar correo según el nuevo estado
        if pedido_data and pedido_data[4]:
            fecha_entrega = pedido_data[2]
            email_cliente = pedido_data[4]
            
            if estado == "En proceso":
                html = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                            <h1 style="color: white; margin: 0;">🔄 Pedido en Proceso</h1>
                        </div>
                        <div style="padding: 30px; background: #f9f9f9;">
                            <h2 style="color: #1a4e7b;">Hola {nombre_cliente},</h2>
                            <p>Tu pedido <strong>{codigo}</strong> está siendo procesado.</p>
                            <p>Estamos lavando tu ropa con el mayor cuidado. La entregaremos el <strong>{fecha_entrega}</strong>.</p>
                        </div>
                    </body>
                </html>
                """
                send_email_async(email_cliente, f"Pedido {codigo} en Proceso", html)
            
            elif estado == "Completado":
                html = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #4CAF50 0%, #388E3C 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                            <h1 style="color: white; margin: 0;">✅ Pedido Completado</h1>
                        </div>
                        <div style="padding: 30px; background: #f9f9f9;">
                            <h2 style="color: #1a4e7b;">Hola {nombre_cliente},</h2>
                            <p>¡Buenas noticias! Tu pedido <strong>{codigo}</strong> está listo.</p>
                            <p>Tu ropa está limpia y lista para ser entregada. La recibirás pronto en tu domicilio.</p>
                        </div>
                    </body>
                </html>
                """
                send_email_async(email_cliente, f"Pedido {codigo} Completado y Listo", html)
        
        flash('Pedido actualizado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al actualizar: {e}', 'danger')
    
    return redirect(url_for('admin.pedido_detalles', id_pedido=id_pedido))


# -----------------------------------------------
# ELIMINAR PEDIDO
# -----------------------------------------------
@bp.route('/eliminar_pedido/<int:id_pedido>', methods=['POST'])
def eliminar_pedido(id_pedido):
    """Eliminar un pedido y sus datos asociados (recibos y prendas)."""
    if not admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('auth.index'))
    
    try:
        # 1. Eliminar recibos asociados al pedido
        run_query(
            "DELETE FROM recibo WHERE id_pedido = :id",
            {"id": id_pedido},
            commit=True
        )
        
        # 2. Eliminar prendas asociadas al pedido
        run_query(
            "DELETE FROM prenda WHERE id_pedido = :id",
            {"id": id_pedido},
            commit=True
        )
        
        # 3. Eliminar el pedido
        run_query(
            "DELETE FROM pedido WHERE id_pedido = :id",
            {"id": id_pedido},
            commit=True
        )
        flash('Pedido eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar: {e}', 'danger')
    
    return redirect(get_safe_redirect())


# -----------------------------------------------
# DETALLES DE PEDIDO
# -----------------------------------------------
@bp.route('/pedido_detalles/<int:id_pedido>')
def pedido_detalles(id_pedido):
    """Ver detalles de un pedido."""
    pedido = run_query(
        "SELECT id_pedido, fecha_ingreso, fecha_entrega, estado, id_cliente, codigo_barras, direccion_recogida, direccion_entrega FROM pedido WHERE id_pedido = :id",
        {"id": id_pedido},
        fetchone=True
    )
    
    if not pedido:
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('admin.pedidos'))
    
    prendas = run_query(
        "SELECT id_prenda, tipo, descripcion, observaciones FROM prenda WHERE id_pedido = :id",
        {"id": id_pedido},
        fetchall=True
    )
    
    # Obtener la página de origen para el botón regresar
    referer = request.args.get('ref') or request.referrer or ''
    return_url = referer if referer and referer != request.url else None
    
    return render_template('pedido_detalles.html', pedido=pedido, prendas=prendas, return_url=return_url)


# -----------------------------------------------
# VER PRENDAS DEL PEDIDO
# -----------------------------------------------
@bp.route('/pedido_prendas/<int:id_pedido>')
def pedido_prendas(id_pedido):
    """Ver las prendas detalladas de un pedido."""
    username = session.get('username')
    rol = session.get('rol')
    
    if not username:
        flash("No autorizado.", "danger")
        return redirect(url_for('auth.login'))
    
    # Obtener datos del pedido
    pedido = run_query("""
        SELECT p.id_pedido, p.id_cliente, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre
        FROM pedido p
        LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE p.id_pedido = :id
    """, {"id": id_pedido}, fetchone=True)
    
    if not pedido:
        flash("Pedido no encontrado.", "danger")
        return redirect(url_for('cliente.cliente_pedidos' if rol != 'administrador' else 'admin.pedidos'))
    
    # Verificar permisos (cliente solo ve sus propios pedidos, admin ve todos)
    if rol != 'administrador':
        usuario = run_query(
            "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
            {"u": username.lower()},
            fetchone=True
        )
        if usuario[0] != pedido[1]:
            flash("No tienes acceso a este pedido.", "danger")
            return redirect(url_for('cliente.cliente_pedidos'))
    
    # Obtener prendas del pedido agrupadas por tipo
    prendas = run_query("""
        SELECT 
            MIN(id_prenda) as id_prenda,
            tipo,
            COUNT(*) as cantidad,
            MAX(descripcion) as descripcion,
            CASE tipo
                WHEN 'Camisa' THEN 5000
                WHEN 'Pantalón' THEN 6000
                WHEN 'Vestido' THEN 8000
                WHEN 'Chaqueta' THEN 10000
                WHEN 'Saco' THEN 7000
                WHEN 'Falda' THEN 5500
                WHEN 'Blusa' THEN 4500
                WHEN 'Abrigo' THEN 12000
                WHEN 'Suéter' THEN 6500
                WHEN 'Jeans' THEN 7000
                WHEN 'Corbata' THEN 3000
                WHEN 'Bufanda' THEN 3500
                WHEN 'Sábana' THEN 8000
                WHEN 'Edredón' THEN 15000
                WHEN 'Cortina' THEN 12000
                ELSE 5000
            END as precio
        FROM prenda
        WHERE id_pedido = :id
        GROUP BY tipo
        ORDER BY tipo
    """, {"id": id_pedido}, fetchall=True)
    
    # Calcular precio total
    precio_dict = {}
    total_costo = 0
    for prenda in prendas:
        tipo = prenda[1]
        cantidad = prenda[2]
        precio = prenda[4]
        precio_dict[tipo] = float(precio)
        total_costo += float(precio) * cantidad
    
    # Obtener la página de origen para el botón regresar
    referer = request.args.get('ref') or request.referrer or ''
    return_url = referer if referer and referer != request.url else None
    
    return render_template('pedido_prendas.html',
                         pedido=pedido,
                         prendas=prendas,
                         precio_dict=precio_dict,
                         total_costo=total_costo,
                         rol=rol,
                         return_url=return_url)


# -----------------------------------------------
# GENERAR RECIBO PDF
# -----------------------------------------------
@bp.route('/generar_recibo/<int:id_pedido>')
def generar_recibo(id_pedido):
    """Genera y descarga el recibo en formato PDF."""
    try:
        # Obtener datos del pedido (compatible con o sin columnas de descuento)
        try:
            # Intentar con columnas de descuento
            pedido = run_query("""
                SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre, p.codigo_barras, u.email, p.direccion_recogida, p.direccion_entrega, p.porcentaje_descuento, p.nivel_descuento
                FROM pedido p
                LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
                LEFT JOIN usuario u ON c.id_cliente = u.id_usuario
                WHERE p.id_pedido = :id
            """, {"id": id_pedido}, fetchone=True)
            tiene_columnas_descuento = True
        except Exception as e:
            # Si falla, usar sin columnas de descuento
            pedido = run_query("""
                SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre, p.codigo_barras, u.email, p.direccion_recogida, p.direccion_entrega
                FROM pedido p
                LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
                LEFT JOIN usuario u ON c.id_cliente = u.id_usuario
                WHERE p.id_pedido = :id
            """, {"id": id_pedido}, fetchone=True)
            tiene_columnas_descuento = False
        
        if not pedido:
            return "Pedido no encontrado", 404
        
        # Obtener prendas
        prendas = run_query("""
            SELECT tipo, descripcion, 
                CASE tipo
                    WHEN 'Camisa' THEN 5000
                    WHEN 'Pantalón' THEN 6000
                    WHEN 'Vestido' THEN 8000
                    WHEN 'Chaqueta' THEN 10000
                    WHEN 'Saco' THEN 7000
                    WHEN 'Falda' THEN 5500
                    WHEN 'Blusa' THEN 4500
                    WHEN 'Abrigo' THEN 12000
                    WHEN 'Suéter' THEN 6500
                    WHEN 'Jeans' THEN 7000
                    WHEN 'Corbata' THEN 3000
                    WHEN 'Bufanda' THEN 3500
                    WHEN 'Sábana' THEN 8000
                    WHEN 'Edredón' THEN 15000
                    WHEN 'Cortina' THEN 12000
                    ELSE 5000
                END as precio
            FROM prenda
            WHERE id_pedido = :id
        """, {"id": id_pedido}, fetchall=True)
        
        # Obtener recibo
        recibo = run_query("""
            SELECT r.monto, r.fecha, r.id_cliente FROM recibo r WHERE id_pedido = :id
        """, {"id": id_pedido}, fetchone=True)
        
        # Calcular descuento
        subtotal = sum(p[2] for p in prendas)
        
        if tiene_columnas_descuento and len(pedido) >= 11:
            descuento_porcentaje = pedido[9] or 0
            nivel_descuento = pedido[10] or "Sin nivel"
        else:
            descuento_porcentaje = 0
            nivel_descuento = "Sin nivel"
        
        descuento_monto = (subtotal * descuento_porcentaje) / 100 if descuento_porcentaje > 0 else 0
        
        # Crear PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Título
        title_style = styles['Title']
        story.append(Paragraph("RECIBO - LA LAVANDERÍA", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Información del pedido
        info_data = [
            ['Pedido #:', str(pedido[0])],
            ['Cliente:', pedido[4] or 'N/A'],
            ['Email:', pedido[6] or 'No registrado'],
            ['Fecha Ingreso:', str(pedido[1])],
            ['Fecha Entrega:', str(pedido[2]) if pedido[2] else 'Por definir'],
            ['Estado:', pedido[3]],
        ]
        
        # Agregar direcciones si existen
        if pedido[7]:
            info_data.append(['Dirección Recogida:', pedido[7]])
        if pedido[8]:
            info_data.append(['Dirección Entrega:', pedido[8]])
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Agregar código de barras si existe
        if pedido[5]:
            story.append(Paragraph("Código de Barras:", styles['Heading3']))
            story.append(Spacer(1, 0.1*inch))
            
            # Generar imagen del código de barras
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(pedido[5], writer=ImageWriter())
            barcode_buffer = BytesIO()
            barcode_instance.write(barcode_buffer, options={
                'module_width': 0.3,
                'module_height': 10.0,
                'quiet_zone': 2.0,
                'font_size': 10,
                'text_distance': 3.0,
                'write_text': True
            })
            barcode_buffer.seek(0)
            
            # Agregar imagen al PDF
            barcode_img = Image(barcode_buffer, width=4*inch, height=1*inch)
            story.append(barcode_img)
            story.append(Spacer(1, 0.3*inch))
        
        # Tabla de prendas
        story.append(Paragraph("Prendas:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        prendas_data = [['Tipo', 'Descripción', 'Precio']]
        total = 0
        for prenda in prendas:
            prendas_data.append([prenda[0], prenda[1] or '-', f'${prenda[2]:,}'])
            total += prenda[2]
        
        prendas_table = Table(prendas_data, colWidths=[2*inch, 2.5*inch, 1.5*inch])
        prendas_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ]))
        story.append(prendas_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Subtotal y descuento
        if recibo:
            # Subtotal
            subtotal_data = [['Subtotal:', f'${subtotal:,.0f}']]
            subtotal_table = Table(subtotal_data, colWidths=[4.5*inch, 1.5*inch])
            subtotal_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ]))
            story.append(subtotal_table)
            
            # Descuento si aplica
            if descuento_monto > 0:
                story.append(Spacer(1, 0.1*inch))
                descuento_data = [[f'Descuento {nivel_descuento} ({descuento_porcentaje}%):', f'-${descuento_monto:,.0f}']]
                descuento_table = Table(descuento_data, colWidths=[4.5*inch, 1.5*inch])
                descuento_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.lightyellow),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                    ('TEXTCOLOR', (1, 0), (1, -1), colors.red),
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ]))
                story.append(descuento_table)
            
            story.append(Spacer(1, 0.1*inch))
            
            # Total final
            total_data = [['TOTAL A PAGAR:', f'${recibo[0]:,.0f}']]
            total_table = Table(total_data, colWidths=[4.5*inch, 1.5*inch])
            total_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgreen),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 14),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ]))
            story.append(total_table)
        
        # Generar PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'recibo_pedido_{id_pedido}.pdf'
        )
    except Exception as e:
        print(f"Error generando PDF: {e}")
        return "Error generando PDF", 500


# -----------------------------------------------
# LECTOR DE CÓDIGOS DE BARRAS
# -----------------------------------------------
@bp.route('/lector_barcode', methods=['GET', 'POST'])
@login_requerido
@admin_requerido
def lector_barcode():
    """Escanear código de barras y mostrar detalles del pedido."""
    if not admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('auth.index'))
    
    if request.method == 'POST':
        # Verificar si se subió una imagen
        if 'barcode_image' not in request.files:
            return jsonify({'success': False, 'error': 'No se subió ninguna imagen'}), 400
        
        file = request.files['barcode_image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'}), 400
        
        try:
            # Validar que el archivo sea una imagen
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            
            if file_ext not in allowed_extensions:
                return jsonify({
                    'success': False, 
                    'error': 'Formato de archivo no válido. Por favor sube una imagen (PNG, JPG, JPEG, GIF, BMP, WEBP)'
                }), 400
            
            # Leer imagen
            image_bytes = file.read()
            
            if len(image_bytes) == 0:
                return jsonify({'success': False, 'error': 'El archivo está vacío o corrupto'}), 400
            
            # Intentar decodificar la imagen
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return jsonify({
                    'success': False, 
                    'error': 'No se pudo leer la imagen. Asegúrate de que el archivo sea una imagen válida'
                }), 400
            
            # Verificar que la imagen tenga un tamaño razonable
            height, width = img.shape[:2]
            if width < 50 or height < 50:
                return jsonify({
                    'success': False, 
                    'error': 'La imagen es demasiado pequeña. Por favor usa una imagen de mejor calidad'
                }), 400
            
            # Convertir a PIL Image para pyzbar
            try:
                img_pil = PILImage.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            except Exception as conv_error:
                return jsonify({
                    'success': False, 
                    'error': 'Error al procesar la imagen. Intenta con otra imagen'
                }), 400
            
            # Decodificar código de barras
            decoded_objects = decode(img_pil)
            
            if not decoded_objects or len(decoded_objects) == 0:
                return jsonify({
                    'success': False, 
                    'error': 'No se detectó ningún código de barras en la imagen. Asegúrate de que la imagen contenga un código de barras visible y bien enfocado'
                }), 400
            
            # Obtener el primer código detectado
            try:
                barcode_data = decoded_objects[0].data.decode('utf-8')
            except UnicodeDecodeError:
                return jsonify({
                    'success': False, 
                    'error': 'El código de barras detectado no es válido o está corrupto'
                }), 400
            
            # Buscar pedido por código de barras
            try:
                pedido = run_query("""
                    SELECT p.id_pedido, p.id_cliente, p.fecha_ingreso, p.fecha_entrega, 
                           p.estado, c.nombre, c.telefono, c.direccion, u.email
                    FROM pedido p
                    JOIN cliente c ON p.id_cliente = c.id_cliente
                    LEFT JOIN usuario u ON c.id_cliente = u.id_usuario
                    WHERE p.codigo_barras = :codigo
                """, {"codigo": barcode_data}, fetchone=True)
            except Exception as db_error:
                print(f"Error en consulta de pedido: {str(db_error)}")
                return jsonify({
                    'success': False, 
                    'error': 'Error al buscar el pedido en la base de datos'
                }), 500
            
            if not pedido:
                return jsonify({'success': False, 'error': f'No se encontró ningún pedido con el código: {barcode_data}'}), 404
            
            # Obtener prendas del pedido
            try:
                prendas = run_query("""
                    SELECT tipo, descripcion, observaciones
                    FROM prenda
                    WHERE id_pedido = :id
                """, {"id": pedido[0]}, fetchall=True)
            except Exception as prendas_error:
                print(f"Error al obtener prendas: {str(prendas_error)}")
                prendas = []
            
            # Obtener recibo del pedido
            try:
                recibo = run_query("""
                    SELECT monto, descuento, fecha
                    FROM recibo
                    WHERE id_pedido = :id
                """, {"id": pedido[0]}, fetchone=True)
            except Exception as recibo_error:
                print(f"Error al obtener recibo: {str(recibo_error)}")
                recibo = None
            
            # Preparar respuesta con manejo seguro de fechas
            try:
                fecha_ingreso_str = 'N/A'
                if pedido[2]:
                    try:
                        fecha_ingreso_str = pedido[2].strftime('%d/%m/%Y %H:%M')
                    except:
                        fecha_ingreso_str = str(pedido[2])
                
                fecha_entrega_str = 'Pendiente'
                if pedido[3]:
                    try:
                        fecha_entrega_str = pedido[3].strftime('%d/%m/%Y')
                    except:
                        fecha_entrega_str = str(pedido[3])
                
                response_data = {
                    'success': True,
                    'codigo_barras': barcode_data,
                    'pedido': {
                        'id': pedido[0],
                        'fecha_ingreso': fecha_ingreso_str,
                        'fecha_entrega': fecha_entrega_str,
                        'estado': pedido[4] or 'Desconocido',
                    },
                    'cliente': {
                        'id': pedido[1],
                        'nombre': pedido[5] or 'No registrado',
                        'telefono': pedido[6] or 'No registrado',
                        'direccion': pedido[7] or 'No registrada',
                        'email': pedido[8] or 'No registrado'
                    },
                    'prendas': [{'tipo': p[0], 'descripcion': p[1] or '', 'observaciones': p[2] or ''} for p in (prendas or [])],
                    'recibo': None
                }
                
                # Agregar información del recibo si existe
                if recibo:
                    try:
                        fecha_recibo_str = 'N/A'
                        if recibo[2]:
                            try:
                                fecha_recibo_str = recibo[2].strftime('%d/%m/%Y')
                            except:
                                fecha_recibo_str = str(recibo[2])
                        
                        response_data['recibo'] = {
                            'monto': float(recibo[0]) if recibo[0] else 0,
                            'descuento': float(recibo[1]) if recibo[1] else 0,
                            'fecha': fecha_recibo_str
                        }
                    except Exception as recibo_format_error:
                        print(f"Error al formatear recibo: {str(recibo_format_error)}")
                        response_data['recibo'] = None
                
            except Exception as format_error:
                print(f"Error al formatear respuesta: {str(format_error)}")
                return jsonify({
                    'success': False, 
                    'error': 'Error al procesar los datos del pedido'
                }), 500
            
            return jsonify(response_data), 200
        
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error inesperado en lector_barcode:")
            print(error_trace)
            
            return jsonify({
                'success': False, 
                'error': f'Error: {str(e)[:100]}'
            }), 500
    
    # GET request - mostrar página
    return render_template('lector_barcode.html')
