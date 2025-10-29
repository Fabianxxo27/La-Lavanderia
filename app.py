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

# Precio por prenda (asunción razonable). Cambia este valor si deseas otra tarifa.
PRICE_PER_PRENDA = 5000.0

# Configuración de la app
app = Flask(__name__)
app.secret_key = "1379"

# Configuración base de datos (usa tus credenciales reales)
# Leer configuración de base de datos desde variables de entorno si están disponibles.
db_user = os.getenv('DB_USER')
if db_user:
    db_user = os.getenv('DB_USER', '437867')  # tu usuario MySQL
    db_password = os.getenv('DB_PASSWORD', 'U4C9FKrw')  # cambia esto
    db_host = os.getenv('DB_HOST', 'mysql-fabianmedina.alwaysdata.net')  # host AlwaysData
    db_name = os.getenv('DB_NAME', 'fabianmedina_miapp')  # nombre de la base de datos
    db_port = os.getenv('DB_PORT', '')  # no es obligatorio para AlwaysData
    if db_port:
        app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{cd.user}:{cd.password}@{cd.host}/{cd.db}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 🔥 Hacer disponible la función now() en todos los templates
app.jinja_env.globals['now'] = datetime.datetime.now

# 🔥 Hacer disponible la función now() en todos los templates
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

            # Redirigir según rol
            if str(user[2]).lower() == 'administrador':
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

            # Enviar correo de confirmación
            send_welcome_email(email, username)

            flash("Usuario registrado exitosamente. Revisa tu correo.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            flash(f"Error al registrar: {e}", "danger")
            return redirect(url_for("registro"))

    return render_template("registro.html")


# -----------------------------------------------
# PÁGINA PRINCIPAL DEL PANEL
# -----------------------------------------------
@app.route('/inicio')
def inicio():
    return render_template('inicio.html')

# -----------------------------------------------
# PÁGINA PRINCIPAL DEL PANEL
# -----------------------------------------------
@app.route('/cliente_inicio')
def cliente_inicio():
    return render_template('cliente_inicio.html')

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
# LOGOUT
# -----------------------------------------------
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('rol', None)
    flash("Has cerrado sesión correctamente", "success")
    return redirect(url_for('login'))

# -----------------------------------------------
# RECIBOS DEL cliente
# -----------------------------------------------
@app.route('/cliente_recibos')
def cliente_recibos():
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

    return render_template('cliente_recibos.html', recibos=recibos, username=username)


# -----------------------------------------------
# PROMOCIONES DEL cliente
# -----------------------------------------------
@app.route('/cliente_promociones')
def cliente_promociones():
    # Para promociones no necesitamos el username, pero mantenemos la comprobación de sesión
    username = session.get('username')
    if not username:
        flash("No se pudo identificar al usuario.", "danger")
        return redirect(url_for('login'))

    # Promociones generales activas
    promociones = run_query("""
        SELECT id_promocion, descripcion, descuento, fecha_inicio, fecha_fin
        FROM promocion
        WHERE fecha_fin >= CURDATE()
        ORDER BY fecha_inicio DESC
    """, fetchall=True) or []

    # Calcular promoción personalizada: 1% acumulativo por cada pedido del cliente (si tiene >=1 pedidos)
    # Contar pedidos asociados al usuario (a través de cliente.email)
    count_row = run_query(
        "SELECT COUNT(*) FROM pedido p JOIN cliente c ON p.id_cliente = c.id_cliente JOIN usuario u ON u.email = c.email WHERE u.username = :u",
        {"u": username},
        fetchone=True
    )
    pedidos_count = int(count_row[0]) if count_row and count_row[0] is not None else 0

    promo_personalizada = None
    if pedidos_count >= 1:
        descuento = float(pedidos_count) * 1.0  # 1% por pedido
        # opcional: limitar descuento máximo si se desea (no solicitado)
        promo_personalizada = {
            'descripcion': f'Descuento de fidelidad: {pedidos_count} pedido(s)',
            'descuento': round(descuento, 2),
            'nota': '1% acumulativo por pedido',
            'fecha_inicio': None,
            'fecha_fin': None
        }

    return render_template('cliente_promociones.html', promociones=promociones, username=username, promo_personalizada=promo_personalizada, pedidos_count=pedidos_count)


# -----------------------------------------------
# AÑADIR pedido (cliente y admin)
# -----------------------------------------------
@app.route('/agregar_pedido', methods=['GET', 'POST'])
def agregar_pedido():
    # Solo usuarios autenticados pueden crear pedidos
    username = session.get('username')
    rol = (session.get('rol') or '').lower()
    if not username:
        flash('Inicia sesión para crear un pedido.', 'warning')
        return redirect(url_for('login'))

    # Obtener lista de 'clientes' desde la tabla usuario para admin (usuarios con rol 'cliente')
    clients = None
    if rol == 'administrador':
        users = run_query("SELECT id_usuario, nombre, username, email FROM usuario WHERE rol = 'cliente' ORDER BY nombre", fetchall=True)
        clients = [(u[0], f"{u[1]} ({u[2]})") for u in users] if users else []

    if request.method == 'POST':
        # Determinar id_cliente: si admin, viene del form; si cliente, buscar por email en usuario->cliente
        if rol == 'administrador':
            # El admin selecciona un usuario (id_usuario). Necesitamos mapearlo a cliente.id_cliente
            selected_uid = request.form.get('id_cliente')
            if not selected_uid:
                flash('Selecciona un cliente (usuario).', 'warning')
                return redirect(url_for('agregar_pedido'))
            try:
                uid = int(selected_uid)
            except ValueError:
                flash('Cliente inválido.', 'danger')
                return redirect(url_for('agregar_pedido'))

            # Obtener datos del usuario
            user_row = run_query(
                "SELECT nombre, email FROM usuario WHERE id_usuario = :uid",
                {"uid": uid},
                fetchone=True
            )
            if not user_row:
                flash('Usuario no encontrado.', 'danger')
                return redirect(url_for('agregar_pedido'))
            user_nombre, user_email = user_row[0], user_row[1]
            # Validar que el usuario tenga email para crear/match con cliente
            if not user_email:
                flash('El usuario seleccionado no tiene email asociado; no se puede crear el pedido.', 'danger')
                return redirect(url_for('agregar_pedido'))

            # Buscar cliente por email
            client_row = run_query(
                "SELECT id_cliente FROM cliente WHERE email = :e",
                {"e": user_email},
                fetchone=True
            )
            if client_row:
                id_cliente = client_row[0]
            else:
                # Crear cliente a partir del usuario
                try:
                    run_query(
                        "INSERT INTO cliente (nombre, telefono, email, direccion) VALUES (:n, NULL, :e, NULL)",
                        {"n": user_nombre, "e": user_email},
                        commit=True
                    )
                    new_row = run_query(
                        "SELECT id_cliente FROM cliente WHERE email = :e ORDER BY id_cliente DESC LIMIT 1",
                        {"e": user_email},
                        fetchone=True
                    )
                    id_cliente = new_row[0] if new_row else None
                except Exception:
                    id_cliente = None

        else:
            # intentar mapear usuario a cliente por email
            # Primero asegurarnos que el usuario existe en usuario
            user_row = run_query("SELECT nombre, email FROM usuario WHERE username = :u", {"u": username}, fetchone=True)
            if not user_row:
                flash('Usuario en sesión no encontrado en la base de datos. Inicia sesión nuevamente o contacta al administrador.', 'danger')
                return redirect(url_for('login'))

            id_cliente_row = run_query(
                "SELECT c.id_cliente FROM cliente c JOIN usuario u ON u.email = c.email WHERE u.username = :u",
                {"u": username},
                fetchone=True
            )
            id_cliente = id_cliente_row[0] if id_cliente_row else None

            # Si no existe un cliente con el mismo email, crear uno a partir del usuario (si tiene email)
            if not id_cliente:
                user_nombre, user_email = user_row[0], user_row[1]
                if not user_email:
                    flash('Tu cuenta no tiene email asociado; no es posible crear el pedido. Contacta al administrador.', 'danger')
                    return redirect(url_for('agregar_pedido'))
                try:
                    run_query(
                        "INSERT INTO cliente (nombre, telefono, email, direccion) VALUES (:n, NULL, :e, NULL)",
                        {"n": user_nombre, "e": user_email},
                        commit=True
                    )
                    # recuperar id_cliente recién creado
                    new_row = run_query(
                        "SELECT id_cliente FROM cliente WHERE email = :e ORDER BY id_cliente DESC LIMIT 1",
                        {"e": user_email},
                        fetchone=True
                    )
                    id_cliente = new_row[0] if new_row else None
                except Exception:
                    id_cliente = None

        if not id_cliente:
            flash('No se pudo determinar el cliente asociado. Contacta al administrador.', 'danger')
            return redirect(url_for('agregar_pedido'))

        # Validar cantidad de articulos y calcular fecha_entrega automáticamente
        cantidad_str = request.form.get('cantidad_articulos') or '0'
        try:
            cantidad = int(cantidad_str)
            if cantidad <= 0:
                raise ValueError()
        except ValueError:
            flash('La cantidad de artículos debe ser un número entero positivo.', 'danger')
            return redirect(url_for('agregar_pedido'))

        # Regla: 1-5 artículos -> 3 días, 6-15 -> 5 días, >15 -> 7 días (ajustable)
        if cantidad <= 5:
            dias = 3
        elif cantidad <= 15:
            dias = 5
        else:
            dias = 7

        fecha_entrega_date = datetime.date.today() + datetime.timedelta(days=dias)
        fecha_entrega = fecha_entrega_date.isoformat()

        # Solo los administradores pueden fijar el estado del pedido
        if rol == 'administrador':
            estado = request.form.get('estado') or 'Pendiente'
        else:
            estado = 'Pendiente'

        # Insertar pedido (asumiendo columnas id_cliente, fecha_ingreso, fecha_entrega, estado)
        try:
            # Insertar pedido (la tabla pedido en el esquema contiene id_pedido, fecha_ingreso, fecha_entrega, estado, id_cliente)
            # Insertar pedido y obtener id_pedido de forma fiable
            id_pedido = run_query(
                "INSERT INTO pedido (id_cliente, fecha_ingreso, fecha_entrega, estado) VALUES (:id_cliente, NOW(), :fecha_entrega, :estado)",
                {"id_cliente": id_cliente, "fecha_entrega": fecha_entrega, "estado": estado},
                commit=True,
                get_lastrowid=True
            )

            # Insertar prendas asociadas si se enviaron desde el formulario
            tipos = request.form.getlist('tipo')
            descripciones = request.form.getlist('descripcion')
            observaciones = request.form.getlist('observaciones')

            if id_pedido and tipos:
                for i, t in enumerate(tipos):
                    t_val = (t or '').strip()
                    if not t_val:
                        continue
                    d_val = (descripciones[i] if i < len(descripciones) else '').strip()
                    o_val = (observaciones[i] if i < len(observaciones) else '').strip()
                    try:
                        run_query(
                            "INSERT INTO prenda (tipo, descripcion, observaciones, id_pedido) VALUES (:tipo, :desc, :obs, :id)",
                            {"tipo": t_val, "desc": d_val, "obs": o_val, "id": id_pedido},
                            commit=True
                        )
                    except Exception:
                        # No detener todo si una prenda falla; seguir con las demás
                        pass

            flash('Pedido creado correctamente.', 'success')
            if rol == 'administrador':
                return redirect(url_for('pedidos'))
            else:
                return redirect(url_for('cliente_pedidos'))
        except Exception as e:
            flash(f'Error al crear pedido: {e}', 'danger')
            return redirect(url_for('agregar_pedido'))

    # GET: mostrar formulario
    return render_template('agregar_pedido.html', clients=clients, rol=rol)

# -----------------------------------------------
# CLIENTES
# -----------------------------------------------
@app.route('/agregar_cliente', methods=['GET', 'POST'])
def agregar_cliente():
    """
    Crear un nuevo cliente como un usuario con rol 'cliente'.
    Campos esperados: nombre, username, email, password
    """
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not all([nombre, username, email, password]):
            flash('Completa nombre, username, email y contraseña.', 'warning')
            return redirect(url_for('agregar_cliente'))

        # Verificar que el username no exista y que el email no esté usado
        exists = run_query("SELECT id_usuario FROM usuario WHERE username = :u", {"u": username}, fetchone=True)
        if exists:
            flash('El nombre de usuario ya existe. Elige otro.', 'danger')
            return redirect(url_for('agregar_cliente'))
        exists_email = run_query("SELECT id_usuario FROM usuario WHERE email = :e", {"e": email}, fetchone=True)
        if exists_email:
            flash('El email ya está en uso por otro usuario.', 'danger')
            return redirect(url_for('agregar_cliente'))

        hashed = generate_password_hash(password)
        try:
            run_query(
                "INSERT INTO usuario (nombre, username, password, rol, email) VALUES (:n, :u, :p, :r, :e)",
                {"n": nombre, "u": username, "p": hashed, "r": 'cliente', "e": email},
                commit=True
            )
            flash('Cliente (usuario) creado exitosamente.', 'success')
            return redirect(url_for('clientes'))
        except Exception as e:
            flash(f'Error al crear usuario: {e}', 'danger')
            return redirect(url_for('agregar_cliente'))

    return render_template('agregar_cliente.html')


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
# ACTUALIZAR / ELIMINAR cliente
# -----------------------------------------------
@app.route('/actualizar_cliente/<int:id_cliente>', methods=['GET', 'POST'])
def actualizar_cliente(id_cliente):
    """
    Actualiza un cliente que en realidad está en la tabla usuario (id_cliente == id_usuario).
    """
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')  # opcional: si viene, actualizar

        if not nombre or not username or not email:
            flash('Nombre, username y email son obligatorios.', 'warning')
            return redirect(url_for('actualizar_cliente', id_cliente=id_cliente))

        try:
            # Evitar colisiones de username con otros usuarios
            existing = run_query("SELECT id_usuario FROM usuario WHERE username = :u AND id_usuario <> :id", {"u": username, "id": id_cliente}, fetchone=True)
            if existing:
                flash('El username ya está en uso por otro usuario.', 'danger')
                return redirect(url_for('actualizar_cliente', id_cliente=id_cliente))

            if password:
                hashed = generate_password_hash(password)
                run_query(
                    "UPDATE usuario SET nombre = :n, username = :u, email = :e, password = :p WHERE id_usuario = :id",
                    {"n": nombre, "u": username, "e": email, "p": hashed, "id": id_cliente},
                    commit=True
                )
            else:
                run_query(
                    "UPDATE usuario SET nombre = :n, username = :u, email = :e WHERE id_usuario = :id",
                    {"n": nombre, "u": username, "e": email, "id": id_cliente},
                    commit=True
                )

            flash('Cliente (usuario) actualizado correctamente.', 'success')
            return redirect(url_for('clientes'))
        except Exception as e:
            flash(f'Error al actualizar usuario: {e}', 'danger')
            return redirect(url_for('actualizar_cliente', id_cliente=id_cliente))

    # GET
    row = run_query("SELECT id_usuario, nombre, username, email FROM usuario WHERE id_usuario = :id", {"id": id_cliente}, fetchone=True)
    if not row:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('clientes'))
    return render_template('actualizar_cliente.html', id_cliente=row[0], nombre=row[1], username=row[2], email=row[3])


