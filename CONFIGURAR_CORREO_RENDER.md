# 📧 Configurar Correo en Render (Paso a Paso)

## ⚠️ Problema Actual
Los correos no se están enviando porque falta la variable `SMTP_PASSWORD` en Render.

---

## 🔧 Solución: Configurar Variables de Entorno en Render

### Paso 1: Generar App Password de Gmail

1. **Ir a tu cuenta de Google**: https://myaccount.google.com/
2. **Seguridad** (menú lateral izquierdo)
3. **Verificación en 2 pasos**: DEBE estar activada
   - Si no está activada, actívala primero
   - Sigue las instrucciones de Google para configurar tu teléfono

4. **Contraseñas de aplicaciones** (aparece solo si tienes 2FA activado)
   - Busca "Contraseñas de aplicaciones" o "App Passwords"
   - Puede estar en la sección de "Acceso a Google"

5. **Crear contraseña**:
   - Nombre: `La Lavandería`
   - Google generará 16 caracteres (ejemplo: `abcd efgh ijkl mnop`)
   - **COPIA ESTOS 16 CARACTERES** (sin espacios: `abcdefghijklmnop`)
   - ⚠️ Solo se muestra una vez, guárdalo

---

### Paso 2: Configurar Variables en Render

1. **Ir al dashboard de Render**: https://dashboard.render.com/

2. **Seleccionar tu servicio** (La-Lavanderia)

3. **Ir a "Environment"** (menú lateral izquierdo)

4. **Agregar las siguientes variables**:

   Clic en **"Add Environment Variable"** para cada una:

   | Key | Value | Ejemplo |
   |-----|-------|---------|
   | `SMTP_SERVER` | `smtp.gmail.com` | `smtp.gmail.com` |
   | `SMTP_PORT` | `587` | `587` |
   | `SMTP_USER` | Tu correo completo | `lalavanderiabogota@gmail.com` |
   | `SMTP_PASSWORD` | Los 16 caracteres sin espacios | `abcdefghijklmnop` |

5. **Guardar cambios**:
   - Clic en **"Save Changes"** al final de la página
   - Render reiniciará automáticamente el servicio (toma 1-2 minutos)

---

### Paso 3: Verificar en los Logs

1. En Render, ir a **"Logs"** (menú lateral)

2. **Esperar a que termine el deploy** (verás "Starting service")

3. **Probar enviando un correo**:
   - Registrar un nuevo usuario
   - Crear un pedido
   - Cambiar estado de un pedido

4. **Buscar en los logs**:
   - ✅ `Correo enviado exitosamente a usuario@gmail.com` = **FUNCIONA**
   - ⚠️ `SMTP_PASSWORD no configurado` = **Falta configurar la variable**
   - ❌ `Error de autenticación SMTP` = **App Password incorrecto**

---

## 🧪 Probar Localmente (Opcional)

Si quieres probar en tu computadora:

1. **Crear archivo `.env`** en la raíz del proyecto:
```env
DATABASE_URL=postgresql://usuario:password@localhost/lavanderia
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tuCorreo@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
```

2. **Ejecutar la aplicación**:
```bash
python app.py
```

3. **Verificar en la consola** si aparecen mensajes de correo enviado

---

## ❓ Problemas Comunes

### Error: "Invalid credentials"
- **Causa**: App Password incorrecto o no generado
- **Solución**: Regenera el App Password en Google y cópialo SIN espacios

### Error: "Username and Password not accepted"
- **Causa**: Verificación en 2 pasos no activada
- **Solución**: Activa 2FA en tu cuenta de Google primero

### Error: "SMTP_PASSWORD no configurado"
- **Causa**: La variable no está en Render o tiene espacios
- **Solución**: Verifica que `SMTP_PASSWORD` esté en Environment sin espacios

### Los correos no llegan
- **Causa**: Gmail puede bloquear correos inicialmente
- **Solución**: 
  1. Revisa la carpeta de Spam
  2. Espera 5-10 minutos (Gmail tiene delays)
  3. Verifica que el email del destinatario sea válido

---

## 📝 Resumen Rápido

```
1. Google Account → Seguridad → Verificación en 2 pasos (activar)
2. Contraseñas de aplicaciones → Crear → Copiar 16 caracteres
3. Render Dashboard → Tu servicio → Environment
4. Add Variable: SMTP_PASSWORD = (pegar los 16 caracteres sin espacios)
5. Save Changes → Esperar redeploy
6. Logs → Verificar "Correo enviado exitosamente"
```

---

## 🎯 Resultado Esperado

Después de configurar, los usuarios recibirán correos automáticos en:
- ✉️ Registro de cuenta nueva
- ✉️ Pedido creado
- ✉️ Cambio de estado del pedido (En proceso, Completado)

---

**Última actualización**: Febrero 2026
