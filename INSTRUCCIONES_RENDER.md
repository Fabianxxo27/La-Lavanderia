# 🚀 Cómo Ejecutar la Migración desde Render.com

## Paso 1: Acceder a la Consola de PostgreSQL en Render

1. Ve a tu dashboard de Render: https://dashboard.render.com/
2. En el menú lateral, busca y haz clic en **PostgreSQL**
3. Selecciona tu base de datos (probablemente se llama algo como `lalavanderia-db` o similar)
4. Una vez dentro, busca el botón **"Shell"** o **"psql"** en la parte superior
5. Haz clic en él para abrir la consola interactiva de PostgreSQL

## Paso 2: Copiar el Script de Migración

Abre el archivo `migration_codigo_barras.sql` y copia TODO su contenido:

```sql
-- Script para agregar código de barras a pedidos y limpiar datos
-- Ejecutar este script en la base de datos PostgreSQL

-- 1. Eliminar todos los recibos (tienen FK a pedido)
DELETE FROM recibo;

-- 2. Eliminar todas las prendas (tienen FK a pedido)
DELETE FROM prenda;

-- 3. Eliminar todos los pedidos
DELETE FROM pedido;

-- 4. Reiniciar secuencia de pedidos para que comience desde 1
ALTER SEQUENCE pedido_id_pedido_seq RESTART WITH 1;

-- 5. Agregar columna codigo_barras a la tabla pedido (si no existe)
ALTER TABLE pedido ADD COLUMN IF NOT EXISTS codigo_barras VARCHAR(50) UNIQUE;

-- 6. Crear índice para búsquedas rápidas por código de barras
CREATE INDEX IF NOT EXISTS idx_pedido_codigo_barras ON pedido(codigo_barras);

-- Script completado
-- Los nuevos pedidos generarán automáticamente sus códigos de barras
```

## Paso 3: Ejecutar el Script

1. En la consola Shell de PostgreSQL que abriste en el Paso 1
2. Pega el contenido completo del script que copiaste
3. Presiona **Enter**
4. Espera a que se ejecuten todos los comandos (debería tardar menos de 5 segundos)

## Paso 4: Verificar que Todo Funcionó

Ejecuta estos comandos para verificar:

```sql
-- Ver la estructura de la tabla pedido (debe mostrar codigo_barras)
\d pedido

-- Verificar que no hay pedidos (tabla limpia)
SELECT COUNT(*) FROM pedido;
```

Deberías ver algo como:

```
                                          Table "public.pedido"
     Column      |         Type          | Collation | Nullable |                   Default                    
-----------------+-----------------------+-----------+----------+----------------------------------------------
 id_pedido       | integer               |           | not null | nextval('pedido_id_pedido_seq'::regclass)
 fecha_ingreso   | date                  |           | not null | 
 fecha_entrega   | date                  |           |          | 
 estado          | character varying(50) |           | not null | 
 id_cliente      | integer               |           | not null | 
 codigo_barras   | character varying(50) |           |          |  👈 NUEVA COLUMNA
```

## Paso 5: Probar Creando un Pedido Nuevo

1. Ve a tu aplicación desplegada en Render
2. Inicia sesión como administrador
3. Crea un nuevo pedido
4. Verifica en la base de datos:

```sql
SELECT id_pedido, codigo_barras, fecha_ingreso, estado FROM pedido;
```

Deberías ver algo como:

```
 id_pedido |     codigo_barras      | fecha_ingreso |  estado   
-----------+------------------------+---------------+-----------
         1 | LAV-20260129-000001    | 2026-01-29    | Pendiente
```

## 🎉 ¡Listo!

Ahora cada pedido nuevo tendrá automáticamente su código de barras único.

## 🔍 Comandos Útiles de PostgreSQL

Si necesitas más información:

```sql
-- Ver todas las tablas
\dt

-- Ver estructura de una tabla específica
\d nombre_tabla

-- Salir de la consola
\q

-- Ver todos los pedidos con sus códigos
SELECT * FROM pedido;

-- Contar pedidos
SELECT COUNT(*) FROM pedido;
```

## ⚠️ Notas Importantes

- **Este script elimina TODOS los pedidos actuales** - Asegúrate de que está bien antes de ejecutar
- La migración es instantánea y no afectará la aplicación en producción
- No necesitas reiniciar el servicio de Render después de la migración
- Los nuevos pedidos tendrán códigos automáticamente
- Los códigos tienen formato: `LAV-YYYYMMDD-NNNNNN`

## 🆘 Solución de Problemas

### Error: "relation pedido_id_pedido_seq does not exist"

Si ves este error, es porque tu base de datos usa otro nombre para la secuencia. Ejecuta:

```sql
-- Encontrar el nombre correcto de la secuencia
SELECT pg_get_serial_sequence('pedido', 'id_pedido');
```

Luego usa ese nombre en lugar de `pedido_id_pedido_seq` en el script.

### Error: "column codigo_barras already exists"

Ya ejecutaste el script antes. No pasa nada, simplemente ejecuta solo:

```sql
DELETE FROM recibo;
DELETE FROM prenda;
DELETE FROM pedido;
ALTER SEQUENCE pedido_id_pedido_seq RESTART WITH 1;
```

## 📸 Capturas de Pantalla Guía

### 1. Dashboard de Render
```
[Tu Base de Datos] > Shell (botón azul arriba a la derecha)
```

### 2. Consola PostgreSQL
```
usuario_abc1234=> [aquí pegas el script]
```

### 3. Verificación
```
usuario_abc1234=> \d pedido
[debe mostrar codigo_barras en la lista de columnas]
```
