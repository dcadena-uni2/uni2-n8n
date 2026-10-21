# Login estándar con Microsoft 365 para flujos n8n

**Tarea:** #389 (antecedente: #374) · **Última actualización:** 20/10/2026 · **Instancia:** `https://uni2.app.n8n.cloud` (plan Pro)

Este documento resume lo que se construyó, por qué se diseñó así, cómo funcionan las sesiones y cómo agregar el login a un flujo nuevo, paso a paso.

---

## 1. Resumen

- Existe **un único flujo de login**, **Login Microsoft 365**, que comparten todos los flujos n8n usados por personas. Hace el ingreso con Microsoft, el regreso, la verificación de sesión, el cierre de sesión, el registro de accesos y la limpieza diaria.
- **Estándar del equipo:** todo formulario para personas se construye con **Webhooks y páginas propias**, **no con nodos Form** de n8n. Es la única forma de que la sesión quede ligada al navegador.
- La interfaz (marca UNI2, banner con el usuario, botón *Cerrar sesión*, formularios) sale de **una fuente única**: `n8n_ui/ui_estandar.js`.
- Hay dos tablas de seguimiento: **sesiones activas** (quién está conectado, en qué app) y **registro de accesos** (inicios y cierres de sesión, con 90 días de retención). Ambas tienen limpieza automática diaria.

### Estado por flujo

| Flujo | Estado |
|---|---|
| **Reconstruye** (`io6wE6X97L0skPAG`) | ✅ **En producción** con el login estándar desde el 20/10/2026 |
| **RindegastosSAP** (`OtyruCQv37g4mnlH`) | ✅ **En producción** desde el 20/10/2026 (versión `f3d0bec8`; la anterior, `9f7987b5` "DEBITOR ACCOUNT", queda para reversión). Enlace: `/webhook/rindegastos-sap`. Incluye validación del ID de informe (8 dígitos) y la página de resultado por secciones |
| **ReporteWompi** (`RSSn3yOijowfQ1Px`) | ⏳ Pendiente (ver §9) |
| **Extractor de Facturación SIIF** (`48FfYGGiN8ns8pw9`) | ⏳ Pendiente, coordinar con Luis Meza (ver §9) |
| **Crítica Contable Diaria SIIF** (`z9kiG31dcSxSkQHv`) | No aplica: se ejecuta por programación y no tiene usuarios que inicien sesión |

---

## 2. Componentes

### 2.1 Flujos

| Flujo | ID | Ubicación | Estado |
|---|---|---|---|
| **Login Microsoft 365** (definitivo) | `1yD3JSYX8nMJqeID` | UNI2 / Utilitarios | Publicado, lo usa Reconstruye |
| **Login Microsoft 365 (pruebas)** | `CfxCvEk1l2ImSob8` | UNI2 / Pruebas | Publicado, lo usa la copia de Rindegastos |
| RindegastosSAP (pruebas - SSO) | `a7sfU8L67yKtO13f` | UNI2 / Pruebas | Publicado, para validación |
| Auth · Microsoft 365 (subflujo anterior) | `NtcAdHyPUYIxWSNl` | UNI2 / Utilitarios | Publicado **sin uso**. Se conserva como reversión de Reconstruye; retirar cuando se confirme |
| Acceso Microsoft 365 (pruebas), Auth · Microsoft 365 (pruebas) | `daZkWPqcYm7krkCN`, `UR5QkUBSFQLxXhub` | UNI2 / Pruebas | Desactivados, quedaron unidos en el login único. **Se pueden borrar** |
| Acceso Office 365 (login propio del Extractor) | `LqnUkmAXBMe3mcBU` | UNI2 / Utilitarios | En producción. Se retira al migrar el Extractor |

El flujo **Login Microsoft 365** tiene **tres entradas**:

| Entrada | La usa | Para qué |
|---|---|---|
| **Webhooks** (`/webhook/acceso-m365`, regreso de cada app) | El navegador | Ingreso, regreso desde Microsoft, cierre de sesión |
| **Entrada** (*Execute Workflow*) | Los flujos de cada app | `verificarSesion` (y las demás operaciones) |
| **Limpieza diaria** (3:00 a. m.) | n8n | Mantenimiento de las tablas |

