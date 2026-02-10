# Migraciones de Base de Datos - La Lavandería

Este documento describe las migraciones SQL que deben ejecutarse manualmente en la base de datos.

## Migraciones Pendientes

### 1. Agregar Direcciones a Pedidos
**Archivo:** `migrations/add_direcciones_to_pedido.sql`
**Fecha:** 2024
**Descripción:** Agrega campos para direcciones de recogida y entrega en el servicio a domicilio.

```bash
# Ejecutar en PostgreSQL
psql -h <host> -U <usuario> -d <base_datos> -f migrations/add_direcciones_to_pedido.sql
```

**Campos agregados:**
- `direccion_recogida VARCHAR(500)` - Dirección donde se recoge la ropa
- `direccion_entrega VARCHAR(500)` - Dirección donde se entrega la ropa lavada

**Validaciones:**
- Longitud mínima de 10 caracteres
- Índice para búsquedas rápidas

### 2. Configuración de Descuentos
**Archivo:** `migrations/create_descuento_config.sql`
**Fecha:** 2024
**Descripción:** Crea tabla para gestionar niveles de descuento de forma dinámica.

```bash
# Ejecutar en PostgreSQL
psql -h <host> -U <usuario> -d <base_datos> -f migrations/create_descuento_config.sql
```

**Tabla creada:** `descuento_config`
**Campos:**
- `id_config SERIAL PRIMARY KEY`
- `nivel VARCHAR(50)` - Nombre del nivel (Bronce, Plata, Oro, Platino)
- `porcentaje DECIMAL(5,2)` - Porcentaje de descuento (0-100)
- `pedidos_minimos INTEGER` - Cantidad mínima de pedidos requeridos
- `pedidos_maximos INTEGER` - Cantidad máxima (NULL = ilimitado)
- `activo BOOLEAN` - Si el nivel está activo
- `fecha_creacion TIMESTAMP`
- `fecha_modificacion TIMESTAMP`

**Datos iniciales:**
- Bronce: 5% (3-5 pedidos)
- Plata: 10% (6-9 pedidos)
- Oro: 15% (10-14 pedidos)
- Platino: 20% (15+ pedidos)

## Cómo Ejecutar las Migraciones

### ⭐ Opción 1: Script Python Automático (RECOMENDADO)

El método más fácil es usar el script `ejecutar_migraciones.py`:

```bash
# Desde la raíz del proyecto
python ejecutar_migraciones.py
```

El script:
- ✅ Verifica automáticamente qué migraciones faltan
- ✅ Ejecuta solo las necesarias
- ✅ Muestra mensajes claros de progreso
- ✅ Verifica que todo quedó correcto
- ✅ No requiere instalar psql

**Requisitos:**
```bash
pip install psycopg2-binary python-dotenv
```

### Opción 2: Desde la línea de comandos (PostgreSQL CLI)
```bash
cd migrations
psql -h tu_host -U tu_usuario -d tu_base_datos -f add_direcciones_to_pedido.sql
psql -h tu_host -U tu_usuario -d tu_base_datos -f create_descuento_config.sql
```

### Opción 3: Desde pgAdmin o DBeaver
1. Abrir el cliente SQL
2. Conectar a la base de datos
3. Abrir cada archivo .sql
4. Ejecutar el contenido

## Variables de Entorno Requeridas

### 📧 Configuración del Sistema de Correos

