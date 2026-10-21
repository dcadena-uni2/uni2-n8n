"""Flujo central "Acceso Microsoft 365" (issue #389): login genérico para flujos con Form o con webhook.

Es la puerta de entrada de todas las apps registradas en el subflujo "Auth · Microsoft 365":
  ingreso:  GET /webhook/<INGRESO>?app=<app>            → Microsoft
  regreso:  GET /webhook/<regreso registrado de la app>  → crea la sesión → urlDestino de la app
  cierre:   GET /webhook/<INGRESO>?app=<app>&salir=1[&sesion=<id>]
La sesión queda en la tabla general "auth_m365_sesiones" (apps con Form: ?sesion=<id>) o en cookie
(apps con webhook). Cada flujo solo verifica la sesión con la operación verificarSesion del subflujo.

Uso:  python3 build_acceso_m365.py <salida.json> [pruebas|produccion]
"""
import json
import sys
import uuid

PERFILES = {
    'pruebas': {'nombre': 'Acceso Microsoft 365 (pruebas)', 'ingreso': 'acceso-m365-pruebas',
                'subflujo': ('UR5QkUBSFQLxXhub', 'Auth · Microsoft 365 (pruebas)')},
    'produccion': {'nombre': 'Acceso Microsoft 365', 'ingreso': 'acceso-m365',
                   'subflujo': ('NtcAdHyPUYIxWSNl', 'Auth · Microsoft 365')},
}
# Webhooks de regreso desde Microsoft: ruta (redirect URI registrada en Entra ID) → app.
# Una ruta solo puede estar en un flujo activo: cada app se agrega al perfil donde ya usa este login.
# (Reconstruye conserva su propio webhook de regreso "reconstruye-auth" y usa solo el motor.)
REGRESOS_POR_PERFIL = {
    'pruebas': {'rindegastos-sap-auth': 'rindegastos'},
    'produccion': {'rindegastos-sap-auth': 'rindegastos'},  # RindegastosSAP migrado el 20/10/2026
}

ESTILOS = ("<style>*{box-sizing:border-box;margin:0;padding:0}body{min-height:100vh;display:flex;align-items:center;"
           "justify-content:center;background:#f3f4f6;font-family:Segoe UI,Open Sans,sans-serif;color:#1f2937;padding:16px}"
           ".card{background:#fff;max-width:520px;width:100%;border-radius:12px;box-shadow:0 4px 18px rgba(0,0,0,.08);"
           "padding:32px 28px;text-align:center}h1{font-size:21px;margin-bottom:12px}p{color:#4b5563;line-height:1.6}"
           "ul.consejos{list-style:none;margin-top:12px;color:#6b7280;line-height:1.6}"
           ".detalle-tecnico{margin-top:14px;font-size:12px;color:#9ca3af;word-break:break-word}"
           ".btn{display:inline-block;margin-top:24px;background:#ee7203;color:#fff;text-decoration:none;font-weight:600;"
           "padding:12px 22px;border-radius:8px}</style>")
assert "'" not in ESTILOS and '}}' not in ESTILOS

CONFIG = r"""// ============================================================
// ACCESO MICROSOFT 365 · puerta de entrada genérica (issue #389)
// ------------------------------------------------------------
// Ingreso:  /webhook/__INGRESO__?app=<app>      Cierre: /webhook/__INGRESO__?app=<app>&salir=1[&sesion=<id>]
// Los datos de cada app (client id, destino tras el login, modo de sesión, dominios) están en el
// subflujo "Auth · Microsoft 365", nodo "Registro de aplicaciones".
// Aquí solo se lista qué webhook de regreso (redirect URI registrada en Entra ID) corresponde a cada app.
// Para agregar una app: entrada en REGRESOS + webhook de regreso con esa ruta conectado a "Config acceso".
// ============================================================
const INGRESO = '__INGRESO__';
const REGRESOS = __REGRESOS__;

const entrada = $input.first().json;
const url = String(entrada.webhookUrl || '').split('?')[0].replace(/\/$/, '');
const i = url.indexOf('/webhook/');
const instancia = i >= 0 ? url.slice(0, i) : '';
const ruta = i >= 0 ? url.slice(i + '/webhook/'.length) : '';
const q = entrada.query || {};

const esRegreso = Object.prototype.hasOwnProperty.call(REGRESOS, ruta);
const app = esRegreso ? REGRESOS[ruta] : String(q.app || '').trim().toLowerCase();
const regreso = Object.keys(REGRESOS).find((r) => REGRESOS[r] === app);

// Salidas de "Acceso: ruta": 0 ingresar, 1 cerrar sesión, 2 regreso desde Microsoft
const salida = esRegreso ? 2 : (q.salir ? 1 : 0);

return [{
  json: {
    ...entrada,
    acceso: {
      salida,
      app,
      sesion: String(q.sesion || '').trim(),
      redirectUri: regreso ? `${instancia}/webhook/${regreso}` : '',
      urls: { ingresar: `${instancia}/webhook/${INGRESO}?app=${encodeURIComponent(app)}` },
    },
  },
  pairedItem: { item: 0 },
}];
"""

