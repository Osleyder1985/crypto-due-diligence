# Esquema de evidencias para investigación de eventos de mercado

## 1. Propósito y límites

Este documento define un modelo de datos interno para registrar eventos, fuentes, evidencias y observaciones de mercado de forma consistente, auditable y versionable. Complementa el proceso de investigación retrospectiva y la taxonomía de eventos del proyecto.

El esquema **no es una norma ISO**, no certifica activos y no demuestra por sí mismo que un evento haya causado un movimiento de precio. La clasificación, la evidencia y la atribución causal son decisiones distintas y deben conservarse como tales.

## 2. Principios de diseño

1. **Trazabilidad:** cada afirmación analítica debe poder rastrearse hasta una o más evidencias y fuentes.
2. **Separación de conceptos:** un evento, una fuente, una pieza de evidencia y una observación de precio son registros distintos.
3. **Tiempo explícito:** no mezclar cuándo ocurrió algo, cuándo se publicó, cuándo se capturó y cuándo se registró.
4. **Incertidumbre visible:** los estados de verificación y la confianza no deben ocultarse en texto libre.
5. **Inmutabilidad práctica:** conservar el registro original de una captura y registrar correcciones como nuevas versiones o cambios auditables.
6. **Reproducibilidad:** guardar la metodología, la ventana temporal, la zona horaria y los datos de mercado utilizados.
7. **Minimización de datos:** no guardar credenciales, tokens de acceso, datos personales innecesarios ni contenido protegido más allá de lo necesario para verificar la fuente.

## 3. Entidades y relaciones

- **Event:** representación normalizada de un acontecimiento o afirmación relevante para el mercado.
- **Source:** publicación, anuncio, documento, feed, endpoint o conjunto de datos del que se obtuvo información.
- **Evidence:** registro de una afirmación o fragmento concreto que respalda, contradice o contextualiza un evento.
- **Market observation:** medición de precio, volumen, liquidez u otra variable dentro de una ventana definida.
- **Attribution assessment:** evaluación analítica que relaciona un evento con observaciones de mercado. Debe mantener hipótesis alternativas y límites explícitos.

Relaciones recomendadas: un evento puede tener varias evidencias; una fuente puede respaldar muchas evidencias; una evidencia puede apoyar o contradecir varios eventos; una evaluación de atribución puede referenciar múltiples eventos y observaciones. No duplicar fuentes solo porque se usaron en más de una investigación.

## 4. Convenciones comunes

### Identificadores

- Usar identificadores estables e inmutables, por ejemplo `evt_<UUID>`, `src_<UUID>`, `evd_<UUID>`, `obs_<UUID>` y `att_<UUID>`.
- No usar el ticker, nombre del proyecto ni URL como identificador primario: pueden cambiar.
- Los identificadores del ejemplo son ilustrativos, no referencias a incidentes reales.

### Fechas y horas

Usar timestamps ISO 8601 en UTC, con sufijo `Z`, por ejemplo `2026-10-18T14:30:00Z`. Si la hora exacta se desconoce, usar `null` y explicar la incertidumbre; no inventar precisión.

- `occurred_at`: momento en que ocurrió el evento, si se conoce.
- `published_at`: momento en que la fuente publicó la información.
- `captured_at`: momento en que el sistema o analista capturó la fuente/evidencia.
- `recorded_at`: momento en que el registro se incorporó al repositorio de investigación.

No asumir que la hora de publicación equivale a la hora del evento.

### Campos desconocidos

Representar información desconocida como `null` cuando el formato lo permita y documentar el motivo en `notes`. No sustituirla por una cadena vacía, cero o una estimación no identificada.

## 5. Esquema de Event

