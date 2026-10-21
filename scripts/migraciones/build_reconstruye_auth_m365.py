"""Issue #389 · fase 2: Reconstruye usa el subflujo "Auth · Microsoft 365".

Toma el respaldo del flujo publicado y reemplaza los nodos propios de login
(Login: …, Auth: …, Verificar sesion) por llamadas al subflujo NtcAdHyPUYIxWSNl.

Uso:  python3 build_reconstruye_auth_m365.py <respaldo.json> <salida.json>
"""
import json
import sys
import uuid

SUBFLUJO = {
    '__rl': True, 'mode': 'list', 'value': 'NtcAdHyPUYIxWSNl',
    'cachedResultName': 'Auth · Microsoft 365', 'cachedResultUrl': '/workflow/NtcAdHyPUYIxWSNl',
}
CTX = "$('Construir contexto').first().json"
ELIMINAR = [
    'Verificar sesion', 'Login: generar nonce', 'Login: firmar state', 'Auth: verificar state',
    'Auth: canjear codigo', 'Auth: leer id_token', 'Auth: validar identidad', 'Auth: firmar sesion',
]

CONFIG_SSO_VIEJO_INICIO = '  sso: {'
CONFIG_SSO_NUEVO = """  sso: {
    habilitado: true, // inicio de sesión con Microsoft 365: único método de acceso
    // Los datos de la app de Entra ID (tenant, client id, dominios permitidos, duración de la sesión)
    // y su secreto viven en el subflujo "Auth · Microsoft 365" (UNI2 / Utilitarios), nodo
    // "Registro de aplicaciones", entrada "reconstruye".
    app: 'reconstruye',
  },"""

CONTEXTO_FINAL = r"""// Aplica la sesión verificada por el subflujo "Auth · Microsoft 365" y decide a qué paso del formulario ir.
const item = $('Construir contexto').first().json;
const ctx = { ...item.ctx };
const sso = ctx.config.sso;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

let destino = ctx.ruta;
ctx.campoSesion = '';
if (sso.habilitado) {
  const sesion = $input.first().json; // salida de "Auth: verificar sesión"
  if (!sesion.ok || !sesion.usuario) {
    destino = 'LOGIN';
  } else {
    const email = String(sesion.usuario.email || '');
    ctx.usuario = { email, nombre: sesion.usuario.nombre || '' };
    // campo oculto "_sesion" que llevan los formularios (ver nota en "Config Reconstruye")
    ctx.campoSesion = sesion.campoOculto;
    ctx.bannerHtml = ctx.bannerHtml.replace('<!--USUARIO-->',
      '<span class="sep">|</span><span class="usuario">' + esc(email) + '</span><a href="' + ctx.urls.auth + '?salir=1">Cerrar sesión</a>');
  }
}

// Salidas de "Router rutas": 0 página 1, 1 créditos activos, 2 línea de crédito, 3 confirmar, 4 iniciar sesión
const i = ['A', 'B', 'B2', 'C'].indexOf(destino);
ctx.salidaRuta = i < 0 ? 4 : i;

return [{ json: { ...item, ctx }, pairedItem: { item: 0 } }];
"""

EVALUAR_CALLBACK = r"""// Ruta "-auth": 0 cerrar sesión (?salir=1), 1 regreso desde Microsoft (lo valida el subflujo "Auth · Microsoft 365")
const q = $('Construir contexto').first().json.query || {};
return [{ json: { salidaAuth: q.salir ? 0 : 1 }, pairedItem: { item: 0 } }];
"""

ESTILOS_ERROR = (".card ul.consejos{list-style:none;margin-top:12px;color:var(--texto-suave);line-height:1.6;text-align:center;}\n"
                 ".card .detalle-tecnico{margin-top:14px;font-size:12px;color:#9a9a9a;word-break:break-word;}\n")

NOTAS = {
    'Nota 1 · Entrada común': ('**Config Reconstruye**: único punto de configuración (app de Microsoft, dominios permitidos).',
                               '**Config Reconstruye**: único punto de configuración del flujo. El login de Microsoft se configura en el subflujo **Auth · Microsoft 365**.'),
    'Nota 2 · Sesion valida': ('Verifica la sesión firmada',
                               'El subflujo **Auth · Microsoft 365** verifica la sesión'),
    'Nota 3 · Sin sesion': ('Página de inicio: se genera el código de seguridad y se envía al login de Microsoft.',
                            'Página de inicio: el subflujo **Auth · Microsoft 365** genera el código de seguridad (un solo uso, 10 min) y se envía al login de Microsoft.'),
    'Nota 4 · Regreso de Microsoft': ('Revisa cancelaciones y errores, canjea el código por la identidad del usuario, valida directorio, app, vencimiento y dominio, y crea la sesión de 1 hora.',
                                      'Cierre de sesión (`?salir=1`) o regreso desde Microsoft. El subflujo **Auth · Microsoft 365** valida el código de seguridad, canjea el código por la identidad del usuario, valida directorio, app, vencimiento y dominio, y crea la sesión de 1 hora. Los errores muestran el mensaje que entrega el subflujo.'),
}