NOTA = """## 🔐 Acceso Microsoft 365 · login genérico (issue #389)
Puerta de entrada para **todos** los flujos que piden login con Microsoft 365.

**Enlace:** `/webhook/__INGRESO__?app=<app>` → Microsoft → regreso → la app (`urlDestino` del registro).
- **App con Form** (p. ej. `rindegastos`): llega a su Form con `?sesion=<id>`. La sesión queda en la tabla general **auth_m365_sesiones**.
- **App con webhook**: llega a su página con la sesión en cookie.

**Cerrar sesión:** `/webhook/__INGRESO__?app=<app>&salir=1&sesion=<id>`.

**En cada flujo solo se agrega:** *Auth: verificar sesión* (Execute Workflow → subflujo, operación `verificarSesion`) + IF.
Todo lo demás (client id, secretos, destino, validaciones) vive en el subflujo **Auth · Microsoft 365** → *Registro de aplicaciones*."""


import os
UI_FUENTE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'n8n_ui', 'ui_estandar.js')
UI_FLUJO = r"""
// ------------------------------------------------------------ Acceso Microsoft 365
const marco = uiMarco({ titulo: 'Acceso con Microsoft 365', app: 'Acceso con Microsoft 365' });
return [{ json: { ...$input.first().json, ui: { inicio: marco.inicio, fin: marco.fin } }, pairedItem: { item: 0 } }];
"""


def expr_html(cuerpo_js):
    """Página con la interfaz estándar (n8n_ui/ui_estandar.js) del nodo "UI estándar"."""
    ui = "$('UI estándar').first().json.ui"
    expr = f"{ui}.inicio + {cuerpo_js} + {ui}.fin"
    assert '}}' not in expr
    return '={{ ' + expr + ' }}'


