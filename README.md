# UNI2 · Flujos n8n con Claude Code

Base y estándar del equipo para crear, modificar y documentar los flujos n8n de UNI2 (`https://uni2.app.n8n.cloud`) con Claude Code y el servidor MCP `n8n-mcp`.

## Puesta en marcha

```bash
git clone --recurse-submodules <url-del-repo>
cd <repo>
cp .mcp.json.example .mcp.json
```

Definir las variables de entorno (por ejemplo en `~/.bashrc`; nunca en archivos del repo):

```bash
export N8N_API_URL="https://uni2.app.n8n.cloud"
export N8N_API_KEY="<tu API key de n8n>"        # n8n → Settings → n8n API
export N8N_MCP_TOKEN="<tu token MCP de n8n>"    # n8n → Settings → MCP
```

Instalar las skills de n8n en Claude Code (una vez):

```
/plugin install czlonkowski/n8n-skills
```

Abrir Claude Code en la carpeta del repo y comprobar con `/mcp` que `n8n` y `n8n-mcp` estén conectados.

## Contenido

| Carpeta | Qué hay |
|---|---|
| `CLAUDE.md` | Instrucciones y reglas que sigue Claude Code en este repo |
| `docs/estandares/` | Estándares del equipo: [Login M365](docs/estandares/LOGIN_M365_ESTANDAR.md) |
| `docs/tareas/` | Documentación de tareas e issues |
| `docs/incidentes/` | Incidentes y lecciones aprendidas |
| `workflows/` | Export vigente de cada flujo, por proyecto |
| `scripts/` | Generadores de flujos (`build_*.py`), con perfiles `pruebas` y `produccion` |
| `n8n_ui/` | Interfaz estándar (marca UNI2, banner de sesión, formularios) |

## Flujos versionados

| Archivo | Flujo en n8n | ID |
|---|---|---|
| `workflows/utilitarios/login_microsoft_365.json` | Login Microsoft 365 | `1yD3JSYX8nMJqeID` |
| `workflows/reconstruye/reconstruye.json` | Reconstruye | `io6wE6X97L0skPAG` |
| `workflows/reconstruye/reconstruye_base_datos.json` | Reconstruye · Base de datos | `kgoDhOOse3BAI37h` |
| `workflows/reconstruye/dev/reconstruye_dev.json` | Reconstruye (dev - SSO #374) | `SYf2UYaooO40I13d` |
| `workflows/reconstruye/dev/reconstruye_base_datos_dev.json` | Reconstruye · Base de datos (dev) | `zNxikoekjqD98VPw` |
| `workflows/rindegastos/rindegastos_sap.json` | RindegastosSAP | `OtyruCQv37g4mnlH` |

## Reglas básicas

1. Nada de secretos ni datos personales en el repo. Los secretos viven en las credenciales de n8n.
2. No ejecutar flujos que escriben en sistemas productivos para "probar".
3. Cambios sobre una copia en *UNI2 / Pruebas*; la persona responsable valida y publica.
4. Tras cambiar un flujo en n8n, reemplazar su export en `workflows/` y hacer commit.
