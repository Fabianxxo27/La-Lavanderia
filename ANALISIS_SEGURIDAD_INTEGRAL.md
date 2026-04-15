# Análisis Integral de Seguridad en La Lavandería

## Introducción

La Lavandería implementa un sistema de seguridad multinivel que protege tanto los datos de los usuarios como la integridad de la aplicación. Este documento realiza un análisis exhaustivo de todas las medidas de seguridad implementadas, comenzando por la protección de contraseñas y expandiéndose a validación de entrada, autenticación, autorización, protección de sesiones y prevención de ataques comunes. Cada medida se documenta con referencias exactas al código, explicación de cómo funciona, y comparación con estándares industriales.

---

## 1. Protección de Contraseñas

### 1.1 Almacenamiento seguro con PBKDF2-SHA256

La Lavandería utiliza el algoritmo PBKDF2-SHA256 para el almacenamiento de contraseñas. Este algoritmo, implementado a través de la librería Werkzeug, es recomendado por OWASP (Open Web Application Security Project) como un estándar seguro para la protección de credenciales. El algoritmo PBKDF2 (Password-Based Key Derivation Function 2) funciona aplicando la función hash SHA256 múltiples veces —específicamente 160,000 iteraciones de forma predeterminada en Werkzeug— lo que hace computacionalmente prohibitivo intentar ataques de fuerza bruta contra las contraseñas almacenadas.

Cada contraseña genera automáticamente un **salt único y aleatorio**, lo que significa que incluso si dos usuarios tienen la misma contraseña, sus hashes almacenados en la base de datos serán completamente diferentes. El formato del hash resultante es `pbkdf2:sha256:160000$<salt_aleatorio>$<hash_final>`, donde el prefijo identifica el algoritmo, 160000 representa las iteraciones, y el resto es una cadena de 128 caracteres que no puede revertirse a la contraseña original.

Las contraseñas se hashean en **cuatro ubicaciones clave**. Primero, durante el registro de nuevos usuarios en `routes/auth.py` línea 163, cuando se ejecuta `generate_password_hash(password, method='pbkdf2:sha256')`. Segundo, cuando los clientes cambian sus contraseñas en `routes/cliente.py` línea 226, en la ruta `/cliente_cambiar_contrasena`. Tercero, cuando un usuario reestablece una contraseña olvidada en `routes/auth.py` línea 455, después de validar un token de seguridad. Y cuarto, cuando un administrador crea rápidamente una cuenta de usuario en `routes/admin.py` línea 1039, con una contraseña autogenerada.

### 1.2 Validación de fortaleza según rol

La aplicación implementa **dos niveles de complejidad** para las contraseñas, diferenciados por el rol del usuario. Para los clientes, cuyas operaciones son más limitadas, se requiere un mínimo de 6 caracteres que deben incluir al menos una letra (A-Z o a-z) y al menos un número (0-9), validados mediante expresiones regulares en `services/validation_service.py` líneas 42-52. El código valida cada requisito verificando que la cadena tenga suficiente longitud, contenga patrones alfabéticos y numéricos.

Para los administradores, que tienen acceso a funciones críticas del sistema, los requisitos son más estrictos. Se requiere un mínimo de 8 caracteres, al menos una letra mayúscula, al menos una letra minúscula, y al menos un número. Esta validación se encuentra en `routes/admin.py` línea 156, reflejando el principio de que los usuarios con mayores privilegios deben tener credenciales más fuertes. Los ejemplos válidos para clientes incluyen `Cliente123` o `Pass01`, mientras que para administradores sería necesario `Admin2024` o `Seguro123`.

### 1.3 Verificación de contraseñas en login

Durante el proceso de inicio de sesión, documentado en `routes/auth.py` líneas 56-95, la aplicación nunca compara contraseñas en texto plano. En su lugar, utiliza la función `check_password_hash(hashed_from_db, user_input)` de Werkzeug, que aplica el mismo algoritmo PBKDF2-SHA256 a la entrada del usuario con el mismo salt original, y compara el resultado con el hash almacenado en la base de datos. Si coinciden, la contraseña es correcta; si no, se muestra un mensaje genérico "Usuario o contraseña incorrectos" sin revelar cuál es incorrecto, previniendo así ataques de enumeración.

