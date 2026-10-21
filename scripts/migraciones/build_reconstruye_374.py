"""Genera la copia dev del flujo Reconstruye con SSO Microsoft 365 + ambiente centralizado (issue #374).

Uso: python3 build_dev.py <workflow_vivo.json> <salida.json>
"""
import copy
import json
import sys
import uuid

SRC, OUT = sys.argv[1], sys.argv[2]
w = json.load(open(SRC))

RUTA_BASE = 'reconstruye-dev'
PG = {'postgres': {'id': 'wbEzFJcs2niCUwGx', 'name': 'Postgres uni2_qa'}}
JWT = {'jwtAuth': {'id': 'tWujlz3CZc6YRlt3', 'name': 'JWT Sesion Reconstruye'}}
# Secreto de Entra: credencial Basic (usuario = client_id, contraseña = secreto). Custom Auth con
# 'body' NO sirve: reemplaza el formulario y Microsoft responde AADSTS900144 (falta grant_type).
ENTRA = {'httpBasicAuth': {'id': 'BLXGJfzuND0fFwR4', 'name': 'Reconstruye · Secreto Entra ID (vence 2027-10-14)'}}

nodes = {n['name']: n for n in w['nodes']}
conns = w['connections']

# ---------------------------------------------------------------- utilidades
def uid():
    return str(uuid.uuid4())

def add(node):
    node.setdefault('id', uid())
    assert node['name'] not in nodes, node['name']
    nodes[node['name']] = node
    return node

def connect(src, dst, out=0):
    outs = conns.setdefault(src, {'main': []})['main']
    while len(outs) <= out:
        outs.append([])
    outs[out].append({'node': dst, 'type': 'main', 'index': 0})

def code(name, pos, js):
    return add({'name': name, 'type': 'n8n-nodes-base.code', 'typeVersion': 2, 'position': pos,
                'parameters': {'jsCode': js}})

def switch(name, pos, expr, n):
    return add({'name': name, 'type': 'n8n-nodes-base.switch', 'typeVersion': 3.2, 'position': pos,
                'parameters': {'mode': 'expression', 'numberOutputs': n, 'output': expr, 'options': {}}})

def if_true(name, pos, expr):
    n = copy.deepcopy(nodes['IF Solicitud Creada'])
    n.update({'id': uid(), 'name': name, 'position': pos})
    c = n['parameters']['conditions']['conditions'][0]
    c['id'] = uid()
    c['leftValue'] = expr
    return add(n)

def respond(name, pos, code_, headers, body=None):
    entries = [{'name': k, 'value': v} for k, v in headers]
    p = {'respondWith': 'text' if body is not None else 'noData',
         'options': {'responseCode': code_, 'responseHeaders': {'entries': entries}}}
    if body is not None:
        p['responseBody'] = body
    return add({'name': name, 'type': 'n8n-nodes-base.respondToWebhook', 'typeVersion': 1.5,
                'position': pos, 'parameters': p})

def jwt(name, pos, params):
    return add({'name': name, 'type': 'n8n-nodes-base.jwt', 'typeVersion': 1, 'position': pos,
                'parameters': params, 'credentials': JWT})

def replace_once(s, old, new):
    assert s.count(old) == 1, (old, s.count(old))
    return s.replace(old, new)

# ------------------------------------------------- 1. webhooks: rutas propias dev
SUFIJOS = {
    'Webhook A - Servir formulario documento': '',
    'Webhook B - Recibir documento': '-creditos-activos',
    'Webhook B2 - Recibir credito seleccionado': '-linea-credito',
    'Webhook C - Confirmar linea de credito': '-confirmar',
}
PRIMER_NODO = {}
for nombre, sufijo in SUFIJOS.items():
    n = nodes[nombre]
    n['parameters']['path'] = RUTA_BASE + sufijo
    n['webhookId'] = uid()
    n['parameters'].pop('authentication', None)  # único acceso: SSO Microsoft 365
    n.pop('credentials', None)
    PRIMER_NODO[nombre] = conns.pop(nombre)['main'][0][0]['node']

