-- Agregar columnas de dirección a la tabla pedido para servicio a domicilio
-- Ejecutar en PostgreSQL

ALTER TABLE pedido 
ADD COLUMN IF NOT EXISTS direccion_recogida VARCHAR(500),
ADD COLUMN IF NOT EXISTS direccion_entrega VARCHAR(500);

-- Crear índice para búsquedas por dirección
CREATE INDEX IF NOT EXISTS idx_pedido_direccion_recogida ON pedido(direccion_recogida);
CREATE INDEX IF NOT EXISTS idx_pedido_direccion_entrega ON pedido(direccion_entrega);

COMMENT ON COLUMN pedido.direccion_recogida IS 'Dirección donde se recoge la ropa para lavar';
COMMENT ON COLUMN pedido.direccion_entrega IS 'Dirección donde se entrega la ropa limpia';
