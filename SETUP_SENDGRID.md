# Configuración de SendGrid para Verificación de Correos

## 1. Crear Cuenta en SendGrid

1. Ir a [SendGrid.com](https://sendgrid.com)
2. Registrarse (plan gratuito: 100 emails/día, suficiente para desarrollo)
3. Verificar el email de confirmación

## 2. Obtener API Key

1. Desde el Dashboard, ir a **Settings > API Keys**
2. Click en **Create API Key**
3. Nombre: `LaLavanderia_Flask` (o similar)
4. Permissions: **Restricted Access**
5. Marcar solo: `Mail Send`
6. Copiar la API Key (aparece una sola vez)

## 3. Verificar Email del Remitente

1. Ir a **Settings > Sender Authentication**
2. Click en **Verify a Single Sender**
3. Ingresar los datos:
   - From Email: `noreply@tudominio.com` (o `tu-email@gmail.com` para testing)
   - From Name: `La Lavandería`
4. Verificar el email siguiendo el link enviado

## 4. Variables de Entorno (en Render o .env local)

```bash
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@lalavanderia.com
```

Para desarrollo local, agregar a `.env`:
```
SENDGRID_API_KEY=tu_api_key_aqui
SENDGRID_FROM_EMAIL=tu-email-verificado@gmail.com
```

## 5. Ejecutar Migración en la Base de Datos

```bash
# Conectarse a PostgreSQL y ejecutar:
psql -U usuario -d base_datos -f migrations/create_verification_codes.sql
```

O desde Python:
```python
from app import app, db

with app.app_context():
    db.create_all()
```

## 6. Uso en el Código

### Registrar usuario con verificación:

```python
from services.verification_service import enviar_email_verificacion

@app.route('/registro', methods=['POST'])
def registro():
    email = request.form.get('email')
    nombre = request.form.get('nombre')
    
    # ... crear usuario ...
    
    # Enviar email de verificación
    enviar_email_verificacion(email, nombre)
    
    return redirect(url_for('verificar_email', email=email))
```

### Página de verificación:

```python
@app.route('/verificar-email', methods=['GET', 'POST'])
def verificar_email():
    email = request.args.get('email')
    
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        
        from services.verification_service import VerificationCode
        if VerificationCode.validar_codigo(email, codigo, 'email_verification'):
            # Actualizar usuario como verificado
            # UPDATE usuario SET email_verificado = TRUE WHERE email = email
            flash('¡Email verificado exitosamente!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Código inválido o expirado', 'error')
    
    return render_template('verificar_email.html', email=email)
```

### Resetear contraseña:

```python
from services.verification_service import enviar_email_reseteo_contrasena

@app.route('/olvide-contrasena', methods=['POST'])
def olvide_contrasena():
    email = request.form.get('email')
    usuario = # ... buscar usuario ...
    
    if usuario:
        enviar_email_reseteo_contrasena(email, usuario.nombre)
        flash('Te enviamos un código al email', 'success')
        return redirect(url_for('resetear_contrasena', email=email))
```

## 7. Monitorear Actividad

Dashboard de SendGrid:
- **Stats > Last 24 Hours**: Ver emails enviados/abiertos/clicks
- **Mail Settings > Event Notification**: Webhooks para eventos
- **Suppressions**: Ver bounces, spam complaints, etc.

## 8. Pruebas Locales

```bash
# Instalar paquete
pip install sendgrid

# Test en consola python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
message = Mail(
    from_email='tu-email@gmail.com',
    to_emails='destinatario@ejemplo.com',
    subject='Test',
    html_content='<p>Test</p>'
)
response = sg.send(message)
print(response.status_code)  # Debe ser 202
```

## 9. Troubleshooting

| Problema | Solución |
|----------|----------|
| `401 Unauthorized` | API Key incorreta o expirada |
| `403 Forbidden` | Email remitente no verificado |
| `400 Bad Request` | Email destinatario inválido |
| `429 Too Many Requests` | Excediste límite de rate (con api key gratuita) |

