from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, Response, jsonify
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
import secrets
import re
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

# Cargar variables de entorno desde .env (si existe)
load_dotenv()

# Configuración de la app
app = Flask(__name__)

# Secret key segura
secret_key = os.getenv('SECRET_KEY')
if not secret_key or len(secret_key) < 16:
    secret_key = secrets.token_hex(32)
    print("[WARN] Usando SECRET_KEY generada automáticamente")
app.secret_key = secret_key

# Configuración de sesión segura
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=2)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB máximo

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
# FUNCIÓN PARA ENVÍO DE CORREOS (ASÍNCRONO)
# -----------------------------------------------
def send_email_async(destinatario, asunto, cuerpo_html):
    """Envía un correo de forma asíncrona para no bloquear la aplicación."""
    def _send():
        try:
            # Configuración SMTP
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', 587))
            smtp_user = os.getenv('SMTP_USER', 'lalavanderiabogota@gmail.com')
            smtp_password = os.getenv('SMTP_PASSWORD', '')
            
            if not smtp_password:
                print("[WARN] SMTP_PASSWORD no configurado en las variables de entorno")
                print("[WARN] Para habilitar correos, configura SMTP_PASSWORD en Render:")
                print("[WARN] Dashboard > Environment > Add Variable > SMTP_PASSWORD")
                return
            
            if not destinatario or '@' not in destinatario:
                print(f"[WARN] Email destinatario invalido: {destinatario}")
                return
            
            # Crear mensaje
            mensaje = MIMEMultipart('alternative')
            mensaje['From'] = f"La Lavandería <{smtp_user}>"
            mensaje['To'] = destinatario
            mensaje['Subject'] = asunto
            
            # Adjuntar HTML
            parte_html = MIMEText(cuerpo_html, 'html')
            mensaje.attach(parte_html)
            
            # Enviar
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(mensaje)
            
            print(f"[OK] Correo enviado a {destinatario}: {asunto}")
        except smtplib.SMTPAuthenticationError as e:
            print(f"[ERROR] Autenticacion SMTP: {e}")
            print("[ERROR] Verifica SMTP_USER y SMTP_PASSWORD en Render")
        except Exception as e:
            print(f"[ERROR] Enviando correo a {destinatario}: {e}")
    
    # Ejecutar en thread separado
    thread = threading.Thread(target=_send)
    thread.daemon = False
    thread.start()


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
# FUNCIONES DE SEGURIDAD BÁSICAS
# -----------------------------------------------
def limpiar_texto(texto, max_length=500):
    """Limpiar entrada de texto para prevenir XSS"""
    if not texto:
        return ""
    # Eliminar caracteres peligrosos
    texto = str(texto).strip()
    # Eliminar etiquetas HTML básicas
    texto = re.sub(r'<[^>]+>', '', texto)
    # Limitar longitud
    return texto[:max_length]

def validar_email(email):
    """Validar formato de email"""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(patron, email))

def validar_contrasena(password):
    """Validar que la contraseña sea fuerte"""
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres"
    if not re.search(r'[A-Za-z]', password):
        return False, "La contraseña debe contener letras"
    if not re.search(r'\d', password):
        return False, "La contraseña debe contener números"
    return True, ""

