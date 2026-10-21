"""RindegastosSAP con el login estándar de Microsoft 365 (issue #389): Webhook + páginas propias.

Estándar del equipo: todo formulario usado por personas se construye con Webhooks (no nodos Form):
la sesión va en cookie (GET) y en el campo oculto firmado "_sesion" (POST), así que una URL copiada
en otro navegador no da acceso.

    GET  /webhook/<ruta>          ─┐
    POST /webhook/<ruta>-enviar   ─┴► Auth: verificar sesión ► UI estándar ► Ruta
                                         0 mostrar formulario · 1 procesar envío · 2 sin sesión → Login Microsoft 365

Cambios en el flujo (solo acceso y presentación; la lógica de negocio no se toca):
  1. El Form Trigger se reemplaza por los dos webhooks + bloque de acceso + "UI estándar".
  2. Un Set llamado "On form submission" entrega los mismos campos que el Form anterior.
  3. Las páginas finales (nodos Form) pasan a Respond to Webhook con la interfaz estándar.
La interfaz (estilos de marca, banner, formulario) sale de n8n_ui/ui_estandar.js (fuente única).

Uso:
  python3 build_rindegastos_sso.py <respaldo_original.json> <salida.json> pruebas      → copia de pruebas
  python3 build_rindegastos_sso.py <respaldo_original.json> <salida.json> produccion   → flujo original
"""
import json
import os
import sys
import uuid

INSTANCIA = 'https://uni2.app.n8n.cloud'
FORM_ORIGINAL = f'{INSTANCIA}/form/19701d96-ddd7-4cd9-babc-5c9cf40fc3f5'
UI_FUENTE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'n8n_ui', 'ui_estandar.js')

PERFILES = {
    'pruebas': {'nombre': 'RindegastosSAP (pruebas - SSO)', 'ruta': 'rindegastos-sap-pruebas',
                'subflujo': ('CfxCvEk1l2ImSob8', 'Login Microsoft 365 (pruebas)'), 'acceso': 'acceso-m365-pruebas'},
    # Flujo "Login Microsoft 365" definitivo (UNI2 / Utilitarios)
    'produccion': {'nombre': None, 'ruta': 'rindegastos-sap',
                   'subflujo': ('1yD3JSYX8nMJqeID', 'Login Microsoft 365'), 'acceso': 'acceso-m365'},
}

# Páginas finales del flujo original (nodos Form) → icono de la página estándar
PAGINAS_FINALES = {
    'Form': "'error'",                                                 # error de autenticación en SAP
    'Se han realizado multiple peticiones a la misma API': "'aviso'",
    'No se encontraron gastos': "'aviso'",
    # tituloEnvio de "Code Construir Resumen": Envio exitoso / Envio con errores / Envio fallido
    'Form Final': "(/fallid/i.test(titulo) ? 'error' : /error/i.test(titulo) ? 'aviso' : 'exito')",
}
ICONOS = "({ exito: '&#10004;', error: '&#10006;', aviso: '!' })"

