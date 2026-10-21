"""Genera el subflujo "Auth · Microsoft 365" (issue #389, fase 1).

Uso:  python3 build_auth_m365.py [pruebas|produccion]  →  escribe auth_m365_subflujo.json (sin id),
listo para PUT /api/v1/workflows/<id> o para comparar con la versión publicada.
  pruebas    → copia "Auth · Microsoft 365 (pruebas)" (UR5QkUBSFQLxXhub)
  produccion → subflujo real "Auth · Microsoft 365" (NtcAdHyPUYIxWSNl), solo al migrar
"""
import json
import uuid

DATA_TABLE_ID = 'U4XPOwosUHbmvNuI'  # auth_m365_inicios (proyecto UNI2)
SESIONES_TABLE_ID = 'AVObiNx5VmIVXtZq'  # auth_m365_sesiones (proyecto UNI2)
CRED_JWT = {'jwtAuth': {'id': 'Uodv7hjzuljIrXNa', 'name': 'Auth M365 · Firma de sesiones'}}
CRED_RECONSTRUYE = {'httpBasicAuth': {'id': 'BLXGJfzuND0fFwR4', 'name': 'Reconstruye · Secreto Entra ID (vence 2027-10-14)'}}
CRED_EXTRACTOR = {'httpCustomAuth': {'id': 'GUd5z4JcQKk34DaQ', 'name': 'Extractor · Secreto Entra ID'}}
CRED_RINDEGASTOS = {'httpBasicAuth': {'id': 'Gve9QdSv7ABeiPLC', 'name': 'Rindegastos · Secreto Entra ID (vence 2027-10-20)'}}


def tabla(table_id, nombre):
    return {
        '__rl': True, 'mode': 'list', 'value': table_id,
        'cachedResultName': nombre,
        'cachedResultUrl': f'/projects/8cm3t3EpvqIU0Vff/datatables/{table_id}',
    }


REGISTRO_TABLE_ID = 'TCWhmYKDNfk2mZOC'  # auth_m365_registro_accesos (proyecto UNI2)
RETENCION_REGISTRO_DIAS = 90

TABLA = tabla(DATA_TABLE_ID, 'auth_m365_inicios')
TABLA_SESIONES = tabla(SESIONES_TABLE_ID, 'auth_m365_sesiones')
TABLA_REGISTRO = tabla(REGISTRO_TABLE_ID, 'auth_m365_registro_accesos')

BASE = "const base = $('Registro de aplicaciones').first().json;\n"

# ---------------------------------------------------------------- código de los nodos Code

REGISTRO = r"""// ============================================================
// REGISTRO DE APLICACIONES · Auth · Microsoft 365 (issue #389)
// ------------------------------------------------------------
// Única fuente de configuración del inicio de sesión con Microsoft 365 (Entra ID, OpenID Connect).
// Cada flujo que usa este subflujo tiene aquí su entrada, identificada por "app".
// Los secretos de cliente NO van aquí: están en las credenciales de los nodos "Canje · …".
//
// Para agregar una aplicación:
//   1. Entrada nueva en APPS con el siguiente número de "ramaCanje".
//   2. Credencial (Basic Auth: usuario = client id, contraseña = secreto de cliente).
//   3. Salida nueva en "Canje: elegir app" + nodo "Canje · <app>" conectado a "Callback: validar identidad".
//
// modoSesion:
//   'jwt'   → flujos con webhooks y páginas propias (cookie + campo oculto "_sesion"). Sesión = JWT firmado.
//   'tabla' → flujos con Form de n8n: la sesión viaja en ?sesion=<id> (el Form solo recibe datos por la URL).
//             El id es aleatorio (256 bits), se guarda en la Data Table "auth_m365_sesiones" y se revoca al cerrar sesión.
// ============================================================
const TENANT_UNI2 = 'f6c1b7c0-d15b-446c-baa7-b6392213858a'; // directorio de UNI2
const INSTANCIA = 'https://uni2.app.n8n.cloud';

const APPS = {
  reconstruye: {
    nombre: 'Reconstruye',
    tenantId: TENANT_UNI2,
    clientId: '10632875-87cd-4b0f-b3b7-e0fac2f288ee', // app "n8n Reconstruye" (solo grupo Desarrollo de Software)
    redirectUris: [`${INSTANCIA}/webhook/reconstruye-auth`, `${INSTANCIA}/webhook/reconstruye-dev-auth`],
    urlDestino: `${INSTANCIA}/webhook/reconstruye`, // a dónde llega el usuario tras el login
    dominiosPermitidos: ['uni2.com.co'],
    modoSesion: 'jwt',
    duracionSesionSegundos: 3600,
    cookieNonce: 'rc_nonce',
    cookieSesion: 'rc_sesion',
    rutaCookie: '/webhook',
    campoSesion: '_sesion',
    prompt: 'select_account',
    ramaCanje: 0,
  },
  extractor: {
    nombre: 'Extractor de Facturación SIIF',
    tenantId: TENANT_UNI2,
    clientId: 'e3e95678-765e-4730-8473-027150d453f4', // app del Extractor (todo el directorio UNI2)
    redirectUris: [`${INSTANCIA}/webhook/extractor-pagares/callback`],
    urlDestino: `${INSTANCIA}/form/extractor-pagares`,
    dominiosPermitidos: ['uni2.com.co'],
    modoSesion: 'tabla', // Form de n8n
    duracionSesionSegundos: 8 * 3600,
    cookieNonce: 'ext_nonce',
    prompt: '',
    ramaCanje: 1,
  },
  rindegastos: {
    nombre: 'Rindegastos SAP',
    tenantId: TENANT_UNI2,
    clientId: '83fa3a4d-4c54-4ec7-a7c7-a4da3a7f8318', // app "Flujo n8n - Rindegastos SAP" (asignación requerida)
    redirectUris: [`${INSTANCIA}/webhook/rindegastos-sap-auth`, `${INSTANCIA}/webhook/rindegastos-sap-dev-auth`],
    urlDestino: '__DESTINO_RINDEGASTOS__', // webhook de entrada del flujo (Webhook + páginas propias)
    dominiosPermitidos: ['uni2.com.co'],
    modoSesion: 'tabla', // id revocable en "auth_m365_sesiones", viaja en cookie + campo oculto
    duracionSesionSegundos: 8 * 3600,
    cookieNonce: 'rg_nonce',
    cookieSesion: 'rg_sesion',
    rutaCookie: '/webhook',
    campoSesion: '_sesion',
    prompt: 'select_account', // como Reconstruye: tras cerrar sesión, Microsoft muestra el selector de cuenta
    ramaCanje: 2,
  },
};

// Índice = salida del nodo "Operación" (4 = error)
const OPERACIONES = ['iniciarLogin', 'procesarCallback', 'verificarSesion', 'cerrarSesion'];

const entrada = $input.first().json;
const operacion = String(entrada.operacion ?? '').trim();
const app = String(entrada.app ?? '').trim().toLowerCase();
const cfg = Object.prototype.hasOwnProperty.call(APPS, app) ? APPS[app] : null;
const redirectUri = String(entrada.redirectUri ?? '').trim().split('?')[0];

// "cookies" llega como la cabecera Cookie completa del webhook
const cookies = {};
String(entrada.cookies ?? '').split(';').forEach((par) => {
  const i = par.indexOf('=');
  if (i <= 0) return;
  try {
    cookies[par.slice(0, i).trim()] = decodeURIComponent(par.slice(i + 1).trim());
  } catch (e) {
    // cookie mal formada: se ignora
  }
});

const query = entrada.query && typeof entrada.query === 'object' ? entrada.query : {};
const tokenSesion = String(entrada.tokenSesion ?? '').trim();

let salida = OPERACIONES.indexOf(operacion);
let codigo = '';
let detalle = '';
if (!cfg) {
  codigo = 'app_desconocida';
  detalle = `app "${app}"`;
} else if (salida < 0) {
  codigo = 'operacion_desconocida';
  detalle = `operación "${operacion}"`;
} else if (['iniciarLogin', 'procesarCallback'].includes(operacion) && !cfg.redirectUris.includes(redirectUri)) {
  codigo = 'redirect_no_permitida';
  detalle = redirectUri || '(vacía)';
}
if (codigo) salida = 4;

return [{ json: { operacion, app, cfg, redirectUri, cookies, query, tokenSesion, salida, codigo, detalle } }];
"""