def login_requerido(f):
    """Decorador para rutas que necesitan autenticación"""
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'id_usuario' not in session:
            flash('Debes iniciar sesión', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorador

def admin_requerido(f):
    """Decorador para rutas de administrador"""
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'id_usuario' not in session:
            flash('Debes iniciar sesión', 'warning')
            return redirect(url_for('login'))
        rol = str(session.get('rol', '')).strip().lower()
        if rol != 'administrador':
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('cliente_inicio'))
        return f(*args, **kwargs)
    return decorador


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
        username = limpiar_texto(request.form.get('username', '').strip().lower(), 100)
        password = request.form.get('password', '').strip()
        
        # Validaciones básicas
        if not username or not password:
            flash('Usuario y contraseña son obligatorios', 'danger')
            return render_template('login.html')
        
        if len(password) > 200:
            flash('Datos inválidos', 'danger')
            return render_template('login.html')
        
        user = run_query(
            "SELECT id_usuario, username, password, rol FROM usuario WHERE LOWER(username) = :u",
            {"u": username},
            fetchone=True
        )
 
        try:
            password_ok = bool(user) and check_password_hash(user[2], password)
        except (ValueError, TypeError):
            flash("Error de autenticación", "danger")
            return redirect(url_for('login'))

        if password_ok:
            # Limpiar sesión anterior y crear nueva
            session.clear()
            session['id_usuario'] = user[0]
            session['username'] = user[1]
            session['rol'] = str(user[3]).strip().lower()  # Normalizar rol
            session['nombre'] = user[1]  # Guardar nombre también
            session.permanent = True
            
            flash(f"Bienvenido {username}", "success")

            # Redirigir según rol
            if session['rol'] == 'administrador':
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
    # Variables para mantener datos del formulario
    form_data = {
        'nombre': '',
        'username': '',
        'email': ''
    }
    
    if request.method == "POST":
        nombre = limpiar_texto(request.form.get("nombre", ""), 200)
        username = limpiar_texto(request.form.get("username", "").strip().lower(), 100)
        email = limpiar_texto(request.form.get("email", "").strip().lower(), 200)
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        
        # Guardar datos para repoblar el formulario en caso de error
        form_data['nombre'] = nombre
        form_data['username'] = username
        form_data['email'] = email

        # Validaciones básicas
        if not all([nombre, username, email, password]):
            flash("Todos los campos son obligatorios.", "warning")
            return render_template("registro.html", form_data=form_data)
        
        # Validar email
        if not validar_email(email):
            flash("El email no tiene un formato válido.", "danger")
            return render_template("registro.html", form_data=form_data)
        
        # Validar contraseña
        es_valida, mensaje = validar_contrasena(password)
        if not es_valida:
            flash(mensaje, "danger")
            return render_template("registro.html", form_data=form_data)

        # Verificar confirmación de contraseña
        if password != password2:
            flash("Las contraseñas no coinciden.", "warning")
            return render_template("registro.html", form_data=form_data)

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

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
                flash("Este correo ya está registrado.", "danger")
                return render_template("registro.html", form_data=form_data)
            if existing_user:
                flash("Este nombre de usuario ya existe. Por favor elige otro.", "danger")
                return render_template("registro.html", form_data=form_data)

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
                
                # Enviar correo de bienvenida (asíncrono)
                html_bienvenida = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #a6cc48 0%, #8fb933 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                            <h1 style="color: white; margin: 0;">¡Bienvenido a La Lavandería!</h1>
                        </div>
                        <div style="padding: 30px; background: #f9f9f9;">
                            <h2 style="color: #1a4e7b;">Hola {nombre},</h2>
                            <p style="font-size: 16px; line-height: 1.6;">
                                Gracias por registrarte en <strong>La Lavandería</strong>, tu servicio de lavandería a domicilio de confianza.
                            </p>
                            <div style="background: white; border-left: 4px solid #a6cc48; padding: 20px; margin: 20px 0; border-radius: 5px;">
                                <h3 style="color: #1a4e7b; margin-top: 0;">📋 Tu cuenta:</h3>
                                <p style="margin: 10px 0;"><strong>Usuario:</strong> {username}</p>
                                <p style="margin: 10px 0;"><strong>Email:</strong> {email}</p>
                            </div>
                            <div style="background: #e8f4f8; padding: 20px; margin: 20px 0; border-radius: 5px;">
                                <h3 style="color: #1a4e7b; margin-top: 0;">🚀 ¿Qué puedes hacer ahora?</h3>
                                <ul style="line-height: 1.8;">
                                    <li>🏠 <strong>Crear pedidos a domicilio</strong> - Recogemos y entregamos en tu puerta</li>
                                    <li>💰 <strong>Obtener descuentos</strong> - Acumula pedidos para recibir beneficios</li>
                                    <li>📊 <strong>Ver historial</strong> - Consulta todos tus pedidos y recibos</li>
                                    <li>🎁 <strong>Promociones exclusivas</strong> - Ofertas especiales para clientes registrados</li>
                                </ul>
                            </div>
                            <div style="text-align: center; margin: 30px 0;">
                                <p style="color: #666;">¡Estamos listos para cuidar tu ropa!</p>
                            </div>
                        </div>
                        <div style="background: #1a4e7b; color: white; padding: 20px; text-align: center; border-radius: 0 0 10px 10px;">
                            <p style="margin: 0;">La Lavandería - Servicio a Domicilio</p>
                            <p style="margin: 5px 0; font-size: 14px;">lalavanderiabogota@gmail.com</p>
                        </div>
                    </body>
                </html>
                """
                send_email_async(email, "Bienvenido a La Lavanderia", html_bienvenida)

            flash("¡Registro exitoso! Ya puedes iniciar sesión.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            print(f"Error en registro: {e}")
            flash("Error al registrar. Por favor intenta de nuevo.", "danger")
            return render_template("registro.html", form_data=form_data)

    return render_template("registro.html", form_data=form_data)


# -----------------------------------------------
# LOGOUT
# -----------------------------------------------
@app.route('/logout')
@login_requerido
def logout():
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for('login'))


# -----------------------------------------------
# PÁGINA PRINCIPAL DEL PANEL (administrador)
# -----------------------------------------------
@app.route('/inicio')
@login_requerido
@admin_requerido
def inicio():
    return render_template('inicio.html')

# -----------------------------------------------
# PÁGINA PRINCIPAL DEL PANEL (cliente)
# -----------------------------------------------
@app.route('/cliente_inicio')
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
    
    # Obtener esquema de descuento del cliente (congelado o actual)
    esquema_cliente = _obtener_esquema_descuento_cliente(id_usuario)
    
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
@login_requerido
@admin_requerido
def pedidos():
    """Mostrar todos los pedidos con búsqueda, filtrado y paginación (para administrador)."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    # Obtener parámetros de filtrado y paginación
    cliente_filter = request.args.get('cliente', '').strip()
    estado_filter = request.args.get('estado', '').strip()
    fecha_desde = request.args.get('desde', '').strip()
    fecha_hasta = request.args.get('hasta', '').strip()
    orden = request.args.get('orden', 'desc').strip().lower()  # 'asc' o 'desc'
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
    if pagina > total_paginas:
        pagina = total_paginas
    
    # Agregar orden
    if orden == 'asc':
        query += " ORDER BY p.id_pedido ASC"
    else:
        query += " ORDER BY p.id_pedido DESC"
    
    # Agregar paginación
    offset = (pagina - 1) * por_pagina
    query += f" LIMIT {por_pagina} OFFSET {offset}"
    
    pedidos = run_query(query, params, fetchall=True)
    
    # Obtener opciones de estado únicas
    estados = run_query("""
        SELECT DISTINCT estado FROM pedido ORDER BY estado
    """, fetchall=True)
    estados = [e[0] for e in estados] if estados else []
    
    # Calcular rango de registros mostrados
    registro_desde = offset + 1 if total_count > 0 else 0
    registro_hasta = min(offset + por_pagina, total_count)
    
    return render_template('pedidos.html', 
                         pedidos=pedidos,
                         cliente_filter=cliente_filter,
                         estado_filter=estado_filter,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta,
                         estados=estados,
                         orden=orden,
                         pagina=pagina,
                         total_paginas=total_paginas,
                         total_count=total_count,
                         registro_desde=registro_desde,
                         registro_hasta=registro_hasta)


