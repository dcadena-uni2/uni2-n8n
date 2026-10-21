"""Flujo único "Login Microsoft 365" (issue #389): el login estándar compartido por todas las apps.

Une en un solo flujo las dos piezas que antes estaban separadas:
  - Acceso (build_acceso_m365.py): webhooks del navegador (ingreso, regreso desde Microsoft, cierre).
  - Auth   (build_auth_m365.py):   motor (validaciones, secretos, sesiones, registro, limpieza diaria).
Entradas del flujo:
  1. Webhooks públicos            → los usa el navegador.
  2. "Entrada" (Execute Workflow) → la usan los flujos de cada app para verificar la sesión.
  3. "Limpieza diaria" (3:00)     → mantenimiento de las tablas.
Las llamadas internas del bloque de acceso apuntan a este mismo flujo ($workflow.id).

Uso:  python3 build_login_m365.py <salida.json> [pruebas|produccion]
"""
import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
NOMBRES = {'pruebas': 'Login Microsoft 365 (pruebas)', 'produccion': 'Login Microsoft 365'}
DESPLAZAMIENTO_ACCESO = (0, -2700)  # el bloque de acceso queda encima del motor

NOTA_GENERAL = """# Login Microsoft 365 · estándar UNI2 (issue #389)
Login único para **todos** los flujos n8n que usan personas. Un solo flujo, tres entradas:

| Entrada | Quién la usa |
|---|---|
| **Webhooks** (bloque superior) | El navegador: `/webhook/<ingreso>?app=<app>`, regreso desde Microsoft, cierre de sesión |
| **Entrada** (Execute Workflow) | Los flujos de cada app: operación `verificarSesion` |
| **Limpieza diaria** (3:00) | Mantenimiento de sesiones, inicios y registro de accesos (90 días) |

**Agregar una app:** entrada en *Registro de aplicaciones* + credencial + rama de canje + webhook de regreso en *Config acceso* (o la URI genérica).
**En el flujo de la app:** Webhook → *Auth: verificar sesión* (este flujo) → *UI estándar* → su lógica."""


def construir(perfil):
    with tempfile.TemporaryDirectory() as tmp:
        # Motor (Auth): el script escribe auth_m365_subflujo.json en el directorio actual
        subprocess.run([sys.executable, '-I', os.path.join(AQUI, 'build_auth_m365.py'), perfil], cwd=tmp, check=True,
                       stdout=subprocess.DEVNULL)
        motor = json.load(open(os.path.join(tmp, 'auth_m365_subflujo.json'), encoding='utf-8'))
        ruta_acceso = os.path.join(tmp, 'acceso.json')
        subprocess.run([sys.executable, '-I', os.path.join(AQUI, 'build_acceso_m365.py'), ruta_acceso, perfil], check=True,
                       stdout=subprocess.DEVNULL)
        acceso = json.load(open(ruta_acceso, encoding='utf-8'))

    repetidos = {n['name'] for n in motor['nodes']} & {n['name'] for n in acceso['nodes']}
    assert not repetidos, f'nombres de nodo repetidos: {repetidos}'

    dx, dy = DESPLAZAMIENTO_ACCESO
    for n in acceso['nodes']:
        n['position'] = [n['position'][0] + dx, n['position'][1] + dy]
        if n['type'] == 'n8n-nodes-base.executeWorkflow':
            # El bloque de acceso llama al motor de este mismo flujo
            n['parameters']['workflowId'] = {'__rl': True, 'mode': 'id', 'value': '={{ $workflow.id }}'}

    nota = {'parameters': {'content': NOTA_GENERAL, 'width': 900, 'height': 460, 'color': 7},
            'id': 'b1f6a0de-3c1e-4c55-9d7a-5d1f0e0a0001', 'name': 'Nota · Login Microsoft 365',
            'type': 'n8n-nodes-base.stickyNote', 'typeVersion': 1, 'position': [-1520, dy - 300]}
    nodos = motor['nodes'] + acceso['nodes'] + [nota]
    conexiones = {**motor['connections'], **acceso['connections']}

    nombres = {n['name'] for n in nodos}
    for k, v in conexiones.items():
        assert k in nombres, k
        for o in v['main']:
            for c in o:
                assert c['node'] in nombres, c
    ids = [n['webhookId'] for n in nodos if n.get('webhookId')]
    assert len(ids) == len(set(ids))
    return {'name': NOMBRES[perfil], 'nodes': nodos, 'connections': conexiones,
            'settings': {'executionOrder': 'v1', 'callerPolicy': 'workflowsFromSameOwner', 'availableInMCP': True}}


if __name__ == '__main__':
    perfil = sys.argv[2] if len(sys.argv) > 2 else 'pruebas'
    w = construir(perfil)
    json.dump(w, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"{len(w['nodes'])} nodos → {sys.argv[1]} ({w['name']})")
