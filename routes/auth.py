"""
Blueprint de autenticación
Maneja registro, login y logout de usuarios
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import run_query
from services import limpiar_texto, validar_email, validar_contrasena, send_email_async
from decorators import login_requerido

bp = Blueprint('auth', __name__)


@bp.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login de usuarios"""
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
            return redirect(url_for('auth.login'))

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
                return redirect(url_for('admin.inicio'))
            else:
                return redirect(url_for('cliente.cliente_inicio'))
        else:
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template('login.html')


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    """Registro de nuevos usuarios"""
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
                print(f"[MAIL] Enviando correo de bienvenida registro a {email}", flush=True)
                send_email_async(email, "Bienvenido a La Lavanderia", html_bienvenida)
                print(f"[MAIL] Disparo de correo registro OK para {email}", flush=True)

            flash("¡Registro exitoso! Ya puedes iniciar sesión.", "success")
            return redirect(url_for("auth.login"))

        except Exception as e:
            print(f"Error en registro: {e}")
            flash("Error al registrar. Por favor intenta de nuevo.", "danger")
            return render_template("registro.html", form_data=form_data)

    return render_template("registro.html", form_data=form_data)


@bp.route('/logout')
@login_requerido
def logout():
    """Cerrar sesión"""
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("auth.login"))
