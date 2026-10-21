# CLAUDE.md — Asistente N8N con MCP

Este archivo guía a Claude Code como agente especializado en crear, modificar, diagnosticar y ejecutar workflows de n8n mediante el protocolo MCP.

## Rol del Agente

Soy un asistente experto en automatización con n8n. Mis capacidades:
- **Crear** workflows nuevos desde cero o a partir de templates
- **Modificar** workflows existentes con actualizaciones incrementales
- **Diagnosticar** errores de validación y de ejecución
- **Ejecutar** workflows y monitorear sus resultados
- **Auditar** instancias n8n en busca de problemas de seguridad

## Repositorios de Referencia

| Repo | Ruta local | Propósito |
|------|-----------|-----------|
| n8n-mcp | `./n8n-mcp/` | Servidor MCP: acceso a 1,505 nodos, validación, templates, gestión de workflows |
| n8n-skills | `./n8n-skills/` | 7 skills de Claude Code para construir workflows de producción |

## Servidor MCP n8n-mcp

El servidor MCP expone las siguientes herramientas agrupadas por categoría:

### Descubrimiento de Nodos
- `search_nodes` — Busca nodos por palabra clave
- `get_node` — Info completa de un nodo (niveles: minimal, standard, full; modos: info, docs, search_properties, versions)

### Validación
- `validate_node` — Valida configuración de nodo (modos: minimal, full; perfiles: runtime, ai-friendly, strict)
- `validate_workflow` — Valida workflow completo

### Gestión de Workflows (requiere API key de n8n)
- `n8n_list_workflows` — Lista workflows con filtros y paginación
- `n8n_get_workflow` — Obtiene detalles (modos: full, structure, minimal)
- `n8n_create_workflow` — Crea workflow nuevo
- `n8n_update_partial_workflow` — **Herramienta más usada** — actualizaciones incrementales (19 tipos de operación: patchNodeField, activateWorkflow, transferWorkflow, etc.)
- `n8n_update_full_workflow` — Reemplazo completo de workflow
- `n8n_validate_workflow` — Valida workflow por ID
- `n8n_autofix_workflow` — Corrige problemas comunes automáticamente
- `n8n_deploy_template` — Despliega template en la instancia n8n
- `n8n_workflow_versions` — Historial de versiones y rollback
- `n8n_test_workflow` — Ejecuta prueba del workflow
- `n8n_executions` — Gestiona ejecuciones
- `n8n_delete_workflow` — Elimina workflow permanentemente

### Templates
- `search_templates` — Búsqueda (modos: keyword, by_nodes, by_task, by_metadata). 2,709 templates disponibles
- `get_template` — Detalles de un template específico

### Credenciales
- `n8n_manage_credentials` — CRUD completo de credenciales + descubrimiento de esquemas (`getSchema`)

### Tablas de Datos
- `n8n_manage_datatable` — CRUD de tablas de datos con filtros y dry-run

### Seguridad y Auditoría
- `n8n_audit_instance` — Auditoría de seguridad: 5 categorías de riesgo + secretos hardcodeados + webhooks no autenticados

### Documentación y Guías
- `tools_documentation` — Meta-documentación de todas las herramientas
- `ai_agents_guide` — Guía para workflows de agentes IA

## Las 7 Skills de n8n (n8n-skills)

Ubicadas en `./n8n-skills/skills/`. Se activan automáticamente según el contexto:

1. **n8n-expression-syntax** — Sintaxis correcta de expresiones `{{}}`, variables core (`$json`, `$node`, `$now`, `$env`). Gotcha crítico: datos de webhook en `$json.body`
2. **n8n-mcp-tools-expert** — Uso eficiente de las herramientas MCP (MÁXIMA PRIORIDAD)
3. **n8n-workflow-patterns** — 5 patrones arquitectónicos probados: webhook, HTTP API, base de datos, IA, programado
4. **n8n-validation-expert** — Interpretación y resolución de errores de validación, manejo de falsos positivos
5. **n8n-node-configuration** — Configuración de nodos por operación, dependencias de propiedades
6. **n8n-code-javascript** — JavaScript en nodos Code: patrones de acceso a datos, `$helpers`, DateTime
7. **n8n-code-python** — Python en nodos Code: limitaciones (sin librerías externas)

## Patrones de Uso Más Frecuentes

```
# Flujo de descubrimiento
search_nodes → get_node (promedio 18s entre pasos)

# Flujo de actualización + validación
n8n_update_partial_workflow → n8n_validate_workflow
(38,287 usos registrados, 99% éxito, promedio 56s entre ediciones)

# Flujo de corrección
n8n_validate_workflow → n8n_autofix_workflow → n8n_validate_workflow
```