La verificación se implementa de manera defensiva con manejo de excepciones para casos donde el hash en la base de datos pueda estar corrupto o malformado. El código verifica que el usuario exista y que la contraseña sea correcta antes de crear la sesión, proporcionando un mensaje de error genérico que no revela si el username o la contraseña fue incorrecta, lo cual es una práctica de seguridad fundamental.

---

## 2. Autenticación y Autorización

### 2.1 Decoradores de protección

La arquitectura de seguridad utiliza **decoradores Python** para proteger rutas y funciones. El decorador `@login_requerido`, definido en `decorators/auth_decorators.py` líneas 8-24, verifica que el usuario tenga una sesión activa antes de permitir acceso a cualquier ruta autenticada. Si el usuario intenta acceder sin autenticarse, es redirigido automáticamente a la página de login con un mensaje de advertencia.

Además, el decorador `@admin_requerido`, definido en líneas 28-48 del mismo archivo, no solo verifica la autenticación sino también el rol del usuario. Comprueba que `session.get('rol')` sea igual a `'administrador'` (normalizado a minúsculas para evitar inconsistencias). Si un cliente intenta acceder a una ruta administrativa, recibe un mensaje de error y es redirigido a su panel de cliente. Este sistema de decoradores aplica el principio de menor privilegio: cada ruta requiere solo los permisos necesarios, y multiples endpoints críticos como `/admin/inicio`, `/pedido_prendas/<id>`, y `/lector_barcode` están protegidos por estos decoradores.

### 2.2 Sesiones seguras

Las sesiones se configuran con múltiples capas de seguridad en `config.py` líneas 24-26. El atributo `SESSION_COOKIE_HTTPONLY = True` hace que la cookie de sesión sea inaccesible desde JavaScript, previniendo que scripts maliciosos (ataques XSS) puedan robar la cookie de sesión. El atributo `SESSION_COOKIE_SAMESITE = 'Lax'` implementa protección contra ataques CSRF (Cross-Site Request Forgery) al asegurar que los navegadores solo envíen la cookie en requests que se originen del mismo sitio o mediante navegación de alto nivel.

La sesión tiene una duración máxima de 2 horas mediante `PERMANENT_SESSION_LIFETIME = datetime.timedelta(hours=2)`. Después de este tiempo, la sesión expira automáticamente y el usuario debe volver a iniciar sesión. Durante el inicio de sesión exitoso, la sesión se inicializa en `routes/auth.py` líneas 81-88 con información esencial: el ID del usuario, nombre de usuario, rol, y nombre completo. Esto se realiza después de limpiar cualquier sesión anterior con `session.clear()`, previniendo ataques de fijación de sesión donde un atacante podría intentar mantener una sesión controlada.

### 2.3 Cierre de sesión

El cierre de sesión en `routes/auth.py` línea 474 implementa el decorador `@login_requerido` y ejecuta `session.clear()`, que elimina completamente toda la información de sesión del navegador. Esto es crítico para dispositivos compartidos, asegurando que el siguiente usuario no pueda acceder a la sesión del anterior. La ruta `/logout` está protegida por el decorador, lo que significa que solo usuarios autenticados pueden ejecutar esta acción.

---

## 3. Validación y Sanitización de Entrada

### 3.1 Limpieza de texto contra XSS

Un ataque Cross-Site Scripting (XSS) ocurre cuando un atacante inyecta código malicioso que se ejecuta en el navegador de otros usuarios. La Lavandería previene esto mediante la función `limpiar_texto()` en `services/validation_service.py` líneas 7-19. Esta función convierte la entrada a string y la recorta de espacios en blanco, elimina todas las etiquetas HTML mediante expresiones regulares, y limita la longitud máxima de entrada para prevenir buffer overflows.

