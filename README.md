# La Lavandería - Sistema de Gestión

Sistema completo de gestión para lavandería con programa de descuentos por lealtad, servicio a domicilio y gestión de pedidos.

## 🚀 Inicio Rápido

### 1. Instalación Local

```bash
# Clonar el repositorio
git clone https://github.com/Fabianxxo27/La-Lavanderia.git
cd La-Lavanderia

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Edita .env con tus credenciales

# Ejecutar migraciones
python ejecutar_migraciones.py

# Iniciar aplicación
python app.py
```

### 2. Desplegar en Render

1. Conecta tu repositorio de GitHub a Render
2. Configura las variables de entorno (ver sección Configuración)
3. Render desplegará automáticamente
4. Ejecuta migraciones desde el panel admin: `/admin/configurar-descuentos`

---

## ⚙️ Configuración

### Variables de Entorno Requeridas

#### Base de Datos
```env
DATABASE_URL=postgresql://usuario:pass@host:5432/database
```

#### Seguridad
```env
SECRET_KEY=tu_clave_secreta_aleatoria
```

#### Correo (Gmail)
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tucorreo@gmail.com
SMTP_PASSWORD=tu_app_password_16_caracteres
```

---

## 📧 Configurar Correo Gmail

### Paso 1: Activar Verificación en 2 Pasos
1. Ve a https://myaccount.google.com/security
2. Habilita **Verificación en dos pasos**

### Paso 2: Crear App Password
1. En la misma página de seguridad, busca **Contraseñas de aplicaciones**
2. Selecciona **Correo** → **Otro (nombre personalizado)**
3. Escribe: **"La Lavandería App"**
4. **Copia los 16 caracteres** que aparecen (sin espacios)

### Paso 3: Configurar en Render
1. Ve a tu servicio en Render → **Environment**
2. Agrega las variables:
   - `SMTP_SERVER` = `smtp.gmail.com`
   - `SMTP_PORT` = `587`
   - `SMTP_USER` = tu correo completo
   - `SMTP_PASSWORD` = los 16 caracteres copiados
3. Guarda y Render reiniciará automáticamente

**Prueba:** Registra un usuario nuevo → Debe llegar correo de bienvenida

---

## 🗄️ Migraciones de Base de Datos

Las migraciones se ejecutan automáticamente desde el panel admin:

1. Ingresa como administrador
2. Ve a `/admin/configurar-descuentos`
3. Haz clic en **"Ejecutar migraciones ahora"**

Esto crea:
- Columnas de dirección en pedidos (servicio a domicilio)
- Tabla de configuración de descuentos

**Alternativa manual:** Ejecuta `python ejecutar_migraciones.py` desde terminal

---

## ✨ Características

### Para Clientes
- ✅ Registro y login
- ✅ Crear pedidos con múltiples prendas
- ✅ Servicio a domicilio (dirección de recogida y entrega)
- ✅ Ver historial de pedidos y recibos
- ✅ Programa de descuentos por lealtad (Bronce → Platino)
- ✅ Notificaciones por correo (registro, pedidos, cambios de estado)

### Para Administradores
- ✅ Gestión completa de clientes
- ✅ Gestión de pedidos
- ✅ Configurar niveles de descuento dinámicos
- ✅ Reportes en PDF y Excel
- ✅ Registro rápido de clientes
- ✅ Calendario de pedidos
- ✅ Códigos de barras para pedidos

---

## 📋 Estructura del Proyecto

```
La-Lavanderia/
├── app.py                      # Aplicación principal Flask
├── credentials.py              # Credenciales locales (no en producción)
├── ejecutar_migraciones.py     # Script automático de migraciones
├── requirements.txt            # Dependencias Python
├── .env.example               # Plantilla de variables de entorno
├── migrations/                # Scripts SQL de migración
│   ├── add_direcciones_to_pedido.sql
│   └── create_descuento_config.sql
├── static/                    # Archivos estáticos (CSS, imágenes)
└── templates/                 # Plantillas HTML Jinja2
```

---

## 🔧 Solución de Problemas

### Error: "tabla descuento_config no existe"
**Solución:** Ejecuta las migraciones desde `/admin/configurar-descuentos`

### Error: "Los correos no llegan"
**Solución:** 
1. Verifica que usas App Password (16 caracteres), NO tu contraseña de Gmail
2. Confirma puerto `587` y servidor `smtp.gmail.com`
3. Revisa la carpeta de SPAM
4. Genera una nueva App Password si persiste el error

### Error: "Modal de registro rápido no abre"
**Solución:** Verifica que Bootstrap 5 esté cargado correctamente

---

## 📚 Tecnologías

- **Backend:** Flask 2.2.5, SQLAlchemy 2.0.43, PostgreSQL
- **Frontend:** Bootstrap 5, Jinja2
- **Email:** SMTP (Gmail)
- **Exportación:** ReportLab (PDF), Pandas + OpenPyXL (Excel)
- **Códigos:** python-barcode, pyzbar
- **Deployment:** Render

---

## 👥 Roles de Usuario

### Administrador
- Acceso completo al sistema
- Gestión de clientes y pedidos
- Configuración de descuentos
- Reportes y estadísticas

### Cliente
- Ver y crear pedidos
- Historial personal
- Recibos y promociones
- Seguimiento de nivel de lealtad

---

## 📞 Soporte

Para consultas técnicas o problemas con el sistema:
- **Email:** soporte@lalavanderia.com
- **GitHub Issues:** https://github.com/Fabianxxo27/La-Lavanderia/issues

---

## 📄 Licencia

© 2024 La Lavandería. Todos los derechos reservados.