Para que el sistema pueda enviar correos electrónicos, necesitas configurar estas variables en Render:

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=tu_app_password_de_16_caracteres
```

### 🔑 Cómo Obtener la App Password de Gmail

Google ya no permite usar tu contraseña normal para aplicaciones. Necesitas crear una "Contraseña de aplicación":

#### Paso 1: Habilitar Verificación en 2 Pasos
1. Ve a tu **Cuenta de Google**: https://myaccount.google.com/
2. En el menú izquierdo, selecciona **Seguridad**
3. Busca la sección **Cómo inicias sesión en Google**
4. Haz clic en **Verificación en dos pasos**
5. Sigue los pasos para activarla (necesitarás tu teléfono)

#### Paso 2: Crear App Password
1. Una vez activada la verificación en 2 pasos, regresa a **Seguridad**
2. Busca **Verificación en dos pasos** y haz clic
3. Desplázate hacia abajo hasta encontrar **Contraseñas de aplicaciones**
4. Haz clic en **Contraseñas de aplicaciones**
5. Es posible que te pida tu contraseña de Google nuevamente
6. En **Seleccionar aplicación**, elige **Correo**
7. En **Seleccionar dispositivo**, elige **Otro (nombre personalizado)**
8. Escribe un nombre como "La Lavandería App"
9. Haz clic en **Generar**
10. **¡IMPORTANTE!** Copia la contraseña de 16 caracteres que aparece (sin espacios)

#### Paso 3: Configurar en Render
1. Ve a tu proyecto en Render: https://dashboard.render.com/
2. Selecciona tu Web Service
3. Ve a la pestaña **Environment**
4. Agrega las siguientes variables:

```
SMTP_SERVER = smtp.gmail.com
SMTP_PORT = 587
SMTP_USER = lalavanderiabogota@gmail.com (o tu correo)
SMTP_PASSWORD = abcd efgh ijkl mnop (la contraseña de 16 caracteres sin espacios)
```

5. Haz clic en **Save Changes**
6. Render reiniciará automáticamente tu aplicación

### 📝 Ejemplo Completo de Variables en Render

```env
# Base de datos (ya debe estar configurada)
DATABASE_URL=postgresql://user:pass@host:5432/database

# Correo electrónico (NUEVAS)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=lalavanderiabogota@gmail.com
SMTP_PASSWORD=abcdefghijklmnop

# Seguridad (ya debe estar configurada)
SECRET_KEY=tu_secret_key_super_segura
```

### ⚠️ Notas Importantes sobre el Correo

1. **La contraseña NO es tu contraseña de Gmail**: Es una contraseña especial de 16 caracteres generada por Google
2. **Verificación en 2 pasos es OBLIGATORIA**: Sin esto, no puedes crear App Passwords
3. **Copia bien la contraseña**: Se muestra solo una vez, sin espacios
4. **Si no funciona**: 
   - Verifica que copiaste la contraseña completa (16 caracteres)
   - Asegúrate de que SMTP_PORT sea 587 (no 465)
   - Revisa que SMTP_SERVER sea exactamente `smtp.gmail.com`
5. **Correos pueden tardar**: Los correos se envían en segundo plano, pueden tardar 1-2 minutos

### 🧪 Probar el Sistema de Correos

Después de configurar, puedes probar:
1. Registra un nuevo usuario
2. Deberías recibir un correo de bienvenida
3. Si no llega, revisa la carpeta de SPAM
4. Verifica los logs en Render para ver errores

## Verificación Post-Migración

### Verificar tabla pedido
```sql
SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'pedido' 
AND column_name IN ('direccion_recogida', 'direccion_entrega');
```

### Verificar tabla descuento_config
```sql
SELECT * FROM descuento_config ORDER BY pedidos_minimos;
```

## Rollback (Opcional)

Si necesitas revertir los cambios:

```sql
-- Revertir direcciones
ALTER TABLE pedido 
DROP COLUMN IF EXISTS direccion_recogida,
DROP COLUMN IF EXISTS direccion_entrega;

-- Revertir descuentos
DROP TABLE IF EXISTS descuento_config;
```

## Notas Importantes

1. **Backup:** Siempre haz un backup de la base de datos antes de ejecutar migraciones.
2. **Producción:** Ejecuta primero en un ambiente de prueba.
3. **Render:** Si usas Render, puedes ejecutar las migraciones desde el dashboard SQL.
4. **Índices:** Las migraciones incluyen índices para mejorar el rendimiento.
5. **Compatibilidad:** Todas las migraciones son compatibles con PostgreSQL 12+.

## Orden de Ejecución

1. `add_direcciones_to_pedido.sql`
2. `create_descuento_config.sql`

## Soporte

Si encuentras problemas con las migraciones, verifica:
- Permisos de usuario en la base de datos
- Versión de PostgreSQL (debe ser 12 o superior)
- Conexión a la base de datos
- Sintaxis SQL específica del motor de base de datos