Cuando un usuario ingresa datos como nombre, email, o dirección, todos pasan por esta función. Por ejemplo, en `routes/auth.py` línea 276, el email se procesa con `email = limpiar_texto(request.form.get('email', '').strip().lower(), 120)`. Si un atacante intenta inyectar `<script>alert('XSS')</script>`, la función elimina las etiquetas, resultando en texto `alert('XSS')` inofensivo. Los templates Jinja2 también utilizan escapado automático de forma predeterminada, proporcionando doble protección: una en backend donde se limpian los datos antes de almacenarlos, y otra en el frontend donde Jinja2 escapa cualquier contenido especial al renderizar HTML.

### 3.2 Validación de email

La validación de email en `services/validation_service.py` líneas 31-43 utiliza una expresión regular que verifica el formato estándar. La expresión busca caracteres alfanuméricos seguidos de un símbolo @, más caracteres de dominio, un punto, y finalmente una extensión de 2 o más caracteres. Esto asegura que solo se acepten emails válidos, previniendo inyecciones maliciosas o datos malformados que podrían causar problemas en el sistema de envío de correos o en consultas a la base de datos.

### 3.3 Prevención de SQL Injection

La aplicación utiliza **consultas parametrizadas** mediante SQLAlchemy y la función `text()` en `models/database.py`. Cada consulta utiliza placeholders nombrados (`:placeholder`) en lugar de concatenación directa de strings. La función `run_query()` siempre ejecuta consultas con `text(query)` y pasa los parámetros como diccionario separado, lo que hace que SQLAlchemy o el driver de la base de datos escape automáticamente cualquier carácter especial.

Un ejemplo real de `routes/auth.py` línea 69 muestra esto correctamente: se consulta a la base de datos con `SELECT * FROM usuario WHERE LOWER(username) = :u` y se pasa `{"u": username}` como parámetro. Si alguien intenta SQL injection como `admin'; DROP TABLE usuario; --`, el parámetro es tratado como un string literal, no como código SQL, haciendo que la inyección sea inefectiva. Este enfoque es más seguro que incluso ORM porque proporciona control explícito y es verificable.

### 3.4 Limitación de tamaño de contenido

En `config.py` línea 25, se configura `MAX_CONTENT_LENGTH = 16 * 1024 * 1024`, limitando a 16 MB el tamaño máximo de cualquier request. Esto previene ataques de denegación de servicio donde alguien intenta enviar datos enormes para abrumar la aplicación o consumir toda la memoria disponible del servidor. Flask automáticamente rechaza cualquier request que exceda este límite con un error 413 Payload Too Large.

---

## 4. Verificación de Email y Códigos de Seguridad

### 4.1 Generación de códigos criptográficos

Cuando un usuario se registra o solicita una recuperación de contraseña, se genera un código de verificación de 6 dígitos. La generación en `services/verification_service.py` líneas 13-17 utiliza `secrets.choice()`, una función criptográficamente segura integrada en Python. El módulo `secrets` está específicamente diseñado para generar tokens criptográficamente seguros adecuados para usos de seguridad, a diferencia de `random` que es predecible y adecuado solo para juegos o simulaciones.

El código genera cada dígito seleccionando aleatoriamente de la cadena `string.digits` que contiene los caracteres 0-9. Esto genera 1,000,000 combinaciones posibles (000000 a 999999), cada una con igual probabilidad de selección. No es posible predecir el siguiente código basándose en los anteriores, haciendo infrutífero cualquier intento de adivinanza sistemática.

### 4.2 Almacenamiento y expiración de códigos

Los códigos se almacenan en la tabla `verification_codes` con una marca de tiempo de expiración establecida a 15 minutos. El método `VerificationCodeModel.limpiar_expirados()` elimina automáticamente códigos viejos que han expirado, manteniendo la base de datos limpia. Cuando se valida un código, el sistema verifica múltiples condiciones: que el código existe en la base de datos, que es del tipo esperado (email_verification, password_reset, etc.), que no ha sido usado previamente, y que no ha expirado.

Después de validar exitosamente, se marca como `used=True`, asegurando que un código solo pueda usarse una única vez. Si alguien intenta reutilizar un código válido después de que ya fue usado, el sistema rechaza el intento. Si permanece más de 15 minutos sin usarse, expira automáticamente.

---

## 5. Recuperación Segura de Contraseña Olvidada

### 5.1 Prevención de enumeración de usuarios

