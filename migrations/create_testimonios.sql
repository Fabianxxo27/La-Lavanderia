-- Crear tabla de testimonios/opiniones de clientes
CREATE TABLE IF NOT EXISTS testimonio (
    id_testimonio SERIAL PRIMARY KEY,
    id_cliente INTEGER,
    nombre_publico VARCHAR(100),
    calificacion INTEGER NOT NULL CHECK (calificacion BETWEEN 1 AND 5),
    comentario TEXT NOT NULL,
    es_anonimo BOOLEAN DEFAULT FALSE,
    aprobado BOOLEAN DEFAULT FALSE,
    clasificacion VARCHAR(50),
    respuesta_admin TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente) ON DELETE SET NULL
);

-- Índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_testimonio_cliente ON testimonio(id_cliente);
CREATE INDEX IF NOT EXISTS idx_testimonio_aprobado ON testimonio(aprobado);
CREATE INDEX IF NOT EXISTS idx_testimonio_fecha ON testimonio(fecha_creacion DESC);
CREATE INDEX IF NOT EXISTS idx_testimonio_calificacion ON testimonio(calificacion);

-- Comentarios
COMMENT ON TABLE testimonio IS 'Tabla de testimonios y opiniones de clientes';
COMMENT ON COLUMN testimonio.calificacion IS 'Calificación de 1 a 5 estrellas';
COMMENT ON COLUMN testimonio.es_anonimo IS 'Indica si el testimonio se muestra de forma anónima';
COMMENT ON COLUMN testimonio.aprobado IS 'Indica si el admin ha aprobado el testimonio para mostrarlo públicamente';
COMMENT ON COLUMN testimonio.clasificacion IS 'Categoría asignada por el admin: excelente, bueno, regular, malo';
COMMENT ON COLUMN testimonio.respuesta_admin IS 'Respuesta del administrador al testimonio';
COMMENT ON COLUMN testimonio.nombre_publico IS 'Nombre mostrado públicamente (del cliente o "Anónimo")';