# -----------------------------------------------
# CALENDARIO DE PEDIDOS
# -----------------------------------------------
@app.route('/calendario-pedidos')
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
# LISTAR CLIENTES
# -----------------------------------------------
@app.route('/clientes', methods=['GET', 'POST'])
@login_requerido
@admin_requerido
def clientes():
    """
    Mostrar todos los clientes basados en la tabla usuario (rol='cliente') con paginación.
    """
    # Obtener parámetros de orden y paginación
    orden = request.args.get('orden', 'desc').strip().lower()  # 'asc' o 'desc'
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 10
    orden_sql = "ASC" if orden == 'asc' else "DESC"
    
    if request.method == 'POST':
        q = request.form.get('q', '').strip()
        
        # Contar total de resultados
        count_result = run_query(
            "SELECT COUNT(*) FROM usuario WHERE rol = 'cliente' AND (nombre LIKE :q OR email LIKE :q OR username LIKE :q)",
            {"q": f"%{q}%"},
            fetchall=True
        )
        total_count = count_result[0][0] if count_result else 0
        total_paginas = (total_count + por_pagina - 1) // por_pagina
        
        # Ajustar página si está fuera de rango
        if pagina < 1:
            pagina = 1
        if pagina > total_paginas and total_paginas > 0:
            pagina = total_paginas
        
        # Obtener datos con paginación
        offset = (pagina - 1) * por_pagina
        data = run_query(
            f"SELECT id_usuario, nombre, username, email FROM usuario WHERE rol = 'cliente' AND (nombre LIKE :q OR email LIKE :q OR username LIKE :q) ORDER BY id_usuario {orden_sql} LIMIT {por_pagina} OFFSET {offset}",
            {"q": f"%{q}%"},
            fetchall=True
        )
    else:
        # Contar total de clientes
        count_result = run_query(
            "SELECT COUNT(*) FROM usuario WHERE rol = 'cliente'",
            fetchall=True
        )
        total_count = count_result[0][0] if count_result else 0
        total_paginas = (total_count + por_pagina - 1) // por_pagina
        
        # Ajustar página si está fuera de rango
        if pagina < 1:
            pagina = 1
        if pagina > total_paginas and total_paginas > 0:
            pagina = total_paginas
        
        # Obtener datos con paginación
        offset = (pagina - 1) * por_pagina
        data = run_query(
            f"SELECT id_usuario, nombre, username, email FROM usuario WHERE rol = 'cliente' ORDER BY id_usuario {orden_sql} LIMIT {por_pagina} OFFSET {offset}",
            fetchall=True
        )
    
    # Calcular rango de registros mostrados
    registro_desde = offset + 1 if total_count > 0 else 0
    registro_hasta = min(offset + por_pagina, total_count)
    
    return render_template('clientes.html', 
                         clients=data, 
                         orden=orden,
                         pagina=pagina,
                         total_paginas=total_paginas,
                         total_count=total_count,
                         registro_desde=registro_desde,
                         registro_hasta=registro_hasta)


# -----------------------------------------------
# AGREGAR CLIENTE
# -----------------------------------------------
@app.route('/registro-rapido', methods=['POST'])
@login_requerido
@admin_requerido
def registro_rapido():
    """Registro rápido de cliente desde búsqueda."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    try:
        nombre = request.form.get('nombre', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        
        # Generar contraseña automática
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        password_auto = ''.join(secrets.choice(alphabet) for _ in range(12))
        
        # Validación
        errores = []
        
        if not nombre or len(nombre) < 3:
            errores.append("El nombre debe tener al menos 3 caracteres.")
        
        if not username or len(username) < 3:
            errores.append("El username debe tener al menos 3 caracteres.")
        
        if not validar_email(email):
            errores.append("Email inválido.")
        
        # Verificar si el username o email ya existen
        if not errores:
            usuario_existente = run_query(
                "SELECT id_usuario FROM usuario WHERE username = :u OR email = :e",
                {"u": username, "e": email},
                fetchone=True
            )
            if usuario_existente:
                errores.append("El username o email ya están registrados.")
        
        if errores:
            for error in errores:
                flash(error, 'danger')
            return redirect(url_for('clientes'))
        
        # Hash de la contraseña generada
        hashed = generate_password_hash(password_auto, method='pbkdf2:sha256')
        
        # Insertar en usuario
        usuario_id = run_query(
            "INSERT INTO usuario (username, email, password, rol) VALUES (:u, :e, :p, 'cliente') RETURNING id_usuario",
            {"u": username, "e": email, "p": hashed},
            fetchone=True,
            commit=True
        )[0]
        
        # Insertar en cliente
        run_query(
            "INSERT INTO cliente (id_usuario, nombre) VALUES (:uid, :n)",
            {"uid": usuario_id, "n": nombre},
            commit=True
        )
        
        # Enviar email con contraseña
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #a6cc48 0%, #84af1d 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="color: white; margin: 0;">¡Bienvenido a La Lavandería!</h1>
                </div>
                <div style="padding: 30px; background: #f9f9f9;">
                    <h2 style="color: #1a4e7b;">Hola {nombre},</h2>
                    <p>Tu cuenta ha sido creada exitosamente por nuestro equipo.</p>
                    <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #a6cc48; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #1a4e7b;">Tus credenciales de acceso:</h3>
                        <p><strong>Usuario:</strong> {username}</p>
                        <p><strong>Contraseña temporal:</strong> <code style="background: #f0f0f0; padding: 4px 8px; border-radius: 4px;">{password_auto}</code></p>
                    </div>
                    <p><strong>Importante:</strong> Te recomendamos cambiar tu contraseña después del primer inicio de sesión.</p>
                    <p>Gracias por confiar en nosotros.</p>
                </div>
            </body>
        </html>
        """
        send_email_async(email, "Bienvenido a La Lavandería - Credenciales de Acceso", html)
        
        flash(f'✅ Cliente "{nombre}" registrado exitosamente. Se ha enviado un correo con las credenciales a {email}', 'success')
        
    except Exception as e:
        print(f"Error en registro_rapido: {e}")
        flash(f'❌ Error al registrar cliente: {str(e)}', 'danger')
    
    return redirect(url_for('clientes'))

