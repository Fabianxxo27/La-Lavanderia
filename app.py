from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
import pandas as pd
import datetime
import credentials as cd
import os
import urllib.parse
from dotenv import load_dotenv
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

# Cargar variables de entorno desde .env (si existe)
load_dotenv()

# Configuración de la app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', '1379')

# Configuración de la base de datos
# En Render: usar DATABASE_URL desde variables de entorno (PostgreSQL)
# En desarrollo local: usar credentials.py (MySQL)
database_url = os.getenv('DATABASE_URL')

if not database_url:
    # Si no hay DATABASE_URL, usar credenciales locales (desarrollo con PostgreSQL)
    print("⚠️ DATABASE_URL no encontrado, usando credentials.py (desarrollo local con PostgreSQL)")
    pwd = urllib.parse.quote_plus(cd.password)
    database_url = f"postgresql://{cd.user}:{pwd}@{cd.host}/{cd.db}"
else:
    # Si viene de Render, convertir postgres:// a postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    print("✓ Usando DATABASE_URL desde Render (PostgreSQL)")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
print(f"✓ Base de datos configurada: {database_url[:50]}...")

# Configuración de conexión para Render
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 5,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 10,
}

# Desactivar track modifications de SQLAlchemy
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# ------------------ fin del bloque ------------------

db = SQLAlchemy(app)

# Hacer disponible la función now() en todos los templates
app.jinja_env.globals['now'] = datetime.datetime.now


# -----------------------------------------------
# FUNCIÓN PARA CONSULTAS SQL
# -----------------------------------------------
def run_query(query, params=None, fetchone=False, fetchall=False, commit=False, get_lastrowid=False):
    """Utility to run SQL queries.

    - For reads: use fetchone=True or fetchall=True.
    - For writes (commit=True): if get_lastrowid=True the function returns the last inserted id (if available).
    """
    if commit:
        # Para INSERT, UPDATE, DELETE
        with db.engine.begin() as conn:        # begin() hace commit al salir del bloque
            result = conn.execute(text(query), params or {})
            
            # Si piden fetchone, devolver la fila
            if fetchone:
                return result.fetchone()
            
            # Si piden fetchall, devolver todas las filas
            if fetchall:
                return result.fetchall()
            
            # Si piden lastrowid, intentar extraerlo
            if get_lastrowid:
                try:
                    return result.lastrowid
                except Exception:
                    return None
            
            return None
    else:
        # Para SELECT
        with db.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            if fetchone:
                return result.fetchone()
            if fetchall:
                return result.fetchall()


# -----------------------------------------------
# FUNCIÓN AUXILIAR: Garantizar que existe registro en cliente
# -----------------------------------------------
def ensure_cliente_exists(id_usuario):
    """
    Garantiza que existe un registro en la tabla cliente para un usuario.
    Si no existe, lo crea automáticamente.
    """
    try:
        cliente_exists = run_query(
            "SELECT id_cliente FROM cliente WHERE id_cliente = :id",
            {"id": id_usuario},
            fetchone=True
        )
        
        if not cliente_exists:
            # Obtener datos del usuario para crear el cliente
            usuario = run_query(
                "SELECT nombre, email FROM usuario WHERE id_usuario = :id",
                {"id": id_usuario},
                fetchone=True
            )
            
            if usuario:
                run_query(
                    "INSERT INTO cliente (id_cliente, nombre, email) VALUES (:ic, :n, :e)",
                    {
                        "ic": id_usuario,
                        "n": usuario[0],
                        "e": usuario[1]
                    },
                    commit=True
                )
                print(f"✓ Cliente creado automáticamente para id_usuario={id_usuario}")
    except Exception as e:
        print(f"✗ Error en ensure_cliente_exists: {e}")
        raise

# -----------------------------------------------
# RUTA PRINCIPAL
# -----------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')


# -----------------------------------------------
# LOGIN
# -----------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        user = run_query(
            "SELECT username, password, rol FROM usuario WHERE LOWER(username) = :u",
            {"u": username},
            fetchone=True
        )
 
        try:
            password_ok = bool(user) and check_password_hash(user[1], password)
        except ValueError:
            # Hash malformado en la base de datos (p. ej. contraseña sin hashear)
            flash("La contraseña almacenada para este usuario tiene un formato inválido. Pide restablecer la contraseña.", "danger")
            return redirect(url_for('login'))

        if password_ok:
            session['username'] = user[0]
            session['rol'] = user[2]
            flash(f"Bienvenido {username}", "success")

            # Redirigir según rol
            if str(user[2]).strip().lower() == 'administrador':
                return redirect(url_for('inicio'))
            else:
                return redirect(url_for('cliente_inicio'))
        else:
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template('login.html')


