-- Ampliar columna code en verification_codes para soportar tokens URL-safe
-- Necesario para el flujo de restablecimiento de contrasena por enlace
-- Es seguro re-ejecutar: ampliar VARCHAR nunca falla ni pierde datos
ALTER TABLE verification_codes ALTER COLUMN code TYPE VARCHAR(100);