@app.route('/agregar_cliente', methods=['GET', 'POST'])
@login_requerido
@admin_requerido
def agregar_cliente():
    """Agregar un nuevo cliente con validación."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        password2 = request.form.get('password2', '').strip()
        
        # Validación
        errores = []
        
        if not nombre or len(nombre) < 3:
            errores.append("El nombre debe tener al menos 3 caracteres.")
        
        if not username or len(username) < 3:
            errores.append("El username debe tener al menos 3 caracteres.")
        
        if not validar_email(email):
            errores.append("Por favor ingresa un email válido.")
        
        # Validar contraseña
        validacion_password = validar_contrasena(password)
        if validacion_password != True:
            errores.append(validacion_password)
        
        if password != password2:
            errores.append("Las contraseñas no coinciden.")
        
        # Verificar si el username o email ya existen
        if not errores:
            usuario_existente = run_query(
                "SELECT id_usuario FROM usuario WHERE username = :u OR email = :e",
                {"u": username, "e": email},
                fetchone=True
            )
            if usuario_existente:
                errores.append("El username o email ya están registrados.")
        
        if errores:
            for error in errores:
                flash(error, 'warning')
            return render_template('agregar_cliente.html', 
                                 nombre=nombre, 
                                 username=username, 
                                 email=email)
        
        try:
            # Hashear la contraseña
            hashed_password = generate_password_hash(password)
            
            # Insertar en la tabla usuario
            run_query(
                "INSERT INTO usuario (nombre, username, email, password, rol) VALUES (:n, :u, :e, :p, 'cliente')",
                {"n": nombre, "u": username, "e": email, "p": hashed_password},
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
            "DELETE FROM usuario WHERE id_usuario = :id AND rol = 'cliente'",
            {"id": id_cliente},
            commit=True
        )
        flash('Cliente eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar cliente: {e}', 'danger')
    
    return redirect(_get_safe_redirect())


# -----------------------------------------------
# TÉRMINOS Y CONDICIONES DE DESCUENTOS
# -----------------------------------------------
@app.route('/terminos-descuentos')
def terminos_descuentos():
    """Página de términos y condiciones del programa de descuentos."""
    fecha_actual = datetime.datetime.now()
    return render_template('terminos_descuentos.html', fecha_actual=fecha_actual)


# -----------------------------------------------
# ADMINISTRACIÓN DE DESCUENTOS
# -----------------------------------------------
@app.route('/admin/configurar-descuentos')
@login_requerido
@admin_requerido
def configurar_descuentos():
    """Panel de administración de configuración de descuentos."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    tabla_existe = _tabla_descuento_existe()
    if not tabla_existe:
        flash('La tabla de descuentos no existe. Ejecuta las migraciones para habilitar el panel.', 'warning')
        return render_template('admin_configurar_descuentos.html', descuentos=[], tabla_descuentos_existe=False)
    
    # Obtener todos los niveles de descuento configurados
    try:
        descuentos = run_query("""
            SELECT id_config, nivel, porcentaje, pedidos_minimos, pedidos_maximos, activo
            FROM descuento_config
            ORDER BY pedidos_minimos ASC
        """, fetchall=True)
    except Exception as e:
        flash(f'Error al cargar descuentos: {e}', 'danger')
        descuentos = []
    
    return render_template('admin_configurar_descuentos.html', descuentos=descuentos, tabla_descuentos_existe=tabla_existe)


