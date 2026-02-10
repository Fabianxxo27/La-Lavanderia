-- Agregar columnas para almacenar el descuento aplicado al momento de crear el pedido
-- Esto evita que cambios posteriores en la configuración de descuentos afecten pedidos antiguos

ALTER TABLE pedido 
ADD COLUMN IF NOT EXISTS porcentaje_descuento INTEGER DEFAULT 0;

ALTER TABLE pedido 
ADD COLUMN IF NOT EXISTS nivel_descuento VARCHAR(50) DEFAULT NULL;

-- Comentarios
COMMENT ON COLUMN pedido.porcentaje_descuento IS 'Porcentaje de descuento aplicado al momento de crear el pedido (0-100)';
COMMENT ON COLUMN pedido.nivel_descuento IS 'Nivel de descuento aplicado (Bronce, Plata, Oro, Platino) al momento de crear el pedido';