def main(destino, perfil):
    p = PERFILES[perfil]
    sub_id, sub_nombre = p['subflujo']
    nodes, con = [], {}
    CTX = "$('Config acceso').first().json.acceso"

    def nuevo(nombre, tipo, version, pos, params, **extra):
        n = {'parameters': params, 'id': str(uuid.uuid4()), 'name': nombre, 'type': tipo, 'typeVersion': version, 'position': pos}
        n.update(extra)
        nodes.append(n)

    def si(nombre, pos):
        nuevo(nombre, 'n8n-nodes-base.if', 2.2, pos, {
            'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose', 'version': 2},
                           'conditions': [{'id': str(uuid.uuid4()), 'leftValue': '={{ $json.ok }}', 'rightValue': '',
                                           'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}],
                           'combinator': 'and'},
            'looseTypeValidation': True, 'options': {}})

    def llamada(nombre, pos, operacion, **valores):
        v = {'operacion': operacion, 'app': f'={{{{ {CTX}.app }}}}', 'redirectUri': '', 'cookies': '',
             'query': "={{ JSON.parse('{}') }}", 'tokenSesion': ''}
        v.update(valores)
        nuevo(nombre, 'n8n-nodes-base.executeWorkflow', 1.2, pos, {
            'workflowId': {'__rl': True, 'mode': 'list', 'value': sub_id, 'cachedResultName': sub_nombre,
                           'cachedResultUrl': f'/workflow/{sub_id}'},
            'workflowInputs': {'mappingMode': 'defineBelow', 'value': v, 'matchingColumns': [],
                               'schema': [{'id': k, 'displayName': k, 'required': False, 'defaultMatch': False, 'display': True,
                                           'canBeUsedToMatch': True, 'type': 'object' if k == 'query' else 'string', 'removed': False}
                                          for k in ('operacion', 'app', 'redirectUri', 'cookies', 'query', 'tokenSesion')],
                               'attemptToConvertTypes': False, 'convertFieldsToString': False},
            'options': {}}, onError='continueRegularOutput')

    def responder(nombre, pos, codigo, cabeceras, cuerpo=None):
        tipo = [('Content-Type', 'text/html; charset=utf-8')] if cuerpo else []
        params = {'respondWith': 'text' if cuerpo else 'noData', 'options': {
            'responseCode': codigo,
            'responseHeaders': {'entries': [{'name': k, 'value': v} for k, v in tipo + cabeceras + [('Cache-Control', 'no-store')]]}}}
        if cuerpo:
            params['responseBody'] = cuerpo
        nuevo(nombre, 'n8n-nodes-base.respondToWebhook', 1.5, pos, params)

    def a(*destinos):
        return {'main': [[{'node': d, 'type': 'main', 'index': 0}] for d in destinos]}

    ingreso = p['ingreso']
    nuevo('Nota · Acceso Microsoft 365', 'n8n-nodes-base.stickyNote', 1, [-60, -560],
          {'content': NOTA.replace('__INGRESO__', ingreso), 'width': 1880, 'height': 1300, 'color': 6})
    nuevo('Webhook Ingresar', 'n8n-nodes-base.webhook', 2.1, [0, -100],
          {'path': ingreso, 'responseMode': 'responseNode', 'options': {}}, webhookId=str(uuid.uuid4()), onError='continueRegularOutput')
    con['Webhook Ingresar'] = a('Config acceso')
    REGRESOS = REGRESOS_POR_PERFIL[perfil]
    for k, (ruta, app) in enumerate(REGRESOS.items()):
        nombre = f'Webhook Regreso · {app}'
        nuevo(nombre, 'n8n-nodes-base.webhook', 2.1, [0, 160 + 200 * k],
              {'path': ruta, 'responseMode': 'responseNode', 'options': {}}, webhookId=str(uuid.uuid4()), onError='continueRegularOutput')
        con[nombre] = a('Config acceso')
    nuevo('Config acceso', 'n8n-nodes-base.code', 2, [220, 40], {'jsCode': CONFIG.replace('__INGRESO__', ingreso)
                                                                 .replace('__REGRESOS__', json.dumps(REGRESOS))})
    nuevo('UI estándar', 'n8n-nodes-base.code', 2, [330, 240], {'jsCode': open(UI_FUENTE, encoding='utf-8').read() + UI_FLUJO})
    nuevo('Acceso: ruta', 'n8n-nodes-base.switch', 3.2, [440, 40],
          {'mode': 'expression', 'numberOutputs': 3, 'output': '={{ $json.acceso.salida }}'})

    cookies = "={{ $('Config acceso').first().json.headers.cookie ?? '' }}"
    reintentar = f"'<a class=\"btn\" href=\"' + {CTX}.urls.ingresar + '\">Intentar de nuevo</a>'"
    denegado = expr_html(f"'<div class=\"status-icon error\">&#10006;</div>' + ($json.html || '<h1>Acceso denegado</h1><p>No fue posible validar tu identidad con Microsoft 365.</p>') + {reintentar}")

    llamada('Auth: iniciar login', [660, -200], 'iniciarLogin', redirectUri=f'={{{{ {CTX}.redirectUri }}}}')
    si('IF Login preparado', [880, -200])
    responder('Respond Redirigir a Microsoft', [1100, -300], 302,
              [('Location', '={{ $json.urlRedireccion }}'), ('Set-Cookie', '={{ $json.setCookie }}')])
    llamada('Auth: cerrar sesión', [660, 40], 'cerrarSesion', cookies=cookies, tokenSesion=f'={{{{ {CTX}.sesion }}}}')
    responder('Respond Sesion cerrada', [880, 40], 200,
              [('Set-Cookie', "={{ $json.setCookie || 'm365_cierre=; Path=/webhook; Max-Age=0' }}")],
              cuerpo=expr_html("'<div class=\"status-icon exito\">&#10004;</div><h1>Sesión cerrada</h1><p>Cerraste tu sesión de Microsoft 365 en este formulario.</p>"
                               f"<a class=\"btn\" href=\"' + {CTX}.urls.ingresar + '\">Iniciar sesión de nuevo</a>'"))
    llamada('Auth: procesar regreso', [660, 280], 'procesarCallback', redirectUri=f'={{{{ {CTX}.redirectUri }}}}',
            cookies=cookies, query="={{ $('Config acceso').first().json.query }}")
    si('IF Sesion creada', [880, 280])
    responder('Respond Ir a la aplicación', [1100, 200], 302,
              [('Location', '={{ $json.urlDestino }}'), ('Set-Cookie', '={{ $json.setCookie }}')])
    responder('Respond Acceso denegado', [1320, 120], 200, [], cuerpo=denegado)

    con['Config acceso'] = a('UI estándar')
    con['UI estándar'] = a('Acceso: ruta')
    con['Acceso: ruta'] = a('Auth: iniciar login', 'Auth: cerrar sesión', 'Auth: procesar regreso')
    con['Auth: iniciar login'] = a('IF Login preparado')
    con['IF Login preparado'] = a('Respond Redirigir a Microsoft', 'Respond Acceso denegado')
    con['Auth: cerrar sesión'] = a('Respond Sesion cerrada')
    con['Auth: procesar regreso'] = a('IF Sesion creada')
    con['IF Sesion creada'] = a('Respond Ir a la aplicación', 'Respond Acceso denegado')

    nombres = {n['name'] for n in nodes}
    for k, v in con.items():
        assert k in nombres, k
        for o in v['main']:
            for c in o:
                assert c['node'] in nombres, c
    w = {'name': p['nombre'], 'nodes': nodes, 'connections': con,
         'settings': {'executionOrder': 'v1', 'availableInMCP': True}}
    json.dump(w, open(destino, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"{len(nodes)} nodos → {destino} ({p['nombre']})")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'pruebas')
