"""
Blueprint de api
API REST endpoints
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

bp = Blueprint('api', __name__)



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


            """, {"id": id_cliente, "json": json.dumps(esquema_actual)}, commit=True)
        except:
            # Si falla (tabla no existe), continuar sin guardar
            pass
        
        return esquema_actual


def _get_safe_redirect():
    """Obtiene una URL segura para redireccionar, priorizando el referrer."""
    referrer = request.referrer
    # Verificar que el referrer sea de la misma aplicación
    if referrer and request.host_url in referrer:
        return referrer
    # Fallback basado en el rol
    rol = session.get('rol', '').strip().lower()
    if rol == 'administrador':
        return url_for('pedidos')
    else:
        return url_for('cliente_pedidos')


    return_url = referer if referer and referer != request.url else None
    
    return render_template('pedido_prendas.html',
                         pedido=pedido,
                         prendas=prendas,
                         precio_dict=precio_dict,
                         total_costo=total_costo,
                         rol=rol,
                         return_url=return_url)


# -----------------------------------------------
# API: OBTENER PRENDAS DE UN PEDIDO (JSON)
# -----------------------------------------------
@bp.route('/api/prendas_pedido/<int:id_pedido>')
def api_prendas_pedido(id_pedido):
    """API para obtener prendas de un pedido en JSON (para cargas dinámicas)."""
    from flask import jsonify
    
    username = session.get('username')
    rol = session.get('rol')
    
    if not username:
        return jsonify({'error': 'No autorizado'}), 401
    
    # Verificar permisos
    pedido = run_query(
        "SELECT id_cliente FROM pedido WHERE id_pedido = :id",
        {"id": id_pedido},
        fetchone=True
    )
    
    if not pedido:
        return jsonify({'error': 'Pedido no encontrado'}), 404
    
    if rol != 'administrador':
        usuario = run_query(
            "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
            {"u": username.lower()},
            fetchone=True
        )
        if usuario[0] != pedido[0]:
            return jsonify({'error': 'Acceso denegado'}), 403
    
    # Obtener prendas con precios calculados según tipo
    prendas_data = run_query("""
        SELECT 
            p.tipo, 
            COUNT(*) as cantidad,
            p.descripcion,
            CASE p.tipo
                WHEN 'Camisa' THEN 5000
                WHEN 'Pantalón' THEN 6000
                WHEN 'Vestido' THEN 8000
                WHEN 'Chaqueta' THEN 10000


                WHEN 'Suéter' THEN 6500
                WHEN 'Jeans' THEN 7000
                WHEN 'Corbata' THEN 3000
                WHEN 'Bufanda' THEN 3500
                WHEN 'Sábana' THEN 8000
                WHEN 'Edredón' THEN 15000
                WHEN 'Cortina' THEN 12000
                ELSE 5000
            END as precio
        FROM prenda p
        WHERE p.id_pedido = :id
        GROUP BY p.tipo, p.descripcion
        ORDER BY p.tipo
    """, {"id": id_pedido}, fetchall=True)
    
    prendas = []
    for prenda in prendas_data:
        prendas.append({
            'tipo': prenda[0],
            'cantidad': int(prenda[1]) if prenda[1] else 0,
            'descripcion': prenda[2] or '',
            'precio': float(prenda[3]) if prenda[3] else 5000
        })
    
    return jsonify({'prendas': prendas})


# -----------------------------------------------
# API: AUTOCOMPLETADO DE CLIENTES


def api_autocomplete_clientes():
    """API para autocompletado de clientes."""
    from flask import jsonify
    
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify([])
    
    # Buscar clientes que coincidan con el query
    clientes = run_query("""
        SELECT id_usuario, nombre, email, username
        FROM usuario
        WHERE rol = 'cliente' 
        AND (
            LOWER(nombre) LIKE LOWER(:q) OR
            LOWER(email) LIKE LOWER(:q) OR