add({'name': 'Webhook Auth - Callback Microsoft', 'type': 'n8n-nodes-base.webhook', 'typeVersion': 2.1,
     'webhookId': uid(), 'onError': 'continueRegularOutput', 'position': [-1008, 2400],
     'parameters': {'path': RUTA_BASE + '-auth', 'responseMode': 'responseNode', 'options': {}}})

# los nodos existentes se corren a la derecha para dejar espacio al bloque común
for n in list(nodes.values()):
    if n['type'] != 'n8n-nodes-base.webhook':
        n['position'] = [n['position'][0] + 2200, n['position'][1]]

# ------------------------------------------------- 2. bloque común: config + ambiente + acceso
CONFIG_JS = r"""// ============================================================
// CONFIGURACIÓN ÚNICA DEL FLUJO RECONSTRUYE (issue #374)
// ------------------------------------------------------------
// AMBIENTE: lo define la credencial Postgres de los nodos de base
//   de datos. Para cambiar de ambiente se cambia esa credencial;
//   el flujo detecta la base real con current_database() y la
//   traduce con "ambientesPorBase". Si la base no está en el mapa,
//   el formulario queda bloqueado.
// SSO: datos de la app registrada en Microsoft Entra ID. El client
//   secret NO va aquí: está en la credencial
//   "Reconstruye · Secreto Entra ID (vence 2027-10-14)" del nodo "Auth: canjear codigo".
// ============================================================
const CONFIG = {
  ambientesPorBase: {
    uni2_dev: 'DEV',
    uni2_qa: 'QA',
    // '<base de producción>': 'PROD',
  },
  sso: {
    habilitado: true, // inicio de sesión con Microsoft 365: único método de acceso
    tenantId: 'f6c1b7c0-d15b-446c-baa7-b6392213858a', // directorio de UNI2
    clientId: '10632875-87cd-4b0f-b3b7-e0fac2f288ee', // app 'n8n Reconstruye' (grupo Desarrollo de Software)
    dominiosPermitidos: ['uni2.com.co'],
    duracionSesionSegundos: 3600,
  },
};

// La ruta base sale de la URL del webhook que se ejecutó: así las URLs
// del formulario siempre coinciden con las rutas de los webhooks.
const SUFIJOS = { B: '-creditos-activos', B2: '-linea-credito', C: '-confirmar', AUTH: '-auth' };

const entrada = $input.first().json;
const url = String(entrada.webhookUrl || '').split('?')[0].replace(/\/$/, '');
let ruta = 'A';
let base = url;
for (const [nombre, sufijo] of Object.entries(SUFIJOS)) {
  if (url.endsWith(sufijo)) {
    ruta = nombre;
    base = url.slice(0, -sufijo.length);
    break;
  }
}

const cookies = {};
String((entrada.headers || {}).cookie || '').split(';').forEach(par => {
  const i = par.indexOf('=');
  if (i <= 0) return;
  try {
    cookies[par.slice(0, i).trim()] = decodeURIComponent(par.slice(i + 1).trim());
  } catch (e) {
    // cookie mal formada: se ignora
  }
});

const urls = {
  inicio: base,
  creditos: base + SUFIJOS.B,
  lineaCredito: base + SUFIJOS.B2,
  confirmar: base + SUFIJOS.C,
  auth: base + SUFIJOS.AUTH,
};

return [{ json: { ...entrada, ctx: { config: CONFIG, ruta, urls, cookies } }, pairedItem: { item: 0 } }];
"""