# Página de resultado del envío (antes "Form Final"): contadores + secciones por estado.
# Lee la lista estructurada de resultados ("Aggregate Todos"), con las mismas reglas que
# "Code Construir Resumen"; si no la encuentra, muestra el texto del resumen como antes.
FORM_FINAL_JS = r"""(function () {
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const ui = $('UI estándar').first().json.ui;
  const r = $('Code Construir Resumen').first().json;
  let items = [];
  try { items = $('Aggregate Todos').first().json.items || []; } catch (e) { items = []; }
  const titulo = String(r.tituloEnvio || 'Resultado del envío');
  const icono = /fallid/i.test(titulo) ? 'error' : (/error/i.test(titulo) ? 'aviso' : 'exito');
  const exitos = items.filter(i => i.result === 'success' && i.tipo !== 'Proveedor');
  const ya = items.filter(i => i.result === 'ya_existia');
  const errores = items.filter(i => i.result === 'error' && i.tipo !== 'Proveedor');
  const bpOk = items.filter(i => i.result === 'success' && i.tipo === 'Proveedor');
  const bpErr = items.filter(i => i.result === 'error' && i.tipo === 'Proveedor');
  const errIntegracion = $json.statusCode ? 'Error ' + $json.statusCode + ': ' + (Array.isArray($json.message) ? $json.message.map(m => m.message).join('; ') : String($json.message)) : '';
  const integrada = r.reportIntegrationStatus === 1 && !errIntegracion;
  const textoIntegracion = r.reportIntegrationStatus === 1 ? (errIntegracion || 'Integrada') : 'No integrada (hay errores sin resolver)';
  const quien = e => esc(e.supplier || e.Supplier || 'Sin proveedor') + ((e.CardCode || e.nit) ? ' <span class="nit">· NIT ' + esc(e.CardCode || e.nit) + '</span>' : '');
  const seccion = (clase, nombre, lista, detalle) => lista.length
    ? '<div class="res-seccion ' + clase + '"><h3>' + nombre + ' <span class="cuenta">' + lista.length + '</span></h3><ul>'
      + lista.map(e => '<li><strong>' + quien(e) + '</strong><span>' + esc(detalle(e)) + '</span></li>').join('') + '</ul></div>'
    : '';
  const chip = (clase, n, txt) => '<div class="chip ' + clase + (n ? ' activo' : '') + '"><b>' + n + '</b>' + txt + '</div>';
  let html = '<div class="status-icon ' + icono + '">' + ({ exito: '&#10004;', error: '&#10006;', aviso: '!' })[icono] + '</div>'
    + '<h1>' + esc(titulo) + '</h1>'
    + '<div class="res-contadores">' + chip('ok', exitos.length, 'creadas') + chip('neutro', ya.length, 'ya existían') + chip('mal', errores.length + bpErr.length, 'con error') + '</div>'
    + '<div class="res-integracion ' + (integrada ? 'ok' : 'mal') + '">Integración Rindegastos: <b>' + esc(textoIntegracion) + '</b></div>';
  if (items.length) {
    html += seccion('mal', 'Errores', errores, e => e.mensaje || 'Error sin detalle')
      + seccion('mal', 'Socios de negocio con error', bpErr, e => e.mensaje || 'Error sin detalle')
      + seccion('ok', 'Creadas en SAP', exitos, e => (e.tipo === 'asiento' ? 'Asiento' : 'Factura') + ' SAP #' + (e.DocNum || '—'))
      + seccion('ok', 'Socios de negocio creados', bpOk, () => 'Creado en SAP')
      + seccion('neutro', 'Ya existían en SAP', ya, e => 'Factura SAP #' + (e.DocNum || '—') + (e.numAtCard ? ' · ' + e.numAtCard : ''));
  } else {
    const texto = String((r.resumen || '') + (r.resumenSocios ? '\n\nSocios de negocio:\n' + r.resumenSocios : '')).trim();
    html += '<div class="mensaje">' + esc(texto).replace(/\n/g, '<br>') + '</div>';
  }
  return ui.inicio + html
    + '<a class="btn" href="' + ui.urlFormulario + '">Volver</a>'
    + '<a class="btn-back" href="' + ui.urlSalir + '">Cerrar sesión</a>' + ui.fin;
})()"""
assert '}}' not in FORM_FINAL_JS

