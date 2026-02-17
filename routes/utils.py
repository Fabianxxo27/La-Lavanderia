"""
Blueprint de utils
Utilidades (barcode, PDF, etc.)
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

bp = Blueprint('utils', __name__)



        
        # Obtener recibo y cliente
        recibo = run_query("""
            SELECT r.monto, r.fecha, r.id_cliente FROM recibo r WHERE id_pedido = :id
        """, {"id": id_pedido}, fetchone=True)
        
        # Calcular descuento (usar guardado si existe, sino calcular)
        subtotal = sum(p[2] for p in prendas)
        
        if tiene_columnas_descuento and len(pedido) >= 11:
            # Usar descuento guardado en el pedido
            descuento_porcentaje = pedido[9] or 0
            nivel_descuento = pedido[10] or "Sin nivel"
        else:
            # Calcular descuento (método antiguo para compatibilidad)
            descuento_monto_calculado = 0
            descuento_porcentaje = 0
            nivel_descuento = "Sin nivel"
            
            if recibo and subtotal > 0:
                descuento_monto_calculado = subtotal - recibo[0]
                if descuento_monto_calculado > 0:
                    descuento_porcentaje = int((descuento_monto_calculado / subtotal) * 100)


                    if descuento_porcentaje >= 15:
                        nivel_descuento = "Oro"
                    elif descuento_porcentaje >= 10:
                        nivel_descuento = "Plata"
                    elif descuento_porcentaje >= 5:
                        nivel_descuento = "Bronce"
        
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


            ['Email:', pedido[6] or 'No registrado'],
            ['Fecha Ingreso:', str(pedido[1])],
            ['Fecha Entrega:', str(pedido[2]) if pedido[2] else 'Por definir'],
            ['Estado:', pedido[3]],
        ]
        
        # Agregar direcciones si existen
        if pedido[7]:  # direccion_recogida
            info_data.append(['Dirección Recogida:', pedido[7]])
        if pedido[8]:  # direccion_entrega
            info_data.append(['Dirección Entrega:', pedido[8]])
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Agregar código de barras como imagen
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
# MIDDLEWARE DE SEGURIDAD
# -----------------------------------------------
@app.after_request
def agregar_headers_seguridad(response):
    """Agregar headers de seguridad básicos"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.errorhandler(404)
def pagina_no_encontrada(error):
    flash('Página no encontrada', 'warning')
    rol = str(session.get('rol', '')).strip().lower()
    if rol == 'administrador':
        return redirect(url_for('inicio')), 404
    elif 'id_usuario' in session:
        return redirect(url_for('cliente_inicio')), 404
    else:
        return redirect(url_for('index')), 404

@app.errorhandler(500)
def error_servidor(error):
    print(f"Error 500: {error}")
    import traceback
    traceback.print_exc()  # Imprimir traceback completo
    flash('Ha ocurrido un error. Intenta de nuevo.', 'danger')
    rol = str(session.get('rol', '')).strip().lower()
    if rol == 'administrador':
        return redirect(url_for('inicio')), 500
    elif 'id_usuario' in session:
        return redirect(url_for('cliente_inicio')), 500
    else:
        return redirect(url_for('index')), 500


# -----------------------------------------------
# MAIN
# -----------------------------------------------
if __name__ == '__main__':
    from waitress import serve
    print("🔒 Servidor iniciado con medidas de seguridad")
    print("📡 Escuchando en http://0.0.0.0:8080")
    serve(app, host='0.0.0.0', port=8080)


    username = session.get('username')
    rol = session.get('rol')
    
    if not username:
        flash("No autorizado.", "danger")
        return redirect(url_for('login'))
    
    # Obtener datos del pedido
    pedido = run_query("""
        SELECT p.id_pedido, p.id_cliente, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre
        FROM pedido p
        LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE p.id_pedido = :id
    """, {"id": id_pedido}, fetchone=True)
    
    if not pedido:
        flash("Pedido no encontrado.", "danger")
        return redirect(url_for('cliente_pedidos' if rol != 'administrador' else 'pedidos'))
    
    # Verificar permisos (cliente solo ve sus propios pedidos, admin ve todos)
    if rol != 'administrador':
        usuario = run_query(
            "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
            {"u": username.lower()},
            fetchone=True
        )
        if usuario[0] != pedido[1]:
            flash("No tienes acceso a este pedido.", "danger")
            return redirect(url_for('cliente_pedidos'))
    
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
    
