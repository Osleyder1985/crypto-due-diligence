# Aprendizaje histórico controlado

## Objetivo

El módulo `historical_learning.py` añade una memoria de casos versionada y reproducible a la metodología de investigación. Permite guardar investigaciones revisadas, recuperar precedentes descriptivamente similares y resumir etiquetas de resultados por categoría de evento.

No es un modelo causal, un predictor de precios ni un sistema de reentrenamiento automático.

## Registro de un caso

Cada caso debe seguir el contrato `schemas/historical-case.schema.json` (versión `1.0.0`). Incluye activo, tipo de evento, hora de detección UTC, ventana de movimiento, dirección y retorno observados, factores candidatos, referencias de evidencia, etiqueta de resultado, estado de revisión, estado de verificación y versión de metodología.

Etiquetas permitidas:
- `SUPPORTED`: la hipótesis fue respaldada por evidencia revisada.
- `PARTIALLY_SUPPORTED`: solo parte de la explicación recibió respaldo.
- `CONTRADICTED`: la hipótesis fue contradicha por la revisión.
- `MULTIPLE_FACTORS`: la revisión encontró varios factores respaldados, sin asignar una causa única.
- `UNKNOWN` / `INSUFFICIENT_EVIDENCE`: no existe conclusión suficiente; se conservan, pero no entran en los resúmenes de aprendizaje.

Solo casos con `review_status=REVIEWED`, `verification_status=VERIFIED` o `PARTIALLY_VERIFIED`, y una etiqueta de resultado resuelta se consideran elegibles para resúmenes. La elegibilidad no significa que se haya demostrado causalidad.

## API y persistencia

```python
from historical_learning import save_case, load_cases, find_similar_cases, summarize_outcomes

save_case("data/historical_cases.json", case_record)
cases = load_cases("data/historical_cases.json")
precedents = find_similar_cases(new_case, cases, limit=5)
summary = summarize_outcomes(cases)
```

El archivo persistente es JSON versionado. `save_case` valida cada registro, rechaza IDs duplicados y utiliza reemplazo atómico para reducir el riesgo de corrupción durante la escritura. No se incluye concurrencia multiusuario ni almacenamiento transaccional; para varios procesos o despliegue de producción debe migrarse a una base de datos con restricciones únicas y auditoría.

La búsqueda de similitud utiliza reglas deterministas y explicables: mismo tipo de evento, misma dirección de movimiento y factores candidatos compartidos. La puntuación solo ordena precedentes; **no** es una probabilidad de que la misma causa explique el nuevo movimiento.

Los resúmenes muestran tamaños de muestra y conteos de etiquetas revisadas. No calculan probabilidades causales, rendimientos esperados ni pronósticos. Los casos no resueltos o no verificados quedan excluidos de los conteos elegibles, pero permanecen en el archivo.

## Validación

```sh
python -m unittest discover -s tests -v
python research_pipeline.py validate-fixtures
```

## Próximas etapas antes de aprendizaje automático

1. Crear un conjunto de casos históricos con revisión y procedencia verificables.
2. Definir criterios consistentes entre analistas y resolver desacuerdos.
3. Medir métricas en periodos posteriores no utilizados durante el desarrollo (evaluación temporal fuera de muestra).
4. Comparar contra una línea base simple y vigilar cambios de régimen, falsos positivos y sesgos de selección.
5. Solo entonces evaluar un modelo supervisado; versionar datos, variables, código y modelo, y exigir validación antes de desplegar actualizaciones.

No se deben usar las fixtures sintéticas del pipeline como historia de mercado ni convertir asociaciones descriptivas en afirmaciones de causalidad.