UI_FLUJO = r"""
// ------------------------------------------------------------ Rindegastos SAP
const APP = 'Rindegastos SAP';
const URL_FORMULARIO = '__ENTRADA__';
const URL_ENVIAR = '__ENTRADA__-enviar';
const URL_ACCESO = '__ACCESO__';
const URL_SALIR = URL_ACCESO + '&salir=1';

const sesion = $input.first().json; // salida de "Auth: verificar sesión"
let esEnvio = false;
try { esEnvio = $('Webhook Enviar').isExecuted; } catch (e) { esEnvio = false; }

const datos = esEnvio ? ($('Webhook Enviar').first().json.body || {}) : {};

// Validación del servidor (la del navegador se puede saltar): el ID de informe tiene 8 dígitos.
// Si no es válido se vuelve a mostrar el formulario y no se consulta Rindegastos ni SAP.
const idInforme = String(datos.id_informe_de_gastos ?? '').trim();
const ID_VALIDO = /^\d{8}$/;

// Salidas de "Ruta": 0 mostrar formulario, 1 procesar envío, 2 sin sesión
let salida = !sesion.ok ? 2 : (esEnvio ? 1 : 0);
let errorFormulario = '';
if (salida === 1 && !ID_VALIDO.test(idInforme)) {
  salida = 0;
  errorFormulario = 'El ID de informe debe tener exactamente 8 dígitos (por ejemplo 14349805). No se envió nada a SAP.';
}
const usuario = sesion.ok ? sesion.usuario.email : '';
const marco = uiMarco({ titulo: 'Rindegastos - SAP', app: APP, usuario, urlSalir: URL_SALIR });
const marcoAncho = uiMarco({ titulo: 'Rindegastos - SAP', app: APP, usuario, urlSalir: URL_SALIR, ancho: true });

const formulario = salida !== 0 ? '' : marco.inicio + uiFormulario({
  titulo: 'Rindegastos - SAP',
  accion: URL_ENVIAR,
  campoSesion: sesion.campoOculto,
  boton: 'Enviar a SAP',
  error: errorFormulario,
  campos: [
    { nombre: 'usuario', etiqueta: 'Usuario de SAP', tipo: 'select', requerido: true, opciones: ['FIN_SERVICELAYER'], valor: 'FIN_SERVICELAYER' },
    { nombre: 'id_informe_de_gastos', etiqueta: 'ID de informe en Rindegastos', tipo: 'text', requerido: true,
      patron: '\\d{8}', longitud: 8, teclado: 'numeric', mensajePatron: 'Debe tener exactamente 8 dígitos',
      placeholder: 'Ej.: 14349805', ayuda: 'Número de 8 dígitos del informe en Rindegastos.',
      valor: errorFormulario ? idInforme : undefined },
  ],
}) + marco.fin;

return [{
  json: {
    salida,
    datos,
    ui: { formulario, inicio: marcoAncho.inicio, fin: marcoAncho.fin, urlFormulario: URL_FORMULARIO, urlSalir: URL_SALIR },
  },
}];
"""

NOTA = """## 🔐 Acceso con Microsoft 365 (login estándar, issue #389)
**Enlace para los usuarios:** `/webhook/__RUTA__`

- **Webhook Formulario** (GET) y **Webhook Enviar** (POST) pasan por **Auth: verificar sesión**: cookie `rg_sesion` o campo oculto `_sesion` (los envíos llegan sin cookies por el *sandbox* de n8n).
- Sin sesión → **Login Microsoft 365** (`/webhook/__ACCESO__?app=rindegastos`) → Microsoft → vuelve al formulario.
- **UI estándar**: estilos de marca, banner con el usuario y *Cerrar sesión*, formulario. Fuente única `n8n_ui/ui_estandar.js` (no editar a mano).
- **On form submission** (Set) entrega los mismos campos que el Form anterior: la lógica no cambia.
- Login y configuración de la app (client id, duración de la sesión): flujo **Login Microsoft 365** → *Registro de aplicaciones* → `rindegastos`."""


