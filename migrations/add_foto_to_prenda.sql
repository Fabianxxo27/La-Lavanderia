-- Agregar campo foto a tabla prenda
ALTER TABLE prenda ADD COLUMN foto VARCHAR(255);

-- Comentario para el campo foto
COMMENT ON COLUMN prenda.foto IS 'Ruta relativa de la foto de la prenda subida por el cliente';