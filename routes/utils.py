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
                print(f"DEBUG - Pedido ID: {pedido[0]}, Prendas encontradas: {len(prendas) if prendas else 0}")
                if prendas:
                    print(f"DEBUG - Prendas: {prendas}")
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
                
                print(f"DEBUG - Response data prendas: {response_data['prendas']}")
                
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
        
        except cv2.error as cv_error:
            return jsonify({
                'success': False, 
                'error': f'Error al procesar la imagen con OpenCV: {str(cv_error)}'
            }), 500
        
        except ValueError as val_error:
            return jsonify({
                'success': False, 
                'error': f'Datos inválidos en la imagen: {str(val_error)}'
            }), 400
        
        except MemoryError:
            return jsonify({
                'success': False, 
                'error': 'La imagen es demasiado grande. Por favor usa una imagen más pequeña'
            }), 400
            
        except Exception as e:
            # Log del error para debugging
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error inesperado en lector_barcode:")
            print(error_trace)
            
            # Intentar obtener más detalles del error
            error_details = str(e)
            if 'psycopg2' in error_trace:
                error_msg = 'Error de base de datos. Por favor contacta al administrador'
            elif 'decode' in error_trace.lower():
                error_msg = 'Error al decodificar el código de barras'
            elif 'image' in error_trace.lower():
                error_msg = 'Error al procesar la imagen'
            else:
                error_msg = f'Error: {error_details[:100]}'
            
            return jsonify({
                'success': False, 
                'error': error_msg
            }), 500
    
    # GET request - mostrar página
    return render_template('lector_barcode.html')


# -----------------------------------------------
# VER PRENDAS DEL PEDIDO (CLIENTE Y ADMIN)
# -----------------------------------------------
@bp.route('/pedido_prendas/<int:id_pedido>')
def pedido_prendas(id_pedido):
    """Ver las prendas detalladas de un pedido (para cliente y admin)."""
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
                    
                    # Determinar nivel según porcentaje
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
            ['Pedido #:', str(pedido[0])],
            ['Cliente:', pedido[4] or 'N/A'],
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