def main(origen, destino, perfil):
    p = PERFILES[perfil]
    w = json.load(open(origen, encoding='utf-8'))
    w = w.get('data', w)
    nodos = {n['name']: n for n in w['nodes']}
    con = w['connections']
    sub_id, sub_nombre = p['subflujo']
    entrada = f"{INSTANCIA}/webhook/{p['ruta']}"
    acceso = f"{INSTANCIA}/webhook/{p['acceso']}?app=rindegastos"
    UI = "$('UI estándar').first().json.ui"

    def nuevo(nombre, tipo, version, pos, params, **extra):
        n = {'parameters': params, 'id': str(uuid.uuid4()), 'name': nombre, 'type': tipo, 'typeVersion': version, 'position': pos}
        n.update(extra)
        w['nodes'].append(n)
        nodos[nombre] = n
        return n

    def responder(nombre, pos, codigo, cabeceras, cuerpo=None):
        tipo = [('Content-Type', 'text/html; charset=utf-8')] if cuerpo else []
        params = {'respondWith': 'text' if cuerpo else 'noData', 'options': {'responseCode': codigo, 'responseHeaders': {
            'entries': [{'name': k, 'value': v} for k, v in tipo + cabeceras + [('Cache-Control', 'no-store')]]}}}
        if cuerpo:
            params['responseBody'] = cuerpo
        return nuevo(nombre, 'n8n-nodes-base.respondToWebhook', 1.5, pos, params)

    def a(*destinos):
        return {'main': [[{'node': d, 'type': 'main', 'index': 0}] for d in destinos]}

    # ---------------------------------------------------------- se quita el Form Trigger
    trig = nodos.pop('On form submission')
    assert trig['type'] == 'n8n-nodes-base.formTrigger'
    assert {c.get('fieldName') for c in trig['parameters']['formFields']['values']} == {'usuario', 'id_informe_de_gastos'}
    assert con['On form submission']['main'] == [[{'node': 'Rindegastos getExpenseReport', 'type': 'main', 'index': 0}]]
    w['nodes'] = [n for n in w['nodes'] if n is not trig]

    # ---------------------------------------------------------- páginas finales: Form → Respond con la UI estándar
    def a_js(valor):
        if valor.startswith('={{') and valor.rstrip().endswith('}}'):
            return '(' + valor[3:].rstrip()[:-2].strip() + ')'
        assert not valor.startswith('='), valor
        return json.dumps(valor, ensure_ascii=False)

    for nombre, icono in PAGINAS_FINALES.items():
        n = nodos[nombre]
        assert n['type'] == 'n8n-nodes-base.form' and n['parameters']['operation'] == 'completion', nombre
        titulo, mensaje = n['parameters']['completionTitle'], n['parameters']['completionMessage']
        mensaje = mensaje.replace(f'\n\n<a href="{FORM_ORIGINAL}">Volver al formulario</a>', '')
        mensaje = mensaje.replace(f" + '\\n\\n<a href=\"{FORM_ORIGINAL}\">Volver al formulario</a>'", '')
        assert 'Volver al formulario' not in mensaje, nombre
        cuerpo = ("(function () { const esc = s => String(s == null ? '' : s).replace(/[&<>\"']/g, c => "
                  "({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', \"'\": '&#39;' })[c]); "
                  f"const titulo = String({a_js(titulo)}); const icono = {icono}; "
                  f"return '<div class=\"status-icon ' + icono + '\">' + {ICONOS}[icono] + '</div><h1>' + esc(titulo) + '</h1>"
                  f"<div class=\"mensaje\">' + esc(String({a_js(mensaje)}).trim()).replace(/\\n/g, '<br>') + '</div>"
                  f"<a class=\"btn\" href=\"' + {UI}.urlFormulario + '\">Volver</a>"
                  f"<a class=\"btn-back\" href=\"' + {UI}.urlSalir + '\">Cerrar sesión</a>'; }})()")
        expr = f"{UI}.inicio + {cuerpo} + {UI}.fin"
        if nombre == 'Form Final':  # resultado del envío: contadores + secciones por estado
            expr = FORM_FINAL_JS
        assert '}}' not in expr, nombre
        n.pop('webhookId', None)
        n.update({'type': 'n8n-nodes-base.respondToWebhook', 'typeVersion': 1.5, 'parameters': {
            'respondWith': 'text', 'responseBody': '={{ ' + expr + ' }}',
            'options': {'responseCode': 200, 'responseHeaders': {'entries': [
                {'name': 'Content-Type', 'value': 'text/html; charset=utf-8'}, {'name': 'Cache-Control', 'value': 'no-store'}]}}}})

    # ---------------------------------------------------------- bloque de acceso estándar + UI
    gx, gy = nodos['Rindegastos getExpenseReport']['position']
    x0, y0 = gx - 1540, gy
    nuevo('Nota · Acceso Microsoft 365', 'n8n-nodes-base.stickyNote', 1, [x0 - 60, y0 - 460],
          {'content': NOTA.replace('__RUTA__', p['ruta']).replace('__ACCESO__', p['acceso']), 'width': 1460, 'height': 820, 'color': 6})
    nuevo('Webhook Formulario', 'n8n-nodes-base.webhook', 2.1, [x0, y0 - 120],
          {'path': p['ruta'], 'responseMode': 'responseNode', 'options': {}}, webhookId=str(uuid.uuid4()), onError='continueRegularOutput')
    nuevo('Webhook Enviar', 'n8n-nodes-base.webhook', 2.1, [x0, y0 + 120],
          {'httpMethod': 'POST', 'path': f"{p['ruta']}-enviar", 'responseMode': 'responseNode', 'options': {}},
          webhookId=str(uuid.uuid4()), onError='continueRegularOutput')
    nuevo('Auth: verificar sesión', 'n8n-nodes-base.executeWorkflow', 1.2, [x0 + 220, y0], {
        'workflowId': {'__rl': True, 'mode': 'list', 'value': sub_id, 'cachedResultName': sub_nombre,
                       'cachedResultUrl': f'/workflow/{sub_id}'},
        'workflowInputs': {
            'mappingMode': 'defineBelow',
            'value': {'operacion': 'verificarSesion', 'app': 'rindegastos', 'redirectUri': '',
                      'cookies': "={{ $json.headers.cookie ?? '' }}",
                      'query': "={{ JSON.parse('{}') }}",
                      'tokenSesion': "={{ $json.body ? String($json.body._sesion || '') : '' }}"},
            'matchingColumns': [],
            'schema': [{'id': k, 'displayName': k, 'required': False, 'defaultMatch': False, 'display': True,
                        'canBeUsedToMatch': True, 'type': 'object' if k == 'query' else 'string', 'removed': False}
                       for k in ('operacion', 'app', 'redirectUri', 'cookies', 'query', 'tokenSesion')],
            'attemptToConvertTypes': False, 'convertFieldsToString': False},
        'options': {}}, onError='continueRegularOutput')
    ui_js = open(UI_FUENTE, encoding='utf-8').read() + UI_FLUJO.replace('__ENTRADA__', entrada).replace('__ACCESO__', acceso)
    nuevo('UI estándar', 'n8n-nodes-base.code', 2, [x0 + 440, y0], {'jsCode': ui_js})
    nuevo('Ruta', 'n8n-nodes-base.switch', 3.2, [x0 + 660, y0], {'mode': 'expression', 'numberOutputs': 3, 'output': '={{ $json.salida }}'})
    responder('Respond Formulario', [x0 + 880, y0 - 200], 200, [], cuerpo='={{ $json.ui.formulario }}')
    nuevo('On form submission', 'n8n-nodes-base.set', 3.4, [x0 + 880, y0], {
        'assignments': {'assignments': [
            {'id': str(uuid.uuid4()), 'name': 'usuario', 'type': 'string', 'value': '={{ $json.datos.usuario }}'},
            {'id': str(uuid.uuid4()), 'name': 'id_informe_de_gastos', 'type': 'string',
             'value': "={{ String($json.datos.id_informe_de_gastos ?? '').trim() }}"},
        ]}, 'options': {}})
    responder('Respond Iniciar sesión', [x0 + 880, y0 + 200], 303, [('Location', acceso)])

    con.pop('On form submission', None)
    con['Webhook Formulario'] = a('Auth: verificar sesión')
    con['Webhook Enviar'] = a('Auth: verificar sesión')
    con['Auth: verificar sesión'] = a('UI estándar')
    con['UI estándar'] = a('Ruta')
    con['Ruta'] = a('Respond Formulario', 'On form submission', 'Respond Iniciar sesión')
    con['On form submission'] = a('Rindegastos getExpenseReport')

    # ---------------------------------------------------------- verificaciones
    nombres = {n['name'] for n in w['nodes']}
    assert len(nombres) == len(w['nodes'])
    for k, v in con.items():
        assert k in nombres, k
        for o in v.get('main', []):
            for c in o:
                assert c['node'] in nombres, c
    texto = json.dumps(w['nodes'], ensure_ascii=False)
    assert 'formTrigger' not in texto and FORM_ORIGINAL not in texto
    assert not any(n['type'] in ('n8n-nodes-base.form', 'n8n-nodes-base.wait') for n in w['nodes'])
    ids = [n['webhookId'] for n in w['nodes'] if n.get('webhookId')]
    assert len(ids) == len(set(ids))

    salida = {'name': p['nombre'] or w['name'], 'nodes': w['nodes'], 'connections': con, 'settings': w['settings']}
    json.dump(salida, open(destino, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"{len(w['nodes'])} nodos → {destino} ({perfil})")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
