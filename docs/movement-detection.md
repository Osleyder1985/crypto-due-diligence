# Detección de movimientos relevantes del mercado cripto

## 1. Propósito y límites

Este documento establece un procedimiento reproducible para identificar movimientos de precio y condiciones de mercado que merecen investigación. La detección responde a **qué se movió, cuánto, cuándo y bajo qué condiciones de mercado**. No determina por qué ocurrió el movimiento, ni predice su continuación.

Una alerta no es una recomendación de compra o venta. Tampoco demuestra que una noticia, una transacción on-chain o una decisión de un actor concreto haya causado el movimiento. La atribución requiere un proceso separado, evidencia trazable e hipótesis alternativas.

## 2. Etapas del proceso

1. **Ingesta:** recuperar velas y, cuando estén disponibles, volumen, operaciones, bid-ask, profundidad, métricas de derivados y benchmarks.
2. **Validación:** comprobar timestamps, duplicados, huecos, unidades, símbolos, venue, moneda de cotización y coherencia OHLCV.
3. **Construcción de métricas:** calcular retornos, volatilidad, volumen relativo y rendimiento frente al mercado de referencia.
4. **Detección:** aplicar reglas configuradas y guardar qué reglas dispararon la alerta.
5. **Agrupación:** combinar señales correlacionadas en un mismo episodio para evitar contar repetidamente la misma oscilación.
6. **Contextualización:** registrar condiciones del mercado general y calidad/cobertura de datos.
7. **Traspaso a investigación:** asociar el episodio con el flujo de cronología, fuentes y atribución; mantener la causa como desconocida hasta que exista evidencia suficiente.

## 3. Datos mínimos y control de calidad

Para cada serie conservar:

- Identidad canónica del activo y, por separado, el ticker observado.
- Exchange, proveedor o dataset; par de negociación y moneda de cotización.
- Intervalo de la vela y zona horaria de origen.
- Timestamp de apertura/cierre de la vela y timestamp de ingesta.
- Precio de apertura, máximo, mínimo, cierre y volumen; documentar si el volumen es base, cotizado o número de contratos.
- Política de ajuste y tratamiento de velas incompletas.
- Versión del extractor, parámetros y momento de cálculo.

### Reglas de calidad

- Rechazar o marcar timestamps no monotónicos, velas duplicadas y velas con valores imposibles, como máximo inferior al mínimo.
- Detectar huecos temporales; no interpolarlos silenciosamente para activar alertas.
- No mezclar pares, unidades o monedas de cotización sin conversión explícita y trazable.
- Identificar mercados con volumen artificial, liquidez insuficiente, spreads extremos o datos de cobertura limitada.
- Excluir velas aún abiertas de los cálculos que requieran velas cerradas, salvo que la señal esté diseñada explícitamente para tiempo real y etiquetada como provisional.
- Marcar discrepancias entre venues. Un precio extremo de un único exchange no debe asumirse automáticamente como precio representativo del mercado.
- Mantener un registro de la razón por la que cada serie se acepta, degrada o rechaza.

Si falla un control crítico, la salida debe ser `INVALID_DATA` o `INSUFFICIENT_COVERAGE`, no una alerta normal.

## 4. Métricas básicas

Sea (P_t) el precio de cierre de una vela válida en el tiempo (t), y (P_{t-k}) el precio de cierre (k) intervalos antes.

### Retorno simple

`return_pct = 100 * (P_t / P_{t-k} - 1)`

Usar una ventana explícita —por ejemplo, 15 minutos, 1 hora, 24 horas o 7 días— según la frecuencia de los datos y el propósito del sistema. Los ejemplos son opciones de configuración, no ventanas universalmente óptimas.

### Retorno logarítmico

`log_return = ln(P_t / P_{t-k})`

Es útil para sumar retornos logarítmicos en el tiempo y para análisis estadístico. Documentar la convención utilizada; no mezclar retornos simples y logarítmicos en comparaciones sin conversión.