LOGIN_ARMAR = BASE + r"""// Arma la dirección de inicio de sesión de Microsoft y la fila que guarda el state 10 minutos.
// state y nonce llegan de los nodos Crypto (el sandbox del nodo Code no tiene crypto).
const VIGENCIA_MS = 10 * 60 * 1000;
const HEX64 = /^[0-9a-f]{64}$/;
const { cfg } = base;
const { state, nonce } = $input.first().json;
if (!HEX64.test(state ?? '') || !HEX64.test(nonce ?? '') || state === nonce) {
  throw new Error('state/nonce sin el formato esperado: revise "Login: generar state" y "Login: generar nonce".');
}

const parametros = {
  client_id: cfg.clientId,
  response_type: 'code',
  redirect_uri: base.redirectUri,
  response_mode: 'query',
  scope: 'openid profile email',
  state,
  nonce,
};
if (cfg.prompt) parametros.prompt = cfg.prompt;
const consulta = Object.entries(parametros).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');

return [{
  json: {
    urlAutorizacion: `https://login.microsoftonline.com/${encodeURIComponent(cfg.tenantId)}/oauth2/v2.0/authorize?${consulta}`,
    fila: { state, nonce, app: base.app, expira: Date.now() + VIGENCIA_MS },
  },
}];
"""

LOGIN_RESULTADO = BASE + r"""const prep = $('Login: armar autorización').first().json;
const { cfg } = base;
return [{
  json: {
    ok: true,
    operacion: 'iniciarLogin',
    app: base.app,
    urlRedireccion: prep.urlAutorizacion,
    // El flujo que llama responde 302 a urlRedireccion con esta cookie (ata el regreso a este navegador)
    setCookie: `${cfg.cookieNonce}=${prep.fila.nonce}; Path=/webhook; Max-Age=600; HttpOnly; Secure; SameSite=Lax`,
  },
}];
"""

CALLBACK_REVISAR = BASE + r"""// Clasifica el regreso desde Microsoft: ?code=…&state=… o ?error=…&error_description=…
const q = base.query;
// Un parámetro repetido llega como lista: se toma el primero
const p = (nombre) => {
  const v = Array.isArray(q[nombre]) ? q[nombre][0] : q[nombre];
  return v === undefined || v === null ? '' : String(v).trim();
};
const error = p('error');
const descripcion = p('error_description');
const code = p('code');
const state = p('state').toLowerCase();

if (error) {
  const aadsts = (descripcion.match(/AADSTS\d+/) ?? [''])[0];
  return [{
    json: {
      continuar: false,
      codigo: aadsts || (error === 'access_denied' ? 'access_denied' : 'ms_error'),
      detalle: `${error}${descripcion ? ' · ' + descripcion.replace(/\s+/g, ' ').slice(0, 300) : ''}`,
    },
  }];
}
if (!code || !state) return [{ json: { continuar: false, codigo: 'respuesta_incompleta', detalle: '' } }];
if (!/^[0-9a-f]{64}$/.test(state)) return [{ json: { continuar: false, codigo: 'state_invalido', detalle: '' } }];

return [{ json: { continuar: true, code, state } }];
"""

CALLBACK_VALIDAR_STATE = BASE + r"""// El state debe existir, no estar vencido, ser de esta app y venir del mismo navegador (cookie de nonce).
// "Callback: consumir state" ya lo borró: se usa una sola vez.
const { cfg } = base;
const revision = $('Callback: revisar respuesta').first().json;
const fila = $('Callback: buscar state').all()
  .map((item) => item.json ?? {})
  .find((f) => String(f.state ?? '').toLowerCase() === revision.state);

let codigo = '';
if (!fila) codigo = 'state_inexistente';
else if (!(Number(fila.expira) > Date.now())) codigo = 'state_vencido';
else if (fila.app !== base.app) codigo = 'state_otra_app';
else if (base.cookies[cfg.cookieNonce] !== fila.nonce) codigo = 'navegador_distinto';
if (codigo) return [{ json: { continuar: false, codigo, detalle: '' } }];

return [{
  json: {
    continuar: true,
    ramaCanje: cfg.ramaCanje,
    nonce: fila.nonce,
    code: revision.code,
    redirectUri: base.redirectUri,
    clientId: cfg.clientId,
    tokenUrl: `https://login.microsoftonline.com/${encodeURIComponent(cfg.tenantId)}/oauth2/v2.0/token`,
  },
}];
"""

CALLBACK_VALIDAR_IDENTIDAD = BASE + r"""// Valida el id_token que entregó el endpoint de tokens de Microsoft y arma la sesión.
// La firma RSA no se verifica: el token llega directo del endpoint por TLS y con autenticación de
// cliente (OpenID Connect Core 1.0 §3.1.3.7, punto 6). Sí se validan todos los claims.
// Los tokens de Microsoft no salen de este nodo.
const { cfg } = base;
const nonceEsperado = $('Callback: validar state').first().json.nonce;
const r = $input.first().json ?? {};
const fallo = (codigo, detalle = '') => [{ json: { continuar: false, codigo, detalle: String(detalle).slice(0, 400) } }];

// ------------------------------------------------------------ respuesta del endpoint de tokens
if (!r.id_token) {
  const error = r.error;
  const descripcion = String(r.error_description ?? '');
  const aadsts = (descripcion.match(/AADSTS\d+/) ?? [''])[0];
  if (typeof error === 'string' && error) {
    const detalle = `${error}${descripcion ? ' · ' + descripcion.replace(/\s+/g, ' ').slice(0, 300) : ''}`;
    if (error === 'invalid_client' || ['AADSTS7000215', 'AADSTS7000222', 'AADSTS7000216'].includes(aadsts)) {
      return fallo('secreto_invalido', detalle);
    }
    if (error === 'invalid_grant') return fallo('codigo_vencido', detalle);
    return fallo(aadsts || 'ms_error', detalle);
  }
  // Falla de red o del nodo HTTP (sigue por "On Error: Continue")
  const texto = error && typeof error === 'object' ? (error.message ?? JSON.stringify(error)) : 'respuesta sin id_token';
  return fallo('ms_sin_respuesta', texto);
}

// ------------------------------------------------------------ id_token (JWT)
let cabecera;
let datos;
try {
  const partes = String(r.id_token).split('.');
  if (partes.length !== 3) throw new Error('formato');
  const leer = (parte) => JSON.parse(Buffer.from(parte, 'base64url').toString('utf8'));
  cabecera = leer(partes[0]);
  datos = leer(partes[1]);
} catch (e) {
  return fallo('id_token_invalido', 'el id_token no se pudo leer');
}

const ahora = Math.floor(Date.now() / 1000);
const TOLERANCIA_RELOJ_S = 300;
const audiencias = Array.isArray(datos.aud) ? datos.aud : [datos.aud];
const emisor = `https://login.microsoftonline.com/${cfg.tenantId}/v2.0`;
const igual = (a, b) => String(a ?? '').toLowerCase() === String(b ?? '').toLowerCase();

const problemas = [];
if (String(cabecera.alg ?? 'none').toLowerCase() === 'none') problemas.push('alg');
if (!audiencias.includes(cfg.clientId)) problemas.push('aud');
if (audiencias.length > 1 && datos.azp !== cfg.clientId) problemas.push('azp');
if (!igual(datos.iss, emisor)) problemas.push('iss');
if (!igual(datos.tid, cfg.tenantId)) problemas.push('tid');
if (!(Number(datos.exp) > ahora - TOLERANCIA_RELOJ_S)) problemas.push('exp');
if (datos.nbf != null && Number(datos.nbf) > ahora + TOLERANCIA_RELOJ_S) problemas.push('nbf');
if (datos.iat != null && Number(datos.iat) > ahora + TOLERANCIA_RELOJ_S) problemas.push('iat');
if (!nonceEsperado || datos.nonce !== nonceEsperado) problemas.push('nonce');
if (problemas.length) {
  return fallo(problemas.includes('tid') ? 'otro_directorio' : 'id_token_invalido', 'claims: ' + problemas.join(', '));
}

const email = String(datos.preferred_username || datos.email || datos.upn || '').trim().toLowerCase();
if (!cfg.dominiosPermitidos.some((d) => email.endsWith('@' + d.toLowerCase()))) {
  return fallo('dominio_no_permitido', email || '(sin correo)');
}

return [{
  json: {
    continuar: true,
    sesion: {
      tipo: 'sesion',
      app: base.app,
      email,
      nombre: String(datos.name ?? ''),
      oid: String(datos.oid ?? ''),
      iat: ahora,
      exp: ahora + cfg.duracionSesionSegundos,
    },
  },
}];
"""

