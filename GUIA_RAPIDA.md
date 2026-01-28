# � Desplegar en Render (5 minutos)

## Tu Configuración

```
Base de Datos: AlwaysData (fabianmedina.alwaysdata.net)
Hosting: Render
Usuario: fabianmedina
BD: fabianmedina_miapp
```

## 3 Pasos

### 1. Ir a Render Dashboard
```
https://dashboard.render.com
→ Tu Web Service
→ Settings → Environment
```

### 2. Agregar Variables
```
DATABASE_URL
mysql+pymysql://fabianmedina:Dragones07@fabianmedina.alwaysdata.net:3306/fabianmedina_miapp?charset=utf8mb4

SECRET_KEY
tu_clave_segura_aleatoria
```
Haz clic en **Save**

### 3. Redeploy
```
Deploy → Redeploy Latest Commit
```

Cuando aparezca "Live", abre tu URL y prueba login.

## ✅ Listo
Tu app está en Render conectada a tu BD en AlwaysData.