# -----------------------------------------------
# REGISTRO
# -----------------------------------------------
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        username = request.form.get("username").strip().lower()
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")
        password2 = request.form.get("password2")

        # Verificar confirmación de contraseña
        if password != password2:
            flash("Las contraseñas no coinciden.", "warning")
            return redirect(url_for("registro"))

        if not all([nombre, username, email, password]):
            flash("Por favor, completa todos los campos.", "warning")
            return redirect(url_for("registro"))

        hashed_password = generate_password_hash(password)

        try:
            # Verificar si el username ya existe (case-insensitive)
            existing_user = run_query(
                "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
                {"u": username},
                fetchone=True
            )
            # Verificar que el email no esté ya registrado en usuario (case-insensitive)
            existing_email = run_query(
                "SELECT id_usuario FROM usuario WHERE LOWER(email) = :e",
                {"e": email},
                fetchone=True
            )
            if existing_email:
                flash("El correo ya está registrado. Usa otro correo o recupera la cuenta.", "danger")
                return redirect(url_for("registro"))
            if existing_user:
                flash("❗ El nombre de usuario ya está registrado. Elige otro.", "danger")
                return redirect(url_for("registro"))

            # Insertar el nuevo usuario
            result = run_query(
                "INSERT INTO usuario (nombre, username, password, rol, email) VALUES (:n, :u, :p, :r, :e) RETURNING id_usuario",
                {
                    "n": nombre,
                    "u": username,
                    "p": hashed_password,
                    "r": "cliente",
                    "e": email
                },
                commit=True,
                fetchone=True
            )
            
            id_usuario = result[0] if result else None
            
            # Crear el registro en la tabla cliente
            if id_usuario:
                run_query(
                    "INSERT INTO cliente (id_cliente, nombre, email) VALUES (:ic, :n, :e)",
                    {
                        "ic": id_usuario,
                        "n": nombre,
                        "e": email
                    },
                    commit=True
                )

            flash("Usuario registrado exitosamente.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            flash(f"Error al registrar: {e}", "danger")
            return redirect(url_for("registro"))

    return render_template("registro.html")


# -----------------------------------------------
# LOGOUT
# -----------------------------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for('login'))


# -----------------------------------------------
# PÁGINA PRINCIPAL DEL PANEL
# -----------------------------------------------
@app.route('/inicio')
def inicio():
    return render_template('inicio.html')

# -----------------------------------------------
# PÁGINA PRINCIPAL DEL PANEL (cliente)
# -----------------------------------------------
@app.route('/cliente_inicio')
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
    
    # Contar pedidos del cliente
    pedidos_count = run_query(
        "SELECT COUNT(*) FROM pedido WHERE id_cliente = :ic",
        {"ic": id_cliente},
        fetchone=True
    )[0]
    
    # Calcular nivel de descuento (tiers: 0-2=0%, 3-5=5%, 6-9=10%, 10+=15%)
    if pedidos_count >= 10:
        nivel = "Diamante"
        descuento_porcentaje = 15
        icono = "💎"
    elif pedidos_count >= 6:
        nivel = "Oro"
        descuento_porcentaje = 10
        icono = "🏆"
    elif pedidos_count >= 3:
        nivel = "Plata"
        descuento_porcentaje = 5
        icono = "⭐"
    else:
        nivel = "Bronce"
        descuento_porcentaje = 0
        icono = "🎯"
    
    # Calcular próximo nivel
    if pedidos_count < 3:
        siguiente_nivel = "Plata"
        pedidos_faltantes = 3 - pedidos_count
    elif pedidos_count < 6:
        siguiente_nivel = "Oro"
        pedidos_faltantes = 6 - pedidos_count
    elif pedidos_count < 10:
        siguiente_nivel = "Diamante"
        pedidos_faltantes = 10 - pedidos_count
    else:
        siguiente_nivel = None
        pedidos_faltantes = 0
    
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
@app.route('/cliente_recibos')
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
@app.route('/cliente_promociones')
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
    
    # Contar pedidos del cliente
    pedidos_count = run_query(
        "SELECT COUNT(*) FROM pedido WHERE id_cliente = :id",
        {"id": id_usuario},
        fetchone=True
    )[0] or 0
    
    # Calcular nivel de cliente y descuento (requisitos reducidos)
    nivel = 'Bronce'
    descuento_base = 0
    icono = '🥉'
    progreso = 0
    siguiente_nivel = 'Plata'
    pedidos_faltantes = 3
    
    if pedidos_count >= 10:
        nivel = 'Diamante'
        descuento_base = 15
        icono = '💎'
        progreso = 100
        siguiente_nivel = 'Máximo nivel alcanzado'
        pedidos_faltantes = 0
    elif pedidos_count >= 6:
        nivel = 'Oro'
        descuento_base = 10
        icono = '🥇'
        progreso = ((pedidos_count - 6) / 4) * 100
        siguiente_nivel = 'Diamante'
        pedidos_faltantes = 10 - pedidos_count
    elif pedidos_count >= 3:
        nivel = 'Plata'
        descuento_base = 5
        icono = '🥈'
        progreso = ((pedidos_count - 3) / 3) * 100
        siguiente_nivel = 'Oro'
        pedidos_faltantes = 6 - pedidos_count
    else:
        progreso = (pedidos_count / 3) * 100
        pedidos_faltantes = 3 - pedidos_count
    
    # Promociones generales activas
    promociones = run_query("""
        SELECT id_promocion, descripcion, descuento, fecha_inicio, fecha_fin
        FROM promocion
        WHERE fecha_fin >= CURRENT_DATE
        ORDER BY fecha_inicio DESC
    """, fetchall=True)
    
    return render_template('cliente_promociones.html', 
                         promociones=promociones,
                         pedidos_count=pedidos_count,
                         nivel=nivel,
                         descuento_base=descuento_base,
                         icono=icono,
                         progreso=progreso,
                         siguiente_nivel=siguiente_nivel,
                         pedidos_faltantes=pedidos_faltantes)


# -----------------------------------------------
# PEDIDOS DEL cliente
# -----------------------------------------------
@app.route('/cliente_pedidos')
def cliente_pedidos():
    """Ver pedidos del cliente actual con paginación."""
    # Usar username desde la sesión (más seguro)
    username = session.get('username')
    if not username:
        flash("No se pudo identificar al usuario.", "danger")
        return redirect(url_for('login'))
    
    # Obtener id_usuario (case-insensitive)
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
        {"u": username.lower()},
        fetchone=True
    )
    
    if not usuario:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('login'))
    
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