CALLBACK_RESULTADO = BASE + r"""const { cfg } = base;
const sesion = $('Callback: validar identidad').first().json.sesion;
const token = String($input.first().json.token ?? '');
if (!token) throw new Error('No se pudo firmar la sesión: revise la credencial de "Callback: firmar sesión".');

return [{
  json: {
    ok: true,
    operacion: 'procesarCallback',
    app: base.app,
    usuario: { email: sesion.email, nombre: sesion.nombre, oid: sesion.oid },
    tokenSesion: token,
    venceSesion: sesion.exp,
    urlDestino: cfg.urlDestino,
    setCookie: `${cfg.cookieSesion}=${token}; Path=${cfg.rutaCookie}; Max-Age=${cfg.duracionSesionSegundos}; HttpOnly; Secure; SameSite=Lax`,
    campoOculto: `<input type="hidden" name="${cfg.campoSesion}" value="${token}">`,
  },
}];
"""

SESION_PREPARAR = BASE + r"""// Modo 'jwt': la sesión llega en el campo oculto del formulario (tokenSesion) o en la cookie de la app.
//   n8n Cloud sirve las páginas con CSP sandbox: los POST de formularios llegan SIN cookies,
//   por eso el campo oculto tiene prioridad; la cookie solo sirve en peticiones GET.
// Modo 'tabla': la sesión es un id aleatorio; llega en tokenSesion o en la cookie de la app (si tiene).
// Salida "modo" = salida de "Sesión: modo" (0 jwt, 1 tabla).
const { cfg } = base;
const tabla = cfg.modoSesion === 'tabla';
const deCookie = String((cfg.cookieSesion && base.cookies[cfg.cookieSesion]) ?? '');
const token = tabla ? (base.tokenSesion || deCookie).toLowerCase() : base.tokenSesion || deCookie;
if (!token) return [{ json: { continuar: false, codigo: 'sin_sesion', detalle: '' } }];
const formato = tabla ? /^[0-9a-f]{64}$/ : /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/;
if (!formato.test(token)) {
  return [{ json: { continuar: false, codigo: 'sesion_invalida', detalle: 'formato' } }];
}
return [{ json: { continuar: true, token, modo: tabla ? 1 : 0 } }];
"""

SESION_VALIDAR_FILA = BASE + r"""// Modo 'tabla': la sesión debe existir, ser de esta app, no haber vencido y ser de un dominio permitido.
const { cfg } = base;
const token = $('Sesión: preparar').first().json.token;
const fila = $input.all()
  .map((item) => item.json ?? {})
  .find((f) => String(f.sesion ?? '').toLowerCase() === token);
const email = String(fila?.email ?? '').toLowerCase();

let codigo = '';
if (!fila) codigo = 'sesion_invalida';
else if (fila.app !== base.app) codigo = 'sesion_otra_app';
else if (!(Number(fila.expira) > Date.now())) codigo = 'sesion_vencida';
else if (!cfg.dominiosPermitidos.some((d) => email.endsWith('@' + d.toLowerCase()))) codigo = 'dominio_no_permitido';
if (codigo) return [{ json: { continuar: false, codigo, detalle: '' } }];

return [{
  json: {
    continuar: true,
    usuario: { email, nombre: String(fila.nombre ?? ''), oid: String(fila.oid ?? '') },
    sesionId: token,
    tokenSesion: token,
    venceSesion: Math.floor(Number(fila.expira) / 1000),
    // Los POST de formularios llegan sin cookies (sandbox de n8n): la sesión viaja en este campo oculto
    campoOculto: `<input type="hidden" name="${cfg.campoSesion || '_sesion'}" value="${token}">`,
  },
}];
"""

CALLBACK_PREPARAR_TABLA = BASE + r"""// Modo 'tabla': fila de "auth_m365_sesiones" (sesiones activas) con el id aleatorio del nodo Crypto.
const sesion = $('Callback: validar identidad').first().json.sesion;
const id = String($input.first().json.sesionId ?? '');
if (!/^[0-9a-f]{64}$/.test(id)) throw new Error('id de sesión sin el formato esperado: revise "Callback: generar id de sesión".');
return [{
  json: {
    sesion: id, app: base.app, email: sesion.email, nombre: sesion.nombre, oid: sesion.oid,
    inicio: new Date(sesion.iat * 1000).toISOString(), expira: sesion.exp * 1000,
  },
}];
"""

REGISTRO_INICIO = BASE + r"""// Registro de accesos: inicio de sesión exitoso (tabla "auth_m365_registro_accesos", retención 90 días).
const sesion = $('Callback: validar identidad').first().json.sesion;
const ahora = new Date();
return [{
  json: {
    fecha: ahora.toISOString(), ts: ahora.getTime(), evento: 'inicio_sesion', app: base.app,
    email: sesion.email, nombre: sesion.nombre,
    detalle: `sesión ${base.cfg.modoSesion}, vence ${new Date(sesion.exp * 1000).toISOString()}`,
  },
}];
"""

CIERRE_PREPARAR = BASE + r"""// Identifica la sesión que se cierra: tokenSesion o cookie de la app.
// Salida "modo" = salida de "Cierre: modo" (0 jwt, 1 tabla). En jwt el usuario se lee del token (sin
// verificar la firma: solo se usa para el registro de accesos).
const { cfg } = base;
const tabla = cfg.modoSesion === 'tabla';
const token = String(base.tokenSesion || (cfg.cookieSesion && base.cookies[cfg.cookieSesion]) || '').trim();
let email = '';
let nombre = '';
if (!tabla && token.split('.').length === 3) {
  try {
    const p = JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString('utf8'));
    if (p.app === base.app) { email = String(p.email ?? ''); nombre = String(p.nombre ?? ''); }
  } catch (e) {
    // token ilegible: se registra sin usuario
  }
}
return [{ json: { modo: tabla ? 1 : 0, token: tabla ? token.toLowerCase() : token, email, nombre } }];
"""