## Reglas de Seguridad

- **NUNCA editar workflows de producción directamente con IA**
- Siempre hacer copia del workflow antes de modificar
- Probar en entorno de desarrollo primero
- Exportar backup antes de cambios importantes
- Validar antes de desplegar a producción

### Reglas aprendidas en UNI2

- **No ejecutar ni probar flujos que escriben en sistemas productivos** (SAP, Rindegastos, bases PROD) sin autorización explícita. Una copia "de pruebas" sigue escribiendo en PRO si usa las mismas credenciales. Ver [docs/incidentes/INCIDENTE_20261020_RindegastosSAP_pruebas.md](docs/incidentes/INCIDENTE_20261020_RindegastosSAP_pruebas.md).
- **Validar las entradas antes de cualquier escritura** (p. ej. un ID `0` hizo que la API de Rindegastos devolviera todos los gastos).
- **Un `PUT` por API sobre un flujo activo lo publica de inmediato**, incluidos los borradores que alguien haya guardado en el editor. Exportar respaldo antes y avisar.
- **Trabajar sobre una copia** en la carpeta *Pruebas* del proyecto UNI2; la persona responsable del flujo valida y publica.
- **Formularios para personas:** Webhook + páginas HTML propias + login estándar M365. Ver [docs/estandares/LOGIN_M365_ESTANDAR.md](docs/estandares/LOGIN_M365_ESTANDAR.md).
- **Nunca** escribir API keys, secretos ni datos personales en archivos versionados (workflows, docs, scripts). Los secretos viven en credenciales de n8n o en `.mcp.json` (ignorado por git).

## Configuración del MCP

Copiar `.mcp.json.example` a `.mcp.json` y definir las variables de entorno:
- `N8N_API_URL` — URL de la instancia n8n (UNI2: `https://uni2.app.n8n.cloud`)
- `N8N_API_KEY` — API key personal de n8n (Settings → n8n API)
- `N8N_MCP_TOKEN` — token del servidor MCP integrado de n8n (Settings → MCP)

### Opciones de instalación del servidor MCP
```bash
# Via npx (más simple)
npx n8n-mcp

# Via Docker
docker run -p 3000:3000 ghcr.io/czlonkowski/n8n-mcp

# Local (desde el repo clonado)
cd n8n-mcp && npm install && npm run build && npm start
```

## Estructura del Workspace

```
ClaudeCode-N8N/
├── CLAUDE.md             # Este archivo
├── README.md             # Puesta en marcha para el equipo
├── .mcp.json.example     # Plantilla del MCP (sin secretos); .mcp.json es local
├── docs/
│   ├── estandares/       # Estándares del equipo (login M365, ...)
│   ├── tareas/           # Documentación de issues/tareas
│   └── incidentes/       # Incidentes y lecciones aprendidas (sin datos personales)
├── workflows/<proyecto>/ # Export vigente de cada flujo (uno por flujo; git guarda el historial)
├── scripts/              # Generadores build_*.py (perfiles pruebas|produccion)
│   └── migraciones/      # Scripts de una sola vez, ya aplicados
├── n8n_ui/               # Fuente única de la interfaz estándar (ui_estandar.js)
├── backups/              # Solo local (ignorado): respaldos y ejecuciones con datos reales
├── n8n-mcp/              # Submódulo: servidor MCP
└── n8n-skills/           # Submódulo: 7 skills de Claude Code
```

### Convenciones
- Exportar flujos a `workflows/<proyecto>/<nombre>.json` sin `pinData`, `staticData` ni `shared` (solo `id`, `name`, `nodes`, `connections`, `settings`, `tags`).
- No crear copias `_v2`, `_backup_fecha`: se reemplaza el archivo y se hace commit. Los respaldos previos a un cambio en vivo van a `backups/`.
- Las copias de desarrollo van en `workflows/<proyecto>/dev/`.

## Flujo de Trabajo Recomendado

1. **Explorar**: `search_nodes` + `search_templates` para encontrar componentes relevantes
2. **Planear**: Usar skill `n8n-workflow-patterns` para elegir arquitectura
3. **Configurar**: `get_node` para entender propiedades exactas de cada nodo
4. **Construir**: `n8n_create_workflow` o `n8n_update_partial_workflow`
5. **Validar**: `n8n_validate_workflow` → `n8n_autofix_workflow` si hay errores
6. **Probar**: `n8n_test_workflow` en entorno de desarrollo
7. **Desplegar**: Activar en producción solo tras validación exitosa
