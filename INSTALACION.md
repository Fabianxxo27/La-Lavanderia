# 🚀 Guía Rápida de Instalación

## Paso 1: Ejecutar Migraciones de Base de Datos

### Opción A: Usando el Script Python (Más Fácil)

```bash
# 1. Asegúrate de tener las dependencias
pip install psycopg2-binary python-dotenv

# 2. Ejecuta el script automático
python ejecutar_migraciones.py
```

El script:
- ✅ Lee tu DATABASE_URL automáticamente
- ✅ Verifica qué migraciones faltan
- ✅ Ejecuta solo las necesarias
- ✅ Muestra el resultado de forma clara
- ✅ Funciona tanto en local como en Render

### Opción B: Manualmente con SQL

Si prefieres hacerlo manual:

```bash
# Conectar a tu base de datos
psql postgresql://usuario:pass@host:5432/database

# O si estás en Render, desde su dashboard SQL Console
```

Luego ejecuta:
1. El contenido de `migrations/add_direcciones_to_pedido.sql`
2. El contenido de `migrations/create_descuento_config.sql`

---

## Paso 2: Configurar Sistema de Correos

### Resumen Super Rápido:

1. **Ir a**: https://myaccount.google.com/security
2. **Activar**: Verificación en dos pasos
3. **Crear**: Contraseña de aplicación
4. **Copiar**: Los 16 caracteres que aparecen
5. **Configurar** en Render o .env:
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=tucorreo@gmail.com
   SMTP_PASSWORD=abcdefghijklmnop  (tu app password)
   ```

### Guía Detallada Paso a Paso:

Ver el archivo **`INSTRUCCIONES_CORREO.md`** para:
- 📸 Instrucciones con imágenes paso a paso
- 🔧 Solución de problemas comunes
- ✅ Cómo verificar que funciona
- 💡 Consejos de seguridad

---

## Paso 3: Verificar que Todo Funciona

### Verificar Migraciones:

```bash
python ejecutar_migraciones.py
```

Deberías ver:
```
✅ Columnas de dirección: OK
✅ Tabla descuento_config: OK
📊 Niveles de descuento configurados:
   • Bronce: 5.00% (3-5 pedidos)
   • Plata: 10.00% (6-9 pedidos)
   • Oro: 15.00% (10-14 pedidos)
   • Platino: 20.00% (15-∞ pedidos)
```

### Verificar Correos:

1. Registra un nuevo usuario
2. Deberías recibir un correo de bienvenida
3. Si no llega, revisa SPAM
4. Si sigue sin llegar, lee `INSTRUCCIONES_CORREO.md`

---

## 📚 Archivos de Ayuda

- **`INSTRUCCIONES_CORREO.md`** - Guía detallada para configurar Gmail
- **`MIGRACIONES.md`** - Documentación técnica completa de migraciones
- **`.env.example`** - Plantilla para variables de entorno
- **`ejecutar_migraciones.py`** - Script automático de migraciones

---

## ⚡ Comandos Rápidos

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar migraciones
python ejecutar_migraciones.py

# Ejecutar aplicación localmente
python app.py

# Ver logs en Render
https://dashboard.render.com/ → Tu servicio → Logs
```

---

## 🆘 ¿Problemas?

1. **Migraciones**: Lee los mensajes de error del script `ejecutar_migraciones.py`
2. **Correos**: Consulta `INSTRUCCIONES_CORREO.md` sección "Solución de Problemas"
3. **Render**: Verifica los logs en el dashboard
4. **Base de datos**: Asegúrate de que DATABASE_URL está bien configurado

---

## 🎯 ¿Qué hace cada archivo nuevo?

| Archivo | Descripción |
|---------|-------------|
| `ejecutar_migraciones.py` | Script que ejecuta migraciones automáticamente |
| `INSTRUCCIONES_CORREO.md` | Guía paso a paso para configurar Gmail |
| `MIGRACIONES.md` | Documentación técnica de todas las migraciones |
| `.env.example` | Plantilla de variables de entorno |
| `migrations/add_direcciones_to_pedido.sql` | Agrega campos de dirección a pedidos |
| `migrations/create_descuento_config.sql` | Crea tabla de configuración de descuentos |
| `templates/admin_configurar_descuentos.html` | Panel admin para gestionar descuentos |
| `templates/terminos_descuentos.html` | Página de términos legales |
| `INSTRUCCIONES_CORREO.md` | Guía para configurar correos |