REGISTRO_CIERRE = BASE + r"""// Registro de accesos: cierre de sesión.
const prep = $('Cierre: preparar').first().json;
let { email, nombre } = prep;
let detalle = '';
if (prep.modo === 1) {
  let filas = [];
  try { filas = $('Cierre: buscar sesión').all().map((i) => i.json ?? {}); } catch (e) { filas = []; }
  const fila = filas.find((f) => f.sesion);
  if (fila) { email = fila.email; nombre = fila.nombre; detalle = 'sesión anulada en el servidor'; }
  else detalle = 'no había una sesión activa';
} else {
  detalle = 'cookie borrada (sesión jwt)';
}
const ahora = new Date();
return [{
  json: { fecha: ahora.toISOString(), ts: ahora.getTime(), evento: 'cierre_sesion', app: base.app, email: email || '', nombre: nombre || '', detalle },
}];
"""

CALLBACK_RESULTADO_TABLA = BASE + r"""// Modo 'tabla': el flujo de acceso redirige a urlDestino.
//   App con cookie (cookieSesion): la sesión va en Set-Cookie.
//   App con Form de n8n: la sesión va en ?sesion=<id> (el Form la toma en su campo oculto "sesion");
//   setCookie solo borra la cookie de nonce, que ya no se necesita.
const { cfg } = base;
const fila = $('Callback: preparar sesión').first().json;
const conCookie = Boolean(cfg.cookieSesion);
const sep = String(cfg.urlDestino).includes('?') ? '&' : '?';
return [{
  json: {
    ok: true,
    operacion: 'procesarCallback',
    app: base.app,
    usuario: { email: fila.email, nombre: fila.nombre, oid: fila.oid },
    sesionId: fila.sesion,
    venceSesion: Math.floor(fila.expira / 1000),
    urlDestino: conCookie ? cfg.urlDestino : `${cfg.urlDestino}${sep}sesion=${fila.sesion}`,
    setCookie: conCookie
      ? `${cfg.cookieSesion}=${fila.sesion}; Path=${cfg.rutaCookie}; Max-Age=${cfg.duracionSesionSegundos}; HttpOnly; Secure; SameSite=Lax`
      : `${cfg.cookieNonce}=; Path=/webhook; Max-Age=0; HttpOnly; Secure; SameSite=Lax`,
  },
}];
"""

SESION_RECHAZADA = r"""// Salida de error de "Sesión: verificar firma": firma alterada, otra llave o token vencido.
const error = $input.first().json.error;
const mensaje = String((error && (error.message ?? error)) || $input.first().json.message || '');
return [{
  json: {
    continuar: false,
    codigo: /expired/i.test(mensaje) ? 'sesion_vencida' : 'sesion_invalida',
    detalle: mensaje.slice(0, 200),
  },
}];
"""

SESION_VALIDAR = BASE + r"""const { cfg } = base;
const p = $input.first().json.payload ?? {};
const token = $('Sesión: preparar').first().json.token;
const ahora = Math.floor(Date.now() / 1000);
const email = String(p.email ?? '').toLowerCase();

let codigo = '';
if (p.tipo !== 'sesion') codigo = 'sesion_invalida';
else if (p.app !== base.app) codigo = 'sesion_otra_app';
else if (!(Number(p.exp) > ahora)) codigo = 'sesion_vencida';
else if (!cfg.dominiosPermitidos.some((d) => email.endsWith('@' + d.toLowerCase()))) codigo = 'dominio_no_permitido';
if (codigo) return [{ json: { continuar: false, codigo, detalle: '' } }];

return [{
  json: {
    continuar: true,
    usuario: { email, nombre: String(p.nombre ?? ''), oid: String(p.oid ?? '') },
    tokenSesion: token,
    venceSesion: Number(p.exp),
    campoOculto: `<input type="hidden" name="${cfg.campoSesion}" value="${token}">`,
  },
}];
"""

SESION_RESULTADO = BASE + r"""const { continuar, ...sesion } = $input.first().json;
return [{ json: { ok: true, operacion: 'verificarSesion', app: base.app, ...sesion } }];
"""

CIERRE_RESULTADO = BASE + r"""// Modo 'jwt': la sesión no se puede revocar en el servidor. Cerrar sesión = borrar la cookie;
//   el flujo que llama debe además dejar de enviar el campo oculto.
// Modo 'tabla': "Cierre: borrar sesión" ya eliminó la fila: el id deja de servir.
const { cfg } = base;
return [{
  json: {
    ok: true,
    operacion: 'cerrarSesion',
    app: base.app,
    // Siempre una cabecera válida: la cookie de sesión de la app o, si no tiene, la de nonce
    setCookie: cfg.cookieSesion
      ? `${cfg.cookieSesion}=; Path=${cfg.rutaCookie}; Max-Age=0; HttpOnly; Secure; SameSite=Lax`
      : `${cfg.cookieNonce}=; Path=/webhook; Max-Age=0; HttpOnly; Secure; SameSite=Lax`,
  },
}];
"""