Cuando un usuario solicita recuperar una contraseña en `routes/auth.py` líneas 269-350, la aplicación implementa una medida de seguridad importante: **nunca revela si un email existe o no en el sistema**. Esto previene que atacantes enumeren todos los emails válidos del sistema. El código busca el usuario con la consulta parametrizada, pero independientemente de si encuentra un resultado o no, muestra el mismo mensaje: "Si el email existe en nuestro sistema, recibirá un enlace de recuperación."

Si el usuario existe, se genera un token y se envía por email. Si no existe, no se hace nada pero el usuario ve el mismo mensaje. Esto hace que sea imposible usar la funcionalidad de olvido de contraseña para descubrir qué emails están registrados en el sistema, lo cual es una protección importante contra el reconocimiento previo a ataques dirigidos.

### 5.2 Generación de tokens seguros

Para asegurar que solo el propietario del email pueda resetear su contraseña, se generan tokens criptográficos firmados usando `itsdangerous.URLSafeTimedSerializer`. Estos tokens son URL-safe, lo que significa que pueden incluirse en links sin causar problemas con caracteres especiales; están firmados criptográficamente, lo que impide que sean alterados sin invalidar la firma; e incluyen un timestamp, permitiendo verificar cuándo se generaron.

El token se genera en `routes/auth.py` línea 345 y se envía al usuario por email como parte de un link como `https://app.com/restablecer-contrasena?token=<token>`. La función `_get_reset_secret_key()` proporciona una clave estable para firmar tokens que persiste entre reinicios de la aplicación, asegurando que tokens generados antes de un reinicio todavía sean válidos después del mismo.

### 5.3 Validación y expiración de tokens

Cuando el usuario hace clic en el link, se valida el token en `routes/auth.py` líneas 35-41 con `_validar_token_reset_fallback()`. Esta función usa `serializer.loads(token, salt='password-reset', max_age=1800)` donde `max_age=1800` establece que los tokens expiren después de 1800 segundos (30 minutos). Si alguien intenta usar un token después de 30 minutos, `SignatureExpired` se lanza y el reset es rechazado con un mensaje indicando que debe solicitar un nuevo link.

Si alguien intenta modificar el token, `BadSignature` se lanza, rechazando el intento. Si el token es válido y no expirado, se devuelve el email incluido en el token, permitiendo que continúe el proceso de reset.

---

## 6. Protección en el Cambio de Contraseña Autenticado

### 6.1 Verificación de contraseña actual

Cuando un cliente quiere cambiar su contraseña desde su panel, implementado en `routes/cliente.py` líneas 169-240, primero debe verificar su contraseña actual. Esto es una medida de seguridad crítica que asegura que incluso si alguien obtiene acceso físico a la sesión del usuario (por ejemplo, en un café con wifi público), no puede cambiar la contraseña sin conocer la actual.

El código obtiene el usuario actual de la base de datos, recupera la contraseña actual que el usuario ingresa en el formulario, y usa `check_password_hash()` para comparar la entrada con el hash almacenado. Maneja excepciones para el caso donde el hash pueda estar corrupto. Si la contraseña no es correcta, se muestra un mensaje de error y se le pide al usuario que intente nuevamente. Solo después de verificar exitosamente la contraseña actual se permite proceder con el cambio.

### 6.2 Validación de nueva contraseña

Después de verificar la contraseña actual, se valida la nueva contraseña con los requisitos específicos para clientes. Se verifica que tenga al menos 6 caracteres, contenga al menos una letra, y contenga al menos un número. Si no cumple con estos requisitos, se muestra un mensaje de error específico indicando exactamente cuál requisito no se cumplió, y se devuelve al formulario sin procesar el cambio.

Se verifica también que la nueva contraseña sea diferente a la actual, evitando cambios que resultarían en la misma contraseña. Esto previene que el usuario accidentalmente haga un cambio que no resulta en un cambio real.

### 6.3 Confirmación en frontend