| Campo | Tipo | Requerido | Descripción |
|---|---|---:|---|
| `schema_version` | string | Sí | Versión del esquema usada para validar el registro. |
| `event_id` | string | Sí | Identificador estable del evento. |
| `asset_id` | string | Sí | Identidad canónica del activo/red; evitar depender solo del ticker. |
| `asset_symbol` | string/null | No | Símbolo observado en el momento de la investigación. |
| `event_type` | string | Sí | Categoría de la taxonomía de eventos del proyecto. |
| `event_subtype` | string/null | No | Subcategoría definida o valor explícito `OTHER`. |
| `title` | string | Sí | Título breve, neutral y factual. |
| `summary` | string | Sí | Resumen que separa hechos confirmados de afirmaciones no verificadas. |
| `occurred_at` | datetime/null | No | Momento de ocurrencia del evento. |
| `published_at` | datetime/null | No | Momento de publicación de la información principal. |
| `captured_at` | datetime | Sí | Momento en que se capturó la evidencia principal. |
| `recorded_at` | datetime | Sí | Momento de creación del registro. |
| `verification_status` | enum | Sí | Estado de verificación factual. |
| `event_status` | enum | Sí | Estado operativo o de desarrollo del evento. |
| `source_ids` | array[string] | Sí | Referencias a registros Source. |
| `evidence_ids` | array[string] | Sí | Referencias a registros Evidence. |
| `observed_price_effect` | object/null | No | Observación descriptiva; no equivale a causalidad. |
| `duplicate_of` | string/null | No | ID canónico si se trata de un duplicado. |
| `notes` | string/null | No | Incertidumbres, contexto y limitaciones. |

### Valores controlados recomendados

`verification_status`: `UNVERIFIED`, `PARTIALLY_VERIFIED`, `VERIFIED`, `DISPUTED`, `REFUTED`.

