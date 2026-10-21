# Ajuste flujo n8n Reconstruye: SSO Microsoft 365, ambiente centralizado y banner

Issue: #374 · Fecha de despliegue: 14/10/2026 · Flujo: **Reconstruye** (`io6wE6X97L0skPAG`)

## Resumen

Se implementaron los tres ajustes solicitados en el flujo **Reconstruye**:

1. **Acceso con Microsoft 365 (SSO).** El login propio del webhook (Basic Auth) se reemplazó por el inicio de sesión con la cuenta corporativa. Es el **único método de acceso** a todas las páginas del formulario.
2. **Ambiente centralizado.** La base de datos (DEV, QA o PROD) se define en **un solo punto**: la credencial del nodo `Ejecutar consulta` del subflujo **Reconstruye · Base de datos**.
3. **Visibilidad del ambiente.** Cada página muestra un banner con el ambiente, el usuario autenticado y la opción de cerrar sesión. El título de la pestaña del navegador también indica el ambiente (por ejemplo, `[QA] Créditos activos`).

Además, se rediseñaron los estilos del formulario para alinearlos con la aplicación oficial de UNI2: contenido centrado y diseño adaptable a celular.

<!-- 📷 Captura: página 1 del formulario con el banner (escritorio) -->

---

## 1. Acceso con Microsoft 365

### Cómo funciona

1. El usuario abre `https://uni2.app.n8n.cloud/webhook/reconstruye`.
2. Si no tiene sesión, el flujo lo redirige al login de Microsoft 365.
3. Microsoft lo devuelve a `https://uni2.app.n8n.cloud/webhook/reconstruye-auth`. El flujo valida la identidad y crea una sesión de **1 hora**.
4. Con la sesión activa, el usuario navega los pasos del formulario normalmente.

**Validaciones de identidad** (sobre el `id_token` que entrega Microsoft):

| Dato | Qué se valida |
|---|---|
| `tid` | Que la cuenta pertenezca al directorio de UNI2 |
| `aud` | Que el token sea para la app **n8n Reconstruye** |
| `nonce` y `state` | Que el regreso corresponda al mismo inicio de sesión y navegador (protección CSRF) |
| `exp` | Que el token no esté vencido |
| correo | Que sea del dominio `@uni2.com.co` |

**Datos que se guardan:** solo el correo, el nombre y el `oid` del usuario, en una cookie firmada de 1 hora. No se guardan tokens ni contraseñas de Microsoft, ni se escribe nada en tablas.

<!-- 📷 Captura: pantalla de login de Microsoft -->
<!-- 📷 Captura: página "Acceso denegado" (login cancelado) -->

### Aplicación en Microsoft Entra ID (registrada por Infraestructura)

| Dato | Valor |
|---|---|
| Nombre | `n8n Reconstruye` |
| Id. de aplicación (cliente) | `10632875-87cd-4b0f-b3b7-e0fac2f288ee` |
| Id. de directorio (inquilino) | `f6c1b7c0-d15b-446c-baa7-b6392213858a` |
| URIs de redirección (Web) | `https://uni2.app.n8n.cloud/webhook/reconstruye-auth` (producción)<br>`https://uni2.app.n8n.cloud/webhook/reconstruye-dev-auth` (pruebas) |
| Acceso | Solo miembros del grupo de seguridad **Desarrollo de Software** (asignación requerida) |
| Secreto de cliente | En n8n, credencial `Reconstruye · Secreto Entra ID (vence 2027-10-14)` |
| **Vencimiento del secreto** | **14/10/2027** |

> Reconstruye usa su **propia** app de Entra. No comparte la del Extractor de pagarés ("Acceso Office 365").

---

## 2. Ambiente centralizado

Todas las consultas del flujo pasan por el subflujo **Reconstruye · Base de datos** (`kgoDhOOse3BAI37h`), que tiene un único nodo Postgres llamado `Ejecutar consulta`. Los 8 nodos de base de datos del flujo principal conservan su nombre, pero llaman a ese subflujo.

