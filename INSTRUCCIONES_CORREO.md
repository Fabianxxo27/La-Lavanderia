# 📧 Configuración del Sistema de Correos - Guía Paso a Paso

## ¿Por qué necesito esto?

La aplicación envía correos electrónicos en estos casos:
- ✉️ Bienvenida cuando un usuario se registra
- ✉️ Confirmación cuando se crea un pedido
- ✉️ Notificación cuando el pedido está "En proceso"
- ✉️ Notificación cuando el pedido está "Completado"
- ✉️ Credenciales cuando el admin crea un cliente rápido

## 🎯 Paso a Paso: Configurar Gmail

### Paso 1: Tener una cuenta de Gmail
Usa `lalavanderiabogota@gmail.com` o crea una nueva cuenta específica para la aplicación.

### Paso 2: Activar Verificación en 2 Pasos

1. **Ir a tu cuenta de Google**
   - Abre: https://myaccount.google.com/
   - O busca en Google: "mi cuenta de google"

2. **Ir a Seguridad**
   - En el menú de la izquierda, haz clic en **"Seguridad"**

3. **Activar verificación en 2 pasos**
   - Busca la sección **"Cómo inicias sesión en Google"**
   - Haz clic en **"Verificación en dos pasos"**
   - Haz clic en **"Empezar"**
   - Sigue los pasos (necesitarás tu celular)
   - Confirma con tu número de teléfono

### Paso 3: Crear una Contraseña de Aplicación

1. **Una vez activada la verificación en 2 pasos**
   - Regresa a https://myaccount.google.com/security
   - Busca **"Verificación en dos pasos"** nuevamente
   - Haz clic para entrar

2. **Buscar "Contraseñas de aplicaciones"**
   - Desplázate hacia abajo
   - Verás una opción que dice **"Contraseñas de aplicaciones"**
   - Haz clic ahí
   - Es posible que te pida tu contraseña de Google otra vez

3. **Generar la contraseña**
   - En **"Seleccionar aplicación"**: Elige **"Correo"**
   - En **"Seleccionar dispositivo"**: Elige **"Otro (nombre personalizado)"**
   - Escribe: **"La Lavandería App"**
   - Haz clic en **"Generar"**

4. **¡IMPORTANTE! Copiar la contraseña**
   - Aparecerá una contraseña de **16 caracteres** en bloques de 4
   - Ejemplo: `abcd efgh ijkl mnop`
   - **Cópiala COMPLETA, SIN ESPACIOS**: `abcdefghijklmnop`
   - Esta contraseña se muestra **solo una vez**
   - Si la pierdes, deberás generar una nueva

### Paso 4: Configurar en tu Aplicación

#### Si trabajas en LOCAL (tu computadora):

1. **Crear archivo .env**
   - En la carpeta raíz del proyecto, crea un archivo llamado `.env`
   - O copia el archivo `.env.example` y renómbralo a `.env`

2. **Agregar estas líneas al archivo .env:**
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=lalavanderiabogota@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
```

3. **Reemplazar valores:**
   - `SMTP_USER`: Tu correo de Gmail completo
   - `SMTP_PASSWORD`: La contraseña de 16 caracteres que copiaste (sin espacios)

#### Si trabajas en RENDER (producción):

1. **Ir a Render Dashboard**
   - Abre: https://dashboard.render.com/
   - Inicia sesión
   - Selecciona tu Web Service **"La Lavandería"**

2. **Ir a Environment**
   - En el menú de la izquierda, haz clic en **"Environment"**

3. **Agregar Variables**
   - Haz clic en **"Add Environment Variable"**
   - Agrega cada una de estas:

   | Key | Value |
   |-----|-------|
   | `SMTP_SERVER` | `smtp.gmail.com` |
   | `SMTP_PORT` | `587` |
   | `SMTP_USER` | `lalavanderiabogota@gmail.com` |
   | `SMTP_PASSWORD` | `abcdefghijklmnop` (tu app password) |

4. **Guardar Cambios**
   - Haz clic en **"Save Changes"**
   - Render reiniciará automáticamente tu aplicación (tarda 1-2 minutos)

## ✅ Verificar que Funciona

### Prueba 1: Registrar un usuario nuevo
1. Ve a tu aplicación
2. Crea un nuevo usuario
3. Deberías recibir un correo de bienvenida
4. **Si no llega**: Revisa la carpeta de SPAM

### Prueba 2: Crear un pedido
1. Inicia sesión como admin
2. Crea un nuevo pedido
3. El cliente debería recibir un correo de confirmación

### Prueba 3: Cambiar estado de pedido
1. Cambia un pedido a "En proceso"
2. El cliente debería recibir un correo
3. Cambia a "Completado"
4. El cliente debería recibir otro correo

## 🔧 Solución de Problemas

### ❌ "No puedo encontrar Contraseñas de aplicaciones"
**Causa**: No has activado la verificación en 2 pasos
**Solución**: Ve al Paso 2 y activa la verificación en 2 pasos primero

### ❌ "Los correos no llegan"
**Posibles causas:**
1. La App Password está mal escrita
   - ✅ Debe ser 16 caracteres sin espacios
   - ❌ NO uses tu contraseña normal de Gmail
2. El puerto está mal
   - ✅ Debe ser `587`
   - ❌ NO uses `465`
3. El servidor está mal
   - ✅ Debe ser exactamente `smtp.gmail.com`
4. El correo está en SPAM
   - Revisa la carpeta de correo no deseado

### ❌ "Authentication failed" en los logs
**Causa**: La App Password es incorrecta
**Solución**: 
1. Ve a Google y genera una nueva App Password
2. Cópiala correctamente (16 caracteres sin espacios)
3. Actualiza la variable `SMTP_PASSWORD`

### ❌ "Connection timed out"
**Causa**: El puerto o servidor están mal
**Solución**: Verifica que sea exactamente:
- SMTP_SERVER: `smtp.gmail.com`
- SMTP_PORT: `587`

## 📝 Resumen Rápido

```
1. Ir a: https://myaccount.google.com/security
2. Activar: Verificación en dos pasos
3. Ir a: Contraseñas de aplicaciones
4. Generar: Contraseña para "La Lavandería App"
5. Copiar: Los 16 caracteres (sin espacios)
6. Configurar: Variables en .env o Render
7. Probar: Registrar un usuario nuevo
```

## 🎥 Video Tutorial (Alternativo)

Si prefieres ver un video, busca en YouTube:
- "Como crear app password gmail 2024"
- "Contraseña de aplicación Gmail"

## 💡 Consejos de Seguridad

1. **Nunca compartas tu App Password**: Es como dar la llave de tu correo
2. **Una App Password por aplicación**: Si la aplicación se compromete, solo revoca esa contraseña
3. **Revoca contraseñas que no uses**: Ve a tu cuenta de Google > Seguridad > Contraseñas de aplicaciones y elimina las que ya no necesites
4. **Usa un correo dedicado**: Considera usar un correo específico para la aplicación, no tu correo personal

## ❓ ¿Necesitas Ayuda?

Si tienes problemas:
1. Revisa los logs de Render para ver el error exacto
2. Verifica que la cuenta de Gmail no tenga restricciones
3. Intenta con otro correo de Gmail
4. Asegúrate de que la aplicación esté usando las variables de entorno correctas
