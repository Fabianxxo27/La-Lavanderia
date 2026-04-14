# La Lavandería - Sistema de Gestión

Un sistema web completo para gestionar una lavandería: clientes, pedidos, descuentos por lealtad, reportes y notificaciones por correo electrónico.

**Este README está escrito paso a paso para que cualquiera pueda levantar el proyecto, incluso sin experiencia previa.**

---

## Tabla de Contenidos

1. [¿Qué hace este sistema?](#qué-hace-este-sistema)
2. [Requisitos antes de empezar](#requisitos-antes-de-empezar)
3. [Instalación paso a paso](#instalación-paso-a-paso)
4. [Configuración del archivo .env](#configuración-del-archivo-env)
5. [Ejecutar localmente](#ejecutar-localmente)
6. [Desplegar en Render (Producción)](#desplegar-en-render-producción)
7. [Migraciones de base de datos](#migraciones-de-base-de-datos)
8. [Solución de problemas (Errores comunes)](#solución-de-problemas)
9. [Estructura del proyecto](#estructura-del-proyecto)
10. [Variables de entorno documentadas](#variables-de-entorno-documentadas)

---

## ¿Qué hace este sistema?

Este es un **panel de control para una lavandería** que incluye:

- [x] **Registro e inicio de sesión** para clientes y administradores
- [x] **Panel de administrador** para gestionar clientes y pedidos
- [x] **Sistema de descuentos por lealtad** (cuantos más pedidos, más descuento)
- [x] **Generación de reportes** en PDF y Excel
- [x] **Códigos de barras** para tracking de pedidos
- [x] **Notificaciones automáticas por correo** (bienvenida, cambios de estado, etc.)
- [x] **Portal del cliente** para ver sus pedidos, descuentos y recibos

---

## Requisitos antes de empezar

Antes de instalar nada, asegúrate de tener:

### 1. **Python 3.10 o superior** (obligatorio)
Descárgalo desde: https://www.python.org/downloads/

Para verificar si lo tienes:
```bash
python --version
```

Debería decirte algo como: `Python 3.10.0` o superior.

### 2. **PostgreSQL** (para la base de datos)

**Opción A: Si quieres usar una BD local en tu computadora**
- Descarga PostgreSQL desde: https://www.postgresql.org/download/

**Opción B: Si quieres usar una BD remota (recomendado para producción)**
- Usa Render.com (incluido en el plan gratuito)
- Te genera una URL lista: `postgresql://usuario:password@host:5432/basedatos`

### 3. **Git** (para clonar el repositorio)
Descárgalo desde: https://git-scm.com/

Para verificar:
```bash
git --version
```

### 4. **Un editor de código** (recomendado)
- Visual Studio Code: https://code.visualstudio.com/
- PyCharm Community: https://www.jetbrains.com/pycharm/

---

## Instalación paso a paso

### **PASO 1: Clonar el repositorio**

Abre tu terminal/PowerShell y ejecuta:

```bash
git clone https://github.com/Fabianxxo27/La-Lavanderia.git
cd La-Lavanderia
```

Esto descarga todo el código a tu computadora. Deberías ver una carpeta llamada `La-Lavanderia`.

### **PASO 2: Crear un entorno virtual**

Un **entorno virtual** es como una "caja sellada" con las librerías que tu proyecto necesita, para que no conflicte con otros proyectos.

**En Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**En Mac o Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Si funciona correctamente, verás `(.venv)` al inicio de tu terminal.

### **PASO 3: Instalar las dependencias**

Las dependencias son librerías de Python que el proyecto necesita. Están listadas en `requirements.txt`.

```bash
pip install -r requirements.txt
```

Esto tardará 1-2 minutos. Verás mucho texto en la pantalla, es normal.

### **PASO 4: Crear el archivo `.env`**

El archivo `.env` contiene información sensible (contraseñas, claves secretas, URLs, etc.). **Nunca** lo subas a GitHub.

- Copia el archivo `.env.example` y llámalo `.env`

**En Windows (PowerShell):**
```powershell
Copy-Item ".env.example" ".env"
```

**En Mac o Linux:**
```bash
cp .env.example .env
```

---

## Configuración del archivo `.env`

Abre el archivo `.env` en tu editor de código. Verás algo así:

```env
# Clave secreta para manejar sesiones
SECRET_KEY=tu_clave_secreta_aqui

# Base de datos
DATABASE_URL=postgresql://usuario:password@localhost:5432/lavanderia

# Email (SendGrid para producción en Render)
SENDGRID_API_KEY=tu_api_key_aqui
SENDGRID_FROM_EMAIL=lalavanderiabogota@gmail.com

# Puerto
PORT=5000
```

### **Explicación de cada variable:**

#### 1. **SECRET_KEY**
Es una clave que Flask usa para manejar sesiones de usuarios (login).

Reemplaza `tu_clave_secreta_aqui` con algo largo y aleatorio, por ejemplo:
```env
SECRET_KEY=asldfk123iusd_23i1u3j_1u3j1@#$%^&*()_+
```

#### 2. **DATABASE_URL**

Es la dirección de tu base de datos PostgreSQL. El formato es:
```
postgresql://usuario:password@host:puerto/nombre_base_datos
```

**Ejemplo para BD local:**
```env
DATABASE_URL=postgresql://postgres:123456@localhost:5432/lavanderia
```

**Ejemplo para BD en Render** (lo configuraremos después):
```env
DATABASE_URL=postgresql://usuario:contraseña@dpg-abc123.postgres.render.com:5432/basedatos
```

#### 3. **SENDGRID_API_KEY**

Para enviar correos de bienvenida, cambios de pedido, etc. necesitas una API key de SendGrid.

**Cómo obtenerla:**
1. Ve a https://sendgrid.com/
2. Crea una cuenta (plan gratuito)
3. Ve a Settings → API Keys → Create API Key
4. Copia la clave y pégala aquí

```env
SENDGRID_API_KEY=SG.1234567890abcdefghijklmnop_xyz
```

#### 4. **SENDGRID_FROM_EMAIL**

Es el correo "desde" donde se envían los emails. Debe estar verificado en SendGrid.

```env
SENDGRID_FROM_EMAIL=lalavanderiabogota@gmail.com
```

#### 5. **PORT**

El puerto donde corre la app. Déjalo en 5000 para desarrollo local.

```env
PORT=5000
```

---

## Ejecutar localmente

Una vez configurado todo, ejecuta:

```bash
python app.py
```

Deberías ver algo así:
```
WARNING in app.run() is not intended for production, use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
```

Abre tu navegador y ve a:
```
http://127.0.0.1:5000
```

¡Listo! Ya deberías ver la página de inicio de La Lavandería.

### **Para detener la app:**
Presiona `Ctrl + C` en la terminal.

---

## Desplegar en Render (Producción)

Render.com permite ejecutar tu app de forma **gratuita** en la nube. Aquí están los pasos detallados:

### **PASO 1: Crear una cuenta en Render**

1. Ve a https://render.com
2. Haz clic en "Sign Up"
3. Crea cuenta con GitHub (recomendado)

### **PASO 2: Subir tu código a GitHub**

Tu repositorio debe estar en GitHub para que Render lo vea.

```bash
git add .
git commit -m "Deploy a Render"
git push origin main
```

### **PASO 3: Crear una BD PostgreSQL en Render**

1. En el dashboard de Render, ve a **PostgreSQL**
2. Click en **+ New**
3. Llena los datos:
   - Name: `lavanderia-db`
   - Database: `lavanderia`
4. Click **Create Database**

Render te dará una URL tipo:
```
postgresql://user:password@dpg-abc123.postgres.render.com:5432/lavanderia
```

**Guarda esta URL, la necesitarás.**

### **PASO 4: Crear el servicio web en Render**

1. En el dashboard, ve a **Web Services**
2. Click en **+ New** → **Web Service**
3. Conecta tu repositorio GitHub
4. Llena los datos:
   - Name: `la-lavanderia`
   - Root Directory: (déjalo vacío)
   - Environment: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `waitress-serve --listen=0.0.0.0:$PORT --threads=4 wsgi:app`

### **PASO 5: Configura las variables de entorno en Render**

1. En la página del servicio web, ve a **Environment**
2. Agrega estas variables:

| Variable | Valor |
|----------|-------|
| `SECRET_KEY` | Una clave aleatoria larga (ej: `asldfk123iusd_23i1u3j...`) |
| `DATABASE_URL` | La URL que Render te dio en PASO 3 |
| `SENDGRID_API_KEY` | Tu API key de SendGrid |
| `SENDGRID_FROM_EMAIL` | Tu correo verificado en SendGrid |
| `PYTHONUNBUFFERED` | `1` (para ver logs en tiempo real) |

3. Click **Save**

### **PASO 6: Deploy**

Render debería empezar a hacer deploy automáticamente. Verás un log mostrando el progreso.

Una vez termine, tu app estará disponible en una URL como:
```
https://la-lavanderia.onrender.com
```

---

## Migraciones de base de datos

Las **migraciones** hacen cambios a la base de datos (agregar tablas, columnas, etc.). Este proyecto necesita ejecutar migraciones para funcionar correctamente.

### **Opción A: Desde el panel admin (Recomendado)**

1. Inicia sesión como **administrador**
2. Ve a `/admin/configurar-descuentos`
3. Haz clic en el botón **"Ejecutar migraciones"**

Listo, se ejecutarán automáticamente.

### **Opción B: Desde la terminal**

```bash
python scripts/ejecutar_migracion.py migrations/create_verification_codes.sql
```

O ejecutar todas a la vez:
```bash
python scripts/ejecutar_migracion.py
```

---

## Solución de problemas

### **Error: "ModuleNotFoundError: No module named 'flask'"**

Significa que no instalaste las dependencias. Ejecuta:
```bash
pip install -r requirements.txt
```

---

### **Error: "could not connect to server: Connection refused"**

Tu base de datos no está corriendo o la URL es incorrecta.

**Si usas BD local:**
1. Asegúrate de que PostgreSQL está ejecutándose
2. Verifica que `DATABASE_URL` en `.env` está bien escrito
3. Prueba con: `psql -U postgres` (en terminal)

**Si usas BD en Render:**
1. Verifica que copiaste bien la URL
2. Espera 5-10 segundos a que la BD esté lista
3. Intenta nuevamente

---

### **Error: "SENDGRID_API_KEY no configurado"**

No encontró tu clave de SendGrid.

1. Verifica que está en `.env`
2. Reinicia la app después de cambiar `.env`
3. Si aún falla, SendGrid tomará mucho tiempo en enviar emails (pero la app seguirá funcionando)

---

### **Error: "tabla xxx no existe"**

Ejecuta las migraciones (ver sección anterior).

---

### **La app arranca pero aparece en blanco**

1. Abre el navegador console (F12)
2. Mira si hay errores en JavaScript
3. Verifica que el `PORT` en `.env` es correcto

---

## Estructura del proyecto

```
La-Lavanderia/
├── app.py                    # Punto de entrada principal
├── config.py                 # Configuración de Flask
├── wsgi.py                   # Configurable para servidores WSGI (Render)
├── requirements.txt          # Lista de dependencias de Python
├── .env.example              # Ejemplo de variables de entorno
├── .env                      # Variables reales (NO se sube a GitHub)
├── Procfile                  # Cómo ejecutar en Render
├── render.yaml               # Configuración de Render
│
├── models/                   # Esquema de BD (SQLAlchemy)
│   ├── database.py          # Conexión a PostgreSQL
│   ├── models.py            # Tablas (Usuario, Pedido, etc.)
│   └── __init__.py
│
├── routes/                   # Endpoints (URLs) de la app
│   ├── auth.py              # Login, registro, logout
│   ├── admin.py             # Panel de administrador
│   ├── cliente.py           # Portal del cliente
│   ├── api.py               # APIs JSON
│   ├── utils.py             # Códigos de barras, PDFs
│   └── __init__.py
│
├── services/                 # Lógica de negocio
│   ├── email_service.py     # Envío de correos
│   ├── validation_service.py # Validaciones
│   ├── verification_service.py # Códigos de verificación
│   └── __init__.py
│
├── decorators/              # Funciones auxiliares de autenticación
│   ├── auth_decorators.py   # @login_requerido, @admin_requerido
│   └── __init__.py
│
├── templates/               # Archivos HTML (Jinja2)
│   ├── index.html
│   ├── login.html
│   ├── admin_inicio.html
│   └── ... (más templates)
│
├── static/                  # Archivos estáticos (CSS, imágenes)
│   ├── css/
│   │   └── main.css
│   └── images/
│       └── logo.png
│
├── scripts/                 # Herramientas auxiliares
│   └── ejecutar_migracion.py # Ejecutor de migraciones SQL
│
├── migrations/              # Archivos SQL de cambios de BD
│   ├── create_verification_codes.sql
│   ├── create_descuento_config.sql
│   └── ... (más migraciones)
│
└── helpers.py               # Funciones auxiliares globales
```

---

## Variables de entorno documentadas

Este es un resumen de TODAS las variables que puedes usar en `.env`:

| Variable | Obligatorio | Ejemplo | Descripción |
|----------|-------------|---------|-------------|
| `SECRET_KEY` | Sí | `asldfk123iusd_23i1u3j...` | Clave para manejar sesiones |
| `DATABASE_URL` | Sí | `postgresql://user:pass@host:5432/db` | URL de PostgreSQL |
| `SENDGRID_API_KEY` | No | `SG.1234567890...` | Para enviar correos |
| `SENDGRID_FROM_EMAIL` | No | `info@lalavanderia.com` | Correo "desde" |
| `PORT` | No | `5000` | Puerto del servidor |
| `PYTHONUNBUFFERED` | No | `1` | Ver logs en tiempo real (Render) |

---

## Características principales

### **Usuarios y Autenticación**
- Registro de nuevos usuarios (clientes y admins)
- Login seguro con contraseñas encriptadas
- Recuperación de contraseña por email
- Sesiones de usuario

### **Panel de Administrador**
- Gestión de clientes (CRUD)
- Gestión de pedidos (crear, actualizar, eliminar)
- Cambio de estado de pedidos (recibido → procesando → entregado)
- Configuración de descuentos por niveles
- Reportes en PDF y Excel

### **Descuentos por Lealtad**
- Sistema de niveles automático
- Cuantos más pedidos, más descuento
- Descuentos se aplican automáticamente

### **Notificaciones**
- Correo de bienvenida al registrarse
- Notificación de cambio de estado de pedido
- Códigos de verificación por email

### **Generación de Reportes**
- Exportar a PDF
- Exportar a Excel
- Filtros por cliente, fecha, estado

### **Códigos de Barras**
- Generar código de barras para cada pedido
- Leer código de barras con cámara
- Descargar código de barras como imagen

---

## Contribuciones

Las contribuciones son bienvenidas. Para cambios importantes:

1. Haz fork del repositorio
2. Crea una rama (`git checkout -b feature/AmazingFeature`)
3. Haz commit (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## Soporte

¿Tienes problemas? 

1. Revisa la sección **Solución de problemas** arriba
2. Abre un issue en GitHub: https://github.com/Fabianxxo27/La-Lavanderia/issues
3. Proporciona:
   - El error exacto (la captura de pantalla o el texto)
   - Qué estabas haciendo cuando ocurrió
   - Tu sistema operativo (Windows, Mac, Linux)

---

## Licencia

Este proyecto está bajo licencia MIT. Ver `LICENSE` para detalles.

---

## Para estudiantes de Proyecto de Grado

Este proyecto es un ejemplo completo de una **aplicación web full-stack**:

- **Backend:** Flask + Python
- **Base de datos:** PostgreSQL
- **Frontend:** HTML + CSS + Bootstrap
- **Autenticación:** Flask Sessions
- **Email:** SendGrid API
- **Reportes:** ReportLab + Pandas
- **Despliegue:** Render.com

Todos los conceptos fundamentales de desarrollo web están aquí. ¡Úsalo como referencia!

---

**Última actualización:** Abril 2026  
**Mantener por:** Fabián Medina  
**GitHub:** https://github.com/Fabianxxo27/La-Lavanderia