@app.route('/admin/ejecutar-migraciones', methods=['POST'])
@login_requerido
@admin_requerido
def ejecutar_migraciones_admin():
    """Ejecutar migraciones SQL desde el panel de admin (solo si es necesario)."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))

    archivos = ['add_direcciones_to_pedido.sql', 'create_descuento_config.sql', 'add_descuento_to_pedido.sql', 'create_cliente_esquema_descuento.sql']
    errores = []

    for archivo in archivos:
        ok, err = _ejecutar_sql_file(archivo)
        if not ok:
            errores.append(f"{archivo}: {err}")

    if errores:
        flash('Errores al ejecutar migraciones: ' + ' | '.join(errores), 'danger')
    else:
        flash('Migraciones ejecutadas correctamente.', 'success')

    return redirect(url_for('configurar_descuentos'))


@app.route('/admin/descuento/crear', methods=['POST'])
@login_requerido
@admin_requerido
def crear_descuento():
    """Crear un nuevo nivel de descuento."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    if not _tabla_descuento_existe():
        flash('La tabla de descuentos no existe. Ejecuta las migraciones antes de crear niveles.', 'warning')
        return redirect(url_for('configurar_descuentos'))
    
    nivel = request.form.get('nivel', '').strip()
    porcentaje = request.form.get('porcentaje', '').strip()
    pedidos_minimos = request.form.get('pedidos_minimos', '').strip()
    pedidos_maximos = request.form.get('pedidos_maximos', '').strip()
    activo = request.form.get('activo') == 'on'
    
    # Validación
    try:
        porcentaje = float(porcentaje)
        pedidos_minimos = int(pedidos_minimos)
        pedidos_maximos = int(pedidos_maximos) if pedidos_maximos else None
        
        if porcentaje < 0 or porcentaje > 100:
            raise ValueError("El porcentaje debe estar entre 0 y 100")
        
        if pedidos_minimos < 0:
            raise ValueError("Los pedidos mínimos deben ser positivos")
        
        if pedidos_maximos and pedidos_maximos < pedidos_minimos:
            raise ValueError("Los pedidos máximos deben ser mayores o iguales a los mínimos")
        
        # Insertar en base de datos
        run_query("""
            INSERT INTO descuento_config (nivel, porcentaje, pedidos_minimos, pedidos_maximos, activo)
            VALUES (:n, :p, :min, :max, :a)
        """, {
            "n": nivel,
            "p": porcentaje,
            "min": pedidos_minimos,
            "max": pedidos_maximos,
            "a": activo
        }, commit=True)
        
        flash(f'Nivel de descuento "{nivel}" creado exitosamente. Se aplicará a CLIENTES NUEVOS o que completen su ciclo actual.', 'success')
    except Exception as e:
        flash(f'Error al crear descuento: {e}', 'danger')
    
    return redirect(url_for('configurar_descuentos'))


@app.route('/admin/descuento/editar/<int:id_config>', methods=['POST'])
@login_requerido
@admin_requerido
def editar_descuento(id_config):
    """Editar un nivel de descuento existente."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    if not _tabla_descuento_existe():
        flash('La tabla de descuentos no existe. Ejecuta las migraciones antes de editar niveles.', 'warning')
        return redirect(url_for('configurar_descuentos'))
    
    nivel = request.form.get('nivel', '').strip()
    porcentaje = request.form.get('porcentaje', '').strip()
    pedidos_minimos = request.form.get('pedidos_minimos', '').strip()
    pedidos_maximos = request.form.get('pedidos_maximos', '').strip()
    activo = request.form.get('activo') == 'on'
    
    try:
        porcentaje = float(porcentaje)
        pedidos_minimos = int(pedidos_minimos)
        pedidos_maximos = int(pedidos_maximos) if pedidos_maximos else None
        
        if porcentaje < 0 or porcentaje > 100:
            raise ValueError("El porcentaje debe estar entre 0 y 100")
        
        if pedidos_minimos < 0:
            raise ValueError("Los pedidos mínimos deben ser positivos")
        
        if pedidos_maximos and pedidos_maximos < pedidos_minimos:
            raise ValueError("Los pedidos máximos deben ser mayores o iguales a los mínimos")
        
        # Actualizar en base de datos
        run_query("""
            UPDATE descuento_config
            SET nivel = :n, porcentaje = :p, pedidos_minimos = :min, 
                pedidos_maximos = :max, activo = :a, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id_config = :id
        """, {
            "n": nivel,
            "p": porcentaje,
            "min": pedidos_minimos,
            "max": pedidos_maximos,
            "a": activo,
            "id": id_config
        }, commit=True)
        
        flash(f'Nivel de descuento "{nivel}" actualizado exitosamente. Los cambios se aplicarán solo a CLIENTES NUEVOS o que completen su ciclo actual.', 'success')
    except Exception as e:
        flash(f'Error al editar descuento: {e}', 'danger')
    
    return redirect(url_for('configurar_descuentos'))


@app.route('/admin/descuento/eliminar/<int:id_config>', methods=['POST'])
@login_requerido
@admin_requerido
def eliminar_descuento(id_config):
    """Eliminar un nivel de descuento."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    if not _tabla_descuento_existe():
        flash('La tabla de descuentos no existe. Ejecuta las migraciones antes de eliminar niveles.', 'warning')
        return redirect(url_for('configurar_descuentos'))
    
    try:
        run_query("""
            DELETE FROM descuento_config WHERE id_config = :id
        """, {"id": id_config}, commit=True)
        
        flash('Nivel de descuento eliminado exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar descuento: {e}', 'danger')
    
    return redirect(url_for('configurar_descuentos'))


# -----------------------------------------------
# REPORTES
# -----------------------------------------------
@app.route('/reportes')
@login_requerido
@admin_requerido
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


