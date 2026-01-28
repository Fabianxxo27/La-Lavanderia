from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
import pandas as pd
import datetime
import smtplib
import credentials as cd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import urllib.parse
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (si existe)
load_dotenv()

# Precio por prenda (asunción razonable). Cambia este valor si deseas otra tarifa.
PRICE_PER_PRENDA = 5000.0

# Configuración de la app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', '1379')

# Configuración de la base de datos
# En Render: usar DATABASE_URL desde variables de entorno (PostgreSQL)
# En desarrollo local: usar credentials.py (MySQL)
database_url = os.getenv('DATABASE_URL')

if not database_url:
    # Si no hay DATABASE_URL, usar credenciales locales (desarrollo con MySQL)
    print("⚠️ DATABASE_URL no encontrado, usando credentials.py (desarrollo local)")
    pwd = urllib.parse.quote_plus(cd.password)
    database_url = f"mysql+pymysql://{cd.user}:{pwd}@{cd.host}/{cd.db}?charset=utf8mb4"
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = run_query(
            "SELECT username, password, rol FROM usuario WHERE username = :u",
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
            # user = (username, password_hash, rol)
            session['username'] = user[0]  # Guarda el username en sesión
            session['rol'] = user[2]       # Guarda el rol en sesión
            flash(f"Bienvenido {username}", "success")
            print(f"DEBUG: Usuario {username} con rol: '{user[2]}'")

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
        username = request.form.get("username")
        email = request.form.get("email")
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
            # Verificar si el username ya 
            existing_user = run_query(
                "SELECT id_usuario FROM usuario WHERE username = :u",
                {"u": username},
                fetchone=True
            )
            # Verificar que el email no esté ya registrado en usuario
            existing_email = run_query(
                "SELECT id_usuario FROM usuario WHERE email = :e",
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
            run_query(
                "INSERT INTO usuario (nombre, username, password, rol, email) VALUES (:n, :u, :p, :r, :e)",
                {
                    "n": nombre,
                    "u": username,
                    "p": hashed_password,
                    "r": "cliente",
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
    return render_template('cliente_inicio.html')


# -----------------------------------------------
# RECIBOS DEL CLIENTE
# -----------------------------------------------
@app.route('/cliente_recibos')
def cliente_recibos():
    """Ver recibos del cliente actual."""
    username = session.get('username')
    if not username:
        flash("No se pudo identificar al usuario.", "danger")
        return redirect(url_for('login'))
    
    recibos = run_query("""
        SELECT r.id_recibo, r.id_pedido, r.monto, r.fecha
        FROM recibo r
        LEFT JOIN usuario u ON r.id_cliente = u.id_usuario
        WHERE u.username = :u
        ORDER BY r.fecha DESC
    """, {"u": username}, fetchall=True)
    
    return render_template('cliente_recibos.html', recibos=recibos)


# -----------------------------------------------
# PROMOCIONES DEL CLIENTE
# -----------------------------------------------
@app.route('/cliente_promociones')
def cliente_promociones():
    """Ver promociones disponibles para el cliente."""
    promociones = run_query("""
        SELECT id_promocion, descripcion, descuento, fecha_inicio, fecha_fin
        FROM promocion
        WHERE fecha_fin >= CURRENT_DATE
        ORDER BY fecha_inicio DESC
    """, fetchall=True)
    
    return render_template('cliente_promociones.html', promociones=promociones)


# -----------------------------------------------
# PEDIDOS DEL cliente
# -----------------------------------------------
@app.route('/cliente_pedidos')
def cliente_pedidos():
    # Usar username desde la sesión (más seguro)
    username = session.get('username')
    if not username:
        flash("No se pudo identificar al usuario.", "danger")
        return redirect(url_for('login'))

    pedidos = run_query("""
        SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado
        FROM pedido p
        LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
        LEFT JOIN usuario u ON u.email = c.email
        WHERE u.username = :u
        ORDER BY p.fecha_ingreso DESC
    """, {"u": username}, fetchall=True)

    return render_template('cliente_pedidos.html', pedidos=pedidos, username=username)


# -----------------------------------------------
# LISTAR PEDIDOS (Administrador)
# -----------------------------------------------
@app.route('/pedidos')
def pedidos():
    """Mostrar todos los pedidos (para administrador)."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    pedidos = run_query("""
        SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre
        FROM pedido p
        LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
        ORDER BY p.fecha_ingreso DESC
    """, fetchall=True)
    
    return render_template('pedidos.html', pedidos=pedidos)


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
    """Agregar un nuevo cliente."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')
        
        try:
            run_query(
                "INSERT INTO cliente (nombre, email, telefono, direccion) VALUES (:n, :e, :t, :d)",
                {"n": nombre, "e": email, "t": telefono, "d": direccion},
                commit=True
            )
            flash('Cliente agregado correctamente.', 'success')
            return redirect(url_for('clientes'))
        except Exception as e:
            flash(f'Error al agregar cliente: {e}', 'danger')
    
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
            return redirect(url_for('clientes'))
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
    
    return redirect(url_for('clientes'))


# -----------------------------------------------
# EXPORTAR tablas a Excel
# -----------------------------------------------
@app.route('/exportar')
def exportar():
    tables = run_query("SHOW TABLES", fetchall=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for table in tables:
            table_name = table[0]
            if table_name.lower() in ('administradores',):
                continue
            data = run_query(f"SELECT * FROM `{table_name}`", fetchall=True)
            columns = [col[0] for col in run_query(f"SHOW COLUMNS FROM `{table_name}`", fetchall=True)]
            df = pd.DataFrame(data, columns=columns)
            df.to_excel(writer, index=False, sheet_name=table_name[:31])

    output.seek(0)
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(output,
                     as_attachment=True,
                     download_name=f"lavanderia_export_{now}.xlsx",
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/exportar/usuarios')
def exportar_usuarios():
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    data = run_query("SELECT id_usuario, nombre, username, rol, email FROM usuario ORDER BY id_usuario DESC", fetchall=True) or []
    cols = ['id_usuario', 'nombre', 'username', 'rol', 'email']
    return _make_excel_response(data, cols, 'usuarios')


@app.route('/exportar/pedidos')
def exportar_pedidos():
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    data = run_query("SELECT id_pedido, fecha_ingreso, fecha_entrega, estado, id_cliente FROM pedido ORDER BY id_pedido DESC", fetchall=True) or []
    cols = ['id_pedido', 'fecha_ingreso', 'fecha_entrega', 'estado', 'id_cliente']
    return _make_excel_response(data, cols, 'pedidos')


@app.route('/exportar/promociones')
def exportar_promociones():
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    data = run_query("SELECT id_promocion, descripcion, descuento, fecha_inicio, fecha_fin FROM promocion ORDER BY id_promocion DESC", fetchall=True) or []
    cols = ['id_promocion', 'descripcion', 'descuento', 'fecha_inicio', 'fecha_fin']
    return _make_excel_response(data, cols, 'promociones')


def _make_excel_response(data, columns, filename):
    output = BytesIO()
    df = pd.DataFrame(data, columns=columns)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=filename[:31])
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"{filename}.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# -----------------------------------------------
# EJEMPLOS DE OPERACIONES CON PEDIDOS / PRENDAS (fragmentos principales)
# -----------------------------------------------
@app.route('/agregar_prenda/<int:id_pedido>', methods=['POST'])
def agregar_prenda(id_pedido):
    """Añade una prenda al pedido indicado por id_pedido."""
    # Validar que el pedido exista
    pedido = run_query("SELECT id_pedido FROM pedido WHERE id_pedido = :id", {"id": id_pedido}, fetchone=True)
    if not pedido:
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('pedidos'))

    tipo = request.form.get('tipo', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    observaciones = request.form.get('observaciones', '').strip()

    if not tipo:
        flash('El campo tipo es obligatorio.', 'warning')
        return redirect(url_for('pedido_detalles', id_pedido=id_pedido))

    try:
        run_query(
            "INSERT INTO prenda (tipo, descripcion, observaciones, id_pedido) VALUES (:tipo, :desc, :obs, :id)",
            {"tipo": tipo, "desc": descripcion, "obs": observaciones, "id": id_pedido},
            commit=True
        )
        flash('Prenda agregada correctamente.', 'success')
    except Exception as e:
        flash(f'Error al agregar prenda: {e}', 'danger')

    return redirect(url_for('pedido_detalles', id_pedido=id_pedido))


# -----------------------------------------------
# REPORTES
# -----------------------------------------------
@app.route('/reportes')
def reportes():
    """Página de reportes para administrador."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    usuarios = run_query(
        "SELECT id_usuario, nombre, email FROM usuario WHERE rol='cliente'",
        fetchall=True
    )
    return render_template('reportes.html', usuarios=usuarios)


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
    
    if request.method == 'POST':
        id_cliente = request.form.get('id_cliente')
        fecha_ingreso = request.form.get('fecha_ingreso')
        fecha_entrega = request.form.get('fecha_entrega')
        
        try:
            run_query(
                "INSERT INTO pedido (fecha_ingreso, fecha_entrega, estado, id_cliente) VALUES (:fi, :fe, :e, :ic)",
                {
                    "fi": fecha_ingreso,
                    "fe": fecha_entrega,
                    "e": "Pendiente",
                    "ic": id_cliente
                },
                commit=True
            )
            flash('Pedido creado correctamente.', 'success')
            
            # Redirigir según el rol
            if _admin_only():
                return redirect(url_for('pedidos'))
            else:
                return redirect(url_for('cliente_pedidos'))
        except Exception as e:
            flash(f'Error al crear pedido: {e}', 'danger')
    
    clientes = run_query(
        "SELECT id_cliente, nombre FROM cliente ORDER BY nombre",
        fetchall=True
    )
    return render_template('agregar_pedido.html', clientes=clientes)


# -----------------------------------------------
# DETALLES DE PEDIDO
# -----------------------------------------------
@app.route('/pedido_detalles/<int:id_pedido>')
def pedido_detalles(id_pedido):
    """Ver detalles de un pedido."""
    pedido = run_query(
        "SELECT id_pedido, fecha_ingreso, fecha_entrega, estado, id_cliente FROM pedido WHERE id_pedido = :id",
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
    """Eliminar un pedido."""
    if not _admin_only():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    try:
        run_query(
            "DELETE FROM pedido WHERE id_pedido = :id",
            {"id": id_pedido},
            commit=True
        )
        flash('Pedido eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar: {e}', 'danger')
    
    return redirect(url_for('pedidos'))


# -----------------------------------------------
# FUNCIONES AUXILIARES (ej. _admin_only)
# -----------------------------------------------
def _admin_only():
    rol = session.get('rol')
    if not rol:
        return False
    return str(rol).strip().lower() == 'administrador'


# -----------------------------------------------
# FUNCIÓN PARA ENVIAR CORREO
# -----------------------------------------------
def send_welcome_email(to_email, username):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "lalavanderiabogota@gmail.com"
    sender_password = "dsjmjtvtwcahqrwy"

    subject = "Bienvenido a La Lavandería"
    body = f"""
Hola {username},

¡Gracias por registrarte en La Lavandería!
Estamos felices de tenerte con nosotros.

Atentamente,
El equipo de La Lavandería.
"""

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Activa cifrado TLS
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, message.as_string())
        print("Correo enviado correctamente")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

# -----------------------------------------------
# MAIN
# -----------------------------------------------
if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=8080)
