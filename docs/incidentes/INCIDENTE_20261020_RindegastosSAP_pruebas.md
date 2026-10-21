# Incidente: ejecución de prueba de RindegastosSAP escribió en SAP PRO y en Rindegastos

**Fecha:** 20/10/2026, 10:21 (hora Colombia) · **Ejecución n8n:** 5778 · **Flujo:** RindegastosSAP (pruebas - SSO), `a7sfU8L67yKtO13f`
**Estado:** el flujo de pruebas está **desactivado**. El flujo original `OtyruCQv37g4mnlH` no se modificó.

## Qué pasó

Durante la prueba del nuevo inicio de sesión con Microsoft 365, se envió el formulario con **ID de informe `0`**, con la intención de que no encontrara gastos y no escribiera nada.

La API de Rindegastos **no filtra cuando `ReportId=0`**: `getExpenses?ReportId=0` devolvió **todos los gastos de la cuenta** (8.267; el flujo procesó la primera página, 100 gastos). El flujo no valida que el ID sea un informe real, así que procesó esos gastos con la lógica normal.

> El mismo comportamiento existe en el **flujo original**: cualquier usuario que escriba `0` (o un ID que la API ignore) desencadena lo mismo.

## Qué se escribió

### SAP PRO

| Tipo | Identificador | Detalle |
|---|---|---|
| Asiento contable | **JdtNum 126335** (Number 108486) | Memo "Leg No. 0 - Desplazamiento a el Cerrito", referencia "LEG GAS JUN", gasto Rindegastos 80920679 ($130.000) |
| Asiento contable | **JdtNum 126333** (Number 108485) | Memo "Leg No. 0 - UNI2 MICROCRÉDITO", referencia "LEG GAS JUN", gasto Rindegastos 81120500 ($50.000) |
| Socio de negocio | **CardCode P10…** (persona natural) | Datos personales omitidos; ver respaldo local |
| Facturas de proveedor | **Ninguna creada** | 44 intentos: 21 ya existían en SAP (se reutilizó su DocNum) y el resto falló (encargado de compras obligatorio / fila sin impuesto) |

### Rindegastos

- **46 gastos** de **32 informes** recibieron `setExpenseIntegration`:
  - **23** con `IntegrationStatus = 1` y un código de integración (DocNum o JdtNum de SAP);
  - **23** con `IntegrationStatus = 0`.
- La lectura previa (`getExpenses`) **no trae el estado de integración**, así que no se puede saber desde n8n si alguno ya estaba marcado antes.
- `setExpenseReportIntegration` se llamó con informe `Id = "0"`, que no corresponde a un informe real.

El detalle gasto por gasto (ids, informes, proveedores y montos) contiene datos personales y no se versiona:
está en el respaldo local `backups/otros/INCIDENTE_20261020_original_con_datos.md`.

## Acciones sugeridas (las decide Contabilidad; no se ejecutó ninguna reversión)

1. **SAP:** revisar y, si corresponde, **anular los asientos 126335 y 126333**.
2. **SAP:** revisar el socio de negocio creado (CardCode en el respaldo local). Puede ser legítimo, pero se creó fuera del proceso normal.
3. **Rindegastos:** revisar los 46 gastos afectados (lista en el respaldo local). Los informes que no se habían procesado deberían volver a su estado previo de integración antes de procesarse con el flujo.
4. **Flujo:** agregar una validación del ID del informe antes de cualquier escritura: número positivo, `getExpenseReport` debe devolver ese mismo `Id`, y todos los gastos deben tener ese `ReportId`. Aplica al flujo original y a la copia.

## Evidencia

- Datos completos de la ejecución: `backups/ejecuciones/incidente_20261020_ejecucion_5778_RindegastosSAP_pruebas.json` (solo local, no se versiona).
- En n8n: ejecución **5778** del flujo `a7sfU8L67yKtO13f`.