# -----------------------------------------------
# LISTAR PEDIDOS (Administrador)
# -----------------------------------------------
@app.route('/pedidos')
def pedidos():
    """Mostrar todos los pedidos con búsqueda y filtrado (para administrador)."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    # Obtener parámetros de filtrado
    cliente_filter = request.args.get('cliente', '').strip()
    estado_filter = request.args.get('estado', '').strip()
    fecha_desde = request.args.get('desde', '').strip()
    fecha_hasta = request.args.get('hasta', '').strip()
    
    # Construir query base
    query = """
        SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre, p.codigo_barras
        FROM pedido p
        LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE 1=1
    """
    params = {}
    
    # Agregar filtros dinámicamente
    if cliente_filter:
        query += " AND (LOWER(c.nombre) LIKE LOWER(:cliente) OR c.id_cliente = :cliente_id)"
        params['cliente'] = f"%{cliente_filter}%"
        try:
            params['cliente_id'] = int(cliente_filter)
        except:
            params['cliente_id'] = -1
    
    if estado_filter:
        query += " AND p.estado = :estado"
        params['estado'] = estado_filter
    
    if fecha_desde:
        query += " AND DATE(p.fecha_ingreso) >= :desde"
        params['desde'] = fecha_desde
    
    if fecha_hasta:
        query += " AND DATE(p.fecha_ingreso) <= :hasta"
        params['hasta'] = fecha_hasta
    
    query += " ORDER BY p.id_pedido ASC"
    
    pedidos = run_query(query, params, fetchall=True)
    
    # Obtener opciones de estado únicas
    estados = run_query("""
        SELECT DISTINCT estado FROM pedido ORDER BY estado
    """, fetchall=True)
    estados = [e[0] for e in estados] if estados else []
    
    return render_template('pedidos.html', 
                         pedidos=pedidos,
                         cliente_filter=cliente_filter,
                         estado_filter=estado_filter,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta,
                         estados=estados)


# -----------------------------------------------
# LISTAR CLIENTES
# -----------------------------------------------
@app.route('/clientes', methods=['GET', 'POST'])
def clientes():
    """
    Mostrar todos los clientes basados en la tabla usuario (rol='cliente').
    """
    if request.method == 'POST':
        q = request.form.get('q', '').strip()
        data = run_query(
            "SELECT id_usuario, nombre, username, email FROM usuario WHERE rol = 'cliente' AND (nombre LIKE :q OR email LIKE :q OR username LIKE :q)",
            {"q": f"%{q}%"},
            fetchall=True
        )
    else:
        data = run_query(
            "SELECT id_usuario, nombre, username, email FROM usuario WHERE rol = 'cliente' ORDER BY id_usuario DESC",
            fetchall=True
        )
    return render_template('clientes.html', clients=data)


# -----------------------------------------------
# AGREGAR CLIENTE
# -----------------------------------------------
@app.route('/agregar_cliente', methods=['GET', 'POST'])
def agregar_cliente():
    """Agregar un nuevo cliente con validación."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip()
        telefono = request.form.get('telefono', '').strip()
        direccion = request.form.get('direccion', '').strip()
        
        # Validación
        errores = []
        
        if not nombre or len(nombre) < 3:
            errores.append("El nombre debe tener al menos 3 caracteres.")
        
        if not email or '@' not in email or len(email) < 5:
            errores.append("Por favor ingresa un email válido.")
        
        if not telefono or len(telefono) < 7:
            errores.append("El teléfono debe tener al menos 7 dígitos.")
        
        if not direccion or len(direccion) < 5:
            errores.append("La dirección debe tener al menos 5 caracteres.")
        
        if errores:
            for error in errores:
                flash(error, 'warning')
            return redirect(url_for('agregar_cliente'))
        
        try:
            run_query(
                "INSERT INTO cliente (nombre, email, telefono, direccion) VALUES (:n, :e, :t, :d)",
                {"n": nombre, "e": email, "t": telefono, "d": direccion},
                commit=True
            )
            flash('✅ Cliente agregado correctamente.', 'success')
            return redirect(url_for('clientes'))
        except Exception as e:
            flash(f'❌ Error al agregar cliente: {str(e)}', 'danger')
    
    return render_template('agregar_cliente.html')


# -----------------------------------------------
# ACTUALIZAR CLIENTE
# -----------------------------------------------
@app.route('/actualizar_cliente/<int:id_cliente>', methods=['GET', 'POST'])
def actualizar_cliente(id_cliente):
    """Actualizar datos de un cliente."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    cliente = run_query(
        "SELECT id_cliente, nombre, email, telefono, direccion FROM cliente WHERE id_cliente = :id",
        {"id": id_cliente},
        fetchone=True
    )
    
    if not cliente:
        flash('Cliente no encontrado.', 'danger')
        return redirect(url_for('clientes'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')
        
        try:
            run_query(
                "UPDATE cliente SET nombre = :n, email = :e, telefono = :t, direccion = :d WHERE id_cliente = :id",
                {"n": nombre, "e": email, "t": telefono, "d": direccion, "id": id_cliente},
                commit=True
            )
            flash('Cliente actualizado correctamente.', 'success')
            return redirect(_get_safe_redirect())
        except Exception as e:
            flash(f'Error al actualizar cliente: {e}', 'danger')
    
    return render_template('actualizar_cliente.html', cliente=cliente, id_cliente=id_cliente)


# -----------------------------------------------
# ELIMINAR CLIENTE
# -----------------------------------------------
@app.route('/eliminar_cliente/<int:id_cliente>', methods=['POST'])
def eliminar_cliente(id_cliente):
    """Eliminar un cliente."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    try:
        run_query(
            "DELETE FROM cliente WHERE id_cliente = :id",
            {"id": id_cliente},
            commit=True
        )
        flash('Cliente eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar cliente: {e}', 'danger')
    
    return redirect(_get_safe_redirect())