CONTEXTO_JS = r"""// Traduce la base conectada a un ambiente, arma el banner y decide el control de acceso.
const item = $('Config Reconstruye').first().json;
const ctx = { ...item.ctx };
const cfg = ctx.config;

const baseDatos = $input.first().json.base_datos || null;
const ambiente = (baseDatos && cfg.ambientesPorBase[baseDatos]) || null;
ctx.baseDatos = baseDatos;
ctx.ambiente = ambiente || 'DESCONOCIDO';
ctx.tituloPrefijo = '[' + ctx.ambiente + '] ';

const ESTILOS = {
  DEV: { fondo: '#b42318', texto: '#ffffff', aviso: '&#9888; AMBIENTE DE DESARROLLO (DEV) &mdash; las solicitudes NO se crean en Producción' },
  QA: { fondo: '#f79009', texto: '#1d2939', aviso: '&#9888; AMBIENTE DE PRUEBAS (QA) &mdash; las solicitudes NO se crean en Producción' },
  PROD: { fondo: '#1f9254', texto: '#ffffff', aviso: 'Ambiente: PRODUCCIÓN' },
  DESCONOCIDO: { fondo: '#b42318', texto: '#ffffff', aviso: '&#9888; AMBIENTE NO RECONOCIDO &mdash; formulario bloqueado' },
};
const e = ESTILOS[ctx.ambiente];
const grande = ctx.ambiente !== 'PROD';
// <!--USUARIO--> se reemplaza en "Contexto final" con el usuario autenticado
ctx.bannerHtml = '<div style="width:100%;background:' + e.fondo + ';color:' + e.texto +
  ';font-family:\'Open Sans\',sans-serif;font-size:' + (grande ? '14px' : '12px') + ';font-weight:700;text-align:center;padding:' +
  (grande ? '10px 16px' : '4px 16px') + ';">' + e.aviso + '<!--USUARIO--></div>';

// Salidas de "Control de acceso": 0 continuar, 1 verificar sesión, 2 iniciar sesión, 3 callback SSO, 4 bloqueado
let salida;
if (!ambiente) {
  salida = 4;
  ctx.mensajeBloqueo = 'La base de datos conectada (' + (baseDatos || 'sin conexión') +
    ') no está registrada en la configuración del flujo. Revisa la credencial Postgres y el nodo "Config Reconstruye".';
} else if (ctx.ruta === 'AUTH') {
  salida = cfg.sso.habilitado ? 3 : 4;
  ctx.mensajeBloqueo = 'El inicio de sesión con Microsoft 365 no está habilitado en este flujo.';
} else if (!cfg.sso.habilitado) {
  salida = 0;
} else if (ctx.cookies.rc_sesion) {
  salida = 1;
} else {
  salida = 2;
}
ctx.salidaAcceso = salida;

return [{ json: { ...item, ctx }, pairedItem: { item: 0 } }];
"""

CONTEXTO_FINAL_JS = r"""// Aplica la sesión verificada (si SSO está activo) y decide a qué paso del formulario ir.
const item = $('Construir contexto').first().json;
const ctx = { ...item.ctx };
const sso = ctx.config.sso;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

let destino = ctx.ruta;
if (sso.habilitado) {
  const sesion = $input.first().json.payload || {};
  const email = String(sesion.email || '').toLowerCase();
  if (sesion.tipo !== 'sesion' || !sso.dominiosPermitidos.some(d => email.endsWith('@' + d.toLowerCase()))) {
    destino = 'LOGIN';
  } else {
    ctx.usuario = { email, nombre: sesion.nombre || '' };
    ctx.bannerHtml = ctx.bannerHtml.replace('<!--USUARIO-->',
      ' &nbsp;|&nbsp; ' + esc(email) + ' &nbsp;<a href="' + ctx.urls.auth + '?salir=1" style="color:inherit;">Cerrar sesión</a>');
  }
}

// Salidas de "Router rutas": 0 página 1, 1 créditos activos, 2 línea de crédito, 3 confirmar, 4 iniciar sesión
const i = ['A', 'B', 'B2', 'C'].indexOf(destino);
ctx.salidaRuta = i < 0 ? 4 : i;

return [{ json: { ...item, ctx }, pairedItem: { item: 0 } }];
"""