@app.route('/reportes/export_excel')
@login_requerido
@admin_requerido
def reportes_export_excel():
    """Exportar todos los reportes a un archivo Excel."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    try:
        from io import BytesIO
        import pandas as pd
        from datetime import datetime
        
        print("\nGenerando archivo Excel...")
        
        # Crear un buffer en memoria
        output = BytesIO()
        
        # Crear el archivo Excel con múltiples hojas
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            # Hoja 1: Resumen General (SIEMPRE se crea)
            resumen_data = {
                'Metrica': [
                    'Total Pedidos',
                    'Total Ingresos (COP)',
                    'Total Prendas Procesadas',
                    'Promedio Prendas/Pedido',
                    'Tasa Completacion (%)',
                    'Promedio Gasto/Cliente (COP)',
                    'Pedidos Pendientes',
                    'Promedio Dias Completar'
                ],
                'Valor': [
                    run_query("SELECT COUNT(*) FROM pedido", fetchone=True)[0] or 0,
                    run_query("SELECT COALESCE(SUM(total), 0) FROM recibo", fetchone=True)[0] or 0,
                    run_query("SELECT COUNT(*) FROM prenda", fetchone=True)[0] or 0,
                    run_query("SELECT AVG(cnt) FROM (SELECT COUNT(*) as cnt FROM prenda GROUP BY id_pedido) subq", fetchone=True)[0] or 0,
                    (run_query("SELECT COUNT(*) FROM pedido WHERE estado = 'Completado'", fetchone=True)[0] or 0) / max(run_query("SELECT COUNT(*) FROM pedido", fetchone=True)[0] or 1, 1) * 100,
                    run_query("SELECT AVG(total) FROM recibo", fetchone=True)[0] or 0,
                    run_query("SELECT COUNT(*) FROM pedido WHERE estado IN ('Pendiente', 'En proceso')", fetchone=True)[0] or 0,
                    run_query("SELECT AVG((fecha_entrega - fecha_ingreso)::integer) FROM pedido WHERE estado = 'Completado' AND fecha_entrega IS NOT NULL", fetchone=True)[0] or 0
                ]
            }
            df_resumen = pd.DataFrame(resumen_data)
            df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
            print("[Resumen]")
            
            # Hoja 2: Estado de Pedidos
            try:
                estado_data = run_query("""
                    SELECT estado, COUNT(*) as cantidad
                    FROM pedido
                    GROUP BY estado
                    ORDER BY cantidad DESC
                """, fetchall=True)
                if estado_data and len(estado_data) > 0:
                    df_estado = pd.DataFrame(estado_data, columns=['Estado', 'Cantidad'])
                    df_estado.to_excel(writer, sheet_name='Estados', index=False)
                    print("[Estados]")
            except Exception as e:
                print(f"[Estados - Error: {e}]")
            
            # Hoja 3: Prendas Mas Procesadas
            try:
                prendas_data = run_query("""
                    SELECT tipo_prenda, COUNT(*) as cantidad
                    FROM prenda
                    GROUP BY tipo_prenda
                    ORDER BY cantidad DESC
                    LIMIT 15
                """, fetchall=True)
                if prendas_data and len(prendas_data) > 0:
                    df_prendas = pd.DataFrame(prendas_data, columns=['Tipo Prenda', 'Cantidad'])
                    df_prendas.to_excel(writer, sheet_name='Prendas', index=False)
                    print("[Prendas]")
            except Exception as e:
                print(f"[Prendas - Error: {e}]")
            
            # Hoja 4: Clientes Mas Activos
            try:
                clientes_data = run_query("""
                    SELECT c.nombre, COUNT(p.id_pedido) as pedidos,
                           COALESCE(SUM(r.total), 0) as gastado
                    FROM cliente c
                    LEFT JOIN pedido p ON c.id_cliente = p.id_cliente
                    LEFT JOIN recibo r ON p.id_pedido = r.id_pedido
                    GROUP BY c.id_cliente, c.nombre
                    HAVING COUNT(p.id_pedido) > 0
                    ORDER BY pedidos DESC
                    LIMIT 20
                """, fetchall=True)
                if clientes_data and len(clientes_data) > 0:
                    df_clientes = pd.DataFrame(clientes_data, columns=['Nombre', 'Pedidos', 'Total (COP)'])
                    df_clientes.to_excel(writer, sheet_name='Clientes', index=False)
                    print("[Clientes]")
            except Exception as e:
                print(f"[Clientes - Error: {e}]")
        
        print("Preparando descarga...")
        
        # IMPORTANTE: seek DESPUES de cerrar el writer
        output.seek(0)
        
        # Preparar respuesta para descarga
        from flask import send_file
        fecha_actual = datetime.now().strftime('%Y-%m-%d_%H-%M')
        filename = f'Reportes_LaLavanderia_{fecha_actual}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except ImportError as e:
        flash(f'❌ Error: Falta instalar dependencias (pandas/openpyxl). Contacta al administrador.', 'danger')
        print(f"Error de importación en export_excel: {e}")
        return redirect(url_for('reportes'))
    except Exception as e:
        flash(f'❌ Error al generar archivo Excel: {str(e)}', 'danger')
        print(f"Error en export_excel: {e}")
        return redirect(url_for('reportes'))


# -----------------------------------------------
# LECTOR DE CÓDIGOS DE BARRAS
# -----------------------------------------------
@app.route('/lector_barcode', methods=['GET', 'POST'])
@login_requerido
@admin_requerido
def lector_barcode():
    """Escanear código de barras y mostrar detalles del pedido."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
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
            # Log del error para debugging (puedes ver esto en los logs de Render)
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
            
            # 1.1 Obtener y validar direcciones (SERVICIO A DOMICILIO)
            direccion_recogida = request.form.get('direccion_recogida', '').strip()
            direccion_entrega = request.form.get('direccion_entrega', '').strip()
            
            # Validar que las direcciones no estén vacías
            if not direccion_recogida or len(direccion_recogida) < 10:
                flash('⚠️ Debes ingresar una dirección de recogida válida (mínimo 10 caracteres).', 'warning')
                return redirect(url_for('agregar_pedido'))
            
            if not direccion_entrega or len(direccion_entrega) < 10:
                flash('⚠️ Debes ingresar una dirección de entrega válida (mínimo 10 caracteres).', 'warning')
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
            
            # 5. Crear pedido con código de barras y direcciones
            # IMPORTANTE: Primero calcular el descuento ANTES de crear el pedido
            
            # 5.1. Calcular descuento según ESQUEMA CONGELADO del cliente
            pedidos_count = run_query(
                "SELECT COUNT(*) FROM pedido WHERE id_cliente = :id",
                {"id": id_cliente},
                fetchone=True
            )[0] or 0
            
            # Obtener esquema de descuento del cliente (congelado o actual)
            esquema_cliente = _obtener_esquema_descuento_cliente(id_cliente)
            
            # Determinar nivel y descuento basado en el esquema del cliente
            descuento_porcentaje_aplicado = 0
            nivel_descuento_aplicado = None
            
            for nivel_config in esquema_cliente:
                min_pedidos = nivel_config.get("min", 0)
                max_pedidos = nivel_config.get("max")
                
                if pedidos_count >= min_pedidos:
                    if max_pedidos is None or pedidos_count <= max_pedidos:
                        descuento_porcentaje_aplicado = nivel_config.get("porcentaje", 0)
                        nivel_descuento_aplicado = nivel_config.get("nivel")
                        break
            
            # 5.2. Crear el pedido (compatible con BD con o sin columnas de descuento)
            try:
                # Intentar con columnas de descuento (nueva estructura)
                result = run_query(
                    """INSERT INTO pedido (fecha_ingreso, fecha_entrega, estado, id_cliente, direccion_recogida, direccion_entrega, porcentaje_descuento, nivel_descuento) 
                       VALUES (:fi, :fe, :e, :ic, :dr, :de, :pd, :nd) RETURNING id_pedido""",
                    {"fi": fecha_ingreso, "fe": fecha_entrega, "e": "Pendiente", "ic": id_cliente, "dr": direccion_recogida, "de": direccion_entrega, "pd": descuento_porcentaje_aplicado, "nd": nivel_descuento_aplicado},
                    commit=True,
                    fetchone=True
                )
            except Exception as e:
                # Si falla (columnas no existen), usar estructura antigua
                if "porcentaje_descuento" in str(e) or "does not exist" in str(e):
                    result = run_query(
                        """INSERT INTO pedido (fecha_ingreso, fecha_entrega, estado, id_cliente, direccion_recogida, direccion_entrega) 
                           VALUES (:fi, :fe, :e, :ic, :dr, :de) RETURNING id_pedido""",
                        {"fi": fecha_ingreso, "fe": fecha_entrega, "e": "Pendiente", "ic": id_cliente, "dr": direccion_recogida, "de": direccion_entrega},
                        commit=True,
                        fetchone=True
                    )
                else:
                    raise e
            
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
            
            # 8. Usar el descuento ya guardado en el pedido (no recalcular)
            # El descuento ya está en descuento_porcentaje_aplicado y nivel_descuento_aplicado
            
            # Calcular monto con descuento
            monto_descuento = (total_costo * descuento_porcentaje_aplicado) / 100
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
                "SELECT nombre, email FROM cliente WHERE id_cliente = :id",
                {"id": id_cliente},
                fetchone=True
            )
            
            # Enviar correo de confirmación de pedido creado (asíncrono)
            if cliente_data:
                nombre_cliente = cliente_data[0]
                email_cliente = cliente_data[1]
                
                html_pedido = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #a6cc48 0%, #8fb933 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                            <h1 style="color: white; margin: 0;">✅ Pedido Creado</h1>
                        </div>
                        <div style="padding: 30px; background: #f9f9f9;">
                            <h2 style="color: #1a4e7b;">Hola {nombre_cliente},</h2>
                            <p style="font-size: 16px;">Tu pedido ha sido creado exitosamente.</p>
                            
                            <div style="background: white; border-left: 4px solid #a6cc48; padding: 20px; margin: 20px 0; border-radius: 5px;">
                                <h3 style="color: #1a4e7b; margin-top: 0;">📦 Información del Pedido</h3>
                                <p><strong>Número:</strong> #{id_pedido}</p>
                                <p><strong>Código:</strong> {codigo_barras}</p>
                                <p><strong>Fecha de recogida:</strong> {fecha_ingreso}</p>
                                <p><strong>Fecha estimada de entrega:</strong> {fecha_entrega}</p>
                                <p><strong>Estado:</strong> Pendiente</p>
                            </div>
                            
                            <div style="background: white; border-left: 4px solid #2196F3; padding: 20px; margin: 20px 0; border-radius: 5px;">
                                <h3 style="color: #1a4e7b; margin-top: 0;">🏠 Direcciones</h3>
                                <p><strong>Recogida:</strong> {direccion_recogida}</p>
                                <p><strong>Entrega:</strong> {direccion_entrega}</p>
                            </div>
                            
                            <div style="background: white; border-left: 4px solid #4CAF50; padding: 20px; margin: 20px 0; border-radius: 5px;">
                                <h3 style="color: #1a4e7b; margin-top: 0;">👕 Prendas: {prendas_insertadas}</h3>
                                <p><strong>Subtotal:</strong> ${total_costo:,.0f}</p>
                                {"<p><strong>Descuento (" + str(descuento_porcentaje_aplicado) + "%):</strong> -${:,.0f}</p>".format(monto_descuento) if descuento_porcentaje_aplicado > 0 else ""}
                                <p style="font-size: 18px; color: #a6cc48;"><strong>Total:</strong> ${monto_final:,.0f}</p>
                            </div>
                            
                            <div style="background: #e8f4f8; padding: 20px; margin: 20px 0; border-radius: 5px; text-align: center;">
                                <p><strong>🚚 Servicio a Domicilio</strong></p>
                                <p>Recogeremos tu ropa en la dirección indicada y la entregaremos limpia en la fecha estimada.</p>
                            </div>
                        </div>
                        <div style="background: #1a4e7b; color: white; padding: 20px; text-align: center; border-radius: 0 0 10px 10px;">
                            <p style="margin: 0;">La Lavandería - Servicio a Domicilio</p>
                        </div>
                    </body>
                </html>
                """
                send_email_async(email_cliente, f"Pedido {id_pedido} Creado - La Lavanderia", html_pedido)
            
            # Mensaje con descuento aplicado y código de barras
            if descuento_porcentaje_aplicado > 0:
                msg_descuento = f" | Nivel {nivel_descuento_aplicado}: Descuento {descuento_porcentaje_aplicado}% (-${monto_descuento:,.0f})"
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
        "SELECT id_pedido, fecha_ingreso, fecha_entrega, estado, id_cliente, codigo_barras, direccion_recogida, direccion_entrega FROM pedido WHERE id_pedido = :id",
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
    
    # Obtener la página de origen para el botón regresar
    referer = request.args.get('ref') or request.referrer or ''
    return_url = referer if referer and referer != request.url else None
    
    return render_template('pedido_detalles.html', pedido=pedido, prendas=prendas, return_url=return_url)


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
        # Obtener datos del pedido y cliente antes de actualizar
        pedido_data = run_query("""
            SELECT p.id_pedido, p.codigo_barras, p.fecha_entrega, c.nombre, c.email
            FROM pedido p
            LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
            WHERE p.id_pedido = :id
        """, {"id": id_pedido}, fetchone=True)
        
        # Actualizar estado
        run_query(
            "UPDATE pedido SET estado = :e WHERE id_pedido = :id",
            {"e": estado, "id": id_pedido},
            commit=True
        )
        
        # Enviar correo según el nuevo estado
        if pedido_data and pedido_data[4]:  # Si tiene email
            codigo = pedido_data[1] or f"#{id_pedido}"
            fecha_entrega = pedido_data[2]
            nombre_cliente = pedido_data[3]
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
# API: AUTOCOMPLETADO DE CLIENTES
# -----------------------------------------------
@app.route('/api/autocomplete/clientes')
@login_requerido
@admin_requerido
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
            LOWER(username) LIKE LOWER(:q) OR
            CAST(id_usuario AS TEXT) LIKE :q
        )
        ORDER BY nombre
        LIMIT 10
    """, {"q": f"%{query}%"}, fetchall=True)
    
    resultados = []
    for cliente in clientes:
        resultados.append({
            'id': cliente[0],
            'nombre': cliente[1],
            'email': cliente[2] or '',
            'username': cliente[3] or '',
            'label': f"{cliente[1]} ({cliente[2] or cliente[3]})"
        })
    
    return jsonify(resultados)