### Volatilidad realizada

Calcular la desviación estándar de retornos de intervalo dentro de una ventana definida. Si se anualiza, documentar la frecuencia y el factor de anualización. La anualización no debe aplicarse mecánicamente a datos irregulares o con huecos.

### Volumen relativo

`relative_volume = volume_current_window / median(volume_baseline_windows)`

La ventana actual debe compararse con ventanas históricas equivalentes y válidas. Para patrones intradía, comparar con periodos de hora/día similares cuando el dataset permita hacerlo. Si la mediana base es cero o no hay suficientes observaciones, la métrica es inválida.

### Rendimiento relativo al benchmark

`relative_return_pct = asset_return_pct - benchmark_return_pct`

Definir el benchmark y su fuente (por ejemplo, BTC, ETH o un índice de mercado). Este cálculo ayuda a separar movimientos específicos del activo de movimientos generales, pero no elimina todos los factores de confusión.

### Liquidez y microestructura

Cuando existan datos de calidad, considerar spread relativo, profundidad disponible a distancias definidas del mid-price, deslizamiento estimado y concentración de volumen por venue. Las cifras deben incluir mercado, timestamp y método. El volumen agregado por sí solo no demuestra que sea posible ejecutar una orden al precio mostrado.

## 5. Baselines y umbrales

No existe un umbral universal que defina un movimiento anómalo para todos los criptoactivos. Un retorno del 5 % puede ser excepcional en un activo líquido y habitual en un activo de alta volatilidad.

Toda regla de detección debe registrar:

- Métrica y dirección evaluada.
- Ventana actual y frecuencia de muestreo.
- Periodo de baseline y número mínimo de observaciones válidas.
- Método estadístico y umbral.
- Segmentación por activo, liquidez, venue o régimen de volatilidad.
- Fecha y dataset utilizados para calibrar el umbral.
- Política de actualización del baseline.

### Métodos admisibles

- **Umbral absoluto:** fácil de interpretar, pero debe calibrarse por clase de activo y horizonte.
- **Cuantil histórico:** alerta cuando la métrica supera un percentil elegido de su distribución histórica.
- **Puntuación estandarizada robusta:** comparar la observación con una mediana y una estimación robusta de dispersión, como MAD, si la muestra es suficiente y no degenerada.
- **Umbral ajustado por volatilidad:** escalar el retorno por una estimación de volatilidad calculada solo con información disponible antes del momento evaluado.
- **Desviación respecto al mercado:** evaluar el retorno relativo a un benchmark, manteniendo visibles tanto el retorno bruto como el relativo.

Evitar calibrar y evaluar con el mismo periodo sin separación temporal. Los umbrales deben validarse fuera de muestra y volver a evaluarse cuando cambien la liquidez, la cobertura o el régimen de mercado.

## 6. Familias de señales

Las siguientes familias pueden combinarse. Cada señal debe tener un identificador de regla y sus propios parámetros.

| Familia | Disparador posible | Requisitos y límites |
|---|---|---|
| Retorno extremo | Retorno absoluto o relativo supera un umbral calibrado | Precios válidos y ventana cerrada o señal provisional explícita. |
| Aceleración | Retorno reciente difiere significativamente de ventanas previas | Definir la referencia; ventanas solapadas pueden generar señales redundantes. |
| Volatilidad | Volatilidad realizada excede su baseline | Muestra suficiente y frecuencia estable. |
| Volumen anómalo | Volumen relativo supera el umbral | Tipo de volumen consistente y control de volumen artificial. |
| Dislocación entre venues | Diferencia de precio o spread entre venues supera un límite | Timestamps sincronizados, pares comparables y costes de arbitraje considerados. |
| Movimiento relativo | Retorno del activo diverge del benchmark | Benchmark documentado y alineación temporal. |
| Evento de microestructura | Spread se amplía o profundidad cae abruptamente | Datos de libro de órdenes suficientemente completos y frecuentes. |
| Derivados | Cambio inusual en open interest, funding o liquidaciones | Contratos, unidades, venue y timestamps comparables; cobertura incompleta debe declararse. |

