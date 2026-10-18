# Validación semántica e integridad de registros

## Propósito

El contrato JSON Schema de [evidence.schema.json](../schemas/evidence.schema.json) valida la estructura de cada registro individualmente. La validación semántica complementa ese contrato al revisar una colección completa.

## Qué valida

El módulo [semantic_validation.py](../semantic_validation.py) expone la función validate_record_collection(envelopes), que devuelve una lista de errores; una lista vacía indica que no detectó infracciones dentro de su alcance.

- **Unicidad de IDs:** los identificadores de Event, Source, Evidence y MarketObservation no deben repetirse.
- **Referencias de Event:** cada ID de source_ids debe corresponder a un Source existente y cada ID de evidence_ids a un Evidence existente.
- **Referencias de Evidence:** source_id debe corresponder a un Source existente.
- **Ventanas temporales:** window_start debe ser estrictamente anterior a window_end en MarketObservation y en observed_price_effect cuando ambos límites están presentes.

La función espera sobres con schema_version, record_type y record. Primero se debe validar cada sobre contra el JSON Schema; la validación semántica no reemplaza la validación estructural.

## Ejecutar las pruebas

Con Python 3.12 o compatible y la dependencia jsonschema instalada:

```sh
python -m pip install "jsonschema>=4.18,<5"
python -m unittest discover -s tests -v
```

Las pruebas de contrato y las semánticas se ejecutan con el mismo comando y están integradas en el workflow [Validate evidence JSON Schema](../.github/workflows/validate-evidence-schema.yml).

## Límites

- Las referencias se comprueban dentro de la colección proporcionada; no se consulta una base de datos ni un servicio externo.
- No se valida autenticidad, integridad criptográfica, veracidad de afirmaciones ni existencia de activos en proveedores externos.
- No se infiere causalidad entre eventos y movimientos de mercado.
- Las ventanas con límites nulos se omiten en la comparación temporal; campos requeridos y formatos se deben validar antes con JSON Schema.
- La función devuelve errores deterministas, pero no corrige ni modifica registros de entrada.