**Para cambiar de ambiente:**

1. Abrir el subflujo **Reconstruye · Base de datos**.
2. En el nodo `Ejecutar consulta`, cambiar la credencial (`Postgres uni2_dev`, `Postgres uni2_qa`, …).
3. Publicar el subflujo.

No se modifica nada en el flujo principal.

**Garantía de consistencia:** el ambiente que muestra el banner se obtiene consultando `current_database()` por esa **misma conexión**. Así, el formulario siempre muestra la base donde realmente se crea la solicitud. Si la base no está registrada en la configuración, el formulario se bloquea con un mensaje.

**Estado actual:** el flujo de Soporte apunta a **QA** (`uni2_qa`).

<!-- 📷 Captura: subflujo "Reconstruye · Base de datos" con la nota de cómo cambiar el ambiente -->

---

## 3. Banner de ambiente y estilos

- **Banner naranja en todas las páginas**, por ejemplo: `⚠ AMBIENTE DE PRUEBAS (QA) | usuario@uni2.com.co  Cerrar sesión`.
- **Textos por ambiente:**
  - `⚠ AMBIENTE DE DESARROLLO (DEV)`
  - `⚠ AMBIENTE DE PRUEBAS (QA)`
  - `AMBIENTE DE PRODUCCIÓN (PROD)`
- **Título de la pestaña:** lleva el prefijo del ambiente (`[DEV]`, `[QA]`, `[PROD]`).
- **Estilos** inspirados en la app oficial:
  - tipografía Nunito;
  - campos con la etiqueta sobre el borde;
  - botones naranja redondeados;
  - selectores (radio) con los colores de la marca;
  - contenido centrado verticalmente y adaptable a celular.
- **Un solo lugar para el diseño:** los estilos de las 9 páginas están en el nodo `Construir contexto` (`ctx.estilos`).

<!-- 📷 Captura: paso 2 "Créditos activos" -->
<!-- 📷 Captura: paso 3 "Línea de crédito y plazo" -->
<!-- 📷 Captura: página de éxito con la solicitud creada -->
<!-- 📷 Captura: vista en celular -->

---

## 4. Organización del flujo

El lienzo se organizó en bloques con notas de color:

| Bloque | Qué hace |
|---|---|
| ① Entrada común (azul) | Las 5 rutas entran aquí; configuración (`Config Reconstruye`), detección del ambiente y armado del banner |
| ② Sesión válida (verde) | Verifica la sesión y envía al paso correspondiente |
| ③ Sin sesión (morado) | Redirige al login de Microsoft |
| ④ Regreso desde Microsoft (morado) | Valida la identidad y crea la sesión |
| ⑤ Bloqueo (rojo) | Base de datos no reconocida |
| ⑥–⑨ Pasos del formulario (amarillo) | Documento → créditos activos → línea de crédito → crear solicitud (estado 30) |

<!-- 📷 Captura: lienzo completo del flujo con las notas de color -->

**Rutas del flujo:**

| Ruta | Uso |
|---|---|
| `/webhook/reconstruye` | Inicio (enlace para Soporte) |
| `/webhook/reconstruye-creditos-activos` | Paso 2 |
| `/webhook/reconstruye-linea-credito` | Paso 3 |
| `/webhook/reconstruye-confirmar` | Paso 4 (crear solicitud) |
| `/webhook/reconstruye-auth` | Regreso desde Microsoft y cierre de sesión |

---

## 5. Pruebas realizadas

| Criterio de aceptación | Resultado |
|---|---|
| Login con Microsoft 365 exitoso | ✅ Usuario `@uni2.com.co` autenticado accede al formulario |
| Login fallido o cancelado | ✅ Página "Acceso denegado"; las rutas sin sesión redirigen al inicio; una sesión falsificada se rechaza |
| Ambiente visible según la configuración | ✅ Banner y título muestran DEV o QA según la credencial del subflujo |
| Ejecución exitosa del flujo | ✅ Se crea la solicitud en estado 30 en el ambiente que muestra el formulario |
| Ejecución con error | ✅ Se mantiene el comportamiento original: mensajes de error por solicitud inactiva o no elegible |

