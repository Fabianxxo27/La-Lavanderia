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

### Opción 1: Desde la línea de comandos
```bash
cd migrations
psql -h tu_host -U tu_usuario -d tu_base_datos -f add_direcciones_to_pedido.sql
psql -h tu_host -U tu_usuario -d tu_base_datos -f create_descuento_config.sql
```

### Opción 2: Desde pgAdmin o DBeaver
1. Abrir el cliente SQL
2. Conectar a la base de datos
3. Abrir cada archivo .sql
4. Ejecutar el contenido

### Opción 3: Desde Python (app.py)
Si tienes acceso a psql desde Python, puedes ejecutar:
```python
import subprocess
subprocess.run(['psql', '-h', 'host', '-U', 'user', '-d', 'db', '-f', 'migrations/add_direcciones_to_pedido.sql'])
subprocess.run(['psql', '-h', 'host', '-U', 'user', '-d', 'db', '-f', 'migrations/create_descuento_config.sql'])
```

## Variables de Entorno Requeridas

Asegúrate de tener configuradas estas variables para el sistema de correos:

```bash
EMAIL_USER=tu_correo@ejemplo.com
EMAIL_PASSWORD=tu_contraseña_o_app_password
EMAIL_HOST=smtp.gmail.com  # o tu servidor SMTP
EMAIL_PORT=587
```

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
