# Evaluación temporal de predicciones

## Propósito

prediction_evaluation.py es una primera prueba controlada para medir si los patrones recientes de precio/volumen aportan señal direccional fuera de muestra. No es un sistema de trading ni una promesa de rentabilidad. Separa el aprendizaje de dirección futura de las etiquetas sobre qué causó un movimiento pasado.

## Ejecución

~~~sh
python -m pip install "jsonschema>=4.18,<5"
python prediction_evaluation.py SOL 2025-01-01 2025-02-01
~~~

La fecha final es inclusiva y las fechas se interpretan en UTC. Por defecto usa velas spot de una hora de Binance para TICKERUSDT, ventana de 24 velas, horizonte de seis velas, al menos 100 ejemplos históricos maduros y 15 vecinos. Guarda métricas y predicciones individuales en prediction_evaluations/.

~~~sh
python prediction_evaluation.py ETH 2025-01-01 2025-03-01 --interval 4h --lookback 24 --horizon 6 --min-train 100 --neighbors 15 --round-trip-fee-bps 20
~~~

## Metodología

- Cada muestra usa retornos pasados a 1, 6 y lookback velas y volumen relativo calculados hasta el instante de predicción.
- El clasificador k-nearest neighbors compara la muestra con patrones anteriores. Un patrón histórico solo puede entrar en entrenamiento si su horizonte futuro completo ya había terminado antes de la predicción actual.
- El informe compara el clasificador con una línea base de momentum que usa el retorno retrospectivo de lookback velas.
- Informa tamaño de muestra, exactitud direccional, exactitud balanceada y rendimiento hipotético compuesto tras una comisión configurable de ida y vuelta.
- Cada predicción conserva la hora de la etiqueta de entrenamiento más reciente; una guarda de ejecución rechaza cualquier fuga temporal.

## Cómo interpretar el resultado

No basta con superar el 50% de aciertos. La exactitud depende del balance de clases y no implica rentabilidad. Compara el modelo con la línea base, rendimiento neto de costes, tamaño de muestra y periodos independientes. El cálculo de costes actual es simplificado y no incorpora spread, slippage, funding, latencia, impuestos, liquidez o impacto de mercado.

Esta versión no hace ajuste de hiperparámetros, selección de modelo ni validación de varios regímenes independientes. Debe considerarse experimental hasta superar pruebas fuera de muestra en activos y periodos que no se hayan usado para diseñar el método. No operar con capital real basándose únicamente en este informe.

## Pruebas

~~~sh
python -m unittest discover -s tests -v
python research_pipeline.py validate-fixtures
~~~

Las pruebas usan velas sintéticas deterministas y no necesitan acceso a Internet.