### 2.2 Operaciones del motor (entrada *Execute Workflow*)

| Operación | Qué hace | Devuelve |
|---|---|---|
| `iniciarLogin` | Genera `state` y `nonce` (256 bits) y arma la URL de Microsoft | `urlRedireccion`, `setCookie` (nonce) |
| `procesarCallback` | Valida el `state` (un solo uso), canjea el código, valida el `id_token` y crea la sesión | `usuario`, `setCookie`, `urlDestino`, `campoOculto` / `sesionId` |
| `verificarSesion` | Valida la sesión (cookie o campo oculto) | `usuario`, `campoOculto` |
| `cerrarSesion` | Cierra o anula la sesión | `setCookie` (de borrado) |

Entradas: `operacion`, `app`, `redirectUri`, `cookies` (cabecera `Cookie`), `query`, `tokenSesion`.
Si falla, la respuesta trae `ok: false` con `codigo`, `accion` (`login` · `reintentar` · `contactar_ti`), `titulo`, `mensaje` y un `html` ya escapado.

### 2.3 Tablas (Data Tables, proyecto UNI2)

| Tabla | ID | Contenido | Limpieza |
|---|---|---|---|
| `auth_m365_inicios` | `U4XPOwosUHbmvNuI` | Inicios de login en curso (`state`, `nonce`, `app`) | Se borra al usarse; las vencidas (más de 10 min), cada día |
| `auth_m365_sesiones` | `AVObiNx5VmIVXtZq` | **Sesiones activas**: `sesion`, `app`, `email`, `nombre`, `oid`, `inicio`, `expira` | Se borra al cerrar sesión; las vencidas, cada día |
| `auth_m365_registro_accesos` | `TCWhmYKDNfk2mZOC` | **Registro de accesos**: `fecha`, `evento` (`inicio_sesion` / `cierre_sesion`), `app`, `email`, `nombre`, `detalle` | Cada día se borran los eventos de **más de 90 días** |

Las tablas son **compartidas por todas las apps**. Cada fila lleva `app`, y el login siempre exige que la app coincida: una sesión de un flujo no sirve en otro.

### 2.4 Credenciales (proyecto UNI2)

| Credencial | ID | Uso | Vence |
|---|---|---|---|
| Auth M365 · Firma de sesiones (JWT) | `Uodv7hjzuljIrXNa` | Firma las sesiones en modo `jwt` | No vence |
| Reconstruye · Secreto Entra ID | `BLXGJfzuND0fFwR4` | Canje del código, app Reconstruye | **14/10/2027** |
| Rindegastos · Secreto Entra ID | `Gve9QdSv7ABeiPLC` | Canje del código, app Rindegastos SAP | **20/10/2027** |
| Extractor · Secreto Entra ID (de Luis Meza, Custom Auth) | `GUd5z4JcQKk34DaQ` | Canje del código, app Extractor | Por confirmar |

### 2.5 Aplicaciones en Entra ID (una por flujo)

| App | Client id | Acceso |
|---|---|---|
| Flujo n8n - Reconstruye | `10632875-87cd-4b0f-b3b7-e0fac2f288ee` | Grupo *Desarrollo de Software* |
| Flujo n8n - Rindegastos SAP | `83fa3a4d-4c54-4ec7-a7c7-a4da3a7f8318` | Usuarios asignados |
| Flujo n8n - Extractor de Facturación SIIF | `e3e95678-765e-4730-8473-027150d453f4` | Todo el directorio UNI2 |

Directorio (tenant) UNI2: `f6c1b7c0-d15b-446c-baa7-b6392213858a`.

### 2.6 Archivos fuente (workspace)

