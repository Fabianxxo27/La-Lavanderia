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