# -----------------------------------------------
# REPORTES
# -----------------------------------------------
@app.route('/reportes')
def reportes():
    """Página de reportes avanzados para administrador."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    import json
    from datetime import datetime, timedelta
    
    # 1. CLIENTES NUEVOS (últimos 30 días)
    clientes_nuevos = run_query("""
        SELECT p.fecha_ingreso::date as fecha, COUNT(DISTINCT p.id_cliente) as cantidad
        FROM pedido p
        WHERE p.fecha_ingreso >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY p.fecha_ingreso::date
        ORDER BY fecha
    """, fetchall=True) or []
    
    # 2. PEDIDOS POR DÍA (últimos 30 días)
    pedidos_por_dia = run_query("""
        SELECT fecha_ingreso::date as fecha, COUNT(*) as cantidad
        FROM pedido
        WHERE fecha_ingreso >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY fecha_ingreso::date
        ORDER BY fecha
    """, fetchall=True) or []
    
    # 3. TIPOS DE PRENDAS Y SU CANTIDAD
    prendas_por_tipo = run_query("""
        SELECT tipo, COUNT(*) as cantidad
        FROM prenda
        GROUP BY tipo
        ORDER BY cantidad DESC
    """, fetchall=True) or []
    
    # 4. INGRESOS POR MES
    ingresos_por_mes = run_query("""
        SELECT DATE_TRUNC('month', fecha)::date as mes, SUM(monto) as total
        FROM recibo
        GROUP BY DATE_TRUNC('month', fecha)
        ORDER BY mes DESC
        LIMIT 12
    """, fetchall=True) or []
    
    # 5. ESTADO DE PEDIDOS
    estado_pedidos = run_query("""
        SELECT estado, COUNT(*) as cantidad
        FROM pedido
        GROUP BY estado
    """, fetchall=True) or []
    
    # 6. TOP 10 CLIENTES POR CANTIDAD DE PEDIDOS
    top_clientes = run_query("""
        SELECT c.nombre, COUNT(p.id_pedido) as cantidad_pedidos
        FROM cliente c
        LEFT JOIN pedido p ON c.id_cliente = p.id_cliente
        GROUP BY c.id_cliente, c.nombre
        ORDER BY cantidad_pedidos DESC
        LIMIT 10
    """, fetchall=True) or []
    
    # 7. ESTADÍSTICAS GENERALES
    total_clientes = run_query("SELECT COUNT(*) FROM cliente", fetchone=True)[0] or 0
    total_pedidos = run_query("SELECT COUNT(*) FROM pedido", fetchone=True)[0] or 0
    total_ingresos = run_query("SELECT COALESCE(SUM(monto), 0) FROM recibo", fetchone=True)[0] or 0
    total_prendas = run_query("SELECT COUNT(*) FROM prenda", fetchone=True)[0] or 0
    
    # 8. PROMEDIO DE PRENDAS POR PEDIDO
    promedio_prendas = run_query("""
        SELECT AVG(cantidad) as promedio
        FROM (
            SELECT COUNT(*) as cantidad
            FROM prenda
            GROUP BY id_pedido
        ) subq
    """, fetchone=True)[0] or 0
    
    # ====== NUEVAS MÉTRICAS ======
    
    # 9. ESTADO DE PEDIDOS CON CONTEO
    estado_pedidos_conteo = run_query("""
        SELECT estado, COUNT(*) as cantidad
        FROM pedido
        GROUP BY estado
    """, fetchall=True) or []
    
    # 10. TOP 5 PRENDAS MÁS SOLICITADAS
    prendas_top = run_query("""
        SELECT tipo, COUNT(*) as cantidad
        FROM prenda
        GROUP BY tipo
        ORDER BY cantidad DESC
        LIMIT 5
    """, fetchall=True) or []
    
    # 11. CLIENTES MÁS ACTIVOS CON ESTADÍSTICAS
    clientes_activos = run_query("""
        SELECT 
            c.id_cliente, 
            c.nombre,
            COUNT(DISTINCT CASE WHEN p.id_pedido IS NOT NULL THEN p.id_pedido END) as cantidad_pedidos,
            COUNT(pr.id_prenda) as total_prendas,
            COALESCE(SUM(
                CASE 
                    WHEN pr.tipo IS NULL THEN 0
                    WHEN pr.tipo = 'Camisa' THEN 5000
                    WHEN pr.tipo = 'Pantalón' THEN 6000
                    WHEN pr.tipo = 'Vestido' THEN 8000
                    WHEN pr.tipo = 'Chaqueta' THEN 10000
                    WHEN pr.tipo = 'Saco' THEN 7000
                    WHEN pr.tipo = 'Falda' THEN 5500
                    WHEN pr.tipo = 'Blusa' THEN 4500
                    WHEN pr.tipo = 'Abrigo' THEN 12000
                    WHEN pr.tipo = 'Suéter' THEN 6500
                    WHEN pr.tipo = 'Jeans' THEN 7000
                    WHEN pr.tipo = 'Corbata' THEN 3000
                    WHEN pr.tipo = 'Bufanda' THEN 3500
                    WHEN pr.tipo = 'Sábana' THEN 8000
                    WHEN pr.tipo = 'Edredón' THEN 15000
                    WHEN pr.tipo = 'Cortina' THEN 12000
                    ELSE 5000
                END
            ), 0)::numeric as gasto_total
        FROM cliente c
        LEFT JOIN pedido p ON c.id_cliente = p.id_cliente
        LEFT JOIN prenda pr ON p.id_pedido = pr.id_pedido
        GROUP BY c.id_cliente, c.nombre
        ORDER BY cantidad_pedidos DESC
        LIMIT 15
    """, fetchall=True) or []
    
    # 12. TASA DE COMPLETACIÓN
    completados = run_query("""
        SELECT COUNT(*) FROM pedido WHERE estado = 'Completado'
    """, fetchone=True)[0] or 0
    tasa_completacion = (completados / total_pedidos * 100) if total_pedidos > 0 else 0
    
    # 13. PROMEDIO DE GASTO POR CLIENTE
    promedio_gasto = run_query("""
        SELECT AVG(gasto)
        FROM (
            SELECT COALESCE(SUM(
                CASE 
                    WHEN pr.tipo IS NULL THEN 0
                    WHEN pr.tipo = 'Camisa' THEN 5000
                    WHEN pr.tipo = 'Pantalón' THEN 6000
                    WHEN pr.tipo = 'Vestido' THEN 8000
                    WHEN pr.tipo = 'Chaqueta' THEN 10000
                    WHEN pr.tipo = 'Saco' THEN 7000
                    WHEN pr.tipo = 'Falda' THEN 5500
                    WHEN pr.tipo = 'Blusa' THEN 4500
                    WHEN pr.tipo = 'Abrigo' THEN 12000
                    WHEN pr.tipo = 'Suéter' THEN 6500
                    WHEN pr.tipo = 'Jeans' THEN 7000
                    WHEN pr.tipo = 'Corbata' THEN 3000
                    WHEN pr.tipo = 'Bufanda' THEN 3500
                    WHEN pr.tipo = 'Sábana' THEN 8000
                    WHEN pr.tipo = 'Edredón' THEN 15000
                    WHEN pr.tipo = 'Cortina' THEN 12000
                    ELSE 5000
                END
            ), 0) as gasto
            FROM cliente c
            LEFT JOIN pedido p ON c.id_cliente = p.id_cliente
            LEFT JOIN prenda pr ON p.id_pedido = pr.id_pedido
            GROUP BY c.id_cliente
        ) subq
    """, fetchone=True)[0] or 0
    
    # 14. PEDIDOS PENDIENTES
    pedidos_pendientes = run_query("""
        SELECT COUNT(*) FROM pedido WHERE estado IN ('Pendiente', 'En proceso')
    """, fetchone=True)[0] or 0
    
    # 15. PROMEDIO DE DÍAS PARA COMPLETAR PEDIDO
    promedio_dias = run_query("""
        SELECT AVG((fecha_entrega - fecha_ingreso)::integer)
        FROM pedido
        WHERE estado = 'Completado' AND fecha_entrega IS NOT NULL
    """, fetchone=True)[0] or 0
    
    # Preparar datos para gráficos (formato JSON)
    graficos = {
        'clientes_nuevos': {
            'labels': [str(row[0]) for row in clientes_nuevos],
            'data': [row[1] for row in clientes_nuevos]
        },
        'pedidos_dia': {
            'labels': [str(row[0]) for row in pedidos_por_dia],
            'data': [row[1] for row in pedidos_por_dia]
        },
        'prendas_tipo': {
            'labels': [row[0] for row in prendas_por_tipo],
            'data': [row[1] for row in prendas_por_tipo]
        },
        'estado_pedidos': {
            'labels': [row[0] for row in estado_pedidos],
            'data': [row[1] for row in estado_pedidos]
        },
        'top_clientes': {
            'labels': [row[0] for row in top_clientes],
            'data': [row[1] for row in top_clientes]
        },
        'ingresos_mes': {
            'labels': [str(row[0]) if row[0] else 'N/A' for row in ingresos_por_mes],
            'data': [float(row[1]) if row[1] else 0 for row in ingresos_por_mes]
        }
    }
    
    return render_template('reportes.html',
                         graficos=json.dumps(graficos),
                         total_clientes=total_clientes,
                         total_pedidos=total_pedidos,
                         total_ingresos=float(total_ingresos),
                         total_prendas=total_prendas,
                         promedio_prendas=round(float(promedio_prendas), 2),
                         estado_pedidos=estado_pedidos_conteo,
                         prendas_top=prendas_top,
                         clientes_activos=clientes_activos,
                         tasa_completacion=round(tasa_completacion, 2),
                         promedio_gasto=round(float(promedio_gasto), 0),
                         pedidos_pendientes=pedidos_pendientes,
                         promedio_dias=round(float(promedio_dias), 1))


# -----------------------------------------------
# LECTOR DE CÓDIGOS DE BARRAS
# -----------------------------------------------
@app.route('/lector_barcode', methods=['GET', 'POST'])
def lector_barcode():
    """Escanear código de barras y mostrar detalles del pedido."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Verificar si se subió una imagen
        if 'barcode_image' not in request.files:
            return {'success': False, 'error': 'No se subió ninguna imagen'}, 400
        
        file = request.files['barcode_image']
        if file.filename == '':
            return {'success': False, 'error': 'No se seleccionó ningún archivo'}, 400
        
        try:
            # Leer imagen
            image_bytes = file.read()
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convertir a PIL Image para pyzbar
            img_pil = PILImage.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            # Decodificar código de barras
            decoded_objects = decode(img_pil)
            
            if not decoded_objects:
                return {'success': False, 'error': 'No se detectó ningún código de barras en la imagen'}, 400
            
            # Obtener el primer código detectado
            barcode_data = decoded_objects[0].data.decode('utf-8')
            
            # Buscar pedido por código de barras
            pedido = run_query("""
                SELECT p.id_pedido, p.id_cliente, p.fecha_ingreso, p.fecha_entrega, 
                       p.estado, p.instrucciones, c.nombre, c.telefono, c.direccion,
                       u.email
                FROM pedido p
                JOIN cliente c ON p.id_cliente = c.id_cliente
                LEFT JOIN usuario u ON c.id_cliente = u.id_usuario
                WHERE p.codigo_barras = :codigo
            """, {"codigo": barcode_data}, fetchone=True)
            
            if not pedido:
                return {'success': False, 'error': f'No se encontró ningún pedido con el código: {barcode_data}'}, 404
            
            # Obtener prendas del pedido
            prendas = run_query("""
                SELECT tipo, estado
                FROM prenda
                WHERE id_pedido = :id
            """, {"id": pedido[0]}, fetchall=True)
            
            # Obtener recibo del pedido
            recibo = run_query("""
                SELECT monto, descuento, fecha
                FROM recibo
                WHERE id_pedido = :id
            """, {"id": pedido[0]}, fetchone=True)
            
            # Preparar respuesta
            response_data = {
                'success': True,
                'codigo_barras': barcode_data,
                'pedido': {
                    'id': pedido[0],
                    'fecha_ingreso': pedido[2].strftime('%d/%m/%Y %H:%M') if pedido[2] else 'N/A',
                    'fecha_entrega': pedido[3].strftime('%d/%m/%Y') if pedido[3] else 'Pendiente',
                    'estado': pedido[4],
                    'instrucciones': pedido[5] or 'Sin instrucciones',
                },
                'cliente': {
                    'id': pedido[1],
                    'nombre': pedido[6],
                    'telefono': pedido[7] or 'No registrado',
                    'direccion': pedido[8] or 'No registrada',
                    'email': pedido[9] or 'No registrado'
                },
                'prendas': [{'tipo': p[0], 'estado': p[1]} for p in prendas] if prendas else [],
                'recibo': {
                    'monto': float(recibo[0]) if recibo and recibo[0] else 0,
                    'descuento': float(recibo[1]) if recibo and recibo[1] else 0,
                    'fecha': recibo[2].strftime('%d/%m/%Y') if recibo and recibo[2] else 'N/A'
                } if recibo else None
            }
            
            return response_data, 200
            
        except Exception as e:
            return {'success': False, 'error': f'Error al procesar la imagen: {str(e)}'}, 500
    
    # GET request - mostrar página
    return render_template('lector_barcode.html')