| Archivo | Qué genera |
|---|---|
| `build_auth_m365.py` | Motor del login: registro de aplicaciones, validaciones, sesiones, registro y limpieza. Perfiles `pruebas` / `produccion` |
| `build_acceso_m365.py` | Bloque de acceso: webhooks, páginas de error y de sesión cerrada |
| `build_login_m365.py` | **Login Microsoft 365**: une los dos anteriores en un solo flujo |
| `n8n_ui/ui_estandar.js` | **Interfaz estándar**: estilos de marca, banner, `uiMarco()`, `uiFormulario()`, `esc()` |
| `build_rindegastos_sso.py` | Ejemplo de flujo con formulario estándar (plantilla para flujos nuevos) |
| `build_reconstruye_auth_m365.py` | Primera integración de Reconstruye con el motor |

> Los flujos se generan desde estos scripts. Un cambio hecho a mano en n8n se pierde en la siguiente generación: si se cambia algo, se cambia en el script.

---

## 3. Cómo funciona

```
Navegador                 Flujo de la app                    Login Microsoft 365                 Microsoft
────────                  ───────────────                    ───────────────────                 ─────────
GET /webhook/<app>  ─►  Auth: verificar sesión ──(interno)──► verificarSesion
                         ├─ con sesión → página / formulario
                         └─ sin sesión → 303 ─────────────────► /webhook/acceso-m365?app=<app>
                                                              iniciarLogin ── 302 ────────────────► login + selector de cuenta
                                                              /webhook/<regreso> ◄─────────────────── ?code=…&state=…
                                                              procesarCallback (valida y crea la sesión)
GET /webhook/<app>  ◄──────────────────────────────────────── 302 + Set-Cookie
POST /webhook/<app>-enviar (campo oculto _sesion) ─► Auth: verificar sesión ─► lógica ─► página final
```

### 3.1 Validaciones de seguridad del login

- **`state`** aleatorio de 256 bits, de **un solo uso**, vence en 10 minutos (protección CSRF).
- **`nonce`** en una cookie: el regreso desde Microsoft solo sirve en el navegador que inició el ingreso.
- **`id_token`**: se valida `alg≠none`, `aud` (client id de la app), `azp`, `iss`, `tid` (directorio UNI2), `exp`, `nbf`, `iat` (con 5 minutos de tolerancia de reloj), `nonce` y el **dominio del correo** (`@uni2.com.co`).
- **El canje del código** usa el secreto de la app (Basic Auth). El secreto nunca está en el código, solo en las credenciales de n8n.
- **Redirect URIs permitidas por app:** el login rechaza cualquier otra (`redirect_no_permitida`).
- **Los errores de Microsoft** (AADSTS50105, 50020, 65004, 50011, secreto vencido, código usado…) se traducen a mensajes claros para el usuario.
- **No se guardan tokens de Microsoft.**

---

## 4. Sesiones: duración y de qué depende

### 4.1 Duración actual por app

| App | Duración de la sesión | Modo | Se puede anular desde la tabla |
|---|---|---|---|
| `reconstruye` | **1 hora** | `jwt` (token firmado en cookie) | No |
| `rindegastos` | **8 horas** | `tabla` (id en `auth_m365_sesiones`, viaja en cookie + campo oculto) | **Sí** |
| `extractor` | **8 horas** | `tabla` (hoy usa su propio login; ver §9) | Sí, cuando migre |

### 4.2 De qué depende

- **`duracionSesionSegundos`** en *Registro de aplicaciones* (`build_auth_m365.py`). Es **por app**: cambiarlo solo afecta a ese flujo. Define el vencimiento de la sesión y el `Max-Age` de la cookie.
- **Recomendación:** sesiones más cortas (1 a 2 horas) en flujos que escriben en sistemas críticos, y más largas en flujos de consulta.
- **Hay otros relojes, que no son la sesión:**
  - **inicio de login** (`state` y cookie de `nonce`): 10 minutos entre ir a Microsoft y volver;
  - **tolerancia de reloj** al validar el `id_token`: 5 minutos.
- **Al vencer**, el usuario vuelve a Microsoft. Si su cuenta sigue abierta, solo escoge la cuenta y continúa.
- **Cerrar sesión** cierra la sesión **de esa aplicación**, no la de Microsoft en general (Outlook, Teams y demás siguen abiertos). Al volver a entrar, Microsoft muestra el **selector de cuenta** (`prompt: 'select_account'`), igual en Reconstruye y Rindegastos.