ERROR_DESCRIBIR = BASE + r"""// Único lugar con los mensajes de error que ve el usuario.
// accion: qué debe hacer el flujo que llama → 'login' (enviar al login), 'reintentar' (página con
// botón para volver a ingresar) o 'contactar_ti' (página de error sin reintento automático).
// titulo/mensaje/consejos/detalle van en texto plano: escaparlos al mostrarlos, o usar "html" (ya escapado).
const { codigo = 'error_desconocido', detalle = '' } = $input.first().json;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const PARA_TI = ['Avise a TI con el detalle técnico que aparece abajo.'];
const VOLVER = ['Vuelva a ingresar desde el enlace del formulario.'];
const MENSAJES = {
  // Configuración del flujo que llama
  app_desconocida: { accion: 'contactar_ti', titulo: 'Aplicación no registrada', mensaje: 'Este flujo no está registrado en el subflujo de autenticación.', consejos: PARA_TI },
  operacion_desconocida: { accion: 'contactar_ti', titulo: 'Operación no válida', mensaje: 'El flujo pidió una operación de autenticación que no existe.', consejos: PARA_TI },
  redirect_no_permitida: { accion: 'contactar_ti', titulo: 'Dirección de retorno no permitida', mensaje: 'La dirección de regreso del flujo no está registrada para esta aplicación.', consejos: PARA_TI },
  // Errores que informa Microsoft (https://learn.microsoft.com/entra/identity-platform/reference-error-codes)
  access_denied: { accion: 'reintentar', titulo: 'Se canceló el inicio de sesión', mensaje: 'Microsoft no completó el ingreso.', consejos: ['Vuelva a intentar. Si el problema sigue, avise a TI.'] },
  AADSTS65004: { accion: 'reintentar', titulo: 'Se canceló el inicio de sesión', mensaje: 'No se aceptaron los permisos que solicita la aplicación.', consejos: ['Vuelva a intentar y acepte el permiso de iniciar sesión y leer su perfil.'] },
  AADSTS50105: { accion: 'contactar_ti', titulo: 'Su cuenta no tiene acceso a esta aplicación', mensaje: 'Microsoft confirmó su identidad, pero su usuario no está habilitado para esta aplicación.', consejos: ['Solicite a Infraestructura que lo agregue al grupo autorizado de la aplicación.'] },
  AADSTS50020: { accion: 'reintentar', titulo: 'Debe ingresar con su cuenta corporativa de UNI2', mensaje: 'La cuenta con la que ingresó pertenece a otra organización o es una cuenta personal.', consejos: ['Cierre la sesión de esa cuenta en Microsoft e ingrese con su correo corporativo.'] },
  AADSTS50034: { accion: 'reintentar', titulo: 'Debe ingresar con su cuenta corporativa de UNI2', mensaje: 'Esa cuenta no existe en el directorio de UNI2.', consejos: ['Revise que escribió bien su correo corporativo.'] },
  AADSTS700016: { accion: 'contactar_ti', titulo: 'La aplicación no está registrada', mensaje: 'Microsoft no reconoce el Id. de aplicación (client id) configurado.', consejos: PARA_TI },
  AADSTS90002: { accion: 'contactar_ti', titulo: 'El directorio no existe', mensaje: 'Microsoft no reconoce el Id. de directorio (tenant) configurado.', consejos: PARA_TI },
  AADSTS50011: { accion: 'contactar_ti', titulo: 'La dirección de retorno no coincide', mensaje: 'La dirección de regreso del flujo no es la registrada en Entra ID.', consejos: PARA_TI },
  ms_error: { accion: 'reintentar', titulo: 'Microsoft no completó el inicio de sesión', mensaje: 'Ocurrió un problema al validar su cuenta.', consejos: ['Vuelva a intentar en unos minutos. Si el problema sigue, avise a TI.'] },
  respuesta_incompleta: { accion: 'reintentar', titulo: 'El inicio de sesión llegó incompleto', mensaje: 'La respuesta de Microsoft no trae los datos esperados.', consejos: VOLVER },
  // state (protección CSRF)
  state_invalido: { accion: 'reintentar', titulo: 'El inicio de sesión no es válido', mensaje: 'El enlace de regreso desde Microsoft no corresponde a un inicio de sesión de este flujo.', consejos: VOLVER },
  state_inexistente: { accion: 'reintentar', titulo: 'El inicio de sesión ya se usó', mensaje: 'Este enlace de regreso ya se usó o no corresponde a un inicio de sesión de este flujo.', consejos: VOLVER },
  state_vencido: { accion: 'reintentar', titulo: 'El inicio de sesión venció', mensaje: 'Pasaron más de 10 minutos entre el inicio y el regreso desde Microsoft.', consejos: VOLVER },
  state_otra_app: { accion: 'reintentar', titulo: 'El inicio de sesión no corresponde a esta aplicación', mensaje: 'El regreso desde Microsoft pertenece a otro flujo.', consejos: VOLVER },
  navegador_distinto: { accion: 'reintentar', titulo: 'El inicio de sesión no corresponde a este navegador', mensaje: 'El regreso desde Microsoft se abrió en un navegador distinto al que inició el ingreso.', consejos: ['Vuelva a ingresar desde este navegador.'] },
  // Canje del código
  secreto_invalido: { accion: 'contactar_ti', titulo: 'El acceso con Microsoft 365 necesita mantenimiento', mensaje: 'El secreto de la aplicación en n8n no es válido o ya venció.', consejos: ['Avise a TI: debe renovar el secreto de cliente en Entra ID y actualizar la credencial del nodo de canje.'] },
  codigo_vencido: { accion: 'reintentar', titulo: 'El inicio de sesión venció', mensaje: 'El código que entregó Microsoft ya se usó o venció.', consejos: VOLVER },
  ms_sin_respuesta: { accion: 'reintentar', titulo: 'No se pudo comunicar con Microsoft', mensaje: 'El servicio de inicio de sesión no respondió como se esperaba.', consejos: ['Vuelva a intentar en unos minutos. Si el problema sigue, avise a TI.'] },
  // Identidad
  id_token_invalido: { accion: 'contactar_ti', titulo: 'No se pudo confirmar su identidad', mensaje: 'La respuesta de Microsoft no pasó las validaciones de seguridad.', consejos: PARA_TI },
  otro_directorio: { accion: 'reintentar', titulo: 'Debe ingresar con su cuenta corporativa de UNI2', mensaje: 'La cuenta no pertenece al directorio de UNI2.', consejos: ['Cierre la sesión de esa cuenta en Microsoft e ingrese con su correo corporativo.'] },
  dominio_no_permitido: { accion: 'contactar_ti', titulo: 'Cuenta no permitida', mensaje: 'La cuenta no es de un dominio permitido para esta aplicación.', consejos: PARA_TI },
  // Sesión
  sin_sesion: { accion: 'login', titulo: 'Debe iniciar sesión', mensaje: 'Ingrese con su cuenta de Microsoft 365 para continuar.', consejos: [] },
  sesion_invalida: { accion: 'login', titulo: 'La sesión no es válida', mensaje: 'Vuelva a iniciar sesión con su cuenta de Microsoft 365.', consejos: [] },
  sesion_vencida: { accion: 'login', titulo: 'La sesión venció', mensaje: 'Vuelva a iniciar sesión con su cuenta de Microsoft 365.', consejos: [] },
  sesion_otra_app: { accion: 'login', titulo: 'La sesión no corresponde a esta aplicación', mensaje: 'Vuelva a iniciar sesión con su cuenta de Microsoft 365.', consejos: [] },
};
const caso = Object.prototype.hasOwnProperty.call(MENSAJES, codigo)
  ? MENSAJES[codigo]
  : { accion: 'reintentar', titulo: 'No se pudo completar el inicio de sesión', mensaje: 'Ocurrió un problema inesperado.', consejos: ['Vuelva a intentar. Si el problema sigue, avise a TI.'] };

const detalleTecnico = [codigo, detalle].filter(Boolean).join(' · ');
const html = `<h1>${esc(caso.titulo)}</h1><p>${esc(caso.mensaje)}</p>`
  + (caso.consejos.length ? `<ul class="consejos">${caso.consejos.map((c) => `<li>${esc(c)}</li>`).join('')}</ul>` : '')
  + `<p class="detalle-tecnico">${esc(detalleTecnico)}</p>`;

return [{
  json: {
    ok: false,
    operacion: base.operacion,
    app: base.app,
    codigo,
    accion: caso.accion,
    titulo: caso.titulo,
    mensaje: caso.mensaje,
    consejos: caso.consejos,
    detalle: detalleTecnico,
    html,
  },
}];
"""

# ---------------------------------------------------------------- notas del lienzo

NOTA_RESUMEN = """## Auth · Microsoft 365
Subflujo reutilizable de inicio de sesión con **Microsoft 365** (Entra ID, OpenID Connect con código de autorización). Issue #389.

Los **webhooks y las páginas** siguen en cada flujo: este subflujo solo hace la parte de seguridad y devuelve datos.

### Entradas (Execute Workflow)
| Campo | Uso |
|---|---|
| `operacion` | `iniciarLogin` · `procesarCallback` · `verificarSesion` · `cerrarSesion` |
| `app` | Clave en *Registro de aplicaciones* (`reconstruye`, `extractor`, `rindegastos`) |
| `redirectUri` | URL del webhook de regreso (debe estar registrada) |
| `cookies` | Cabecera `Cookie` del webhook (`$json.headers.cookie`) |
| `query` | Query del webhook de regreso (`$json.query`) |
| `tokenSesion` | Campo oculto `_sesion` (modo jwt) o campo `sesion` del Form (modo tabla) |

### Salida
`ok: true` + datos de la operación (`urlRedireccion`, `setCookie`, `usuario`, `tokenSesion`, `campoOculto`, `sesionId`…), u
`ok: false` + `codigo`, `accion` (`login` · `reintentar` · `contactar_ti`), `titulo`, `mensaje`, `consejos`, `detalle` y `html` (ya escapado).

### Dos modos de sesión (`modoSesion` en el registro)
- **jwt** (flujos con webhooks, p. ej. Reconstruye): **JWT firmado** con la credencial *Auth M365 · Firma de sesiones*, con claim `app`. Viaja en cookie + campo oculto.
- **tabla** (p. ej. Rindegastos SAP, Webhook + Wait form): **id aleatorio** (256 bits) en la Data Table **auth_m365_sesiones**. Viaja en la cookie de la app (`cookieSesion`) o en `tokenSesion`; se **revoca** al cerrar sesión.

### Seguridad
- `state` aleatorio (256 bits), **un solo uso**, 10 min, en la Data Table **auth_m365_inicios**.
- `nonce` en cookie: el regreso solo sirve en el navegador que inició el ingreso.
- Las tablas son compartidas por todas las apps: cada fila lleva `app` (y `email`) y siempre se exige que la app coincida.
- **auth_m365_registro_accesos**: eventos `inicio_sesion` y `cierre_sesion` (fecha, app, usuario), 90 días.
- No se guardan tokens de Microsoft."""

