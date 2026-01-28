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
    return render_template('cliente_inicio.html')


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
        SELECT r.id_recibo, r.id_pedido, r.monto, r.fecha
        FROM recibo r
        LEFT JOIN usuario u ON r.id_cliente = u.id_usuario
        WHERE u.username = :u
        ORDER BY r.fecha DESC
    """, {"u": username}, fetchall=True)
    
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
    
    # Obtener id_usuario del cliente
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE username = :u",
        {"u": username},
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
    # Usar username desde la sesión (más seguro)
    username = session.get('username')
    if not username:
        flash("No se pudo identificar al usuario.", "danger")
        return redirect(url_for('login'))
    
    # Obtener id_usuario
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE username = :u",
        {"u": username},
        fetchone=True
    )
    
    if not usuario:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('login'))
    
    id_usuario = usuario[0]

    # Obtener pedidos con conteo de prendas
    pedidos = run_query("""
        SELECT 
            p.id_pedido, 
            p.fecha_ingreso, 
            p.fecha_entrega, 
            p.estado,
            COUNT(pr.id_prenda) as total_prendas
        FROM pedido p
        LEFT JOIN prenda pr ON p.id_pedido = pr.id_pedido
        WHERE p.id_cliente = :id
        GROUP BY p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado
        ORDER BY p.fecha_ingreso DESC
    """, {"id": id_usuario}, fetchall=True)
    
    # Estadísticas del cliente
    stats = {
        'total_pedidos': len(pedidos),
        'pendientes': sum(1 for p in pedidos if p[3] == 'Pendiente'),
        'en_proceso': sum(1 for p in pedidos if p[3] == 'En proceso'),
        'completados': sum(1 for p in pedidos if p[3] == 'Completado')
    }

    return render_template('cliente_pedidos.html', 
                         pedidos=pedidos, 
                         username=username,
                         stats=stats)


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

    if not tipo:
        flash('El campo tipo es obligatorio.', 'warning')
        return redirect(url_for('pedido_detalles', id_pedido=id_pedido))

    try:
        run_query(
            "INSERT INTO prenda (tipo, id_pedido) VALUES (:tipo, :id)",
            {"tipo": tipo, "id": id_pedido},
            commit=True
        )
        flash('Prenda agregada correctamente.', 'success')
    except Exception as e:
        flash(f'Error al agregar prenda: {e}', 'danger')

    return redirect(url_for('pedido_detalles', id_pedido=id_pedido))


# -----------------------------------------------
# REPORTES
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
                         promedio_prendas=round(float(promedio_prendas), 2))


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
        "SELECT rol FROM usuario WHERE username = :u",
        {"u": username},
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
            
            # Obtener id_cliente
            if rol == 'administrador':
                id_cliente = request.form.get('id_cliente')
            else:
                # Buscar el id_usuario que actúa como id_cliente
                cliente_data = run_query(
                    "SELECT id_usuario FROM usuario WHERE username = :u",
                    {"u": username},
                    fetchone=True
                )
                if not cliente_data:
                    flash('No se encontró tu usuario en el sistema.', 'danger')
                    return redirect(url_for('cliente_inicio'))
                id_cliente = cliente_data[0]
            
            # Garantizar que existe el cliente antes de crear el pedido
            ensure_cliente_exists(id_cliente)
            
            # Procesar las prendas del formulario
            tipos = request.form.getlist('tipo[]')
            cantidades = request.form.getlist('cantidad[]')
            descripciones = request.form.getlist('descripcion[]')
            
            if not tipos or not cantidades:
                flash('Debes agregar al menos una prenda al pedido.', 'warning')
                return redirect(url_for('agregar_pedido'))
            
            # Calcular total de prendas y fecha de entrega
            total_prendas = sum(int(c) for c in cantidades if c)
            dias_entrega = 3 if total_prendas <= 5 else (5 if total_prendas <= 15 else 7)
            
            fecha_ingreso = datetime.now().strftime('%Y-%m-%d')
            fecha_entrega = (datetime.now() + timedelta(days=dias_entrega)).strftime('%Y-%m-%d')
            
            # Crear el pedido
            result = run_query(
                "INSERT INTO pedido (fecha_ingreso, fecha_entrega, estado, id_cliente) VALUES (:fi, :fe, :e, :ic) RETURNING id_pedido",
                {
                    "fi": fecha_ingreso,
                    "fe": fecha_entrega,
                    "e": "Pendiente",
                    "ic": id_cliente
                },
                commit=True,
                fetchone=True
            )
            
            id_pedido = result[0] if result else None
            
            if not id_pedido:
                flash('Error al crear el pedido.', 'danger')
                return redirect(url_for('agregar_pedido'))
            
            # Insertar las prendas
            total_costo = 0
            try:
                for i, tipo in enumerate(tipos):
                    if tipo and i < len(cantidades):
                        cantidad = int(cantidades[i]) if cantidades[i] else 1
                        descripcion = descripciones[i] if i < len(descripciones) else ''
                        
                        # Calcular costo (usar precios de prendas_default)
                        precio_prenda = 5000  # precio por defecto
                        for prenda in prendas_default:
                            if prenda['nombre'] == tipo:
                                precio_prenda = prenda['precio']
                                break
                        
                        total_costo += precio_prenda * cantidad
                        
                        # Insertar cada prenda según la cantidad
                        for _ in range(cantidad):
                            run_query(
                                "INSERT INTO prenda (tipo, descripcion, observaciones, id_pedido) VALUES (:t, :d, :o, :ip)",
                                {
                                    "t": tipo,
                                    "d": descripcion or '',
                                    "o": '',
                                    "ip": id_pedido
                                },
                                commit=True
                            )
            except Exception as e:
                print(f"ERROR al insertar prendas: {e}")
                flash(f'Error al insertar prendas: {str(e)}', 'danger')
                raise
            
            # Crear recibo automáticamente
            try:
                run_query(
                    "INSERT INTO recibo (id_pedido, id_cliente, monto, fecha) VALUES (:ip, :ic, :m, :f)",
                    {
                        "ip": id_pedido,
                        "ic": id_cliente,
                        "m": total_costo,
                        "f": fecha_ingreso
                    },
                    commit=True
                )
            except Exception as e:
                print(f"ERROR al crear recibo: {e}")
            
            flash(f'¡Pedido creado exitosamente! Total: {total_prendas} prendas. Entrega estimada: {fecha_entrega}', 'success')
            
            # Redirigir según el rol
            if rol == 'administrador':
                return redirect(url_for('pedidos'))
            else:
                return redirect(url_for('cliente_pedidos'))
                
        except Exception as e:
            flash(f'Error al crear pedido: {e}', 'danger')
    
    clientes = run_query(
        "SELECT id_cliente, nombre FROM cliente ORDER BY nombre",
        fetchall=True
    )
    
    return render_template('agregar_pedido.html', 
                         clientes=clientes, 
                         rol=rol,
                         prendas_default=prendas_default)


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