### 4.3 Modo `jwt` vs. modo `tabla`

| | `jwt` (token firmado) | `tabla` (id en la tabla) |
|---|---|---|
| Dónde está la sesión | Dentro del token: app, correo y vencimiento, firmados | En `auth_m365_sesiones`; la cookie solo lleva un id aleatorio |
| Consultas por petición | Ninguna | 1 lectura a la tabla |
| Cerrar sesión | Borra la cookie | Borra la cookie **y anula la sesión en el servidor** |
| Ver quién está conectado | No | Sí |
| Anular una sesión a mano | No (dura hasta que vence) | Sí: se borra su fila |

### 4.4 Ver quién está conectado y anular sesiones

- **Ver:** en n8n, *Data tables* → `auth_m365_sesiones`, filtrando por `app`. Solo sirve para apps en modo `tabla`.
- **Anular:** se borra la fila de esa sesión. La persona queda fuera en su siguiente acción.
- **Historial:** `auth_m365_registro_accesos` (90 días). Para guardar más tiempo, mover el registro a Postgres.

---

## 5. Decisiones de diseño y por qué

| # | Decisión | Por qué |
|---|---|---|
| 1 | **Una app de Entra ID por flujo** | Cada flujo tiene su propio control de acceso (qué usuarios o grupos entran), su propio secreto y su propio vencimiento. Un problema en uno no afecta a los demás |
| 2 | **Un solo flujo de login compartido** | Antes había dos implementaciones distintas (Reconstruye y Extractor). Ahora una corrección de seguridad se hace una sola vez y la heredan todos. Primero fueron dos flujos (Acceso + Auth); se unieron para tener **una sola pieza que mantener** |
| 3 | **Formularios con Webhook y páginas propias, sin nodos Form** | Ver §6 |
| 4 | **Interfaz en una fuente única** (`ui_estandar.js`) | Misma marca en todos los flujos, escapado de datos y campo de sesión ya resueltos. El script la copia en un nodo Code de cada flujo: **no agrega ejecuciones**. Es el mismo patrón que ya usaba el equipo del Extractor |
| 5 | **Sesiones activas y registro de accesos en tablas separadas** | La tabla de sesiones se mantiene pequeña, porque se consulta en cada petición. El historial crece aparte y con retención. Guardar todo sin borrar no es sostenible en Data Tables (capacidad limitada) |
| 6 | **Configuración de cada app dentro del login** | Ningún flujo puede pedir un login con un client id o una redirect URI arbitrarios |
| 7 | **Las llamadas al login solo se permiten desde el mismo proyecto** (`callerPolicy: workflowsFromSameOwner`) | Solo los flujos del proyecto UNI2 pueden usarlo |

---

## 6. Por qué no se usaron los nodos Form de n8n

Se probaron tres alternativas antes de llegar al estándar:

| Alternativa | Resultado |
|---|---|
| **Form Trigger + `?sesion=<id>`** en la URL | ❌ La URL funciona como una llave: copiada en otro navegador, da acceso durante toda la sesión. Además, **el formulario vacío se ve sin iniciar sesión** (el Form Trigger solo admite Basic Auth y dibuja la página sin ejecutar nodos) |
| **Webhook + nodo Wait (formulario)** | ❌ La URL `/form-waiting/<id>?signature=…` está firmada (sin firma responde 401), pero **también se puede copiar** a otro navegador mientras está vigente. Además, los nodos Form no funcionan después de un Wait |
| **Webhook + páginas propias** (como Reconstruye) | ✅ **Elegida.** Las URLs no llevan nada secreto: en otro navegador piden login. La sesión va en una cookie (GET) y en un campo oculto firmado (POST) |

**Causa de fondo:** n8n Cloud sirve los formularios en modo *sandbox*, así que el navegador **no envía cookies** al enviarlos, y el Form no le entrega al flujo las cabeceras. Con nodos Form no hay forma de comprobar que quien envía es el mismo navegador que inició sesión.

