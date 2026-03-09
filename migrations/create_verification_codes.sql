-- Crear tabla para códigos de verificación temporal
CREATE TABLE IF NOT EXISTS verification_codes (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) NOT NULL,
    code VARCHAR(10) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '15 minutes',
    used BOOLEAN DEFAULT FALSE,
    UNIQUE(email, tipo)
);

-- Índice para búsquedas rápidas
CREATE INDEX idx_verification_email_type ON verification_codes(email, tipo);
CREATE INDEX idx_verification_code ON verification_codes(code);
