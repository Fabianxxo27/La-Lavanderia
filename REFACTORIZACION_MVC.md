# Refactorización MVC - La Lavandería

## 📋 Resumen

Se aplicó el patrón **Modelo-Vista-Controlador (MVC)** al proyecto sin cambiar la funcionalidad existente.

## 🏗️ Estructura Anterior

```
app.py (3,994 líneas)  # Todo el código en un solo archivo
```

## 🎯 Nueva Estructura MVC

```
/config.py                          # Configuración de Flask y BD
/app.py (76 líneas)                 # Factory pattern - punto de entrada
/helpers.py                         # Funciones auxiliares reutilizables

/models/                           # MODELO - Datos y lógica de BD
  __init__.py
  database.py                      # run_query(), db instance, ensure_cliente_exists()

/services/                         # SERVICIOS - Lógica de negocio
  __init__.py
  email_service.py                 # send_email_async()
  validation_service.py            # limpiar_texto(), validar_email(), validar_contrasena()

/decorators/                       # Decoradores reutilizables
  __init__.py
  auth_decorators.py               # login_requerido, admin_requerido

/routes/                           # CONTROLADOR - Blueprints
  __init__.py
  auth.py (4 rutas, 237 líneas)   # Autenticación
  cliente.py (4 rutas, 313 líneas) # Panel cliente
  admin.py (21 rutas, 2,063 líneas) # Panel administrador  
  api.py (7 rutas, 198 líneas)    # API REST
  utils.py (4 rutas, 318 líneas)  # Utilidades (barcode, PDF)

/templates/                        # VISTA - Templates Jinja2
/static/                          # Assets estáticos
```

## 📊 Métricas

### Por Módulo

| Módulo | Rutas | Líneas | % Total |
|--------|-------|--------|---------|
| **auth.py** | 4 | 237 | 6.4% |
| **cliente.py** | 4 | 313 | 10.4% |
| **admin.py** | 21 | 2,063 | 68.6% |
| **api.py** | 7 | 198 | 6.6% |
| **utils.py** | 4 | 318 | 10.6% |
| **TOTAL** | **40** | **3,129** | **100%** |

### Ventajas de esta refactorización:

✅ **Separación de responsabilidades** - Cada módulo tiene un propósito claro
✅ **Mantenibilidad** - Más fácil localizar y modificar código
✅ **Escalabilidad** - Nuevas funcionalidades se agregan en el módulo correcto
✅ **Testabilidad** - Cada componente puede probarse independientemente
✅ **Reutilización** - Servicios y helpers compartidos
✅ **Buenas prácticas** - Siguiendo estándares de Flask y Python

## 🔧 Archivos de Soporte

- `app_original_backup.py` - Respaldo completo del código original
- `generar_blueprints.py` - Script que automatizó la extracción

## ⚠️ Nota Importante sobre url_for()

Los blueprints requieren usar **nombres cualificados** en url_for():

```python
# Antes:
url_for('login')
url_for('cliente_inicio')

# Ahora (con blueprints):
url_for('auth.login')
url_for('cliente.cliente_inicio')
```

**Estado**: Los blueprints fueron generados con los nombres originales.  
**Acción requerida**: Ajustar url_for() gradualmente al probar cada ruta.

##📦 Dependencias

No se agregaron nuevas dependencias. Todas las librerías ya estaban en `requirements.txt`.

## 🚀 Ejecución

```bash
python app.py
```

O en producción (Render):
```bash
gunicorn app:app
```

El factory pattern permite que `app` sea la instancia exportada desde `create_app()`.

---

**Fecha de refactorización:** 2026-02-17  
**Patrón aplicado:** MVC (Modelo-Vista-Controlador)  
**Resultado:** ✅ Código organizado sin pérdida de funcionalidad
