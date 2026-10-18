# Documentation

Documentación metodológica y contratos de datos de CryptoDueDiligence.

## Methodology

- [Market Event Attribution](market-event-attribution.md): metodología para reconstruir movimientos históricos del precio y evaluar eventos potencialmente relacionados.
- [Crypto Market Event Taxonomy](crypto-market-event-taxonomy.md): categorías normalizadas para clasificar eventos sin presuponer causalidad.
- [Market Movement Detection](movement-detection.md): criterios reproducibles para detectar y delimitar movimientos de mercado.
- [End-to-end research pipeline](research-pipeline.md): fixtures, validación integral, detección OHLCV, captura de fuentes y evaluación de hipótesis.
- [Aprendizaje histórico controlado](historical-learning.md): memoria versionada de casos revisados, búsqueda explicable de precedentes y resúmenes descriptivos.
- [Investigación autónoma por moneda y período](autonomous-research.md): consulta de mercado, recopilación de feeds, informe y registro de casos.
- [Evaluación temporal de predicciones](prediction-evaluation.md): evaluación walk-forward sin fuga temporal y comparación con una línea base de momentum.
- [Memoria persistente de resultados](prediction-memory.md): conserva retornos observados y reutiliza ejemplos maduros de investigaciones anteriores.

## Data contracts

- [Evidence Schema](evidence-schema.md): definición documental de eventos, fuentes, evidencias y observaciones de mercado.
- [Executable Evidence JSON Schema](../schemas/evidence.schema.json): contrato estructural versionado 1.0.0.
- [Historical case JSON Schema](../schemas/historical-case.schema.json): contrato versionado para la memoria histórica.
- [Historical learning tests](../tests/test_historical_learning.py): pruebas de almacenamiento, elegibilidad y recuperación de casos.
- [Evidence schema tests](../tests/test_evidence_schema.py): pruebas automatizadas del contrato estructural.
- [Semantic evidence validation](evidence-validation.md): integridad referencial, IDs únicos y orden temporal de ventanas.
- [Semantic validation tests](../tests/test_evidence_semantics.py): pruebas automatizadas de las reglas semánticas.
- [Semantic validator implementation](../semantic_validation.py): validador determinista de colecciones de registros.
- [Research pipeline entry point](../research_pipeline.py): valida registros estructuralmente y luego semánticamente.
- [Autonomous research entry point](../autonomous_research.py): investiga un ticker en un intervalo UTC y conserva un caso preliminar.
- [Prediction evaluation entry point](../prediction_evaluation.py): compara un clasificador experimental con momentum en una evaluación temporal.
- [Persistent prediction memory](../prediction_memory.py): almacena ejemplos de retorno futuro con filtros temporales e idempotencia.
- [Research fixtures](../fixtures/research/): casos sintéticos completos, contradictorios y con datos insuficientes.

## Running checks

\`\`\`sh
python -m pip install "jsonschema>=4.18,<5"
python research_pipeline.py validate-fixtures
python -m unittest discover -s tests -v
\`\`\`

## Governance

La documentación y el código se modifican mediante Issues y Pull Requests. No se realizan cambios directamente en main. La validación estructural o semántica no demuestra autenticidad, veracidad ni causalidad.