`event_status`: `RUMOR`, `ANNOUNCED`, `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `UNKNOWN`.

`event_type` debe utilizar los identificadores de la taxonomía del proyecto, por ejemplo `PROJECT_FUNDAMENTALS`, `TOKENOMICS_SUPPLY`, `EXCHANGE_MARKET_ACCESS`, `MARKET_MICROSTRUCTURE`, `DERIVATIVES_LEVERAGE`, `ONCHAIN_ACTIVITY`, `SECURITY_INCIDENT`, `GOVERNANCE_DECENTRALIZATION`, `REGULATORY_LEGAL`, `MACROECONOMIC_GEOPOLITICAL`, `SENTIMENT_INFORMATION`, `COMPETITOR_ECOSYSTEM` o `DATA_QUALITY_OPERATIONAL`. La lista canónica y sus subcategorías se mantienen en el documento de taxonomía; no crear variantes por diferencias de mayúsculas o redacción.

## 6. Esquema de Source

| Campo | Tipo | Requerido | Descripción |
|---|---|---:|---|
| `source_id` | string | Sí | Identificador estable de la fuente. |
| `source_type` | enum/string | Sí | Tipo: `OFFICIAL_ANNOUNCEMENT`, `REGULATORY_FILING`, `NEWS_MEDIA`, `EXCHANGE_DATA`, `ONCHAIN_DATA`, `SOCIAL_MEDIA`, `RESEARCH_REPORT`, `OTHER`. |
| `publisher` | string | Sí | Organización, cuenta, protocolo o proveedor responsable. |
| `title` | string/null | No | Título visible de la fuente. |
| `url` | string | Sí | URL original o endpoint consultado, cuando exista. |
| `published_at` | datetime/null | No | Fecha/hora declarada de publicación. |
| `retrieved_at` | datetime | Sí | Momento en que se consultó o descargó la fuente. |
| `content_hash` | string/null | No | Hash del artefacto capturado, si se conserva el archivo. Indicar algoritmo. |
| `reliability_assessment` | enum/string | No | Evaluación contextual; no es una verdad universal sobre el emisor. |
| `access_method` | string/null | No | Navegador, API pública, archivo, nodo, etc. |
| `notes` | string/null | No | Límites de acceso, edición, paywall, archivado o autenticidad. |

La reputación general del emisor no reemplaza la verificación de una afirmación específica. Una cuenta oficial puede publicar información incompleta y una fuente secundaria puede aportar corroboración válida.

## 7. Esquema de Evidence

| Campo | Tipo | Requerido | Descripción |
|---|---|---:|---|
| `evidence_id` | string | Sí | Identificador estable de la evidencia. |
| `source_id` | string | Sí | Fuente de origen. |
| `claim` | string | Sí | Afirmación concreta y verificable, redactada sin exagerar. |
| `evidence_role` | enum | Sí | `SUPPORTS`, `CONTRADICTS`, `CONTEXTUALIZES`, `REFUTES`. |
| `excerpt_or_locator` | string/null | No | Extracto breve, sección, página, transacción o selector que permite localizar el dato. |
| `captured_at` | datetime | Sí | Fecha/hora de captura. |
| `content_hash` | string/null | No | Hash del contenido conservado, con algoritmo indicado. |
| `verification_method` | string | Sí | Cómo se verificó: fuente primaria, corroboración independiente, consulta on-chain, etc. |
| `verification_status` | enum | Sí | Mismos valores controlados que Event. |
| `limitations` | string/null | No | Ambigüedades, datos faltantes, dependencia de terceros o límites de interpretación. |

Conservar un extracto mínimo y su localizador cuando sea suficiente; si la fuente cambia, guardar una nueva captura con su propio timestamp y hash. No afirmar que un hash prueba la veracidad: solo ayuda a detectar cambios en el artefacto comparado.

## 8. Esquema de Market observation

| Campo | Tipo | Requerido | Descripción |
|---|---|---:|---|
| `observation_id` | string | Sí | Identificador estable de la observación. |
| `asset_id` | string | Sí | Identidad canónica del activo. |
| `metric` | string | Sí | Métrica, por ejemplo `price_return`, `volume`, `open_interest` o `liquidity`. |
| `value` | number/string/null | Sí | Valor observado; no mezclar unidades incompatibles. |
| `unit` | string | Sí | Unidad, moneda y/o escala. |
| `window_start` | datetime | Sí | Inicio de la ventana de medición en UTC. |
| `window_end` | datetime | Sí | Fin de la ventana de medición en UTC. |
| `venue_or_dataset` | string | Sí | Exchange, proveedor, cadena o dataset de origen. |
| `methodology_version` | string | Sí | Versión del cálculo o método de extracción. |
| `captured_at` | datetime | Sí | Momento en que se obtuvo la observación. |
| `limitations` | string/null | No | Liquidez, cobertura, datos faltantes, outliers o sesgo del proveedor. |

Las ventanas, los mercados y las unidades deben ser comparables. Una variación porcentual no es reproducible si no se conoce el precio de referencia, la ventana y el dataset de origen.

## 9. Ejemplo JSON ilustrativo

El siguiente ejemplo muestra la estructura y los nombres de campo; los identificadores, URL y valores son ficticios y no representan un evento real. Es un ejemplo de registro, no un JSON Schema formal.

```json
{
  "schema_version": "1.0.0",
  "event_id": "evt_00000000-0000-4000-8000-000000000001",
  "asset_id": "chain:example-network:asset:example-token",
  "asset_symbol": "EXM",
  "event_type": "PROJECT_FUNDAMENTALS",
  "event_subtype": "PROTOCOL_UPGRADE",
  "title": "Example protocol upgrade announced",
  "summary": "The project published an announcement describing a planned protocol upgrade. The implementation status has not yet been independently confirmed.",
  "occurred_at": null,
  "published_at": "2026-10-18T14:00:00Z",
  "captured_at": "2026-10-18T14:05:00Z",
  "recorded_at": "2026-10-18T14:10:00Z",
  "verification_status": "PARTIALLY_VERIFIED",
  "event_status": "ANNOUNCED",
  "source_ids": ["src_00000000-0000-4000-8000-000000000001"],
  "evidence_ids": ["evd_00000000-0000-4000-8000-000000000001"],
  "observed_price_effect": {
    "direction": "UNKNOWN",
    "return_pct": null,
    "window_start": null,
    "window_end": null,
    "methodology_version": null
  },
  "duplicate_of": null,
  "notes": "Announcement verified as published; implementation and any causal price effect remain unverified."
}
```

El objeto `observed_price_effect` es descriptivo. Si no se ha ejecutado un cálculo con datos trazables, mantener sus métricas en `null`; no inferir un efecto solo por proximidad temporal.

## 10. Reglas de validación

- Rechazar registros sin identificador, versión de esquema, tipo de evento o timestamps obligatorios.
- Validar fechas como ISO 8601 UTC; `window_start` debe ser anterior a `window_end`.
- Verificar que cada ID referenciado exista y que las relaciones no creen referencias circulares inválidas.
- Restringir los estados y categorías a los valores controlados documentados.
- Si `verification_status = VERIFIED`, exigir evidencia suficiente y una nota del método de verificación; el estado no debe asignarse automáticamente por existir una fuente.
- Si hay conflicto entre fuentes, usar `DISPUTED` o `PARTIALLY_VERIFIED` según corresponda y registrar la evidencia contradictoria. No eliminar silenciosamente el desacuerdo.
- Marcar duplicados con `duplicate_of` y preservar los registros de origen; no fusionar fuentes independientes en una sola evidencia.
- No completar campos ausentes mediante inferencias sin etiquetarlas como estimaciones.
- Para observaciones cuantitativas, conservar dataset, unidad, ventana y versión de metodología.
- Los cambios de esquema incompatibles requieren un cambio de versión mayor; adiciones compatibles, versión menor; correcciones editoriales sin impacto semántico, versión de parche.

## 11. Conflictos, rumores y correcciones

1. Registrar rumores como afirmaciones no verificadas, con fuente y hora de captura.
2. Separar la existencia de una publicación de la verdad de lo que afirma.
3. Mantener evidencia que contradiga la hipótesis inicial; no seleccionar fuentes solo por coincidir con la conclusión.
4. Para una corrección, conservar el registro previo en el historial de cambios y documentar quién/cuándo/por qué se actualizó, usando las capacidades de auditoría disponibles.
5. Si una publicación desaparece o se edita, registrar la nueva captura y la diferencia observada; no dar por hecho el motivo.
6. Para fuentes sindicadas o republicaciones, identificar la fuente original cuando sea posible y evitar contar copias como corroboraciones independientes.

## 12. Seguridad, privacidad y retención

- No almacenar claves privadas, seed phrases, API keys, cookies de sesión ni credenciales.
- Evitar datos personales no necesarios; cumplir las políticas de retención y licencias aplicables.
- Restringir acceso a capturas privadas o material sujeto a derechos; conservar metadatos y extractos mínimos cuando proceda.
- El hash no sustituye controles de acceso, firma, auditoría ni verificación de autenticidad.
- Documentar la procedencia y los cambios sin exponer secretos en logs, commits o issues públicos.

## 13. Relación con la atribución

Este esquema prepara los insumos para el análisis, pero no determina la causa de un movimiento. La atribución debe realizarse en un registro separado que incluya hipótesis competidoras, ventanas de evento y mercado, retornos de referencia, factores de confusión, calidad de datos y nivel de confianza. Una asociación temporal aislada no debe etiquetarse como causalidad demostrada.

## 14. Evolución del esquema

- Mantener este documento como contrato de datos versionado.
- Cambiar `schema_version` cuando un registro use una nueva versión.
- Añadir migraciones o notas de compatibilidad cuando cambien nombres, tipos o valores controlados.
- Actualizar la documentación y los ejemplos en el mismo PR que modifica el esquema.
- Al integrar la taxonomía y la metodología de atribución, enlazar aquí sus rutas canónicas para evitar enlaces a ramas temporales.