NOTA_LOGIN = """## ① iniciarLogin
Genera `state` y `nonce`, guarda el `state` 10 min y devuelve la URL de Microsoft.
El flujo responde **302** a `urlRedireccion` con la cabecera `Set-Cookie: setCookie`."""

NOTA_CALLBACK = """## ② procesarCallback
Revisa la respuesta de Microsoft → busca y **borra** el `state` → limpia vencidos → valida `state` y cookie de `nonce` → canjea el código con la credencial **de la app** → valida el `id_token` (`alg`, `aud`, `azp`, `iss`, `tid`, `exp`, `nbf`, `iat`, `nonce`, dominio) → crea la sesión según el modo.
- **jwt:** firma la sesión; el flujo responde **303** a su página inicial con `Set-Cookie: setCookie`.
- **tabla:** guarda la sesión en *auth_m365_sesiones*; el flujo responde con `Set-Cookie: setCookie` (o usa `sesionId`)."""

NOTA_SESION = """## ③ verificarSesion
- **jwt:** sesión del campo oculto (`tokenSesion`) o de la cookie de la app; verifica firma y vencimiento, y que sea de esta `app`.
- **tabla:** busca el id (`tokenSesion`) en *auth_m365_sesiones*; exige que exista, sea de esta `app` y no haya vencido.
Devuelve `usuario` (y `campoOculto` / `sesionId`)."""

NOTA_CIERRE = """## ④ cerrarSesion
- **jwt:** devuelve la cookie de borrado (un JWT no se revoca en el servidor).
- **tabla:** busca y borra la fila de la sesión: el id deja de servir (sesión anulada).
En los dos casos deja el evento `cierre_sesion` en **auth_m365_registro_accesos**."""

NOTA_LIMPIEZA = """## ⑤ Limpieza diaria (3:00 a. m.)
- **auth_m365_sesiones**: borra las sesiones vencidas → la tabla solo tiene **sesiones activas** (usuario, app, inicio, vence).
- **auth_m365_inicios**: borra los inicios de login sin terminar.
- **auth_m365_registro_accesos**: borra eventos de más de **90 días**.

**Ver quién está conectado:** abrir *auth_m365_sesiones* (filtrar por `app`).
**Anular una sesión:** borrar su fila; la persona queda fuera en su siguiente petición (apps en modo *tabla*)."""

NOTA_ERROR = """## ✖ Errores
Todos los rechazos llegan aquí con un `codigo`. Este nodo es el **único lugar** con los mensajes para el usuario."""

NOTA_CANJE = """### Una rama por app
n8n no permite elegir la credencial en tiempo de ejecución: cada app tiene su nodo de canje con su secreto.
**Extractor:** usa por ahora la misma credencial Custom Auth que *Acceso Office 365*; en la fase 3 pasa a Basic Auth."""

# ---------------------------------------------------------------- construcción

nodes = []
connections = {}


def nodo(nombre, tipo, version, pos, params, **extra):
    n = {'parameters': params, 'id': str(uuid.uuid4()), 'name': nombre, 'type': tipo, 'typeVersion': version, 'position': list(pos)}
    n.update(extra)
    nodes.append(n)
    return nombre


def code(nombre, pos, js, **extra):
    return nodo(nombre, 'n8n-nodes-base.code', 2, pos, {'jsCode': js}, **extra)


