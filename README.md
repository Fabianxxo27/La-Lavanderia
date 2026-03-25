# La Lavanderia

Sistema web para gestionar clientes, pedidos, descuentos por lealtad, reportes y notificaciones de una lavanderia.

Este README esta escrito para que puedas levantar el proyecto aunque no tengas mucha experiencia.

## Que hace este sistema

- Registro e inicio de sesion.
- Panel de administrador para clientes y pedidos.
- Configuracion de descuentos por niveles.
- Reportes en PDF y Excel.
- Soporte de codigos de barras.
- Notificaciones por correo.

## Requisitos minimos

- Python 3.10 o superior.
- PostgreSQL (local o remoto).
- `pip` actualizado.

## Arranque rapido (local)

1. Clona el repositorio y entra a la carpeta.

```bash
git clone https://github.com/Fabianxxo27/La-Lavanderia.git
cd La-Lavanderia
```

2. Crea y activa un entorno virtual.

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Instala dependencias.

```bash
pip install -r requirements.txt
```

4. Crea el archivo `.env` basado en `.env.example` y agrega tus datos.

Variables recomendadas:

```env
SECRET_KEY=pon_una_clave_larga_y_unica
DATABASE_URL=postgresql://usuario:password@host:5432/base_de_datos

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=tu_app_password
```

Notas:

- Si no defines `DATABASE_URL`, la app intenta usar `credentials.py`.
- En produccion no se recomienda usar `credentials.py`.

5. Ejecuta la aplicacion.

```bash
python app.py
```

6. Abre en tu navegador:

```text
http://127.0.0.1:5000
```

## Migraciones de base de datos

Tienes dos caminos.

### Opcion A (recomendada): desde el panel admin

1. Inicia sesion como administrador.
2. Entra a `/admin/configurar-descuentos`.
3. Ejecuta migraciones desde ese panel.

### Opcion B: por terminal

Ejecuta una migracion manual con:

```bash
python scripts/ejecutar_migracion.py migrations/create_verification_codes.sql
```

Si no pasas archivo, usa por defecto `migrations/create_verification_codes.sql`.

## Archivos necesarios para ejecutar la app

Estos si son parte del funcionamiento normal:

- `app.py`
- `config.py`
- `requirements.txt`
- `models/`
- `routes/`
- `services/`
- `decorators/`
- `templates/`
- `static/`
- `migrations/` (necesario cuando aplicas cambios de esquema)
- `helpers.py`

## Archivos que no son estrictamente necesarios para la ejecucion

Puedes correr la app sin estos archivos (algunos son utiles solo para despliegue, documentacion o mantenimiento):

- `CONFIGURAR_CORREO_RENDER.md`
- `SETUP_SENDGRID.md`
- `REFACTORIZACION_MVC.md`
- `RUTAS_ADMIN_EXTRAIDAS.txt`
- `scripts/_check_template_diff_temp.py`
- `scripts/_compare_mvc_diff_temp.py`
- `scripts/_compare_mvc_temp.py`
- `deploy.bat`
- `fabianmedina_miapp.sql` (dump/respaldo SQL)
- `wsgi.py` (solo si arrancas con servidor WSGI como waitress/gunicorn)
- `Procfile` (solo para ciertos despliegues)
- `render.yaml` (solo para Render)
- `Dockerfile` (solo si usas Docker)
- `__pycache__/` (cache de Python, se puede borrar)

Importante:

- No borres `credentials.py` si tu entorno local depende de ese archivo y no usas `DATABASE_URL`.
- No borres `.env` ni `.env.example`.

## Errores comunes y solucion

### Error: tabla `descuento_config` no existe

Ejecuta migraciones desde `/admin/configurar-descuentos` o por terminal.

### Error: no llegan correos

- Revisa `SMTP_USER` y `SMTP_PASSWORD`.
- Si usas Gmail, utiliza App Password.
- Verifica puerto `587`.

### Error: no conecta a la base de datos

- Revisa `DATABASE_URL`.
- Si estas en local con `credentials.py`, valida usuario, password, host y base.

## Estructura general

```text
La-Lavanderia/
   app.py
   config.py
   requirements.txt
   models/
   routes/
   services/
   templates/
   static/
   migrations/
```

## Despliegue

El proyecto esta preparado para desplegar en Render.

- Si usas Render, revisa `render.yaml` y `Procfile`.
- Si usas Docker, revisa `Dockerfile`.

## Soporte

Si encuentras un problema, abre un issue en:

`https://github.com/Fabianxxo27/La-Lavanderia/issues`