No exigir que todas las familias estén disponibles para todos los activos. Una ausencia de datos no equivale a ausencia de señal.

## 7. Configuración reproducible de ejemplo

La siguiente configuración es ilustrativa; sus umbrales no deben emplearse en producción sin calibración y evaluación.

```yaml
config_version: "1.0.0"
asset_id: "chain:example-network:asset:example-token"
market_data:
  source: "example-provider"
  venue: "example-venue"
  pair: "EXM-USD"
  interval: "5m"
  use_closed_candles: true
quality:
  min_valid_baseline_observations: 500
  max_missing_interval_ratio: 0.01
  reject_duplicate_candles: true
  reject_incomplete_candles: true
signals:
  - rule_id: "RETURN_1H_ABSOLUTE"
    metric: "return_pct"
    window: "1h"
    baseline_window: "90d"
    threshold_method: "historical_quantile"
    quantile: 0.995
    direction: "absolute"
  - rule_id: "VOLUME_1H_RELATIVE"
    metric: "relative_volume"
    window: "1h"
    baseline_window: "30d"
    threshold_method: "historical_quantile"
    quantile: 0.99
    direction: "upper"
benchmarks:
  - asset_id: "benchmark:btc"
    metric: "relative_return_pct"
reporting:
  group_correlation_window: "30m"
  retain_rule_parameters: true
  retain_input_data_references: true
```

Los valores de cuantil, ventanas y controles son solo demostrativos. La calibración final debe considerar costes de datos, cobertura, frecuencia de alertas, falsas alarmas y capacidad operativa de investigación.

## 8. Pseudocódigo del flujo

```text
for each asset and evaluation_time:
    series = load_data(asset, evaluation_time)
    quality = validate(series)

    if quality.critical_failure:
        emit_status(INVALID_DATA, quality.reasons)
        continue

    metrics = calculate_metrics(
        valid_closed_candles=series,
        config=versioned_config,
        information_cutoff=evaluation_time
    )

    fired_rules = apply_calibrated_rules(metrics)

    if fired_rules is empty:
        continue

    episode = group_correlated_signals(
        asset=asset,
        time=evaluation_time,
        rules=fired_rules
    )

    save_detection(
        episode=episode,
        metrics=metrics,
        quality=quality,
        data_references=series.references,
        config_version=versioned_config.version,
        detected_at=evaluation_time
    )

    route_to_investigation(episode)
```

La implementación debe evitar que el cálculo use observaciones posteriores al momento de detección. Si los datos se corrigen retrospectivamente, conservar tanto el resultado original como la versión recalculada y su motivo.

## 9. Agrupación y clasificación del episodio

Varias reglas pueden dispararse por el mismo movimiento. Para no inflar el número de eventos:

- Agrupar señales del mismo activo cuyas ventanas se solapen según una política configurada.
- Conservar cada regla disparada; agrupar no debe borrar la procedencia de la señal.
- Mantener separados episodios de activos distintos salvo que exista una regla explícita de evento de mercado general.
- Registrar dirección observada —alcista, bajista, mixta o indeterminada— sin asignarle significado positivo o negativo para la inversión.
- Permitir estados como `DETECTED`, `UNDER_REVIEW`, `INVALIDATED` y `CLOSED`, diferenciados del estado de verificación del evento externo.
- Registrar una razón de cierre: datos inválidos, señal revertida, duplicado, revisión completada u otra categoría definida.

Una señal basada en retorno y otra basada en volatilidad pueden estar describiendo el mismo episodio; no deben contarse como dos causas independientes.

## 10. Evaluación del detector

