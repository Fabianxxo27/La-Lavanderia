"""
Blueprint de autenticación
Maneja registro, login y logout de usuarios
"""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from models import run_query
from services import limpiar_texto, validar_email, validar_contrasena, send_email_async
from decorators import login_requerido

bp = Blueprint('auth', __name__)


def _get_reset_secret_key():
    """Clave estable para firmar enlaces de reset entre reinicios de la app."""
    # Recomendado: configurar PASSWORD_RESET_SECRET en Render.
    # Fallback razonable: SECRET_KEY del entorno.
    # Ultimo fallback: SENDGRID_API_KEY (estable si no existe SECRET_KEY en env).
    return (
        os.getenv('PASSWORD_RESET_SECRET')
        or os.getenv('SECRET_KEY')
        or os.getenv('SENDGRID_API_KEY')
        or current_app.config['SECRET_KEY']
    )


def _crear_token_reset_fallback(email):
    """Genera token firmado sin depender de BD."""
    serializer = URLSafeTimedSerializer(_get_reset_secret_key())
    return serializer.dumps(email, salt='password-reset')


def _validar_token_reset_fallback(token, max_age=1800):
    """Valida token firmado generado con itsdangerous."""
    serializer = URLSafeTimedSerializer(_get_reset_secret_key())
    try:
        return serializer.loads(token, salt='password-reset', max_age=max_age)
    except SignatureExpired:
        return None
    except BadSignature:
        return None


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


@bp.route('/olvide-contrasena', methods=['GET', 'POST'])
def olvide_contrasena():
    """Solicitar enlace de restablecimiento de contraseña"""
    if request.method == 'POST':
        email = limpiar_texto(request.form.get('email', '').strip().lower(), 120)

        if not email or not validar_email(email):
            flash('Ingresa un correo electrónico válido.', 'danger')
            return render_template('olvide_contrasena.html')

        # Buscar usuario — siempre mostrar el mismo mensaje para evitar enumerar correos
        usuario = run_query(
            "SELECT id_usuario, username FROM usuario WHERE LOWER(email) = :e",
            {"e": email},
            fetchone=True
        )

        if usuario:
            token = None

            # Flujo principal: token persistido en BD
            try:
                from services.verification_service import generar_token_reset
                token = generar_token_reset(email)
                if token:
                    print(f"[RESET] Token BD generado para {email}", flush=True)
                else:
                    print(f"[RESET][WARN] Token BD no generado para {email}, usando fallback firmado", flush=True)
            except Exception as token_error:
                print(f"[RESET][WARN] Error token BD para {email}: {token_error}", flush=True)

            # Fallback: token firmado (independiente de migraciones/tabla)
            if not token:
                token = _crear_token_reset_fallback(email)
                print(f"[RESET] Token fallback generado para {email}", flush=True)

            if token:
                nombre = usuario[1] if usuario[1] else 'Usuario'
                link = url_for('auth.restablecer_contrasena', token=token, _external=True)
                html = f"""
                <!DOCTYPE html>
                <html lang="es">
                <head><meta charset="UTF-8"></head>
                <body style="margin:0;padding:0;background:#f4f6f0;font-family:Arial,sans-serif;">
                  <table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f4f6f0">
                    <tr><td align="center" style="padding:40px 0;">
                      <table width="520" cellpadding="0" cellspacing="0" border="0"
                             style="background:#ffffff;border-radius:12px;overflow:hidden;
                                    box-shadow:0 4px 16px rgba(0,0,0,0.08);">
                        <!-- Header -->
                        <tr>
                          <td align="center" style="background:linear-gradient(135deg,#a6cc48,#84af1d);
                              padding:30px 20px;">
                            <h1 style="color:#1a4e7b;margin:0;font-size:26px;font-weight:700;
                                letter-spacing:0.5px;">La Lavandería</h1>
                            <p style="color:#3a5c1a;margin:6px 0 0;font-size:13px;">
                              Restablecimiento de contraseña</p>
                          </td>
                        </tr>
                        <!-- Body -->
                        <tr>
                          <td style="padding:36px 36px 28px;">
                            <p style="font-size:16px;color:#222;margin:0 0 12px;">Hola, <strong>{nombre}</strong>.</p>
                            <p style="font-size:15px;color:#444;margin:0 0 28px;line-height:1.6;">
                              Recibimos una solicitud para restablecer la contraseña de tu cuenta.
                              Haz clic en el botón de abajo para crear una nueva.
                            </p>
                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                              <tr>
                                <td align="center" style="padding-bottom:28px;">
                                  <a href="{link}"
                                     style="display:inline-block;padding:14px 36px;
                                            background:#1a4e7b;color:#ffffff;
                                            text-decoration:none;border-radius:8px;
                                            font-size:16px;font-weight:700;
                                            letter-spacing:0.3px;">
                                    Restablecer contraseña
                                  </a>
                                </td>
                              </tr>
                            </table>
                            <!-- Warning box -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                              <tr>
                                <td style="background:#fff8e1;border:1px solid #f0c040;
                                    border-radius:8px;padding:14px 18px;">
                                  <p style="margin:0;font-size:13px;color:#7a5c00;">
                                    <strong>Aviso:</strong> Este enlace es válido por
                                    <strong>30 minutos</strong>. Si no solicitaste este cambio,
                                    puedes ignorar este correo.
                                  </p>
                                </td>
                              </tr>
                            </table>
                            <!-- Fallback link -->
                            <p style="font-size:12px;color:#888;margin:24px 0 0;word-break:break-all;">
                              Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
                              <a href="{link}" style="color:#1a4e7b;">{link}</a>
                            </p>
                          </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                          <td align="center"
                              style="background:#1a4e7b;padding:20px;color:#ffffff;
                                     font-size:12px;">
                            &copy; La Lavandería — todos los derechos reservados
                          </td>
                        </tr>
                      </table>
                    </td></tr>
                  </table>
                </body>
                </html>
                """
                send_email_async(
                    destinatario=email,
                    asunto='Restablece tu contraseña — La Lavandería',
                    cuerpo_html=html
                )
                print(f"[RESET] Disparo correo recuperacion a {email}", flush=True)

        # Siempre el mismo mensaje (no revelar si el correo existe)
        flash(
            'Si ese correo está registrado, recibirás un enlace en los próximos minutos.',
            'success'
        )
        return redirect(url_for('auth.login'))

    return render_template('olvide_contrasena.html')


