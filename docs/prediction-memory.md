# Memoria persistente de resultados de mercado

## Propósito

prediction_memory.py guarda ejemplos derivados de velas reales para que una ejecución posterior pueda reutilizar experiencias anteriores del mismo activo e intervalo. Cada ejemplo conserva los factores numéricos observados antes del movimiento y el retorno que ocurrió durante el horizonte posterior.

La memoria direccional es distinta de la memoria causal: conocer el retorno futuro de una vela es una observación de mercado, pero no demuestra qué noticia o evento lo causó.

## Almacenamiento

Por defecto, el sistema guarda los ejemplos en data/prediction_memory.json. El archivo contiene una versión de esquema, activo, intervalo, lookback, horizonte, hora de la muestra, hora en que maduró su resultado, variables, retorno realizado y dirección observada. La clave idempotente evita duplicar una muestra cuando se vuelve a investigar un periodo.

~~~sh
python autonomous_research.py SOL 2025-01-01 2025-01-07
~~~

Se puede cambiar la ubicación con --prediction-memory-path. Las muestras de una ejecución solo se incorporan después de calcular la señal y la evaluación de esa ejecución.

## Barreras contra fuga temporal

- Solo se reutilizan ejemplos del mismo activo, intervalo, lookback y horizonte.
- La muestra histórica debe comenzar antes de la ventana que se está evaluando.
- El resultado futuro de esa muestra debe haber madurado antes del timestamp de predicción.
- Las evaluaciones walk-forward vuelven a comprobar el corte temporal para cada predicción.
- Los archivos malformados se reportan; el sistema no los sobrescribe silenciosamente.

## Límites

La memoria aprende asociaciones de precio/volumen, no causas verificadas. La calidad depende del proveedor, de la ventana y de la cobertura histórica. Los cambios de régimen, costes de ejecución, liquidez, spread, slippage y selección de activos pueden invalidar los patrones. Los ejemplos almacenados no son garantía de que una dirección se repita y no deben interpretarse como probabilidades calibradas.

La memoria causal de investigaciones sigue en estado DRAFT/UNVERIFIED hasta revisión; no se mezclan etiquetas causales no verificadas con resultados direccionales observados.
