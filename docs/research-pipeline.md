# Pipeline de investigación end-to-end

## Componentes y versiones

- Contrato de registros: `schemas/evidence.schema.json` (schema `1.0.0`).
- Validador de colección: `research_pipeline.py` (pipeline `1.0.0`).
- Detección OHLCV: `movement_detection.py` (metodología `1.0.0`).
- Captura HTTP de evidencia: `evidence_collector.py` (collector `1.0.0`).
- Evaluación de hipótesis: `hypothesis_evaluation.py` (evaluator `1.0.0`).

## Validar fixtures

Instalar la dependencia existente para validar JSON Schema y ejecutar todos los tests:

```sh
python -m pip install "jsonschema>=4.18,<5"
python research_pipeline.py validate-fixtures
python -m unittest discover -s tests -v
```

Validar una fixture individual:

```sh
python research_pipeline.py validate fixtures/research/supporting_evidence.json
```

El punto de entrada valida primero cada sobre con JSON Schema Draft 2020-12 y comprobador de formatos; si hay errores estructurales, no ejecuta la fase semántica. Después comprueba IDs únicos, referencias entre registros y ventanas temporales.

## Fixtures

`fixtures/research/` contiene casos sintéticos explícitamente marcados:
- `supporting_evidence.json`: registro completo de evento, fuente, evidencia y observaciones.
- `contradictory_evidence.json`: rumor corregido/refutado y reacción de mercado no material.
- `insufficient_data.json`: rumor no verificado sin medición de precio suficiente.

Los timestamps, activos, URLs y cifras de estos casos son ilustrativos. No son datos históricos ni deben citarse como sucesos reales.

## Motor de detección

La función `detect_movements(rows, config, benchmark_rows=None)` recibe velas OHLCV ya obtenidas por el usuario o por un proveedor. No realiza descarga de precios. Requiere timestamps UTC ascendentes y campos `timestamp, open, high, low, close, volume`. La configuración queda incluida en cada alerta. Detecta retorno de una vela frente a la anterior y volumen relativo respecto a la mediana de las velas previas. Dispara alerta cuando cruza el umbral absoluto de retorno o el de volumen relativo con retorno no nulo. Si se facilitan velas de benchmark con timestamps coincidentes, informa retorno relativo.

Los umbrales por defecto son demostrativos, no universales ni calibrados para operar. El motor informa `INVALID_DATA`, `INSUFFICIENT_COVERAGE`, `NO_ALERTS` o `ALERTS`. No decide la causa del movimiento. La validación de velas detecta datos básicos inválidos, pero la completitud de la serie, las lagunas del calendario de mercado y la representatividad del proveedor requieren controles específicos del dataset.

## Captura de fuentes

`collect_url(...)` realiza una petición HTTP(S) explícita a una URL pública y devuelve registros Source y Evidence, timestamp de captura, URL original, URL final, hash SHA-256, tipo de contenido, estado HTTP y metadata Last-Modified. El campo `published_at` solo se rellena con el timestamp de publicación original proporcionado por el llamador; Last-Modified se conserva como metadata de transporte y no se equipara a la fecha original de publicación.

La captura es opt-in: no hay crawler programado ni consulta automática de redes sociales. No se descargan datos de mercado automáticamente, no se requieren credenciales y el contenido no se persiste como archivo. Los cuerpos grandes se rechazan por límite de bytes. El hash sirve para comparar los bytes capturados, no para demostrar quién publicó el contenido o que sea verdadero. El análisis de HTML, RSS/Atom, autenticación, políticas de acceso y licencias debe añadirse por proveedor antes de producción.

## Evaluación de hipótesis

`evaluate_hypotheses(hypotheses, envelopes, market_context=None)` consume IDs de evidencia explícitos por hipótesis: `supporting_evidence_ids`, `contradicting_evidence_ids` y `contextual_evidence_ids`. Considera la evidencia relevante que esté marcada `VERIFIED` o `PARTIALLY_VERIFIED` y cuyo rol corresponda. Devuelve `EVIDENCE_FAVORS`, `EVIDENCE_AGAINST` o `INCONCLUSIVE`; nunca calcula probabilidad causal.

La función no descubre hipótesis, no prueba independencia entre fuentes ni decide automáticamente si la verificación es apropiada. El analista debe evitar contar como independientes artículos que repiten una misma fuente primaria y documentar explicaciones alternativas y evidencia contradictoria. `market_context` se adjunta al resultado para auditoría, pero no se transforma en una puntuación causal.

## Límites de producción

Este PR proporciona componentes deterministas y contratos de integración, no una plataforma autónoma de investigación. No incluye scheduler, almacenamiento persistente, APIs comerciales, conectores autenticados, proveedor de datos de mercado ni modelo causal validado. Los resultados deben revisarse por un analista y las configuraciones calibrarse y evaluarse fuera de muestra antes de cualquier uso operacional.