# -----------------------------------------------
# AGREGAR PEDIDO
# -----------------------------------------------
@app.route('/agregar_pedido', methods=['GET', 'POST'])
def agregar_pedido():
    """Crear un nuevo pedido (clientes y administradores)."""
    username = session.get('username')
    if not username:
        flash('Debes iniciar sesión para crear pedidos.', 'danger')
        return redirect(url_for('login'))
    
    # Obtener rol del usuario
    usuario = run_query(
        "SELECT rol FROM usuario WHERE LOWER(username) = :u",
        {"u": username.lower()},
        fetchone=True
    )
    rol = usuario[0].strip().lower() if usuario else 'cliente'
    
    # Prendas predefinidas con precios estimados
    prendas_default = [
        {'nombre': 'Camisa', 'precio': 5000},
        {'nombre': 'Pantalón', 'precio': 6000},
        {'nombre': 'Vestido', 'precio': 8000},
        {'nombre': 'Chaqueta', 'precio': 10000},
        {'nombre': 'Saco', 'precio': 7000},
        {'nombre': 'Falda', 'precio': 5500},
        {'nombre': 'Blusa', 'precio': 4500},
        {'nombre': 'Abrigo', 'precio': 12000},
        {'nombre': 'Suéter', 'precio': 6500},
        {'nombre': 'Jeans', 'precio': 7000},
        {'nombre': 'Corbata', 'precio': 3000},
        {'nombre': 'Bufanda', 'precio': 3500},
        {'nombre': 'Sábana', 'precio': 8000},
        {'nombre': 'Edredón', 'precio': 15000},
        {'nombre': 'Cortina', 'precio': 12000}
    ]
    
    if request.method == 'POST':
        try:
            from datetime import datetime, timedelta
            
            # 1. Determinar id_cliente
            if rol == 'administrador':
                id_cliente = request.form.get('id_cliente')
            else:
                usuario_data = run_query(
                    "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
                    {"u": username.lower()},
                    fetchone=True
                )
                id_cliente = usuario_data[0] if usuario_data else None
            
            if not id_cliente:
                flash('Error al identificar el cliente.', 'danger')
                return redirect(url_for('agregar_pedido'))
            
            # 2. Asegurar que existe en tabla cliente
            ensure_cliente_exists(id_cliente)
            
            # 3. Obtener prendas
            tipos = request.form.getlist('tipo[]')
            cantidades = request.form.getlist('cantidad[]')
            descripciones = request.form.getlist('descripcion[]')
            
            # Debug: verificar que las listas tengan el mismo tamaño
            print(f"DEBUG: tipos={len(tipos)}, cantidades={len(cantidades)}, descripciones={len(descripciones)}")
            print(f"DEBUG: cantidades={cantidades}")
            print(f"DEBUG: descripciones={descripciones}")
            
            if not tipos or len(tipos) == 0:
                flash('Debes agregar al menos una prenda.', 'warning')
                return redirect(url_for('agregar_pedido'))
            
            # 4. Calcular fechas
            total_prendas = sum(int(c) for c in cantidades if c)
            dias_entrega = 3 if total_prendas <= 5 else (5 if total_prendas <= 15 else 7)
            fecha_ingreso = datetime.now().strftime('%Y-%m-%d')
            fecha_entrega = (datetime.now() + timedelta(days=dias_entrega)).strftime('%Y-%m-%d')
            
            # 5. Crear pedido con código de barras
            result = run_query(
                "INSERT INTO pedido (fecha_ingreso, fecha_entrega, estado, id_cliente) VALUES (:fi, :fe, :e, :ic) RETURNING id_pedido",
                {"fi": fecha_ingreso, "fe": fecha_entrega, "e": "Pendiente", "ic": id_cliente},
                commit=True,
                fetchone=True
            )
            
            if not result or len(result) == 0:
                flash('Error al crear el pedido.', 'danger')
                return redirect(url_for('agregar_pedido'))
            
            id_pedido = result[0]
            
            # 5.1. Generar código de barras único (formato: LAV-YYYYMMDD-000001)
            codigo_barras = f"LAV-{datetime.now().strftime('%Y%m%d')}-{id_pedido:06d}"
            
            # 5.2. Actualizar pedido con código de barras
            run_query(
                "UPDATE pedido SET codigo_barras = :cb WHERE id_pedido = :id",
                {"cb": codigo_barras, "id": id_pedido},
                commit=True
            )
            
            # 6. Procesar y calcular costo primero
            prendas_a_insertar = []
            total_costo = 0
            
            for i in range(len(tipos)):
                tipo = tipos[i]
                if not tipo or tipo.strip() == '':
                    continue
                
                # Procesar cantidad con validación robusta
                cantidad_str = cantidades[i] if i < len(cantidades) else '0'
                try:
                    cantidad = int(cantidad_str) if cantidad_str and cantidad_str.strip() else 0
                    # Si la cantidad es 0 o negativa, saltar esta prenda
                    if cantidad <= 0:
                        continue
                except (ValueError, AttributeError):
                    continue
                
                descripcion = descripciones[i] if i < len(descripciones) else ''
                
                # Buscar precio
                precio = 5000  # default
                for prenda_def in prendas_default:
                    if prenda_def['nombre'] == tipo:
                        precio = prenda_def['precio']
                        break
                
                prendas_a_insertar.append({
                    'tipo': tipo,
                    'cantidad': cantidad,
                    'descripcion': descripcion,
                    'precio': precio
                })
                
                total_costo += precio * cantidad
            
            # Validar que haya al menos una prenda
            if not prendas_a_insertar or total_costo == 0:
                flash('Debes agregar al menos una prenda con cantidad mayor a 0.', 'warning')
                return redirect(url_for('agregar_pedido'))
            
            # 7. Insertar prendas en la base de datos
            prendas_insertadas = 0
            
            for prenda in prendas_a_insertar:
                tipo = prenda['tipo']
                cantidad = prenda['cantidad']
                descripcion = prenda['descripcion']
                
                for unidad in range(cantidad):
                    run_query(
                        "INSERT INTO prenda (tipo, descripcion, observaciones, id_pedido) VALUES (:tipo, :desc, :obs, :id_ped)",
                        {"tipo": tipo, "desc": descripcion, "obs": '', "id_ped": id_pedido},
                        commit=True
                    )
                    prendas_insertadas += 1
            
            # 8. Calcular descuento según la cantidad de pedidos del cliente (ciclo cada 10 pedidos)
            
            pedidos_count = run_query(
                "SELECT COUNT(*) FROM pedido WHERE id_cliente = :id",
                {"id": id_cliente},
                fetchone=True
            )[0] or 0
            
            # Determinar nivel y descuento (ciclo cada 10 pedidos)
            pedidos_en_ciclo = pedidos_count % 10  # Resetea cada 10 pedidos
            descuento_porcentaje = 0
            nivel_descuento = "Sin nivel"
            
            if pedidos_en_ciclo == 0 and pedidos_count > 0:
                # El pedido 10, 20, 30, etc. tiene 15%
                descuento_porcentaje = 15
                nivel_descuento = "Oro"
            elif pedidos_en_ciclo >= 6 or (pedidos_en_ciclo == 0 and pedidos_count == 0):
                descuento_porcentaje = 10
                nivel_descuento = "Plata"
            elif pedidos_en_ciclo >= 3:
                descuento_porcentaje = 5
                nivel_descuento = "Bronce"
            else:
                descuento_porcentaje = 0
                nivel_descuento = "Sin nivel"
            
            # Calcular monto con descuento
            monto_descuento = (total_costo * descuento_porcentaje) / 100
            monto_final = total_costo - monto_descuento
            
            # 9. Crear recibo con descuento
            run_query(
                """INSERT INTO recibo (id_pedido, id_cliente, monto, fecha) 
                   VALUES (:ip, :ic, :m, CURRENT_TIMESTAMP)""",
                {"ip": id_pedido, "ic": id_cliente, "m": monto_final},
                commit=True
            )
            
            # 10. Obtener datos del cliente para el flash
            cliente_data = run_query(
                "SELECT nombre FROM cliente WHERE id_cliente = :id",
                {"id": id_cliente},
                fetchone=True
            )
            
            # Mensaje con descuento aplicado y código de barras
            if descuento_porcentaje > 0:
                msg_descuento = f" | Nivel {nivel_descuento}: Descuento {descuento_porcentaje}% (-${monto_descuento:,.0f})"
            else:
                msg_descuento = ""
            
            flash(f'¡Pedido #{id_pedido} creado! Código: {codigo_barras} | {prendas_insertadas} prendas. Subtotal: ${total_costo:,.0f}{msg_descuento}. Total: ${monto_final:,.0f}. Entrega: {fecha_entrega}', 'success')
            
            # Redirigir según el rol
            if rol == 'administrador':
                return redirect(url_for('pedidos'))
            else:
                return redirect(url_for('cliente_pedidos'))
                
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('agregar_pedido'))
    
    clientes = run_query(
        "SELECT id_usuario, nombre FROM usuario WHERE rol = 'cliente' ORDER BY nombre",
        fetchall=True
    )
    
    # Obtener información de descuento del cliente actual si no es admin
    descuento_info = None
    if rol != 'administrador':
        usuario_data = run_query(
            "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
            {"u": username.lower()},
            fetchone=True
        )
        if usuario_data:
            id_cliente = usuario_data[0]
            pedidos_count = run_query(
                "SELECT COUNT(*) FROM pedido WHERE id_cliente = :id",
                {"id": id_cliente},
                fetchone=True
            )[0] or 0
            
            pedidos_en_ciclo = pedidos_count % 10
            if pedidos_en_ciclo == 0 and pedidos_count > 0:
                descuento_info = {"nivel": "Oro", "porcentaje": 15, "pedidos": pedidos_count}
            elif pedidos_en_ciclo >= 6:
                descuento_info = {"nivel": "Plata", "porcentaje": 10, "pedidos": pedidos_count}
            elif pedidos_en_ciclo >= 3:
                descuento_info = {"nivel": "Bronce", "porcentaje": 5, "pedidos": pedidos_count}
            else:
                descuento_info = {"nivel": "Sin nivel", "porcentaje": 0, "pedidos": pedidos_count}
    
    return render_template('agregar_pedido.html', 
                         clientes=clientes, 
                         rol=rol,
                         prendas_default=prendas_default,
                         descuento_info=descuento_info)