def llamada(nombre, pos, operacion):
    valores = {
        'operacion': operacion,
        'app': f"={{{{ {CTX}.ctx.config.sso.app }}}}",
        'redirectUri': f"={{{{ {CTX}.ctx.urls.auth }}}}",
        'cookies': f"={{{{ {CTX}.headers.cookie ?? '' }}}}",
        'query': f"={{{{ {CTX}.query }}}}",
        'tokenSesion': f"={{{{ {CTX}.ctx.tokenSesion }}}}",
    }
    tipos = {'query': 'object'}
    return {
        'parameters': {
            'workflowId': SUBFLUJO,
            'workflowInputs': {
                'mappingMode': 'defineBelow',
                'value': valores,
                'matchingColumns': [],
                'schema': [{'id': k, 'displayName': k, 'required': False, 'defaultMatch': False, 'display': True,
                            'canBeUsedToMatch': True, 'type': tipos.get(k, 'string'), 'removed': False} for k in valores],
                'attemptToConvertTypes': False,
                'convertFieldsToString': False,
            },
            'options': {},
        },
        'id': str(uuid.uuid4()), 'name': nombre, 'type': 'n8n-nodes-base.executeWorkflow', 'typeVersion': 1.2,
        'position': pos, 'onError': 'continueRegularOutput',
    }