Medir, como mínimo:

- **Tasa de falsas alarmas:** alertas que no cumplen la definición operativa de un movimiento relevante después de revisión.
- **Precisión y recall:** cuando exista una etiqueta de referencia confiable y una definición explícita de evento.
- **Frecuencia de alertas:** por activo, venue, regla y periodo.
- **Latencia de detección:** diferencia entre el inicio observable del movimiento y el momento de emisión.
- **Estabilidad:** cambios de desempeño por activo, liquidez y régimen de mercado.
- **Cobertura:** porcentaje de periodos elegibles con datos suficientes.
- **Coste operativo:** proporción de alertas que requieren revisión manual y tiempo de resolución.

Definir el criterio de relevancia antes de medir precisión/recall. Si las etiquetas de referencia son subjetivas o incompletas, declararlo y evitar presentar las métricas como objetivas. Una menor tasa de alertas no es necesariamente mejor si aumenta el número de movimientos importantes que pasan inadvertidos.

## 11. Sesgos y controles

- **Look-ahead bias:** calcular cada señal usando solo datos disponibles en el momento evaluado, incluidos retrasos reales de publicación e ingesta.
- **Survivorship bias:** conservar activos retirados, fallidos o deslistados cuando el objetivo sea evaluar históricamente el universo de activos.
- **Selection bias:** documentar cómo se seleccionan activos, venues, ventanas y eventos revisados.
- **Data snooping:** separar periodos de calibración, validación y evaluación final; registrar intentos y versiones de reglas.
- **Dependencia entre señales:** considerar autocorrelación, ventanas solapadas y múltiples pruebas al evaluar falsas alarmas.
- **Sesgo de venue:** no asumir que un exchange representa el mercado global.
- **Sesgo de liquidez:** los umbrales pueden funcionar de forma distinta en mercados profundos y poco líquidos.
- **Sesgo retrospectivo:** no usar el conocimiento posterior para describir qué era observable durante la señal original.

## 12. Registro de detección

Cada episodio debe conservar, al menos:

- `detection_id`, `asset_id`, venue/dataset y par.
- `detected_at`, `window_start` y `window_end` en UTC.
- Métricas calculadas, unidades y benchmark.
- Reglas disparadas y sus parámetros exactos.
- Versión de configuración, código y proveedor/dataset.
- Resultado de validación de calidad y advertencias.
- Referencias a datos de entrada o identificadores de observación.
- Estado de revisión, agrupación y motivo de cierre.
- Incertidumbres y limitaciones conocidas.

No sobrescribir silenciosamente una detección si el proveedor corrige datos. Registrar la nueva versión y permitir comparar el resultado original con el recalculado.

## 13. Relación con la investigación de eventos

Tras detectar un episodio, el investigador puede buscar anuncios, cambios de tokenomics, incidentes de seguridad, actividad on-chain, cambios de derivados, factores macroeconómicos y explicaciones alternativas. La búsqueda debe cubrir el periodo previo, durante y posterior al movimiento, con timestamps de publicación y captura separados.

La falta de una noticia identificada no prueba manipulación ni una causa oculta. Una noticia publicada después del inicio del movimiento no debe tratarse como causa inicial sin evidencia adicional. Eventos simultáneos deben permanecer como hipótesis competidoras cuando los datos no permitan distinguir sus efectos.

## 14. Gobernanza de cambios

- Versionar configuración, código, fuentes y reglas.
- Cambiar los umbrales mediante una modificación revisable y con justificación.
- Registrar resultados de backtesting, falsos positivos conocidos y limitaciones.
- Recalibrar con periodos históricos definidos y validar fuera de muestra.
- No presentar resultados de backtesting como garantía de desempeño futuro.
- Mantener separados los módulos de detección, clasificación de eventos y atribución causal.

Este documento describe una metodología interna del proyecto; no es una norma ISO ni una garantía de rendimiento de inversión.