# -----------------------------------------------
# DETALLES DE PEDIDO
# -----------------------------------------------
@app.route('/pedido_detalles/<int:id_pedido>')
def pedido_detalles(id_pedido):
    """Ver detalles de un pedido."""
    pedido = run_query(
        "SELECT id_pedido, fecha_ingreso, fecha_entrega, estado, id_cliente, codigo_barras FROM pedido WHERE id_pedido = :id",
        {"id": id_pedido},
        fetchone=True
    )
    
    if not pedido:
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('pedidos'))
    
    prendas = run_query(
        "SELECT id_prenda, tipo, descripcion, observaciones FROM prenda WHERE id_pedido = :id",
        {"id": id_pedido},
        fetchall=True
    )
    
    return render_template('pedido_detalles.html', pedido=pedido, prendas=prendas)


# -----------------------------------------------
# ACTUALIZAR PEDIDO
# -----------------------------------------------
@app.route('/actualizar_pedido/<int:id_pedido>', methods=['POST'])
def actualizar_pedido(id_pedido):
    """Actualizar estado de un pedido."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    estado = request.form.get('estado')
    
    try:
        run_query(
            "UPDATE pedido SET estado = :e WHERE id_pedido = :id",
            {"e": estado, "id": id_pedido},
            commit=True
        )
        flash('Pedido actualizado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al actualizar: {e}', 'danger')
    
    return redirect(url_for('pedido_detalles', id_pedido=id_pedido))


# -----------------------------------------------
# ELIMINAR PEDIDO
# -----------------------------------------------
@app.route('/eliminar_pedido/<int:id_pedido>', methods=['POST'])
def eliminar_pedido(id_pedido):
    """Eliminar un pedido y sus datos asociados (recibos y prendas)."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
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
    
    return redirect(_get_safe_redirect())