code('Config Reconstruye', [-760, 1000], CONFIG_JS)
add({'name': 'Detectar ambiente', 'type': 'n8n-nodes-base.postgres', 'typeVersion': 2.6,
     'alwaysOutputData': True, 'onError': 'continueErrorOutput', 'position': [-540, 1000],
     'parameters': {'operation': 'executeQuery', 'query': 'SELECT current_database() AS base_datos;', 'options': {}},
     'credentials': PG})
code('Construir contexto', [-320, 1000], CONTEXTO_JS)
switch('Control de acceso', [-100, 1000], '={{ $json.ctx.salidaAcceso }}', 5)
jwt('Verificar sesion', [120, 900], {'operation': 'verify', 'token': '={{ $json.ctx.cookies.rc_sesion }}', 'options': {}})
nodes['Verificar sesion']['onError'] = 'continueErrorOutput'
code('Contexto final', [340, 1000], CONTEXTO_FINAL_JS)
switch('Router rutas', [560, 1000], '={{ $json.ctx.salidaRuta }}', 5)

for nombre in list(SUFIJOS) + ['Webhook Auth - Callback Microsoft']:
    connect(nombre, 'Config Reconstruye')
connect('Config Reconstruye', 'Detectar ambiente')
connect('Detectar ambiente', 'Construir contexto', 0)
connect('Detectar ambiente', 'Construir contexto', 1)
connect('Construir contexto', 'Control de acceso')
connect('Control de acceso', 'Contexto final', 0)
connect('Control de acceso', 'Verificar sesion', 1)
connect('Verificar sesion', 'Contexto final', 0)
connect('Contexto final', 'Router rutas')
for i, nombre in enumerate(SUFIJOS):
    connect('Router rutas', PRIMER_NODO[nombre], i)

# ------------------------------------------------- 3. páginas: banner, título y URLs
CF = "$('Contexto final').first().json.ctx"
CC = "$('Construir contexto').first().json.ctx"
VIEJA = 'https://uni2.app.n8n.cloud/webhook/'

p1 = nodes['Respond Pagina 1']['parameters']
s = p1['responseBody']
s = replace_once(s, '<title>', '<title>{{ ' + CF + '.tituloPrefijo }}')
s = replace_once(s, '<body>', '<body>{{ ' + CF + '.bannerHtml }}')
s = replace_once(s, VIEJA + 'reconstruye-creditos-activos', '{{ ' + CF + '.urls.creditos }}')
p1['responseBody'] = s

for nombre in ('Respond Error B', 'Respond Error C', 'Respond Exito C'):
    p = nodes[nombre]['parameters']
    s = p['responseBody']
    s = replace_once(s, '<title>', "<title>' + " + CF + ".tituloPrefijo + '")
    s = replace_once(s, '<body>', "<body>' + " + CF + ".bannerHtml + '")
    s = replace_once(s, VIEJA + 'reconstruye"', "' + " + CF + ".urls.inicio + '\"")
    p['responseBody'] = s

for nombre, ruta, clave in (('Code Construir Pagina 2 - Creditos Activos', 'reconstruye-linea-credito', 'lineaCredito'),
                            ('Code Construir Pagina 3 - Linea de Credito', 'reconstruye-confirmar', 'confirmar')):
    p = nodes[nombre]['parameters']
    s = "const ctx = " + CF + ";\n" + p['jsCode']
    s = replace_once(s, '<title>', '<title>${ctx.tituloPrefijo}')
    s = replace_once(s, '<body>', '<body>${ctx.bannerHtml}')
    s = replace_once(s, VIEJA + ruta, '${ctx.urls.' + clave + '}')
    p['jsCode'] = s

# plantilla para las páginas nuevas (mismo estilo que "Respond Error B")
plantilla = nodes['Respond Error B']['parameters']['responseBody']
ini = plantilla.index('<div class="status-icon')
fin = plantilla.index('</div></div><div class="overlay"')
cabeza, cola = plantilla[:ini], plantilla[fin:]