Antes de enviar el formulario, el frontend en `templates/cliente_cambiar_contrasena.html` valida que la nueva contraseña y su confirmación sean idénticas, proporcionando feedback visual en tiempo real. Si coinciden, el campo de confirmación se vuelve verde; si no coinciden, se vuelve rojo. Adicionalmente, se solicita confirmación mediante un modal bootstrap antes de procesar el cambio, asegurando que sea una acción intencional. El usuario debe hacer clic en un botón de confirmación en el modal para finalmente procesar el cambio.

---

## 7. Protección contra Ataques Comunes

### 7.1 Headers HTTP de seguridad

En `app.py` líneas 34-37, se agregan headers HTTP después de cada respuesta mediante el decorador `@app.after_request`. Esto aplica a toda respuesta que sale de la aplicación, haciéndolo una protección aplicada globalmente.

El header `X-Content-Type-Options: nosniff` previene que navegadores adivinen el tipo de contenido. Sin este header, un navegador podría servirse un archivo .js como HTML si alguien lo solicita. Con este header, el navegador respeta el Content-Type enviado por el servidor.

El header `X-Frame-Options: SAMEORIGIN` previene que la aplicación se cargue dentro de un iframe de un sitio diferente, evitando ataques de clickjacking donde se oculta contenido de la aplicación bajo un iframe y se engaña al usuario para que haga clic en elementos invisibles.

El header `X-XSS-Protection: 1; mode=block` instruye a navegadores antiguos (principalmente Internet Explorer) que bloqueen páginas si detectan posible XSS, aunque navegadores modernos ignoran este header en favor de Content-Security-Policy.

### 7.2 Escapado de templates

Los templates Jinja2 utilizan escapado automático por defecto. Cuando se muestra información de usuario en HTML, como `<h1>Bienvenido {{ usuario.nombre }}</h1>`, Jinja2 automáticamente escapa caracteres peligrosos. Si `usuario.nombre` contiene `<script>`, se renderiza como `&lt;script&gt;`, convirtiéndolo en texto inofensivo en lugar de código ejecutable en el navegador.

Este escapado es automático a menos que se use el filtro `|safe`, que debe ser usado con extrema cautela solo cuando se tiene la certeza de que el contenido es seguro. La combinación de limpieza en backend y escapado en templates proporciona defensa en profundidad contra XSS.

### 7.3 Post-Redirect-Get pattern

Cuando se procesa un formulario POST exitosamente, se utiliza `redirect()` en lugar de renderizar directamente la respuesta. Por ejemplo, después de cambiar una contraseña, se ejecuta `return redirect(url_for('cliente.cliente_perfil'))`. Esto implementa el patrón Post-Redirect-Get (PRG) que previene un problema común en aplicaciones web.

Sin este patrón, si el usuario presiona F5 después de enviar un formulario, el navegador enviaría nuevamente el mismo POST, causando que la acción se ejecute dos veces. Con PRG, el POST se procesa, se guarden los cambios, y se redirige a una página GET, por lo que presionar F5 simplemente recarga esa página GET sin duplicar la acción.

---

## 8. Configuración de Seguridad en Deployment

### 8.1 Generación de SECRET_KEY

En `config.py` líneas 18-23, se genera una `SECRET_KEY` de 256 bits (32 bytes) usando `secrets.token_hex(32)`. Esta clave se utiliza para firmar sesiones y tokens en toda la aplicación. Si existe una variable de entorno `SECRET_KEY`, se utiliza esa; de lo contrario, se genera una nueva aleatoriamente. La validación asegura que nunca sea menor a 128 bits, garantizando suficiente entropía.

En producción deployada en Render, se establece la variable de entorno `SECRET_KEY` a una cadena aleatoria larga, evitando que se genere una nueva cada vez que se reinicia el servidor. Esta consistencia es importante porque si cambia la clave entre reinicios, todas las sesiones existentes se invalidarían, desconectando a todos los usuarios.

### 8.2 Base de datos segura

En producción en Render, la aplicación se conecta a PostgreSQL mediante `DATABASE_URL`, una variable de entorno proporcionada por Render. En `config.py` líneas 32-50, el código inteligentemente maneja ambos escenarios: en desarrollo local usa `credentials.py` para MySQL/PostgreSQL local, y en producción usa `DATABASE_URL` de Render.