# -----------------------------------------------
# API: AUTOCOMPLETADO DE ESTADOS
# -----------------------------------------------
@app.route('/api/autocomplete/estados')
@login_requerido
def api_autocomplete_estados():
    """API para autocompletado de estados de pedidos."""
    from flask import jsonify
    
    query = request.args.get('q', '').strip().lower()
    
    # Estados posibles
    todos_estados = ['Pendiente', 'En proceso', 'Completado', 'Cancelado', 'Entregado']
    
    if not query:
        return jsonify(todos_estados)
    
    # Filtrar estados que coincidan
    estados_filtrados = [e for e in todos_estados if query in e.lower()]
    
    return jsonify(estados_filtrados)


# -----------------------------------------------
# FUNCIONES AUXILIARES (ej. _admin_only)
# -----------------------------------------------
def _admin_only():
    rol = session.get('rol')
    if not rol:
        return False
    return str(rol).strip().lower() == 'administrador'


def _tabla_descuento_existe():
    try:
        result = run_query(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'descuento_config')",
            fetchone=True
        )
        return bool(result[0]) if result else False
    except Exception:
        return False


def _parse_sql_statements(sql_text):
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


def _ejecutar_sql_file(nombre_archivo):
    ruta = os.path.join(os.path.dirname(__file__), 'migrations', nombre_archivo)
    if not os.path.exists(ruta):
        return False, 'Archivo no encontrado'
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
        statements = _parse_sql_statements(contenido)
        for stmt in statements:
            run_query(stmt, commit=True)
        return True, None
    except Exception as e:
        return False, str(e)


