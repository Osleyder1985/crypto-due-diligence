# Investigación autónoma por moneda y período

## Uso

Con Python 3.10+:

~~~sh
python -m pip install "jsonschema>=4.18,<5"
python autonomous_research.py SOL 2025-01-01 2025-01-07
~~~

Solo se requieren ticker, fecha inicial y fecha final. Las fechas usan UTC y la fecha final es inclusiva. Por defecto el sistema consulta velas spot de Binance contra USDT, usa velas de una hora e intenta comparar el rendimiento con BTC.

~~~sh
python autonomous_research.py ETH 2025-01-01 2025-01-03 --interval 15m
~~~

Intervalos admitidos: 1m, 5m, 15m, 30m, 1h, 4h y 1d. El informe Markdown y el registro JSON se escriben en research_runs/; los casos se agregan a data/historical_cases.json.

## Qué recopila y documenta

- Datos de velas OHLCV del endpoint público de Binance para el par TICKERUSDT.
- Retorno observado, extremos, volumen, huecos detectables y comparación con BTC cuando está disponible.
- Coincidencias literales del ticker en feeds RSS/Atom públicos configurados en autonomous_research.py, dentro de la ventana de publicación solicitada.
- Una búsqueda RSS de Google News con el ticker y las fechas solicitadas para ampliar la detección de noticias históricas.
- Errores de feeds, enlaces, fechas y estado de verificación de las evidencias.
- Casos históricos similares y resúmenes de casos revisados elegibles.
- Una señal direccional experimental para el horizonte de seis velas y métricas de evaluación walk-forward frente a una línea base de momentum, si el periodo contiene suficientes velas.
- Memoria persistente de retornos observados para que ejecuciones posteriores reutilicen ejemplos maduros del mismo activo e intervalo.

## Límites importantes

La cobertura RSS y de Google News es incompleta; la búsqueda actual detecta menciones literales del ticker, no una búsqueda semántica de todo Internet ni todos los alias de un activo. Los símbolos cortos pueden producir falsos positivos; las noticias deben revisarse y contrastarse con fuentes primarias. El proveedor de precios es Binance spot y el par por defecto es TICKERUSDT; no se cambia de proveedor silenciosamente. El endpoint público puede limitar peticiones o no ofrecer el activo. Las entradas de feeds se marcan como no verificadas: coincidencia temporal o textual no demuestra causalidad.

Cada ejecución se guarda inicialmente como caso DRAFT, UNVERIFIED, con resultado UNKNOWN. Por separado, los retornos de mercado ya observados se guardan en data/prediction_memory.json para aprendizaje direccional entre ejecuciones; no se usan etiquetas causales sin verificar. Esos casos no participan en resúmenes de aprendizaje causal hasta que un analista revise fuentes y registre un resultado verificado. El informe ahora incluye una señal direccional experimental basada en patrones históricos de precio/volumen y evaluación walk-forward, si hay datos suficientes. La proporción de votos de vecinos no es una probabilidad calibrada ni una garantía. No usar fixtures sintéticas como historia real de mercado.

Para evaluar predicciones en el futuro se necesitarán resultados posteriores definidos de antemano, un conjunto de casos revisados, validación temporal fuera de muestra, comparación con líneas base y calibración. No se deben convertir asociaciones históricas en afirmaciones causales. La señal direccional y la explicación causal son tareas distintas: la primera estima la dirección de un horizonte; la segunda requiere evidencia revisada.

## Pruebas sin red

~~~sh
python -m unittest discover -s tests -v
python research_pipeline.py validate-fixtures
~~~

Las pruebas usan respuestas simuladas; no necesitan acceso a Binance ni a los feeds.