### Ventajas y desventajas del estándar

| Ventajas | Desventajas |
|---|---|
| La sesión queda ligada al navegador: un enlace copiado no sirve | Más trabajo inicial: el formulario se arma con código (mitigado con `uiFormulario()`) |
| Nada visible sin sesión | Cambiar un campo requiere editar el script, no el editor visual |
| Diseño de marca en todas las páginas | Archivos, validaciones y errores hay que manejarlos en el flujo |
| Un solo modo de login para todos los flujos | Algunos controles que n8n hacía solo pasan a ser responsabilidad del equipo (ver §7) |

---

## 7. Controles obligatorios en flujos con páginas propias

| Control | Qué hacer |
|---|---|
| Escapar los datos | Todo dato del usuario o de una API pasa por `esc()` antes de ir al HTML (evita XSS) |
| Validar en el servidor | Validar en el flujo los campos obligatorios, el formato y los rangos, no solo en el navegador (ver §10, incidente del 20/10) |
| Archivos | Limitar el tipo (`aceptar`) y el tamaño antes de procesarlos |
| Campo `_sesion` | Todo formulario lo lleva (`campoSesion`). **No quitarlo**: los envíos llegan sin cookies |
| Todas las ramas terminan en una página | Cada rama de la lógica debe llegar a un *Respond to Webhook*; si no, el navegador queda esperando |
| Duración de la sesión | Corta en flujos que escriben en sistemas críticos |

---

## 8. Paso a paso: agregar el login a un flujo nuevo

### Paso 1 · Pedir la app a Infraestructura (Entra ID)

- **Nombre:** `Flujo n8n - <Nombre del flujo>`
- **Tipos de cuenta:** solo este directorio (inquilino único)
- **Plataforma:** Web
- **Redirect URIs:** `https://uni2.app.n8n.cloud/webhook/<ruta>-auth` (y `…/<ruta>-dev-auth` si habrá copia de pruebas)
- **Secreto de cliente:** vigencia de 1 año
- **Permisos (Graph, delegados):** `openid`, `profile`, `email`, `User.Read` + **consentimiento de administrador**
- **Aplicación empresarial:** *¿Se requiere asignación?* = Sí, y asignar los usuarios o grupos

**De vuelta:** client id y fecha de vencimiento del secreto. **El secreto se carga directo en la credencial de n8n**, nunca por chat ni por correo.

### Paso 2 · Credencial en n8n (proyecto UNI2)

Tipo **Basic Auth**:
- **Nombre:** `<Flujo> · Secreto Entra ID (vence AAAA-MM-DD)`
- **Usuario:** client id
- **Contraseña:** secreto

### Paso 3 · Registrar la app en el login (`build_auth_m365.py`)

1. **Entrada en `APPS`** (*Registro de aplicaciones*):

   | Campo | Ejemplo / significado |
   |---|---|
   | `nombre` | Nombre visible |
   | `tenantId` | `TENANT_UNI2` |
   | `clientId` | El de Infraestructura |
   | `redirectUris` | `[…/webhook/<ruta>-auth]` |
   | `urlDestino` | `…/webhook/<ruta>`, a dónde llega tras el login |
   | `dominiosPermitidos` | `['uni2.com.co']` |
   | `modoSesion` | `'tabla'` (recomendado: revocable y auditable) o `'jwt'` |
   | `duracionSesionSegundos` | Por ejemplo `3600` |
   | `cookieNonce` / `cookieSesion` | Nombres únicos por app, por ejemplo `xx_nonce` / `xx_sesion` |
   | `rutaCookie` | `'/webhook'` |
   | `campoSesion` | `'_sesion'` |
   | `prompt` | `'select_account'` |
   | `ramaCanje` | Siguiente número libre |

2. **Constante de la credencial** (`CRED_<APP>`) y **nodo `Canje · <App>`** con `canje(...)`.
3. **`Canje: elegir app`:** aumentar `numberOutputs` y conectar la rama nueva a `Callback: validar identidad`.