def main(origen, destino):
    w = json.load(open(origen, encoding='utf-8'))
    nodos = {n['name']: n for n in w['nodes']}
    pos = {k: nodos[k]['position'] for k in ELIMINAR}

    # ---------------------------------------------------------- nodos modificados
    cfg = nodos['Config Reconstruye']['parameters']
    js = cfg['jsCode']
    ini = js.index(CONFIG_SSO_VIEJO_INICIO)
    fin = js.index('  },', ini) + len('  },')
    js = js[:ini] + CONFIG_SSO_NUEVO + js[fin:]
    js = js.replace("""// SSO: datos de la app registrada en Microsoft Entra ID. El client
//   secret NO va aquí: está en la credencial
//   "Reconstruye · Secreto Entra ID (vence 2027-10-14)" del nodo "Auth: canjear codigo".""",
                    """// SSO: el inicio de sesión con Microsoft 365 lo hace el subflujo
//   "Auth · Microsoft 365" (issue #389); aquí solo se indica la app.""")
    assert 'Auth: canjear codigo' not in js and 'tenantId' not in js, 'Config Reconstruye: revisar reemplazo'
    cfg['jsCode'] = js

    ctxjs = nodos['Construir contexto']['parameters']['jsCode']
    assert ctxjs.count('</style>') == 1
    nodos['Construir contexto']['parameters']['jsCode'] = ctxjs.replace('</style>', ESTILOS_ERROR + '</style>')

    nodos['Contexto final']['parameters']['jsCode'] = CONTEXTO_FINAL
    nodos['Auth: evaluar callback']['parameters']['jsCode'] = EVALUAR_CALLBACK
    nodos['Auth: decidir']['parameters']['numberOutputs'] = 2

    # Redirigir a Microsoft: URL y cookie de nonce las entrega el subflujo
    for h in nodos['Respond Redirigir a Microsoft']['parameters']['options']['responseHeaders']['entries']:
        if h['name'] == 'Location':
            h['value'] = '={{ $json.urlRedireccion }}'
        elif h['name'] == 'Set-Cookie':
            h['value'] = '={{ $json.setCookie }}'
    # Sesión iniciada y cerrada: la cookie la entrega el subflujo
    for nombre in ('Respond Sesion iniciada', 'Respond Sesion cerrada'):
        for h in nodos[nombre]['parameters']['options']['responseHeaders']['entries']:
            if h['name'] == 'Set-Cookie':
                h['value'] = '={{ $json.setCookie }}'

    # Acceso denegado: muestra el mensaje del subflujo (html ya escapado)
    p = nodos['Respond Acceso denegado']['parameters']
    cuerpo = p['responseBody']
    ini = cuerpo.index('<h1>Acceso denegado</h1><p>')
    fin = cuerpo.index("</p><a class=\\\"btn-back\\\"", ini) if "</p><a class=\\\"btn-back\\\"" in cuerpo else cuerpo.index('</p><a class="btn-back"', ini)
    p['responseBody'] = (cuerpo[:ini]
                         + "' + ($json.html || '<h1>Acceso denegado</h1><p>No fue posible validar tu identidad con Microsoft 365.</p>') + '"
                         + cuerpo[fin + len('</p>'):])

    # IF Identidad valida → IF Sesion creada (salida del subflujo)
    sif = nodos['IF Identidad valida']
    sif['name'] = 'IF Sesion creada'
    sif['parameters']['conditions']['conditions'][0]['leftValue'] = '={{ $json.ok }}'

    # Notas
    for nombre, (viejo, nuevo) in NOTAS.items():
        c = nodos[nombre]['parameters']['content']
        assert viejo in c, nombre
        nodos[nombre]['parameters']['content'] = c.replace(viejo, nuevo)
    r = nodos['Nota 0 · Resumen']['parameters']
    r['content'] += ('\n\n**Inicio de sesión con Microsoft 365:** lo hace el subflujo **Auth · Microsoft 365** (UNI2 / Utilitarios, issue #389). '
                     'Los nodos *Auth: …* de este flujo solo lo llaman; la app de Entra ID, los dominios y la duración de la sesión se configuran en su nodo **Registro de aplicaciones**.')

    # ---------------------------------------------------------- nodos nuevos y eliminados
    cerrada = nodos['Respond Sesion cerrada']['position']
    nuevos = [
        llamada('Auth: verificar sesión', pos['Verificar sesion'], 'verificarSesion'),
        llamada('Auth: iniciar login', pos['Login: generar nonce'], 'iniciarLogin'),
        llamada('Auth: procesar regreso', pos['Auth: verificar state'], 'procesarCallback'),
        llamada('Auth: cerrar sesión', [pos['Auth: verificar state'][0], cerrada[1]], 'cerrarSesion'),
    ]
    login_ok = json.loads(json.dumps(sif))
    login_ok.update({'id': str(uuid.uuid4()), 'name': 'IF Login preparado', 'position': pos['Login: firmar state']})
    login_ok['parameters']['conditions']['conditions'][0]['id'] = str(uuid.uuid4())
    nuevos.append(login_ok)
    sif['position'] = pos['Auth: canjear codigo']

    w['nodes'] = [n for n in w['nodes'] if n['name'] not in ELIMINAR] + nuevos

    # ---------------------------------------------------------- conexiones
    con = w['connections']
    for k in ELIMINAR + ['IF Identidad valida']:
        con.pop(k, None)

    def a(*destinos):
        return [[{'node': d, 'type': 'main', 'index': 0}] if d else [] for d in destinos]

    salidas = con['Control de acceso']['main']
    salidas[1] = [{'node': 'Auth: verificar sesión', 'type': 'main', 'index': 0}]
    con['Auth: verificar sesión'] = {'main': a('Contexto final')}
    con['IF Pagina inicial'] = {'main': a('Auth: iniciar login', 'Respond Volver al inicio')}
    con['Auth: iniciar login'] = {'main': a('IF Login preparado')}
    con['IF Login preparado'] = {'main': a('Respond Redirigir a Microsoft', 'Respond Acceso denegado')}
    con['Auth: decidir'] = {'main': a('Auth: cerrar sesión', 'Auth: procesar regreso')}
    con['Auth: cerrar sesión'] = {'main': a('Respond Sesion cerrada')}
    con['Auth: procesar regreso'] = {'main': a('IF Sesion creada')}
    con['IF Sesion creada'] = {'main': a('Respond Sesion iniciada', 'Respond Acceso denegado')}

    # ---------------------------------------------------------- verificaciones
    nombres = {n['name'] for n in w['nodes']}
    texto = json.dumps(w['nodes'], ensure_ascii=False)
    for k in ELIMINAR + ['IF Identidad valida']:
        assert f"$('{k}')" not in texto and f'"node": "{k}"' not in json.dumps(con), k
    for k, v in con.items():
        assert k in nombres, k
        for o in v['main']:
            for c in o:
                assert c['node'] in nombres, c
    for clave in ('sso.tenantId', 'sso.clientId', 'sso.dominiosPermitidos', 'sso.duracionSesionSegundos'):
        assert clave not in texto, clave

    salida = {'name': w['name'], 'nodes': w['nodes'], 'connections': con, 'settings': w['settings']}
    json.dump(salida, open(destino, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"{len(w['nodes'])} nodos → {destino}")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
