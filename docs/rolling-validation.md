# Validación rolling de memoria predictiva

## Objetivo

`rolling_validation.py` compara el clasificador direccional con la memoria persistente activada y desactivada, además de una referencia de momentum. Solo puntúa timestamps fuera de muestra que ambas variantes predijeron, para comparar los mismos resultados realizados.

## Ejecución

```sh
python rolling_validation.py SOL 2024-01-01 2025-01-01
python rolling_validation.py ETH 2023-01-01 2025-01-01 --interval 4h --lookback 24 --horizon 6 --min-train 100 --neighbors 15 --fold-size 240 --round-trip-fee-bps 20
```

La fecha final es inclusiva y las fechas se interpretan en UTC. El runner descarga velas spot de Binance para `TICKERUSDT` y guarda un JSON en `rolling_validations/`. La duración mínima depende de los parámetros; los periodos cortos se rechazan explícitamente.

## Controles temporales

- Cada fold tiene un tramo de calentamiento antes de su ventana de prueba.
- La memoria de cada fold se construye solo con velas anteriores al inicio de ese calentamiento.
- Las etiquetas de entrenamiento deben haber madurado en el timestamp de predicción.
- Ambas variantes deben coincidir en timestamp y retorno observado para incluir una predicción en la comparación.
- Se informa exactitud direccional, exactitud balanceada, rendimiento compuesto neto estimado y la diferencia memoria menos no-memoria.

## Interpretación y límites

Un delta positivo favorece a la memoria en esa métrica dentro de la muestra histórica; uno negativo la perjudica. Un solo activo o período no demuestra una ventaja. Repetir la evaluación en activos, regímenes e intervalos no usados para diseñar el método, y reservar un período final intacto.

La comisión round-trip es un supuesto simplificado. No se incluyen spread, slippage, latencia, liquidez, impacto de mercado ni impuestos. Esto es simulación histórica, no una garantía de rentabilidad, recomendación financiera, explicación causal ni probabilidad calibrada.

## Pruebas

```sh
python -m unittest discover -s tests -v
```

Las pruebas usan velas sintéticas deterministas y no requieren conexión de red.