### Paso 4 · Webhook de regreso (`build_acceso_m365.py`)

Agregar `'<ruta>-auth': '<app>'` en `REGRESOS_POR_PERFIL` del perfil que corresponda.

> **Una ruta solo puede estar en un flujo activo.** Si una copia de pruebas usa la ruta, hay que desactivarla antes de usarla en producción.

### Paso 5 · Regenerar y publicar el login

```bash
python3 build_login_m365.py login.json pruebas      # o produccion
```

PUT sobre el flujo correspondiente (`CfxCvEk1l2ImSob8` pruebas / `1yD3JSYX8nMJqeID` producción).

⚠️ **El login es compartido:** guardar respaldo antes y, después, probar el ingreso de las apps que ya lo usan.

### Paso 6 · Construir el flujo de la app

Usar como plantilla `build_rindegastos_sso.py`:

```
Webhook <Formulario> (GET /<ruta>) ─┐
Webhook <Enviar> (POST /<ruta>-enviar) ┴─► Auth: verificar sesión ─► UI estándar ─► Ruta
                                                                                     ├ 0 → Respond Formulario (HTML)
                                                                                     ├ 1 → lógica del flujo → páginas finales (Respond)
                                                                                     └ 2 → 303 a /webhook/acceso-m365?app=<app>
```

- **Auth: verificar sesión** (*Execute Workflow* → Login Microsoft 365):
  - `operacion = verificarSesion`
  - `app = <app>`
  - `cookies = {{ $json.headers.cookie }}`
  - `tokenSesion = {{ $json.body._sesion }}`
  - `onError: continueRegularOutput`
- **UI estándar** (Code): el script copia `ui_estandar.js` y agrega la parte propia del flujo: título, campos (`uiFormulario`), URLs y `campoSesion: sesion.campoOculto`.
- **Páginas finales:** `{{ ui.inicio + contenido + ui.fin }}`, con los botones *Nueva consulta* y *Cerrar sesión* (`/webhook/acceso-m365?app=<app>&salir=1`).

### Paso 7 · Probar y publicar

- [ ] Sin sesión → pide login de Microsoft y vuelve al formulario.
- [ ] La URL del formulario pegada en una ventana privada → pide login.
- [ ] Un usuario no asignado en Entra → error *AADSTS50105* (mensaje claro).
- [ ] *Cerrar sesión* → página "Sesión cerrada"; al volver, Microsoft muestra el selector de cuenta.
- [ ] La sesión aparece en `auth_m365_sesiones` (modo tabla) y los eventos en `auth_m365_registro_accesos`.
- [ ] Anular la sesión (borrar su fila) → la siguiente acción pide login.
- [ ] Todas las ramas de la lógica terminan en una página.
- [ ] Probar primero en una copia, y nunca con datos que escriban en sistemas productivos sin aprobación del área dueña.

### Costo en ejecuciones

- **Cada página o envío:** 1 ejecución del flujo + 1 del login (verificar sesión).
- **Cada inicio de sesión:** unas 4 ejecuciones (ida y vuelta a Microsoft). Ocurre una vez por cada vencimiento de sesión.
- Por confirmar en *Settings → Usage and plan* si las ejecuciones del login cuentan para el límite del plan.

---

## 9. Flujos pendientes

### 9.1 ReporteWompi

**Hoy:** un Form con Basic Auth (campo *Fecha*) y un webhook **"Descargar Plano Wompi" sin autenticación**: quien tenga el enlace descarga el archivo.

**Plan:**
1. Pedir la app *Flujo n8n - Reporte Wompi* (paso 1) y crear su credencial (paso 2).
2. Agregar la app `wompi` al login (pasos 3 a 5).
3. En una copia del flujo:
   - el Form pasa a Webhook GET/POST + *Verificar sesión* + *UI estándar*, con el campo *Fecha* (`tipo: 'date'`);
   - las 2 páginas finales pasan a Respond;
   - se quita la Basic Auth.