def pagina(ctx_expr, titulo, icono, cuerpo_js, enlace_js, texto_enlace):
    """Devuelve una expresión n8n con una tarjeta: título, mensaje (expresión JS) y botón."""
    c = cabeza.replace("' + " + CF + ".tituloPrefijo + '", "' + " + ctx_expr + ".tituloPrefijo + '")
    c = c.replace("' + " + CF + ".bannerHtml + '", "' + " + ctx_expr + ".bannerHtml + '")
    c = c.replace('<title>' + "' + " + ctx_expr + ".tituloPrefijo + '" + 'Error</title>',
                  '<title>' + "' + " + ctx_expr + ".tituloPrefijo + '" + titulo + '</title>')
    return (c + '<div class="status-icon ' + icono + '">' + ('&#10006;' if icono == 'error' else '&#10004;') +
            '</div><h1>' + titulo + "</h1><p>' + (" + cuerpo_js + ") + '</p><a class=\"btn-back\" href=\"' + " +
            enlace_js + " + '\">" + texto_enlace + '</a>' + cola)

HTML = ('Content-Type', 'text/html; charset=utf-8')
NO_CACHE = ('Cache-Control', 'no-store')

respond('Respond Bloqueado', [120, 1400], 403, [HTML, NO_CACHE],
        pagina(CC, 'Formulario bloqueado', 'error', CC + '.mensajeBloqueo', CC + '.urls.inicio', 'Reintentar'))
connect('Control de acceso', 'Respond Bloqueado', 4)

# ------------------------------------------------- 4. inicio de sesión (sin sesión válida)
if_true('IF Pagina inicial', [340, 2600], "={{ $('Construir contexto').first().json.ctx.ruta === 'A' }}")
connect('Control de acceso', 'IF Pagina inicial', 2)
connect('Verificar sesion', 'IF Pagina inicial', 1)
connect('Router rutas', 'IF Pagina inicial', 4)

add({'name': 'Login: generar nonce', 'type': 'n8n-nodes-base.crypto', 'typeVersion': 2, 'position': [560, 2500],
     'parameters': {'action': 'generate', 'encodingType': 'hex', 'stringLength': 32, 'dataPropertyName': 'nonce'}})
jwt('Login: firmar state', [780, 2500], {
    'operation': 'sign', 'useJson': True,
    'claimsJson': "={{ JSON.stringify({ tipo: 'state', n: $json.nonce, exp: Math.floor(Date.now() / 1000) + 600 }) }}",
    'options': {}})
AUTHORIZE = ("={{ 'https://login.microsoftonline.com/' + encodeURIComponent(" + CC + ".config.sso.tenantId) + "
             "'/oauth2/v2.0/authorize?client_id=' + encodeURIComponent(" + CC + ".config.sso.clientId) + "
             "'&response_type=code&response_mode=query&scope=' + encodeURIComponent('openid profile email') + "
             "'&redirect_uri=' + encodeURIComponent(" + CC + ".urls.auth) + "
             "'&state=' + encodeURIComponent($json.token) + "
             "'&nonce=' + $('Login: generar nonce').first().json.nonce + "
             "'&prompt=select_account' }}")
respond('Respond Redirigir a Microsoft', [1000, 2500], 302, [
    ('Location', AUTHORIZE),
    ('Set-Cookie', "={{ 'rc_nonce=' + $('Login: generar nonce').first().json.nonce + '; Path=/webhook; Max-Age=600; HttpOnly; Secure; SameSite=Lax' }}"),
    NO_CACHE])
respond('Respond Volver al inicio', [560, 2700], 303, [('Location', '={{ ' + CC + '.urls.inicio }}'), NO_CACHE])
connect('IF Pagina inicial', 'Login: generar nonce', 0)
connect('IF Pagina inicial', 'Respond Volver al inicio', 1)
connect('Login: generar nonce', 'Login: firmar state')
connect('Login: firmar state', 'Respond Redirigir a Microsoft')

