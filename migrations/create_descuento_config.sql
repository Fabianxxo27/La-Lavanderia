-- Crear tabla de configuración de descuentos
CREATE TABLE IF NOT EXISTS descuento_config (
    id_config SERIAL PRIMARY KEY,
    nivel VARCHAR(50) NOT NULL UNIQUE,
    porcentaje DECIMAL(5,2) NOT NULL CHECK (porcentaje >= 0 AND porcentaje <= 100),
    pedidos_minimos INTEGER NOT NULL CHECK (pedidos_minimos >= 0),
    pedidos_maximos INTEGER CHECK (pedidos_maximos IS NULL OR pedidos_maximos >= pedidos_minimos),
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar configuración inicial de descuentos
INSERT INTO descuento_config (nivel, porcentaje, pedidos_minimos, pedidos_maximos, activo) VALUES
('Bronce', 5.00, 3, 5, true),
('Plata', 10.00, 6, 9, true),
('Oro', 15.00, 10, 14, true),
('Platino', 20.00, 15, NULL, true)
ON CONFLICT (nivel) DO NOTHING;

-- Índice para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_descuento_activo ON descuento_config(activo);
CREATE INDEX IF NOT EXISTS idx_descuento_pedidos ON descuento_config(pedidos_minimos, pedidos_maximos);