La URL se codifica para gestionar caracteres especiales en contraseñas mediante `urllib.parse.quote_plus()`. La conexión se configura con opciones de conexión segura mediante `SQLALCHEMY_ENGINE_OPTIONS`, incluyendo pool de conexiones, reciclaje de conexiones, y pre-ping para verificar que la conexión siga activa.

### 8.3 HTTPS en producción

En Render, HTTPS se configura automáticamente. Todos los comentarios en el código enfatizan esto, y la aplicación confía en que Render maneja los certificados SSL/TLS. El navegador siempre comunica con la aplicación a través de TLS/SSL, encriptando todos los datos en tránsito, incluyendo contraseñas y tokens de sesión.

Cualquier intento de acceder a la aplicación a través de HTTP (no encriptado) es redirigido a HTTPS automáticamente por Render. Esto protege todas las comunicaciones entre el navegador del usuario y el servidor de ser interceptadas o modificadas.

---

## 9. Flujo de Seguridad Completo: Casos de Uso

### 9.1 Registro de nuevo usuario

Un nuevo usuario accede a la página de registro en `registro.html`, completa el formulario con username, email, contraseña, y confirmación de contraseña, y hace clic en registrarse. El navegador valida básicamente la coincidencia de contraseñas, pero esto es solo para mejorar la experiencia del usuario.

El backend recibe el POST `/registro` y comienza la validación. Se verifica que el email tenga un formato válido usando la expresión regular de validación. Se limpia el email con `limpiar_texto()` para eliminar cualquier etiqueta HTML o contenido sospechoso. Se verifica que el username no esté ya registrado. Se valida la contraseña asegurando que tenga al menos 6 caracteres, contenga al menos una letra y al menos un número.

Se genera el hash de la contraseña con `generate_password_hash(password, method='pbkdf2:sha256')`, que internamente genera un salt único y aplica 160,000 iteraciones del algoritmo SHA256. Se almacena en la base de datos el username, email, y hash (nunca la contraseña en texto plano). Se genera un código de verificación de 6 dígitos usando `secrets.choice()`, se almacena en la tabla `verification_codes` con expiración de 15 minutos.

Se envía un email al usuario con el código de verificación. Se muestra una página indicando que debe verificar su email. Cuando el usuario hace clic en el link o ingresa el código, se valida que sea correcto, no haya sido usado, y no haya expirado. Al validar exitosamente, se marca como `used=True` y se activa la cuenta.

### 9.2 Login del usuario

El usuario ingresa su username y contraseña en el formulario de login en `login.html`. El navegador envía POST `/login` al backend. El backend busca en la base de datos con `run_query("SELECT ... WHERE username = :u", {"u": username})`, usando parametrización para prevenir SQL injection.

Se ejecuta `check_password_hash(hash_almacenado, contraseña_ingresada)` que aplica el algorithm PBKDF2-SHA256 con el salt original y compara el resultado con el hash almacenado. Si coinciden, se ejecuta si no coinciden, se muestra un mensaje genérico "Usuario o contraseña incorrectos" sin revelar cuál fue incorrecto.

Una vez que la contraseña es verificada, se ejecuta `session.clear()` para limpiar cualquier sesión anterior, impidiendo ataques de fijación de sesión. Se crea una nueva sesión con `session['id_usuario']`, `session['username']`, `session['rol']` (normalizado a minúsculas), y `session['nombre']`. Se establece `session.permanent = True` para que persista según `PERMANENT_SESSION_LIFETIME`.

Se redirige al usuario: si es administrador, a `/admin/inicio`; si es cliente, a `/cliente_inicio`. El navegador automáticamente almacena la cookie de sesión que es HTTPONLY (no accesible desde JavaScript) y SAMESITE=Lax (solo enviada en requests del mismo sitio).

### 9.3 Cambio de contraseña autenticado

El cliente autenticado accede a `/cliente_cambiar_contrasena` que está protegido por `@login_requerido`. La página muestra un formulario pidiendo contraseña actual, contraseña nueva, y confirmación. Se obtiene el usuario actual de la sesión y se busca en la base de datos.

