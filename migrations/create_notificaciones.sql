-- Crear tabla de notificaciones
CREATE TABLE IF NOT EXISTS notificacion (
    id_notificacion SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    mensaje TEXT NOT NULL,
    tipo VARCHAR(50) DEFAULT 'info',
    leida BOOLEAN DEFAULT FALSE,
    url VARCHAR(500),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
);

-- Índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_notificacion_usuario ON notificacion(id_usuario);
CREATE INDEX IF NOT EXISTS idx_notificacion_leida ON notificacion(leida);
CREATE INDEX IF NOT EXISTS idx_notificacion_fecha ON notificacion(fecha_creacion DESC);

-- Comentarios
COMMENT ON TABLE notificacion IS 'Tabla de notificaciones para usuarios del sistema';
COMMENT ON COLUMN notificacion.tipo IS 'Tipo de notificación: info, success, warning, error, pedido';
COMMENT ON COLUMN notificacion.leida IS 'Indica si la notificación ha sido leída';
COMMENT ON COLUMN notificacion.url IS 'URL opcional a la que redirige la notificación al hacer clic';