# ------------------------------------------------- 5. callback de Microsoft
EVALUAR_JS = r"""// Clasifica la respuesta de Microsoft: 0 cerrar sesión, 1 denegado, 2 canjear código
const q = $('Construir contexto').first().json.query || {};
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let salidaAuth = 2;
let motivo = '';
if (q.salir) {
  salidaAuth = 0;
} else if (q.error) {
  salidaAuth = 1;
  motivo = q.error === 'access_denied'
    ? 'Se canceló el inicio de sesión o la cuenta no tiene acceso a esta aplicación.'
    : 'Microsoft 365 rechazó el inicio de sesión (' + esc(String(q.error).slice(0, 80)) + ').';
} else if (!q.code || !q.state) {
  salidaAuth = 1;
  motivo = 'La respuesta del inicio de sesión llegó incompleta.';
}
return [{ json: { salidaAuth, motivo }, pairedItem: { item: 0 } }];
"""

VALIDAR_JS = r"""// Valida el id_token recibido directamente del endpoint de Microsoft (canal TLS, OIDC 3.1.3.7).
const ctx = $('Construir contexto').first().json.ctx;
const sso = ctx.config.sso;
const state = $('Auth: verificar state').first().json.payload || {};
const p = $input.first().json.payload || {};
const email = String(p.preferred_username || p.email || p.upn || '').toLowerCase();
const ahora = Math.floor(Date.now() / 1000);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const fallas = [];
if (state.tipo !== 'state' || !state.n) fallas.push('el parámetro state no es válido');
if (ctx.cookies.rc_nonce !== state.n) fallas.push('el inicio de sesión no corresponde a este navegador');
if (p.nonce !== state.n) fallas.push('el nonce no coincide');
if (p.tid !== sso.tenantId) fallas.push('la cuenta no pertenece al directorio de UNI2');
if (p.aud !== sso.clientId) fallas.push('el token fue emitido para otra aplicación');
if (!p.exp || p.exp < ahora - 60) fallas.push('el token está vencido');
if (!sso.dominiosPermitidos.some(d => email.endsWith('@' + d.toLowerCase()))) {
  fallas.push('la cuenta ' + esc(email || '(sin correo)') + ' no es de un dominio permitido (' + sso.dominiosPermitidos.join(', ') + ')');
}

return [{
  json: {
    valido: fallas.length === 0,
    motivo: fallas.length ? 'Acceso denegado: ' + fallas.join('; ') + '.' : '',
    sesion: { tipo: 'sesion', email, nombre: p.name || '', oid: p.oid || '', exp: ahora + sso.duracionSesionSegundos },
  },
  pairedItem: { item: 0 },
}];
"""

code('Auth: evaluar callback', [120, 3100], EVALUAR_JS)
switch('Auth: decidir', [340, 3100], '={{ $json.salidaAuth }}', 3)
jwt('Auth: verificar state', [560, 3200], {'operation': 'verify', 'token': "={{ $('Construir contexto').first().json.query.state }}", 'options': {}})
nodes['Auth: verificar state']['onError'] = 'continueErrorOutput'
add({'name': 'Auth: canjear codigo', 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2,
     'onError': 'continueErrorOutput', 'position': [780, 3200], 'credentials': ENTRA,
     'parameters': {
         'method': 'POST',
         'url': "={{ 'https://login.microsoftonline.com/' + encodeURIComponent(" + CC + ".config.sso.tenantId) + '/oauth2/v2.0/token' }}",
         'authentication': 'genericCredentialType', 'genericAuthType': 'httpBasicAuth',
         'sendBody': True, 'contentType': 'form-urlencoded',
         'bodyParameters': {'parameters': [
             {'name': 'grant_type', 'value': 'authorization_code'},
             {'name': 'code', 'value': "={{ $('Construir contexto').first().json.query.code }}"},
             {'name': 'redirect_uri', 'value': '={{ ' + CC + '.urls.auth }}'},
             {'name': 'client_id', 'value': '={{ ' + CC + '.config.sso.clientId }}'},
             {'name': 'scope', 'value': 'openid profile email'},
         ]},
         'options': {}}})