Se solicita la contraseña actual. Se valida contra el hash almacenado con `check_password_hash()`. Si no coincide, se rechaza. Si coincide, se solicita la nueva contraseña. Se valida que sea diferente a la actual, que tenga al menos 6 caracteres, letra, y número. Se solicita confirmación.

Se muestra un modal de confirmación pidiendo que el usuario confirme la acción, asegurando que es intencional. Solo después de hacer clic en "Confirmar" se procesa el cambio. Se genera el nuevo hash con `generate_password_hash()` y se actualiza en la base de datos. Se muestra un mensaje de éxito y se redirige al perfil del cliente.

### 9.4 Recuperación de contraseña olvidada

El usuario en la página de login hace clic en "¿Olvidaste tu contraseña?" y es dirigido a `olvide_contrasena`. Ingresa su email y hace clic en "Enviar enlace de recuperación". El backend busca el usuario pero **nunca revela si existe o no**, mostrando el mismo mensaje en ambos casos.

Si existe, genera un token firmado con `URLSafeTimedSerializer` que expira en 30 minutos. Envía un email con un link como `https://app.com/restablecer-contrasena?token=<token>`. Cuando el usuario hace clic, el backend valida el token con `_validar_token_reset_fallback()`, verifica que no haya expirado, y muestra un formulario para ingresar nueva contraseña.

Se valida la nueva contraseña según requisitos. Se genera el nuevo hash. Se actualiza en la base de datos. Se muestra mensaje de éxito indicando que puede iniciar sesión con la nueva contraseña.

---

## 10. Comparación con Estándares Industriales

| Medida de Seguridad | La Lavandería | Recomendación OWASP | Cumplimiento |
|---------------------|---------------|---------------------|--------------|
| **Algoritmo hashing** | PBKDF2-SHA256 | PBKDF2, bcrypt, scrypt, Argon2 | ✅ Cumple |
| **Iteraciones hash** | 160,000 | 100,000+ | ✅ Cumple |
| **Salt único** | Sí, automático | Obligatorio | ✅ Cumple |
| **Longitud salt** | 64 bits (mínimo generado por Werkzeug) | 128 bits | ⚠️ Borderline |
| **HTTPS** | Sí, Render | Obligatorio | ✅ Cumple |
| **Cookies HTTPONLY** | Sí | Obligatorio | ✅ Cumple |
| **CSRF protection** | Sí, SAMESITE=Lax | Obligatorio | ✅ Cumple |
| **Validación entrada** | Sí, limpieza + regex | Obligatorio | ✅ Cumple |
| **Parametrized queries** | Sí, SQLAlchemy | Obligatorio | ✅ Cumple |
| **Token expiración** | Sí (30 min reset, 15 min email) | 15-60 min | ✅ Cumple |
| **Sesión expiración** | 2 horas | Configurable | ✅ Cumple |
| **Contraseñas mínimas** | Clientes 6, Admins 8 | OWASP 8+ | ⚠️ Clientes bajos |
| **Verificación email actual** | No | Recomendado | ❌ No |
| **2FA** | No | Recomendado para admin | ❌ No |
| **Rate limiting login** | No | Recomendado | ❌ No |
| **Headers HTTP security** | 3 headers | 5+ recomendado | ⚠️ Incompleto |
| **Logging de seguridad** | Básicos | Recomendado | ⚠️ Incompleto |

---

## 11. Recomendaciones de Mejora

### 11.1 Corto plazo (Fácil, < 1 hora)

**Aumentar requisito de contraseña a mínimo 8 caracteres para clientes**. Actualmente es 6, lo que es relativamente bajo. Cambiar la línea en `services/validation_service.py` de 6 a 8 aumentaría significativamente la seguridad. Esto afectaría solo a nuevas contraseñas; las existentes permanecerían igual.

**Implementar rate limiting en login**. Agregar la librería `flask_limiter` y decorar la función login con `@limiter.limit("5 per minute")`. Esto previene ataques de fuerza bruta al permitir solo 5 intentos por minuto. El usuario legítimo raramente necesita más de 5 intentos, pero un bot de ataque podría intentar miles.

**Agregar más headers HTTP de seguridad**. Implementar `Strict-Transport-Security` para forzar HTTPS, y `Content-Security-Policy` para prevenir ciertos tipos de ataques XSS. Esto requiere quizás 10 líneas de código.

