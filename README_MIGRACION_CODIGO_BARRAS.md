# Migración: Código de Barras para Pedidos

## Descripción
Esta migración agrega la funcionalidad de código de barras único para cada pedido.

## Formato del Código de Barras
- **Formato**: `LAV-YYYYMMDD-NNNNNN`
- **Ejemplo**: `LAV-20260129-000001`
  - `LAV`: Prefijo de la lavandería
  - `YYYYMMDD`: Fecha de creación (20260129 = 29 de enero de 2026)
  - `NNNNNN`: ID del pedido con 6 dígitos (000001, 000002, etc.)

## Pasos para Aplicar la Migración

### Opción 1: Ejecutar desde psql (Recomendado)
```bash
psql -h <host> -U <usuario> -d <base_de_datos> -f migration_codigo_barras.sql
```

### Opción 2: Ejecutar desde la consola de PostgreSQL
1. Conectar a tu base de datos PostgreSQL
2. Copiar y pegar el contenido de `migration_codigo_barras.sql`
3. Ejecutar

### Opción 3: Desde Render.com (si usas Render)
1. Ve a tu servicio de base de datos en Render
2. Abre la consola de PostgreSQL (Shell)
3. Copia y pega el script SQL

## ¿Qué hace esta migración?

1. ✅ Elimina todos los recibos existentes
2. ✅ Elimina todas las prendas existentes
3. ✅ Elimina todos los pedidos existentes
4. ✅ Reinicia el contador de IDs de pedidos desde 1
5. ✅ Agrega la columna `codigo_barras` a la tabla `pedido`
6. ✅ Crea un índice para búsquedas rápidas

## Cambios en el Código

### app.py
- Al crear un nuevo pedido, se genera automáticamente un código de barras único
- El código incluye la fecha y el ID del pedido
- Se actualiza el pedido con el código generado

## Uso Futuro

Una vez aplicada la migración:
- Cada nuevo pedido tendrá automáticamente un código de barras único
- El código se puede usar para:
  - Escanear pedidos con un lector de código de barras
  - Identificar pedidos rápidamente
  - Búsqueda por código en el sistema
  - Imprimir etiquetas con código de barras

## ⚠️ IMPORTANTE
- Esta migración elimina TODOS los pedidos existentes
- Asegúrate de hacer un backup si necesitas conservar los datos actuales
- Después de la migración, los nuevos pedidos comenzarán desde el ID 1

## Verificación
Después de aplicar la migración, puedes verificar:
```sql
-- Ver estructura de la tabla pedido
\d pedido

-- Crear un pedido de prueba en la aplicación y verificar
SELECT id_pedido, codigo_barras, fecha_ingreso FROM pedido;
```

## Ejemplo de Resultado
```
id_pedido | codigo_barras          | fecha_ingreso
----------|------------------------|---------------
1         | LAV-20260129-000001    | 2026-01-29
2         | LAV-20260129-000002    | 2026-01-29
3         | LAV-20260130-000003    | 2026-01-30
```