def _obtener_esquema_descuento_cliente(id_cliente):
    """
    Obtiene el esquema de descuento para un cliente específico.
    - Si tiene esquema congelado activo, lo retorna
    - Si no tiene o completó ciclo, obtiene el esquema actual y lo congela
    - Retorna: lista de dicts con nivel, porcentaje, min, max
    """
    import json
    
    # Verificar si tiene esquema activo
    try:
        esquema_guardado = run_query("""
            SELECT id_esquema, esquema_json, fecha_inicio
            FROM cliente_esquema_descuento
            WHERE id_cliente = :id AND activo = true
        """, {"id": id_cliente}, fetchone=True)
    except:
        # Si la tabla no existe, usar esquema actual
        esquema_guardado = None
    
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
    
    if esquema_guardado:
        # Tiene esquema congelado, verificar si completó ciclo
        try:
            esquema_json = json.loads(esquema_guardado[1])
            
            # Contar pedidos del cliente
            pedidos_count = run_query(
                "SELECT COUNT(*) FROM pedido WHERE id_cliente = :id",
                {"id": id_cliente},
                fetchone=True
            )[0] or 0
            
            # Encontrar nivel máximo del esquema guardado
            nivel_maximo = max((n.get("max") or 999) for n in esquema_json)
            
            # Si completó el ciclo, actualizar a esquema actual
            if pedidos_count > nivel_maximo:
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
            
            return esquema_json
        except:
            # Error parseando JSON, usar actual
            return esquema_actual
    else:
        # No tiene esquema, congelar el actual
        try:
            run_query("""
                INSERT INTO cliente_esquema_descuento (id_cliente, esquema_json, activo)
                VALUES (:id, :json, true)
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
