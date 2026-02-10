-- Crear tabla para almacenar el esquema de descuentos congelado por cliente
-- Esto permite que cada cliente mantenga su esquema de promociones hasta completar el ciclo

CREATE TABLE IF NOT EXISTS cliente_esquema_descuento (
    id_esquema SERIAL PRIMARY KEY,
    id_cliente INTEGER NOT NULL REFERENCES cliente(id_cliente) ON DELETE CASCADE,
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    esquema_json TEXT NOT NULL,
    activo BOOLEAN DEFAULT true,
    UNIQUE(id_cliente, activo)
);

-- Índice para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_cliente_esquema_activo ON cliente_esquema_descuento(id_cliente, activo);

-- Comentarios
COMMENT ON TABLE cliente_esquema_descuento IS 'Almacena el esquema de descuentos congelado para cada cliente hasta que complete su ciclo';
COMMENT ON COLUMN cliente_esquema_descuento.esquema_json IS 'JSON con la configuración completa de niveles de descuento: [{"nivel":"Bronce","porcentaje":5,"min":0,"max":2}]';
COMMENT ON COLUMN cliente_esquema_descuento.activo IS 'Solo un esquema activo por cliente. Se desactiva cuando completa el ciclo y se crea uno nuevo';