@app.route('/eliminar_cliente/<int:id_cliente>', methods=['POST'])
def eliminar_cliente(id_cliente):
    try:
        run_query("DELETE FROM usuario WHERE id_usuario = :id", {"id": id_cliente}, commit=True)
        flash('Usuario (cliente) eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar usuario: {e}', 'danger')
    return redirect(url_for('clientes'))


# -----------------------------------------------
# PEDIDOS
# -----------------------------------------------
@app.route('/pedidos', methods=['GET', 'POST'])
def pedidos():
    pedidos = run_query("""
        SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre 
        FROM pedido p
        LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
        ORDER BY p.id_pedido DESC
    """, fetchall=True)

    return render_template('pedidos.html', pedidos=pedidos)


@app.route('/eliminar_pedido/<int:id_pedido>', methods=['POST'])
def eliminar_pedido(id_pedido):
    """Eliminar un pedido (y sus prendas por FK)."""
    try:
        run_query("DELETE FROM pedido WHERE id_pedido = :id", {"id": id_pedido}, commit=True)
        flash('Pedido eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar pedido: {e}', 'danger')
    return redirect(url_for('pedidos'))


@app.route('/reportes')
def reportes():
    # Solo administradores (aceptar variantes como 'admin')
    rol = (session.get('rol') or '').strip().lower()
    allowed = {'administrador', 'admin', 'superadmin'}
    if rol not in allowed:
        flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
        return redirect(url_for('index'))

    # Búsqueda opcional por nombre (para usuarios)
    q = (request.args.get('q') or '').strip()
    if q:
        raw_users = run_query(
            "SELECT id_usuario, nombre, username, rol, email FROM usuario WHERE nombre LIKE :q ORDER BY id_usuario DESC",
            {"q": f"%{q}%"},
            fetchall=True
        ) or []
    else:
        raw_users = run_query("SELECT id_usuario, nombre, username, rol, email FROM usuario ORDER BY id_usuario DESC", fetchall=True) or []

    # Calcular pedidos_count y descuento acumulado por usuario (1% por pedido)
    usuarios = []
    for ru in raw_users:
        uid = ru[0]
        cnt_row = run_query(
            "SELECT COUNT(*) FROM pedido p JOIN cliente c ON p.id_cliente = c.id_cliente JOIN usuario u ON u.email = c.email WHERE u.id_usuario = :uid",
            {"uid": uid},
            fetchone=True
        )
        pedidos_count_user = int(cnt_row[0]) if cnt_row and cnt_row[0] is not None else 0
        descuento_acum = round(pedidos_count_user * 1.0, 2) if pedidos_count_user >= 1 else 0.0
        usuarios.append({
            'id': uid,
            'nombre': ru[1],
            'username': ru[2],
            'rol': ru[3],
            'email': ru[4],
            'pedidos_count': pedidos_count_user,
            'descuento': descuento_acum
        })

    # Pedidos: si se pasa user_id mostrar solo pedidos de ese usuario
    user_id = request.args.get('user_id')
    pedidos = []
    pedidos_owner = None
    if user_id:
        try:
            uid = int(user_id)
            # Obtener pedidos asociados al usuario (mediante cliente.email)
            pedidos = run_query(
                "SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, p.id_cliente "
                "FROM pedido p JOIN cliente c ON p.id_cliente = c.id_cliente JOIN usuario u ON u.email = c.email "
                "WHERE u.id_usuario = :uid ORDER BY p.id_pedido DESC",
                {"uid": uid},
                fetchall=True
            ) or []
            # Obtener nombre/username del usuario seleccionado
            usr = run_query("SELECT id_usuario, nombre, username FROM usuario WHERE id_usuario = :id", {"id": uid}, fetchone=True)
            if usr:
                pedidos_owner = {'id': usr[0], 'nombre': usr[1], 'username': usr[2]}
        except ValueError:
            pedidos = []
    else:
        pedidos = run_query("SELECT id_pedido, fecha_ingreso, fecha_entrega, estado, id_cliente FROM pedido ORDER BY id_pedido DESC", fetchall=True) or []

    # Promociones
    promociones = run_query("SELECT id_promocion, descripcion, descuento, fecha_inicio, fecha_fin FROM promocion ORDER BY id_promocion DESC", fetchall=True) or []

    return render_template('reportes.html', usuarios=usuarios, pedidos=pedidos, promociones=promociones, q=q, pedidos_owner=pedidos_owner)