def si(nombre, pos, expresion):
    return nodo(nombre, 'n8n-nodes-base.if', 2.2, pos, {
        'conditions': {
            'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose', 'version': 2},
            'conditions': [{'id': str(uuid.uuid4()), 'leftValue': expresion, 'rightValue': '',
                            'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}],
            'combinator': 'and',
        },
        'looseTypeValidation': True,
        'options': {},
    })


def nota(nombre, pos, contenido, ancho, alto, color):
    nodo(nombre, 'n8n-nodes-base.stickyNote', 1, pos, {'content': contenido, 'width': ancho, 'height': alto, 'color': color})


def unir(origen, *salidas):
    """salidas: una lista de destinos por cada salida del nodo origen."""
    connections[origen] = {'main': [[{'node': d, 'type': 'main', 'index': 0} for d in destinos] for destinos in salidas]}


def canje(nombre, pos, credencial, tipo_auth, extra_headers):
    params = {
        'method': 'POST',
        'url': '={{ $json.tokenUrl }}',
        'authentication': 'genericCredentialType',
        'genericAuthType': tipo_auth,
        'sendBody': True,
        'contentType': 'form-urlencoded',
        'bodyParameters': {'parameters': [
            {'name': 'grant_type', 'value': 'authorization_code'},
            {'name': 'client_id', 'value': '={{ $json.clientId }}'},
            {'name': 'code', 'value': '={{ $json.code }}'},
            {'name': 'redirect_uri', 'value': '={{ $json.redirectUri }}'},
            {'name': 'scope', 'value': 'openid profile email'},
        ]},
        'options': {'response': {'response': {'neverError': True, 'responseFormat': 'json'}}, 'timeout': 20000},
    }
    if extra_headers:
        params['sendHeaders'] = True
        params['headerParameters'] = {'parameters': [{'name': 'Content-Type', 'value': 'application/x-www-form-urlencoded'}]}
    return nodo(nombre, 'n8n-nodes-base.httpRequest', 4.2, pos, params, credentials=credencial, onError='continueRegularOutput')


ERROR = 'Error: describir'

# Notas (primero, para que queden detrás)
nota('Nota 0 · Resumen', (-520, -380), NOTA_RESUMEN, 480, 1180, 7)
nota('Nota 1 · iniciarLogin', (660, -380), NOTA_LOGIN, 1140, 320, 6)
nota('Nota 2 · procesarCallback', (660, -20), NOTA_CALLBACK, 4240, 580, 4)
nota('Nota 3 · verificarSesion', (660, 600), NOTA_SESION, 1600, 500, 5)
nota('Nota 4 · cerrarSesion', (660, 1140), NOTA_CIERRE, 1600, 400, 3)
nota('Nota 5 · Errores', (2560, 1140), NOTA_ERROR, 460, 340, 2)
nota('Nota 7 · Limpieza', (-60, 1600), NOTA_LIMPIEZA, 900, 320, 7)
nota('Nota 6 · Canje', (2400, -260), NOTA_CANJE, 460, 200, 1)

# Entrada común
nodo('Entrada', 'n8n-nodes-base.executeWorkflowTrigger', 1.1, (0, 300), {
    'inputSource': 'workflowInputs',
    'workflowInputs': {'values': [
        {'name': 'operacion', 'type': 'string'},
        {'name': 'app', 'type': 'string'},
        {'name': 'redirectUri', 'type': 'string'},
        {'name': 'cookies', 'type': 'string'},
        {'name': 'query', 'type': 'object'},
        {'name': 'tokenSesion', 'type': 'string'},
    ]},
})
code('Registro de aplicaciones', (220, 300), REGISTRO)
nodo('Operación', 'n8n-nodes-base.switch', 3.2, (440, 300), {'mode': 'expression', 'numberOutputs': 5, 'output': '={{ $json.salida }}'})

# ① iniciarLogin
crypto = {'action': 'generate', 'encodingType': 'hex', 'stringLength': 64}
nodo('Login: generar state', 'n8n-nodes-base.crypto', 2, (720, -200), {**crypto, 'dataPropertyName': 'state'})
nodo('Login: generar nonce', 'n8n-nodes-base.crypto', 2, (940, -200), {**crypto, 'dataPropertyName': 'nonce'})
code('Login: armar autorización', (1160, -200), LOGIN_ARMAR)
nodo('Login: guardar state', 'n8n-nodes-base.dataTable', 1, (1380, -200), {
    'dataTableId': TABLA,
    'columns': {
        'mappingMode': 'defineBelow',
        'value': {c: '={{ $json.fila.%s }}' % c for c in ('state', 'nonce', 'app', 'expira')},
        'matchingColumns': [],
        'schema': [{'id': c, 'displayName': c, 'required': False, 'defaultMatch': False, 'display': True,
                    'type': 'number' if c == 'expira' else 'string', 'canBeUsedToMatch': True}
                   for c in ('state', 'nonce', 'app', 'expira')],
        'attemptToConvertTypes': False,
        'convertFieldsToString': False,
    },
    'options': {},
})
code('Login: resultado', (1600, -200), LOGIN_RESULTADO)

# ② procesarCallback
STATE = "={{ $('Callback: revisar respuesta').first().json.state }}"
code('Callback: revisar respuesta', (720, 200), CALLBACK_REVISAR)
si('¿Respuesta completa?', (940, 200), '={{ $json.continuar }}')
nodo('Callback: buscar state', 'n8n-nodes-base.dataTable', 1, (1160, 120), {
    'operation': 'get', 'dataTableId': TABLA, 'matchType': 'allConditions',
    'filters': {'conditions': [{'keyName': 'state', 'keyValue': STATE}]}, 'limit': 5,
}, alwaysOutputData=True)
nodo('Callback: consumir state', 'n8n-nodes-base.dataTable', 1, (1380, 120), {
    'operation': 'deleteRows', 'dataTableId': TABLA, 'matchType': 'allConditions',
    'filters': {'conditions': [{'keyName': 'state', 'keyValue': STATE}]}, 'options': {},
}, alwaysOutputData=True)
nodo('Callback: limpiar vencidos', 'n8n-nodes-base.dataTable', 1, (1600, 120), {
    'operation': 'deleteRows', 'dataTableId': TABLA,
    'filters': {'conditions': [{'keyName': 'expira', 'condition': 'lt', 'keyValue': '={{ $now.toMillis() }}'}]}, 'options': {},
}, alwaysOutputData=True)
code('Callback: validar state', (1820, 200), CALLBACK_VALIDAR_STATE)
si('¿State válido?', (2040, 200), '={{ $json.continuar }}')
nodo('Canje: elegir app', 'n8n-nodes-base.switch', 3.2, (2260, 200), {'mode': 'expression', 'numberOutputs': 3, 'output': '={{ $json.ramaCanje }}'})
canje('Canje · Reconstruye', (2480, 60), CRED_RECONSTRUYE, 'httpBasicAuth', False)
canje('Canje · Extractor', (2480, 220), CRED_EXTRACTOR, 'httpCustomAuth', True)
canje('Canje · Rindegastos', (2480, 380), CRED_RINDEGASTOS, 'httpBasicAuth', False)
code('Callback: validar identidad', (2700, 200), CALLBACK_VALIDAR_IDENTIDAD)
si('¿Identidad válida?', (2920, 200), '={{ $json.continuar }}')


def insertar(nombre, pos, tabla_rl, columnas):
    """Data Table insert de las columnas que entrega el nodo anterior (mismos nombres)."""
    tipos = {'expira': 'number', 'ts': 'number', 'inicio': 'dateTime', 'fecha': 'dateTime'}
    return nodo(nombre, 'n8n-nodes-base.dataTable', 1, pos, {
        'dataTableId': tabla_rl,
        'columns': {
            'mappingMode': 'defineBelow',
            'value': {c: '={{ $json.%s }}' % c for c in columnas},
            'matchingColumns': [],
            'schema': [{'id': c, 'displayName': c, 'required': False, 'defaultMatch': False, 'display': True,
                        'type': tipos.get(c, 'string'), 'canBeUsedToMatch': True} for c in columnas],
            'attemptToConvertTypes': True,
            'convertFieldsToString': False,
        },
        'options': {},
    })


COLUMNAS_REGISTRO = ('fecha', 'evento', 'app', 'email', 'nombre', 'detalle', 'ts')
code('Registro: preparar inicio', (3140, 200), REGISTRO_INICIO)
insertar('Registro: guardar inicio', (3360, 200), TABLA_REGISTRO, COLUMNAS_REGISTRO)
MODO = "={{ $('Registro de aplicaciones').first().json.cfg.modoSesion === 'tabla' ? 1 : 0 }}"
nodo('Callback: modo', 'n8n-nodes-base.switch', 3.2, (3580, 200), {'mode': 'expression', 'numberOutputs': 2, 'output': MODO})
nodo('Callback: firmar sesión', 'n8n-nodes-base.jwt', 1, (3800, 80), {
    'useJson': True, 'claimsJson': "={{ JSON.stringify($('Callback: validar identidad').first().json.sesion) }}", 'options': {},
}, credentials=CRED_JWT)
code('Callback: resultado', (4020, 80), CALLBACK_RESULTADO)
nodo('Callback: generar id de sesión', 'n8n-nodes-base.crypto', 2, (3800, 340), {**crypto, 'dataPropertyName': 'sesionId'})
code('Callback: preparar sesión', (4020, 340), CALLBACK_PREPARAR_TABLA)
insertar('Callback: guardar sesión', (4240, 340), TABLA_SESIONES, ('sesion', 'app', 'email', 'nombre', 'oid', 'inicio', 'expira'))
nodo('Callback: limpiar sesiones vencidas', 'n8n-nodes-base.dataTable', 1, (4460, 340), {
    'operation': 'deleteRows', 'dataTableId': TABLA_SESIONES,
    'filters': {'conditions': [{'keyName': 'expira', 'condition': 'lt', 'keyValue': '={{ $now.toMillis() }}'}]}, 'options': {},
}, alwaysOutputData=True)
code('Callback: resultado (tabla)', (4680, 340), CALLBACK_RESULTADO_TABLA)

# ③ verificarSesion
code('Sesión: preparar', (720, 800), SESION_PREPARAR)
si('¿Hay sesión?', (940, 800), '={{ $json.continuar }}')
nodo('Sesión: modo', 'n8n-nodes-base.switch', 3.2, (1160, 800), {'mode': 'expression', 'numberOutputs': 2, 'output': '={{ $json.modo }}'})
nodo('Sesión: verificar firma', 'n8n-nodes-base.jwt', 1, (1380, 720), {
    'operation': 'verify', 'token': '={{ $json.token }}', 'options': {},
}, credentials=CRED_JWT, onError='continueErrorOutput')
code('Sesión: validar', (1600, 700), SESION_VALIDAR)
code('Sesión: firma rechazada', (1600, 860), SESION_RECHAZADA)
nodo('Sesión: buscar en tabla', 'n8n-nodes-base.dataTable', 1, (1380, 1000), {
    'operation': 'get', 'dataTableId': TABLA_SESIONES, 'matchType': 'allConditions',
    'filters': {'conditions': [
        {'keyName': 'sesion', 'keyValue': '={{ $json.token }}'},
        {'keyName': 'app', 'keyValue': "={{ $('Registro de aplicaciones').first().json.app }}"},
    ]}, 'limit': 5,
}, alwaysOutputData=True)
code('Sesión: validar fila', (1600, 1000), SESION_VALIDAR_FILA)
si('¿Sesión válida?', (1820, 800), '={{ $json.continuar }}')
code('Sesión: resultado', (2040, 780), SESION_RESULTADO)

# ④ cerrarSesion
FILTRO_CIERRE = {'conditions': [
    {'keyName': 'sesion', 'keyValue': "={{ $('Cierre: preparar').first().json.token || '-' }}"},
    {'keyName': 'app', 'keyValue': "={{ $('Registro de aplicaciones').first().json.app }}"},
]}
code('Cierre: preparar', (720, 1300), CIERRE_PREPARAR)
nodo('Cierre: modo', 'n8n-nodes-base.switch', 3.2, (940, 1300), {'mode': 'expression', 'numberOutputs': 2, 'output': '={{ $json.modo }}'})
nodo('Cierre: buscar sesión', 'n8n-nodes-base.dataTable', 1, (1160, 1400), {
    'operation': 'get', 'dataTableId': TABLA_SESIONES, 'matchType': 'allConditions', 'filters': FILTRO_CIERRE, 'limit': 5,
}, alwaysOutputData=True)
nodo('Cierre: borrar sesión', 'n8n-nodes-base.dataTable', 1, (1380, 1400), {
    'operation': 'deleteRows', 'dataTableId': TABLA_SESIONES, 'matchType': 'allConditions', 'filters': FILTRO_CIERRE, 'options': {},
}, alwaysOutputData=True)
code('Registro: preparar cierre', (1600, 1300), REGISTRO_CIERRE)
insertar('Registro: guardar cierre', (1820, 1300), TABLA_REGISTRO, COLUMNAS_REGISTRO)
code('Cierre: resultado', (2040, 1300), CIERRE_RESULTADO)

# Errores
code(ERROR, (2700, 1300), ERROR_DESCRIBIR)

# ⑤ Limpieza programada (diaria, 3:00 a. m.)
nodo('Limpieza diaria', 'n8n-nodes-base.scheduleTrigger', 1.2, (0, 1760),
     {'rule': {'interval': [{'field': 'days', 'triggerAtHour': 3}]}})
nodo('Limpieza: sesiones vencidas', 'n8n-nodes-base.dataTable', 1, (220, 1760), {
    'operation': 'deleteRows', 'dataTableId': TABLA_SESIONES,
    'filters': {'conditions': [{'keyName': 'expira', 'condition': 'lt', 'keyValue': '={{ $now.toMillis() }}'}]}, 'options': {},
}, alwaysOutputData=True)
nodo('Limpieza: inicios vencidos', 'n8n-nodes-base.dataTable', 1, (440, 1760), {
    'operation': 'deleteRows', 'dataTableId': TABLA,
    'filters': {'conditions': [{'keyName': 'expira', 'condition': 'lt', 'keyValue': '={{ $now.toMillis() }}'}]}, 'options': {},
}, alwaysOutputData=True)
nodo('Limpieza: registro antiguo', 'n8n-nodes-base.dataTable', 1, (660, 1760), {
    'operation': 'deleteRows', 'dataTableId': TABLA_REGISTRO,
    'filters': {'conditions': [{'keyName': 'ts', 'condition': 'lt',
                                'keyValue': '={{ $now.minus({ days: %d }).toMillis() }}' % RETENCION_REGISTRO_DIAS}]}, 'options': {},
}, alwaysOutputData=True)

# Conexiones
unir('Entrada', ['Registro de aplicaciones'])
unir('Registro de aplicaciones', ['Operación'])
unir('Operación', ['Login: generar state'], ['Callback: revisar respuesta'], ['Sesión: preparar'], ['Cierre: preparar'], [ERROR])
unir('Login: generar state', ['Login: generar nonce'])
unir('Login: generar nonce', ['Login: armar autorización'])
unir('Login: armar autorización', ['Login: guardar state'])
unir('Login: guardar state', ['Login: resultado'])
unir('Callback: revisar respuesta', ['¿Respuesta completa?'])
unir('¿Respuesta completa?', ['Callback: buscar state'], [ERROR])
unir('Callback: buscar state', ['Callback: consumir state'])
unir('Callback: consumir state', ['Callback: limpiar vencidos'])
unir('Callback: limpiar vencidos', ['Callback: validar state'])
unir('Callback: validar state', ['¿State válido?'])
unir('¿State válido?', ['Canje: elegir app'], [ERROR])
unir('Canje: elegir app', ['Canje · Reconstruye'], ['Canje · Extractor'], ['Canje · Rindegastos'])
unir('Canje · Reconstruye', ['Callback: validar identidad'])
unir('Canje · Extractor', ['Callback: validar identidad'])
unir('Canje · Rindegastos', ['Callback: validar identidad'])
unir('Callback: validar identidad', ['¿Identidad válida?'])
unir('¿Identidad válida?', ['Registro: preparar inicio'], [ERROR])
unir('Registro: preparar inicio', ['Registro: guardar inicio'])
unir('Registro: guardar inicio', ['Callback: modo'])
unir('Callback: modo', ['Callback: firmar sesión'], ['Callback: generar id de sesión'])
unir('Callback: firmar sesión', ['Callback: resultado'])
unir('Callback: generar id de sesión', ['Callback: preparar sesión'])
unir('Callback: preparar sesión', ['Callback: guardar sesión'])
unir('Callback: guardar sesión', ['Callback: limpiar sesiones vencidas'])
unir('Callback: limpiar sesiones vencidas', ['Callback: resultado (tabla)'])
unir('Sesión: preparar', ['¿Hay sesión?'])
unir('¿Hay sesión?', ['Sesión: modo'], [ERROR])
unir('Sesión: modo', ['Sesión: verificar firma'], ['Sesión: buscar en tabla'])
unir('Sesión: verificar firma', ['Sesión: validar'], ['Sesión: firma rechazada'])
unir('Sesión: validar', ['¿Sesión válida?'])
unir('Sesión: buscar en tabla', ['Sesión: validar fila'])
unir('Sesión: validar fila', ['¿Sesión válida?'])
unir('Cierre: preparar', ['Cierre: modo'])
unir('Cierre: modo', ['Registro: preparar cierre'], ['Cierre: buscar sesión'])
unir('Cierre: buscar sesión', ['Cierre: borrar sesión'])
unir('Cierre: borrar sesión', ['Registro: preparar cierre'])
unir('Registro: preparar cierre', ['Registro: guardar cierre'])
unir('Registro: guardar cierre', ['Cierre: resultado'])
unir('Limpieza diaria', ['Limpieza: sesiones vencidas'])
unir('Limpieza: sesiones vencidas', ['Limpieza: inicios vencidos'])
unir('Limpieza: inicios vencidos', ['Limpieza: registro antiguo'])
unir('Sesión: firma rechazada', [ERROR])
unir('¿Sesión válida?', ['Sesión: resultado'], [ERROR])

workflow = {
    'name': 'Auth · Microsoft 365',
    'nodes': nodes,
    'connections': connections,
    'settings': {'executionOrder': 'v1', 'callerPolicy': 'workflowsFromSameOwner', 'availableInMCP': True},
}

# Lo único que cambia entre la copia de pruebas y el subflujo real
PERFILES = {
    'pruebas': {'nombre': 'Auth · Microsoft 365 (pruebas)',
                '__DESTINO_RINDEGASTOS__': 'https://uni2.app.n8n.cloud/webhook/rindegastos-sap-pruebas'},
    'produccion': {'nombre': 'Auth · Microsoft 365',
                   '__DESTINO_RINDEGASTOS__': 'https://uni2.app.n8n.cloud/webhook/rindegastos-sap'},
}

if __name__ == '__main__':
    import sys
    perfil = PERFILES[sys.argv[1] if len(sys.argv) > 1 else 'pruebas']
    texto = json.dumps(workflow, ensure_ascii=False, indent=2)
    for marca, valor in perfil.items():
        if marca.startswith('__'):
            texto = texto.replace(marca, valor)
    salida = json.loads(texto)
    salida['name'] = perfil['nombre']
    assert '__DESTINO_' not in json.dumps(salida)
    with open('auth_m365_subflujo.json', 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"{len(nodes)} nodos → auth_m365_subflujo.json ({salida['name']})")
