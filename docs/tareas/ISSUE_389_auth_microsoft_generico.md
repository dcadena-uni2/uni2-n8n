# Componente genérico de autenticación con Microsoft 365 para flujos n8n

**Tipo:** Mejora técnica · **Flujos involucrados:** Reconstruye, Acceso Office 365, Extractor de Facturación SIIF
**Antecedente:** #374 (SSO Microsoft 365 en Reconstruye)

## Contexto

Hoy hay dos implementaciones distintas del inicio de sesión con Microsoft 365 (OpenID Connect sobre Entra ID). Ambas funcionan, pero cada una resuelve el mismo problema a su manera:

| | Acceso Office 365 + Extractor de Facturación SIIF | Reconstruye |
|---|---|---|
| Dónde vive el login | Flujo aparte (`LqnUkmAXBMe3mcBU`); el Extractor solo verifica la sesión | Dentro del mismo flujo (`io6wE6X97L0skPAG`) |
| `state` / `nonce` | Aleatorios, en la Data Table `extractor_sesiones`, de un solo uso | `state` = JWT firmado (reutilizable durante 10 min); `nonce` en la cookie `rc_nonce` |
| Sesión | Fila en Data Table (8 h), viaja como `?sesion=` en la URL | JWT firmado (1 h), cookie `rc_sesion` + campo oculto `_sesion` |
| Canje del código | Custom Auth | Basic Auth (`client_secret_basic`) |
| App de Entra | `e3e95678…` (todo el directorio UNI2) | `10632875…` (solo grupo *Desarrollo de Software*) |
| Cierre de sesión | No tiene | Sí (`?salir=1`) |

Con esto, cualquier ajuste de seguridad (por ejemplo, una validación nueva del `id_token`) hay que hacerlo dos veces, y un flujo nuevo que necesite login tendría que copiar alguna de las dos implementaciones.

## Objetivo

Construir **un componente reutilizable de autenticación con Microsoft 365**, tomando lo mejor de las dos implementaciones, y usarlo en **Reconstruye** y en el **Extractor de Facturación SIIF**.

> n8n Cloud no permite instalar nodos propios, así que el "nodo genérico" se implementa como un **subflujo** que los flujos llaman con un nodo *Execute Workflow*, igual que hoy se hace con **Reconstruye · Base de datos**.

## Decisiones tomadas

| # | Tema | Decisión |
|---|---|---|
| 1 | Apps de Entra ID | **Una app por flujo.** Cada flujo conserva su app, su secreto y su restricción de acceso (Reconstruye: grupo *Desarrollo de Software*; Extractor: todo el directorio UNI2). |
| 2 | Almacenamiento | **Flujos con webhooks (Reconstruye): sesión en JWT firmado. Flujos con Form de n8n (Rindegastos SAP, Extractor): id opaco de 256 bits en la Data Table `auth_m365_sesiones`, revocable.** El `state` va en una Data Table, de un solo uso. |
| 3 | Ubicación | Subflujo en el proyecto **UNI2**, carpeta **Utilitarios**. Plan actual: **Pro**. |
| 4 | Transporte de la sesión | Webhooks: **esquema de campo oculto de Reconstruye**. Form de n8n: `?sesion=<id opaco>`, porque el Form solo recibe datos por la URL (resuelve el *Punto a validar*). |

## Diseño

### Subflujo "Auth · Microsoft 365" (UNI2 / Utilitarios)

El flujo que llama solo indica **qué aplicación** es (`app`) y **qué operación** necesita. Los datos de cada app (tenant, client id, redirect URI, dominios, duración de la sesión) viven **dentro del subflujo**, en un único nodo de configuración `Registro de aplicaciones`. Así, ningún flujo puede pedir un login con un `client_id` o una redirect URI arbitrarios.

| Operación | Qué hace | Devuelve |
|---|---|---|
| `iniciarLogin` | Genera `state` y `nonce` (nodo Crypto, 256 bits), guarda el `state` en la Data Table y arma la URL de Microsoft | URL de redirección + cookie de `nonce` |
| `procesarCallback` | Busca y **borra** el `state` (un solo uso, 10 min), verifica el `nonce` de la cookie, canjea el código, valida el `id_token` y firma la sesión | Token de sesión + usuario, o motivo y página de error |
| `verificarSesion` | Verifica la firma, el vencimiento y la app del token (cookie o campo oculto) | Usuario (`email`, `nombre`, `oid`) + campo oculto listo para insertar, o motivo |
| `cerrarSesion` | Arma la respuesta de cierre | Cookie de borrado |