# -----------------------------------------------
# VER PRENDAS DEL PEDIDO (CLIENTE Y ADMIN)
# -----------------------------------------------
@app.route('/pedido/<int:id_pedido>/prendas')
def ver_prendas_pedido(id_pedido):
    """Ver las prendas detalladas de un pedido (para cliente y admin)."""
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
    
    return render_template('pedido_prendas.html',
                         pedido=pedido,
                         prendas=prendas,
                         precio_dict=precio_dict,
                         total_costo=total_costo,
                         rol=rol)


# -----------------------------------------------
# API: OBTENER PRENDAS DE UN PEDIDO (JSON)
# -----------------------------------------------
@app.route('/api/prendas_pedido/<int:id_pedido>')
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
# FUNCIONES AUXILIARES (ej. _admin_only)
# -----------------------------------------------
def _admin_only():
    rol = session.get('rol')
    if not rol:
        return False
    return str(rol).strip().lower() == 'administrador'

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


@app.route('/barcode/<codigo>')
def generar_barcode(codigo):
    """Genera una imagen de código de barras en formato Code128."""
    try:
        # Crear el código de barras Code128
        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(codigo, writer=ImageWriter())
        
        # Generar la imagen en memoria
        buffer = BytesIO()
        barcode_instance.write(buffer, options={
            'module_width': 0.3,
            'module_height': 10.0,
            'quiet_zone': 2.0,
            'font_size': 10,
            'text_distance': 3.0,
            'write_text': True
        })
        buffer.seek(0)
        
        # Retornar la imagen
        return Response(buffer.getvalue(), mimetype='image/png')
    except Exception as e:
        print(f"Error generando código de barras: {e}")
        return "Error generando código de barras", 500