4. **Proteger "Descargar Plano Wompi"** con *Verificar sesión* (es un GET, así que la cookie llega).
5. Validar, migrar al original y comunicar el enlace nuevo.

**Esfuerzo:** bajo (similar a Rindegastos). **Prioridad:** alta, por el enlace de descarga abierto.

### 9.2 Extractor de Facturación SIIF (coordinar con Luis Meza)

**Hoy:** un Form (usuario y contraseña de SIIF, número de crédito o Excel, tipo de proceso), con su propio login en *Acceso Office 365* y la tabla `extractor_sesiones`. La sesión viaja en `?sesion=` en la URL.

**Plan:**
1. **Login:** la app `extractor` **ya está** en el registro.
   - Mover su redirect URI `extractor-pagares/callback` al login, o registrar `…/webhook/acceso-m365-auth`.
   - Cambiar el canje a Basic Auth: hay que volver a cargar el secreto.
2. **Formulario:** rehacerlo con `uiFormulario()`:
   - usuario SIIF (texto), contraseña (`password`), forma de consulta (`select`), número de crédito, Excel (`file`, `.xlsx`) y tipo de proceso;
   - el Excel llega como binario en el webhook, así que hay que ajustar *Leer Excel de créditos*;
   - para la opción "número o archivo", el flujo ya valida; se puede agregar un script pequeño que muestre u oculte los campos.
3. **Página final** (*Construir página final*, con resumen y descarga): adaptarla a Respond con la UI estándar, cuidando la entrega del archivo resultante.
4. **`Registrar uso`:** tomar el correo de `usuario.email` del login.
5. **Retirar:** *Acceso Office 365* y `extractor_sesiones` (`extractor_registro_uso` se mantiene).

**Esfuerzo:** medio. Lo más delicado es la carga del Excel y la descarga del resultado.

### 9.3 Otros pendientes

- [x] **RindegastosSAP migrado** (20/10/2026). La copia de pruebas `a7sfU8L67yKtO13f` y el *Login Microsoft 365 (pruebas)* `CfxCvEk1l2ImSob8` quedaron desactivados. El webhook `rindegastos-sap-auth` ahora está en el login definitivo.
- [ ] **Comunicar a Contabilidad** el enlace nuevo `https://uni2.app.n8n.cloud/webhook/rindegastos-sap` (el formulario `/form/19701d96-…` ya no existe).
- [ ] **Borrar** las copias desactivadas `daZkWPqcYm7krkCN` y `UR5QkUBSFQLxXhub`.
- [ ] **Retirar** el subflujo anterior `NtcAdHyPUYIxWSNl` cuando se confirme Reconstruye.
- [ ] **URI genérica:** pedir a Infraestructura `…/webhook/acceso-m365-auth` en cada app, para no agregar un webhook de regreso por app.
- [ ] **Rotar los secretos** de Reconstruye y Rindegastos: se compartieron por chat durante la configuración.
- [ ] **Recordatorios de vencimiento:** 14/10/2027 (Reconstruye) y 20/10/2027 (Rindegastos).
- [ ] Opcional: pasar Reconstruye a modo `tabla` para poder anular sesiones, y registrar también los intentos de login rechazados.

---

## 10. Incidente del 20/10/2026 y lecciones

Durante una prueba de la copia de RindegastosSAP se envió el ID de informe `0` para que "no encontrara gastos". La API de Rindegastos **ignora `ReportId=0` y devolvió todos los gastos**, y el flujo creó **2 asientos y 1 socio de negocio en SAP PRO** y marcó **46 gastos** en Rindegastos. Detalle en `INCIDENTE_20261020_RindegastosSAP_pruebas.md`.

**Lecciones:**
- **Validar en el servidor** los datos de entrada: RindegastosSAP no valida que el ID sea un informe real, y el flujo original tiene el mismo comportamiento.
- **No hacer pruebas reales de flujos que escriben en sistemas productivos** sin un caso aprobado por el área dueña. Las copias usan las mismas credenciales que el original.
- **Separar responsabilidades:** el área de desarrollo del login prueba la autenticación; la persona dueña del flujo valida su funcionamiento.