Los webhooks y las páginas HTML **siguen en cada flujo**: el subflujo no responde al navegador, solo entrega los datos para que el flujo responda. Así, las redirect URIs registradas en Entra ID **no cambian**.

**Una rama por app.** El nodo HTTP que canjea el código usa una credencial fija (n8n no permite elegirla en tiempo de ejecución), así que el subflujo tiene un *Switch* por `app`, con un nodo de canje por credencial. Agregar una app nueva = una entrada en `Registro de aplicaciones` + una credencial + una rama.

**Sesión JWT.** Una sola credencial de firma para el subflujo. El token lleva un claim `app` que `verificarSesion` exige que coincida, para que una sesión de Reconstruye no sirva en el Extractor ni al revés. La duración sigue siendo propia de cada app (Reconstruye 1 h, Extractor 8 h).

**Data Table de `state`.** Una tabla nueva en el proyecto UNI2 (nombre propuesto `auth_m365_inicios`: `state`, `nonce`, `app`, `expira`), con limpieza de vencidos en cada callback.

**Validaciones del `id_token`** (unión de las dos implementaciones):
`alg≠none`, `aud` = client id de la app, `azp` (si hay varias audiencias), `iss`, `tid` = directorio UNI2, `exp`, `nbf`, `iat` (con tolerancia de reloj de 5 min), `nonce`, y correo de un dominio permitido.

**Errores:** páginas claras según el código AADSTS (sin acceso `50105`, cuenta externa `50020`/`50034`, permisos rechazados `65004`, redirect URI `50011`, app o tenant mal configurados `700016`/`90002`, secreto vencido `7000215`/`7000222`, código ya usado `invalid_grant`). El contenido del error lo arma el subflujo; el diseño de la página, cada flujo.

## Alcance

### Fase 1 · Subflujo
- Crear **Auth · Microsoft 365** en UNI2 / Utilitarios, con las 4 operaciones, `Registro de aplicaciones` y notas en el lienzo.
- Crear la Data Table `auth_m365_inicios` y la credencial JWT de sesión.
- Ajustar la política de llamadas del subflujo para que solo lo invoquen los flujos autorizados.
- Probar cada operación de forma aislada (ejecuciones manuales con datos de prueba).

### Fase 2 · Reconstruye
- Copia de desarrollo de Reconstruye (rutas `reconstruye-dev*`, redirect URI ya registrada).
- Reemplazar los nodos `Login: …` y `Auth: …` por llamadas al subflujo. Se elimina la credencial `JWT Sesion Reconstruye` cuando ya no se use.
- Pruebas en desarrollo → promover al flujo de Soporte.
- Sin cambios para el usuario: banner, cierre de sesión, sesión de 1 hora, acceso solo para el grupo *Desarrollo de Software*.

### Fase 3 · Extractor de Facturación SIIF
- **Acceso Office 365** conserva sus webhooks (`extractor-pagares/ingresar` y `/callback`) y pasa a llamar al subflujo.
- El Extractor reemplaza `Buscar sesión` + `Verificar sesión` por `verificarSesion` del subflujo.
- Cambiar al esquema de campo oculto: la sesión deja de viajar en `?sesion=` (ver *Punto a validar*).
- Cambiar el canje a Basic Auth: crear una credencial nueva con el client id y el secreto de la app del Extractor.
- Retirar la Data Table `extractor_sesiones` (sesiones y `state`) cuando ya no se use. **`extractor_registro_uso` se mantiene.**
- Agregar cierre de sesión.

### Fuera de alcance
- Verificar la firma RSA del `id_token` con las llaves públicas de Microsoft (JWKS). Se mantiene la excepción de OIDC Core §3.1.3.7: el token llega directo del endpoint de tokens por TLS y con autenticación de cliente.
- Control de acceso por roles o grupos dentro del flujo; se sigue usando la asignación de Entra ID.
- Revocar sesiones antes de su vencimiento (consecuencia de usar JWT).
- Cambios en la lógica de negocio de Reconstruye o del Extractor.
- Cambios en las apps de Entra ID o en sus redirect URIs.

## Punto a validar al inicio de la fase 3

El Extractor usa un **Formulario de n8n** (*Form Trigger*). Hoy recibe la sesión en un campo oculto que n8n llena **desde la URL** (`?sesion=`), que es la única forma que ofrece ese nodo. Para quitarla de la URL hay que confirmar una de estas opciones:

- **A.** El formulario de n8n recibe la cookie de sesión al enviarse. Hay que probarlo: las páginas de webhook de n8n Cloud se sirven en modo *sandbox* y no envían cookies en los POST. Si el formulario también está en ese modo, esta opción no sirve.
- **B.** Reemplazar el *Form Trigger* por webhook + página propia, como Reconstruye. Aumenta el esfuerzo: hay que manejar a mano la carga del archivo Excel y la página de resultado.

Se hace una prueba corta antes de estimar la fase 3.

## Criterios de aceptación

### Subflujo

1. Inicio de sesión exitoso
- Dado un usuario con cuenta `@uni2.com.co` autorizado en la app de Entra del flujo
- Cuando abre el flujo sin sesión y completa el login de Microsoft 365
- Entonces el subflujo valida el `id_token`, firma una sesión JWT con el claim `app` del flujo y el usuario llega a la página inicial con su correo visible

2. `state` reutilizado
- Dado un regreso de Microsoft cuyo `state` ya se usó en un inicio de sesión anterior
- Cuando el navegador vuelve a abrir la URL de callback
- Entonces el subflujo rechaza el ingreso, no canjea el código y el usuario ve la página de acceso denegado

3. `state` vencido o inexistente
- Dado un `state` creado hace más de 10 minutos, o que no existe en `auth_m365_inicios`
- Cuando llega al callback
- Entonces el subflujo rechaza el ingreso con un mensaje que invita a iniciar sesión de nuevo

4. Regreso desde otro navegador
- Dado un enlace de callback válido generado en un navegador
- Cuando se abre en otro navegador, que no tiene la cookie de `nonce`
- Entonces el subflujo rechaza el ingreso

5. `id_token` inválido
- Dado un `id_token` con `aud`, `iss`, `tid`, `nonce` o fechas (`exp`, `nbf`, `iat`) que no corresponden, o con `alg=none`
- Cuando el subflujo lo valida
- Entonces rechaza el ingreso e indica el motivo sin mostrar el token

6. Dominio no permitido
- Dado un usuario autenticado por Microsoft cuyo correo no es de un dominio permitido para la app
- Cuando regresa al callback
- Entonces el subflujo rechaza el ingreso e indica que la cuenta no es de un dominio permitido

7. Sesión de otra aplicación
- Dada una sesión JWT válida firmada para Reconstruye
- Cuando se presenta en el Extractor (o al revés)
- Entonces `verificarSesion` la rechaza y el usuario es enviado al login

8. Sesión alterada o vencida
- Dado un token de sesión con la firma modificada o con `exp` en el pasado
- Cuando el usuario navega a cualquier página del flujo
- Entonces `verificarSesion` la rechaza y el usuario es enviado al login

9. Errores informados por Microsoft
- Dado que Microsoft responde con uno de los códigos AADSTS listados en el diseño (por ejemplo `50105`, `50020`, `7000215`)
- Cuando el subflujo procesa la respuesta
- Entonces el usuario ve una página con un mensaje claro y la acción sugerida, y el detalle técnico queda visible para soporte

10. Secretos fuera del código
- Dado el subflujo publicado
- Cuando se revisa el JSON del flujo
- Entonces no contiene secretos de cliente ni llaves de firma: todos están en credenciales de n8n

11. Limpieza de inicios vencidos
- Dados registros en `auth_m365_inicios` con `expira` en el pasado
- Cuando se procesa cualquier callback
- Entonces esos registros se eliminan de la tabla

### Reconstruye

12. Login con Microsoft 365 en Reconstruye
- Dado un miembro del grupo *Desarrollo de Software*
- Cuando abre `/webhook/reconstruye` sin sesión e inicia sesión con Microsoft
- Entonces llega al paso 1 del formulario con el banner de ambiente, su correo y la opción de cerrar sesión, y la sesión dura 1 hora

13. Usuario fuera del grupo
- Dado un usuario de UNI2 que no pertenece al grupo *Desarrollo de Software*
- Cuando intenta iniciar sesión en Reconstruye
- Entonces Microsoft lo rechaza (`AADSTS50105`) y no accede al formulario

14. Login cancelado
- Dado un usuario en la pantalla de Microsoft
- Cuando cancela el inicio de sesión
- Entonces ve la página de acceso denegado de Reconstruye

15. Navegación con sesión activa
- Dado un usuario con sesión activa en Reconstruye
- Cuando avanza por los pasos 1 a 4 y crea una solicitud
- Entonces cada formulario envía la sesión en el campo oculto `_sesion` y la solicitud se crea en el ambiente que muestra el banner