> Las pruebas se hicieron primero en una copia de desarrollo y luego se promovieron al flujo de Soporte. Durante las pruebas se crearon en **QA** las solicitudes **250640** y **250641**.

<!-- 📷 Captura: ejecución exitosa en n8n (lista de ejecuciones) -->

---

## 6. Cosas a tener en cuenta

- **Acceso de nuevos usuarios:** para que alguien use el formulario, Infraestructura debe agregarlo al grupo **Desarrollo de Software** en Entra ID. Quien no esté en el grupo ve el error `AADSTS50105` en la página de Microsoft.
- **Vencimiento del secreto (14/10/2027):** antes de esa fecha, Infraestructura debe generar un secreto nuevo y actualizar la credencial `Reconstruye · Secreto Entra ID` en n8n. Si vence, nadie podrá iniciar sesión. Se recomienda dejar un recordatorio.
- **Rotar el secreto actual:** el secreto actual se compartió por un canal no seguro durante la configuración. Se recomienda rotarlo: nuevo secreto en Entra y actualización de la credencial en n8n.
- **Sesión de 1 hora:** al vencer, el usuario vuelve al login de Microsoft. Si deja la pantalla de Microsoft abierta más de 10 minutos, el regreso se rechaza y debe intentar de nuevo.
- **Restricción técnica de n8n Cloud:** n8n sirve las páginas de los webhooks en modo *sandbox*, y en ese modo el navegador no envía cookies al enviar formularios. Por eso cada formulario lleva la sesión firmada en un campo oculto `_sesion`. No eliminar ese campo al modificar las páginas.
- **Ejecuciones del subflujo:** cada consulta a la base genera también una ejecución del subflujo en el historial de n8n.
- **No volver a agregar nodos Postgres al flujo principal:** toda consulta nueva debe pasar por el subflujo, para que el ambiente siga definido en un solo punto.
- **Paso a producción:** cuando se apruebe, basta con cambiar la credencial del subflujo **Reconstruye · Base de datos** a la de producción. El banner mostrará `AMBIENTE DE PRODUCCIÓN (PROD)`. Antes hay que registrar la base de producción en `Config Reconstruye` (`ambientesPorBase`).
- **Consentimiento:** si los usuarios ven una pantalla de "Permisos solicitados" en su primer ingreso, Infraestructura puede **conceder el consentimiento de administrador** en la app para evitarla.

---

## 7. Referencias

| Elemento | ID / ubicación |
|---|---|
| Flujo de Soporte | **Reconstruye** · `io6wE6X97L0skPAG` |
| Subflujo de base de datos (Soporte) | **Reconstruye · Base de datos** · `kgoDhOOse3BAI37h` (apunta a `uni2_qa`) |
| Flujo de pruebas | **Reconstruye (dev - SSO #374)** · `SYf2UYaooO40I13d` · rutas `/webhook/reconstruye-dev*` |
| Subflujo de base de datos (pruebas) | **Reconstruye · Base de datos (dev - SSO #374)** · `zNxikoekjqD98VPw` (apunta a `uni2_dev`) |
| Credencial de sesiones | `JWT Sesion Reconstruye` |
| Credencial del secreto de Entra | `Reconstruye · Secreto Entra ID (vence 2027-10-14)` |
| Respaldo de la versión anterior | `workflow_io6wE6X97L0skPAG_Reconstruye_backup_20261014_preSSO.json` |

**Reversión:** si fuera necesario volver atrás, se restaura la versión anterior desde el historial de versiones del flujo en n8n o con el respaldo JSON. La versión anterior usa Basic Auth y apunta a QA.
