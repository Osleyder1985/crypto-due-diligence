# Documentation

Documentación metodológica y contratos de datos de CryptoDueDiligence.

## Methodology

- [Market Event Attribution](market-event-attribution.md): metodología para reconstruir movimientos históricos del precio y evaluar eventos potencialmente relacionados.
- [Crypto Market Event Taxonomy](crypto-market-event-taxonomy.md): categorías normalizadas para clasificar eventos sin presuponer causalidad.
- [Market Movement Detection](movement-detection.md): criterios reproducibles para detectar y delimitar movimientos de mercado.

## Data contracts

- [Evidence Schema](evidence-schema.md): definición documental de eventos, fuentes, evidencias y observaciones de mercado.
- [Executable Evidence JSON Schema](../schemas/evidence.schema.json): contrato estructural versionado 1.0.0.
- [Evidence schema tests](../tests/test_evidence_schema.py): pruebas automatizadas del contrato estructural.
- [Semantic evidence validation](evidence-validation.md): integridad referencial, IDs únicos y orden temporal de ventanas.
- [Semantic validation tests](../tests/test_evidence_semantics.py): pruebas automatizadas de las reglas semánticas.
- [Semantic validator implementation](../semantic_validation.py): validador determinista de colecciones de registros.

## Governance

La documentación y el código se modifican mediante Issues y Pull Requests. No se realizan cambios directamente en main. La validación estructural o semántica no demuestra autenticidad, veracidad ni causalidad.