16. Cierre de sesión en Reconstruye
- Dado un usuario con sesión activa
- Cuando hace clic en *Cerrar sesión*
- Entonces se borra la cookie de sesión, ve la página de sesión cerrada y al volver al inicio se le pide login de nuevo

17. Sin nodos de login propios
- Dado el flujo Reconstruye publicado
- Cuando se revisa el lienzo
- Entonces no tiene nodos `Login: …` ni `Auth: …`: todo el login pasa por el subflujo

### Extractor de Facturación SIIF

18. Login y consulta en el Extractor
- Dado un usuario del directorio de UNI2
- Cuando entra por `/webhook/extractor-pagares/ingresar`, inicia sesión y hace una consulta en SIIF
- Entonces la consulta funciona como hoy, el uso queda en `extractor_registro_uso` y la sesión dura 8 horas

19. Sesión fuera de la URL
- Dado un usuario que acaba de iniciar sesión en el Extractor
- Cuando llega al formulario
- Entonces la dirección del navegador no contiene `?sesion=` ni ningún token de sesión

20. Formulario sin sesión
- Dado un usuario sin sesión válida
- Cuando abre o envía el formulario del Extractor
- Entonces no se consulta SIIF y se le pide iniciar sesión

21. Cierre de sesión en el Extractor
- Dado un usuario con sesión activa en el Extractor
- Cuando hace clic en *Cerrar sesión*
- Entonces su sesión deja de ser válida y debe iniciar sesión de nuevo para consultar

22. Retiro de la tabla de sesiones anterior
- Dado el Extractor y Acceso Office 365 usando el subflujo
- Cuando se revisan los dos flujos
- Entonces ninguno usa `extractor_sesiones` y la tabla se retira tras exportar un respaldo

### General

23. Respaldo y reversión
- Dado cualquier flujo que se vaya a modificar en esta tarea
- Cuando se publica el cambio
- Entonces existe un respaldo JSON previo y un procedimiento de reversión documentado

24. Uso en un flujo nuevo
- Dado un desarrollador que necesita agregar login de Microsoft a un flujo nuevo
- Cuando sigue la guía de la tarea
- Entonces puede integrarlo agregando una entrada en `Registro de aplicaciones`, una credencial y una rama, sin copiar la lógica de validación

## Riesgos

- **Componente compartido:** un error en el subflujo afecta a todos los flujos que lo usan. Se mitiga probando con copias de desarrollo y publicando el subflujo solo después de validar.
- **Ejecuciones adicionales:** cada llamada al subflujo aparece como una ejecución más en el historial de n8n.
- **Formulario del Extractor:** según el resultado del *Punto a validar*, la fase 3 puede requerir rehacer la entrada del formulario (opción B).
- **Secreto del Extractor:** para pasar a Basic Auth hay que volver a cargar el secreto en una credencial nueva. n8n no permite leer el valor de una credencial existente; lo debe cargar Infraestructura o quien lo tenga.
- **Vencimiento de secretos:** Reconstruye vence el 14/10/2027; falta confirmar la fecha del secreto del Extractor.

## Referencias

| Elemento | Ubicación | ID |
|---|---|---|
| Proyecto | UNI2 | `8cm3t3EpvqIU0Vff` |
| Carpeta del subflujo | UNI2 / Utilitarios | `BcrmLnFwuZllFNQa` |
| Subflujo **Auth · Microsoft 365** | UNI2 / Utilitarios | `NtcAdHyPUYIxWSNl` |
| Data Table del `state` | `auth_m365_inicios` (UNI2) | `U4XPOwosUHbmvNuI` |
| Credencial de firma de sesiones | `Auth M365 · Firma de sesiones` (UNI2) | `Uodv7hjzuljIrXNa` |
| Reconstruye (Soporte) | UNI2 / Desarrollo de software | `io6wE6X97L0skPAG` |
| Acceso Office 365 | UNI2 / Utilitarios | `LqnUkmAXBMe3mcBU` |
| Extractor de Facturación SIIF | UNI2 / Cartera | `48FfYGGiN8ns8pw9` |
| App Entra · Reconstruye | `n8n Reconstruye` | `10632875-87cd-4b0f-b3b7-e0fac2f288ee` |
| App Entra · Extractor | — | `e3e95678-765e-4730-8473-027150d453f4` |
| Directorio (tenant) UNI2 | — | `f6c1b7c0-d15b-446c-baa7-b6392213858a` |