### 11.2 Mediano plazo (Moderado, 4-8 horas)

**Migrar a bcrypt**. Aunque PBKDF2 es seguro, bcrypt es específicamente diseñado para contraseñas y es más resistente a ataques con GPU/ASIC. Cambiar `method='pbkdf2:sha256'` a `method='bcrypt'` en Werkzeug requiere instalar `bcrypt` y puede causar inicios de sesión más lentos (bcrypt es intencionalmente lento).

**Implementar logging de intentos fallidos**. Registrar quién intentó login fallido, con qué usuario, desde qué IP, y en qué momento. Alertar si hay más de 3 intentos fallidos desde la misma IP en 5 minutos. Esto ayudaría a detectar ataques en tiempo real.

**Implementar 2FA para administradores**. Requerir autenticación de dos factores para cuentas administrativas usando TOTP (Time-based One-Time Password), SMS, o autenticador de email. Esto protegería las cuentas con mayores privilegios significativamente.

### 11.3 Largo plazo (Significativo, 16+ horas)

**Autenticación de dos factores completa**. Extender 2FA a todos los usuarios, no solo admins. Integrar con autenticadores como Google Authenticator o Authy.

**Historial de cambios de contraseña**. Mantener registro de cambios previos y prevenir reutilización de contraseñas recientes. Esto previene que usuarios cambien a una contraseña que acababan de cambiar la semana anterior.

**Single Sign-On (SSO)**. Integrar OAuth2 con Google, Microsoft, o GitHub para permitir que usuarios inicien sesión con sus cuentas existentes. Esto reduce la fatiga de contraseña y las malas prácticas de reutilización.

**Monitoreo y análisis de seguridad**. Implementar alertas para comportamientos sospechosos: múltiples fallos de login, múltiples cambios de contraseña, acceso desde ubicaciones geográficas inusuales, etc.

---

## 12. Conclusión

**La Lavandería implementa un nivel de seguridad sólido, robusto y basado en estándares industriales**, especialmente considerando que es un proyecto académico de grado. La aplicación protege las contraseñas mediante hashing criptográfico PBKDF2-SHA256 estándar con 160,000 iteraciones y salt único generado automáticamente. Las sesiones están protegidas contra CSRF mediante cookies SAMESITE y contra XSS mediante HTTPONLY.

La validación de entrada previene SQL injection mediante consultas parametrizadas en todo el código. Los tokens de recuperación de contraseña expiran en 30 minutos y no revelan si un email existe en el sistema, previniendo enumeración de usuarios. El control de acceso se implementa mediante decoradores aplicados consistentemente a todas las rutas sensibles. Los datos en tránsito se encriptan mediante HTTPS en producción.

**Fortalezas principales:**
- ✅ PBKDF2-SHA256 con 160,000 iteraciones y salt único automático
- ✅ Validación robusta de entrada contra XSS en backend y frontend
- ✅ Consultas parametrizadas confiables contra SQL injection
- ✅ Sesiones HTTPONLY + SAMESITE contra CSRF
- ✅ Tokens con firma criptográfica y expiración
- ✅ Decoradores consistentes para control de acceso basado en rol
- ✅ HTTPS obligatorio en producción en Render
- ✅ Headers HTTP de seguridad

**Áreas de mejora:**
- ⚠️ Rate limiting en login sería fácil de agregar
- ⚠️ 2FA para administradores sería ideal para producción
- ⚠️ Más headers de seguridad (CSP, HSTS, HPKP)
- ⚠️ Logging más detallado de eventos de seguridad
- ⚠️ Requisito de 8 caracteres mínimos para clientes (actualmente 6)

Para un **proyecto de grado académico**, esta implementación es **excelente, bien fundamentada, y lista para defensa**. Se pueden presentar todas las medidas de seguridad implementadas como evidencia de arquitectura robusta, decisiones de diseño conscientes de seguridad, y conocimiento profundo de amenazas y mitigaciones. Para uso en producción real con datos sensibles, aplicar las recomendaciones de mejora proporcionaría seguridad adicional, pero la base implementada es sólida y profesional.