@app.route('/descargar_barcode/<codigo>')
def descargar_barcode(codigo):
    """Descarga la imagen del código de barras."""
    try:
        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(codigo, writer=ImageWriter())
        
        buffer = BytesIO()
        barcode_instance.write(buffer, options={
            'module_width': 0.3,
            'module_height': 10.0,
            'quiet_zone': 2.0,
            'font_size': 10,
            'text_distance': 3.0,
            'write_text': True
        })
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'barcode_{codigo}.png'
        )
    except Exception as e:
        print(f"Error descargando código de barras: {e}")
        return "Error", 500


@app.route('/descargar_recibo_pdf/<int:id_pedido>')
def descargar_recibo_pdf(id_pedido):
    """Genera y descarga el recibo en formato PDF."""
    try:
        # Obtener datos del pedido
        pedido = run_query("""
            SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre, p.codigo_barras, u.email
            FROM pedido p
            LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
            LEFT JOIN usuario u ON c.id_cliente = u.id_usuario
            WHERE p.id_pedido = :id
        """, {"id": id_pedido}, fetchone=True)
        
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
        
        # Calcular descuento aplicado
        subtotal = sum(p[2] for p in prendas)
        descuento_monto = 0
        descuento_porcentaje = 0
        nivel_descuento = "Sin nivel"
        
        if recibo and subtotal > 0:
            descuento_monto = subtotal - recibo[0]
            if descuento_monto > 0:
                descuento_porcentaje = int((descuento_monto / subtotal) * 100)
                
                # Determinar nivel según porcentaje
                if descuento_porcentaje >= 15:
                    nivel_descuento = "Oro (10+ pedidos en ciclo)"
                elif descuento_porcentaje >= 10:
                    nivel_descuento = "Plata (6-9 pedidos en ciclo)"
                elif descuento_porcentaje >= 5:
                    nivel_descuento = "Bronce (3-5 pedidos en ciclo)"
        
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
# MAIN
# -----------------------------------------------
if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=8080)