jwt('Auth: leer id_token', [1000, 3200], {'operation': 'decode', 'token': '={{ $json.id_token }}', 'options': {}})
nodes['Auth: leer id_token']['onError'] = 'continueErrorOutput'
code('Auth: validar identidad', [1220, 3200], VALIDAR_JS)
if_true('IF Identidad valida', [1440, 3200], '={{ $json.valido }}')
jwt('Auth: firmar sesion', [1660, 3100], {'operation': 'sign', 'useJson': True,
                                          'claimsJson': '={{ JSON.stringify($json.sesion) }}', 'options': {}})
respond('Respond Sesion iniciada', [1880, 3100], 303, [
    ('Location', '={{ ' + CC + '.urls.inicio }}'),
    ('Set-Cookie', "={{ 'rc_sesion=' + $json.token + '; Path=/webhook; Max-Age=' + " + CC + ".config.sso.duracionSesionSegundos + '; HttpOnly; Secure; SameSite=Lax' }}"),
    NO_CACHE])
respond('Respond Acceso denegado', [1660, 3400], 403, [HTML, NO_CACHE],
        pagina(CC, 'Acceso denegado', 'error',
               "$json.motivo || 'No fue posible validar tu identidad con Microsoft 365. Ingresa con una cuenta ' + "
               + CC + ".config.sso.dominiosPermitidos.map(d => '@' + d).join(' o ') + '.'",
               CC + '.urls.inicio', 'Intentar de nuevo'))
respond('Respond Sesion cerrada', [560, 2950], 200, [
    HTML, NO_CACHE,
    ('Set-Cookie', "rc_sesion=; Path=/webhook; Max-Age=0; HttpOnly; Secure; SameSite=Lax")],
        pagina(CC, 'Sesión cerrada', 'success', "'Cerraste la sesión del formulario Reconstruye.'",
               CC + '.urls.inicio', 'Iniciar sesión de nuevo'))

connect('Control de acceso', 'Auth: evaluar callback', 3)
connect('Auth: evaluar callback', 'Auth: decidir')
connect('Auth: decidir', 'Respond Sesion cerrada', 0)
connect('Auth: decidir', 'Respond Acceso denegado', 1)
connect('Auth: decidir', 'Auth: verificar state', 2)
connect('Auth: verificar state', 'Auth: canjear codigo', 0)
connect('Auth: verificar state', 'Respond Acceso denegado', 1)
connect('Auth: canjear codigo', 'Auth: leer id_token', 0)
connect('Auth: canjear codigo', 'Respond Acceso denegado', 1)
connect('Auth: leer id_token', 'Auth: validar identidad', 0)
connect('Auth: leer id_token', 'Respond Acceso denegado', 1)
connect('Auth: validar identidad', 'IF Identidad valida')
connect('IF Identidad valida', 'Auth: firmar sesion', 0)
connect('IF Identidad valida', 'Respond Acceso denegado', 1)
connect('Auth: firmar sesion', 'Respond Sesion iniciada')

# ------------------------------------------------- salida
out = {
    'name': 'Reconstruye (dev - SSO #374)',
    'nodes': list(nodes.values()),
    'connections': conns,
    'settings': {'executionOrder': 'v1'},
}
for n in out['nodes']:
    s = json.dumps(n)
    assert 'uni2.app.n8n.cloud/webhook/' not in s, n['name']
json.dump(out, open(OUT, 'w'), indent=2, ensure_ascii=False)
print('nodos:', len(out['nodes']))