# -----------------------------------------------
# DETALLES DE UN pedido
# -----------------------------------------------
@app.route('/pedido/<int:id_pedido>')
@app.route('/pedido_detalles/<int:id_pedido>')
def pedido_detalles(id_pedido):
    # Obtener pedido
    pedido = run_query(
        "SELECT id_pedido, fecha_ingreso, fecha_entrega, estado, id_cliente FROM pedido WHERE id_pedido = :id",
        {"id": id_pedido},
        fetchone=True
    )
    if not pedido:
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('pedidos'))

    # Obtener nombre del cliente
    cliente = run_query(
        "SELECT nombre FROM cliente WHERE id_cliente = :id",
        {"id": pedido[4]},
        fetchone=True
    )
    cliente_nombre = cliente[0] if cliente else 'Desconocido'

    # Obtener prendas asociadas
    prendas = run_query(
        "SELECT id_prenda, tipo, descripcion, observaciones FROM prenda WHERE id_pedido = :id",
        {"id": id_pedido},
        fetchall=True
    ) or []

    return render_template('pedido_detalles.html', pedido=pedido, cliente_nombre=cliente_nombre, prendas=prendas)


@app.route('/actualizar_pedido/<int:id_pedido>', methods=['POST'])
def actualizar_pedido(id_pedido):
    # Solo administradores pueden cambiar estado
    rol = (session.get('rol') or '').lower()
    if rol != 'administrador' and rol != 'admin':
        flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
        return redirect(url_for('pedido_detalles', id_pedido=id_pedido))

    nuevo_estado = request.form.get('estado')
    if not nuevo_estado:
        flash('Estado no proporcionado.', 'warning')
        return redirect(url_for('pedido_detalles', id_pedido=id_pedido))

    try:
        run_query("UPDATE pedido SET estado = :e WHERE id_pedido = :id", {"e": nuevo_estado, "id": id_pedido}, commit=True)

        # Si el pedido se marca como completado, generar recibo automáticamente (si no existe aún)
        if nuevo_estado.lower() in ('completado', 'finalizado', 'entregado'):
            # Verificar si ya existe recibo para este pedido
            existing = run_query("SELECT id_recibo FROM recibo WHERE id_pedido = :id", {"id": id_pedido}, fetchone=True)
            if not existing:
                # contar prendas
                cnt = run_query("SELECT COUNT(*) FROM prenda WHERE id_pedido = :id", {"id": id_pedido}, fetchone=True)
                prendas_count = int(cnt[0]) if cnt and cnt[0] is not None else 0

                # recuperar usuario (id_usuario) a partir del pedido -> cliente -> usuario
                usr = run_query(
                    "SELECT u.id_usuario FROM usuario u JOIN cliente c ON u.email = c.email JOIN pedido p ON p.id_cliente = c.id_cliente WHERE p.id_pedido = :id",
                    {"id": id_pedido},
                    fetchone=True
                )
                user_id_for_recibo = usr[0] if usr else None

                # calcular monto: precio por prenda * cantidad, aplicar descuento acumulado (1% por pedido del usuario)
                subtotal = prendas_count * PRICE_PER_PRENDA
                descuento_pct = 0.0
                if user_id_for_recibo:
                    cnt_row = run_query(
                        "SELECT COUNT(*) FROM pedido p JOIN cliente c ON p.id_cliente = c.id_cliente JOIN usuario u ON u.email = c.email WHERE u.id_usuario = :uid",
                        {"uid": user_id_for_recibo},
                        fetchone=True
                    )
                    pedidos_count_user = int(cnt_row[0]) if cnt_row and cnt_row[0] is not None else 0
                    if pedidos_count_user >= 1:
                        descuento_pct = pedidos_count_user * 1.0

                monto = subtotal * (1.0 - descuento_pct / 100.0)
                # insertar recibo
                try:
                    run_query(
                        "INSERT INTO recibo (id_pedido, id_cliente, monto, fecha) VALUES (:idp, :idc, :m, NOW())",
                        {"idp": id_pedido, "idc": user_id_for_recibo or 0, "m": round(monto,2)},
                        commit=True
                    )
                    flash('Recibo generado automáticamente al completar el pedido.', 'success')
                except Exception as e:
                    flash(f'Pedido actualizado, pero error al generar recibo: {e}', 'warning')
        else:
            flash('Estado del pedido actualizado.', 'success')

    except Exception as e:
        flash(f'Error al actualizar pedido: {e}', 'danger')

    return redirect(url_for('pedido_detalles', id_pedido=id_pedido))


# -----------------------------------------------
# EXPORTAR DATOS
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


def _admin_only():
    rol = (session.get('rol') or '').strip().lower()
    return rol in {'administrador', 'admin', 'superadmin'}


def _make_excel_response(data, columns, filename):
    output = BytesIO()
    df = pd.DataFrame(data, columns=columns)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=filename[:31])
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"{filename}.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


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
    app.run(debug=True, port=6969)