@bp.route('/restablecer-contrasena', methods=['GET', 'POST'])
def restablecer_contrasena():
    """Restablecer contraseña usando el token del enlace"""
    token = request.values.get('token', '').strip()

    if not token:
        flash('Enlace inválido o expirado.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if password != password2:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('restablecer_contrasena.html', token=token)

        valida, mensaje = validar_contrasena(password)
        if not valida:
            flash(mensaje, 'danger')
            return render_template('restablecer_contrasena.html', token=token)

        email = None

        # Intentar primero validación de token en BD
        try:
            from services.verification_service import validar_token_reset
            email = validar_token_reset(token)
        except Exception as token_error:
            print(f"[RESET][WARN] Error validando token BD: {token_error}", flush=True)

        # Si no existe token BD válido, intentar token firmado
        if not email:
            email = _validar_token_reset_fallback(token)

        if not email:
            flash('El enlace ya expiró o no es válido. Solicita uno nuevo.', 'danger')
            return redirect(url_for('auth.olvide_contrasena'))

        usuario_actual = run_query(
            "SELECT id_usuario, password FROM usuario WHERE LOWER(email) = :e",
            {"e": email.lower()},
            fetchone=True
        )

        if not usuario_actual:
            flash('No fue posible encontrar la cuenta asociada a este enlace.', 'danger')
            return redirect(url_for('auth.olvide_contrasena'))

        try:
            if check_password_hash(usuario_actual[1], password):
                flash('La nueva contraseña debe ser diferente a la actual.', 'danger')
                return render_template('restablecer_contrasena.html', token=token)
        except (ValueError, TypeError):
            flash('No fue posible validar la contraseña actual. Intenta nuevamente.', 'danger')
            return redirect(url_for('auth.olvide_contrasena'))

        hashed = generate_password_hash(password)
        updated_user = run_query(
            "UPDATE usuario SET password = :p WHERE LOWER(email) = :e RETURNING id_usuario",
            {"p": hashed, "e": email.lower()},
            commit=True,
            fetchone=True
        )

        if not updated_user:
            flash('No fue posible actualizar la contraseña. Intenta nuevamente.', 'danger')
            return redirect(url_for('auth.olvide_contrasena'))

        flash('Contraseña actualizada correctamente. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('restablecer_contrasena.html', token=token)


@bp.route('/logout')
@login_requerido
def logout():
    """Cerrar sesión"""
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("auth.login"))
