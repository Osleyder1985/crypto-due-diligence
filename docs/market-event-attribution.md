# Market Event Attribution

## 1. Propósito

Este documento define una metodología de investigación retrospectiva para estudiar movimientos relevantes del precio de un criptoactivo y evaluar qué noticias, eventos, condiciones de mercado o factores on-chain podrían estar relacionados con ellos.

El objetivo no es asignar una causa automáticamente ni predecir con certeza el precio futuro. El objetivo es producir conclusiones trazables, reproducibles y proporcionales a la evidencia disponible.

## 2. Alcance

La investigación puede abarcar:

- Inicio, continuación, agotamiento y reversión de movimientos alcistas.
- Inicio, continuación, agotamiento y reversión de movimientos bajistas.
- Consolidaciones y periodos de rango lateral.
- Rupturas y rechazos de niveles técnicos.
- Noticias, anuncios oficiales, decisiones regulatorias e incidentes de seguridad.
- Cambios del protocolo, actividad de desarrollo y eventos de gobernanza.
- Token unlocks, emisiones, quema de tokens y otros cambios de oferta.
- Volumen, liquidez, spreads, profundidad de mercado y diferencias entre exchanges.
- Derivados: open interest, funding rates y liquidaciones, cuando existan datos fiables.
- Métricas on-chain y movimientos de grandes tenedores, considerando las limitaciones de atribución de direcciones.
- Condiciones del mercado general, incluidos BTC, ETH y factores macroeconómicos relevantes.

La cobertura efectiva depende de la disponibilidad, calidad, licencia y granularidad de los datos. La ausencia de un evento en las fuentes consultadas no demuestra que el evento no haya ocurrido.

## 3. Principios metodológicos

1. **Evidence first:** cada conclusión material debe vincularse a evidencia identificable.
2. **Temporal ordering:** la cronología debe comprobarse antes de proponer una explicación.
3. **Alternative hypotheses:** evaluar explicaciones alternativas, incluida la dinámica general del mercado.
4. **No automatic causality:** la proximidad temporal entre una noticia y un movimiento no demuestra causalidad.
5. **Reproducibility:** registrar parámetros, ventanas temporales, fuentes, timestamps y limitaciones.
6. **Uncertainty disclosure:** permitir conclusiones inconclusas cuando la evidencia no sea suficiente.
7. **No hindsight leakage:** al evaluar modelos históricos, usar solo la información que habría estado disponible en el momento analizado.
8. **Source integrity:** distinguir fuentes primarias, fuentes secundarias, rumores y contenido no verificado.
9. **Separation of facts and interpretation:** presentar hechos observados por separado de las hipótesis explicativas.
10. **No investment guarantee:** los resultados no constituyen una garantía de rendimiento ni una recomendación automática de inversión.

## 4. Flujo de investigación

### 4.1 Detectar y delimitar el movimiento

Definir objetivamente el evento de precio que se investigará. Registrar, como mínimo:

- Activo, par, exchange o fuente de precio.
- Timeframe y zona horaria de los datos.
- Inicio y final de la ventana de movimiento.
- Precio inicial y final, retorno porcentual y duración.
- Volumen y una referencia comparable para determinar si fue inusual.
- Volatilidad y contexto técnico previo.
- Método utilizado para detectar el movimiento y sus parámetros.

La detección puede basarse en umbrales de retorno, cambios de volatilidad, anomalías de volumen, rupturas de rango u otros criterios predefinidos. Los umbrales deben documentarse y validarse; no deben ajustarse retrospectivamente para que encajen con una historia concreta.

### 4.2 Construir la línea temporal

Buscar acontecimientos en una ventana anterior, durante y posterior al movimiento. La ventana debe definirse según el timeframe, la liquidez del activo y la naturaleza del evento; no existe una ventana universal.

Para cada evento, registrar:

- Qué ocurrió y qué afirmación concreta se está evaluando.
- Timestamp de publicación original, si se conoce.
- Primer timestamp verificable en que la información estuvo disponible.
- Timestamp del evento subyacente, si es distinto del anuncio.
- Timestamp de captura por el sistema.
- URL o identificador de la fuente y fecha de consulta.
- Fuente primaria o secundaria y su nivel de independencia.
- Estado de verificación: confirmado, parcialmente confirmado, no verificado o refutado.

Normalizar los timestamps a UTC para comparar fuentes y conservar el timestamp original, la zona horaria declarada y la precisión conocida. Usar fechas y horas inequívocas, siguiendo como referencia ISO 8601-1:2019.

No tratar la hora de actualización de una página como si fuera necesariamente la hora de publicación original. Si el timestamp es incierto, marcarlo explícitamente.

### 4.3 Evaluar fuentes

Priorizar, cuando existan:

1. Comunicados oficiales del proyecto, exchange, regulador o proveedor de infraestructura involucrado.
2. Datos directos de mercado, documentación técnica, repositorios de código y datos on-chain verificables.
3. Medios reconocidos que enlacen a fuentes primarias.
4. Analistas o publicaciones sociales identificables, como evidencia secundaria.
5. Rumores o publicaciones anónimas, que no deben tratarse como hechos confirmados.

La fuente oficial puede confirmar que se hizo un anuncio, pero no demuestra por sí sola que el anuncio causó el movimiento del precio. Verificar también si la información ya era pública, había sido anticipada o fue corregida posteriormente.

### 4.4 Analizar el contexto del mercado

Comparar el comportamiento del activo con referencias apropiadas, por ejemplo BTC, ETH, un índice de mercado o activos comparables. Documentar por qué se eligió cada benchmark.

Según disponibilidad y fiabilidad, evaluar:

- Retornos y volatilidad del mercado general.
- Volumen spot, spread y profundidad de mercado.
- Actividad y diferencias entre exchanges.
- Open interest, funding rates y liquidaciones en derivados.
- Concentración de liquidez y posibles efectos de baja profundidad.
- Métricas on-chain, emisiones, desbloqueos y movimientos de tesorería.
- Eventos macroeconómicos o regulatorios que afecten a múltiples activos.

Las métricas de derivados y on-chain tienen limitaciones de cobertura y atribución. No inferir la identidad o intención de un participante solo a partir de una dirección o de un movimiento aislado.

### 4.5 Formular hipótesis competidoras

Para cada movimiento, formular una o más hipótesis comprobables. Ejemplos:

- Un anuncio positivo incrementó la demanda.
- Una noticia negativa elevó la presión vendedora.
- El activo se movió principalmente en línea con BTC o con el mercado general.
- Una ruptura técnica coincidió con un aumento de volumen.
- Las liquidaciones amplificaron un movimiento que ya había comenzado.
- La falta de liquidez amplificó el impacto de órdenes relativamente pequeñas.
- La noticia apareció después del movimiento y no explica su inicio.
- La evidencia disponible no permite distinguir entre explicaciones plausibles.

Cada hipótesis debe indicar evidencia favorable, evidencia contradictoria, predicciones observables y qué dato adicional permitiría evaluarla mejor.

### 4.6 Estudiar el movimiento y sus fases

No reducir un movimiento extenso a una única causa. Analizar por separado, cuando sea posible:

- **Initiation:** posibles factores asociados al comienzo.
- **Continuation:** factores compatibles con la persistencia.
- **Acceleration:** eventos o condiciones asociados a una aceleración.
- **Exhaustion:** señales de pérdida de impulso o absorción de órdenes.
- **Rejection:** rechazo de una zona de precio o fallo de ruptura.
- **Reversal:** evidencia de cambio de dirección.
- **Consolidation:** equilibrio temporal, contracción de volatilidad o ausencia de catalizadores claros.

Los patrones técnicos describen el comportamiento del precio; por sí solos no identifican la causa fundamental del movimiento.

### 4.7 Cuantificar el movimiento anormal

Cuando los datos y el tamaño de muestra lo permitan, estimar el retorno esperado según un benchmark o un modelo predefinido y comparar con el retorno observado:

`AbnormalReturn = ObservedReturn - ExpectedReturn`

La especificación del modelo, el periodo de estimación, el benchmark y las ventanas del evento deben registrarse. En análisis multitemporal puede calcularse el retorno anormal acumulado durante una ventana definida.

El rendimiento anormal no demuestra causalidad. Los resultados dependen del modelo, la ventana seleccionada, la liquidez, la calidad de los datos y los acontecimientos simultáneos. Si no existe un modelo razonable o los datos son insuficientes, informar la limitación en vez de producir una cifra engañosa.

### 4.8 Emitir y revisar la conclusión

La conclusión debe responder:

- ¿Qué movimiento se observó y cómo se delimitó?
- ¿Qué eventos verificables ocurrieron antes o durante el movimiento?
- ¿Qué hipótesis tiene más respaldo y por qué?
- ¿Qué evidencia contradice esa hipótesis?
- ¿Qué parte del movimiento parece compartida con el mercado general?
- ¿Qué limitaciones, vacíos o incertidumbres permanecen?
- ¿Qué hallazgos podrían refutar la conclusión?

Usar un lenguaje proporcional a la evidencia: “confirmado como evento”, “consistente con”, “posiblemente relacionado”, “evidencia insuficiente” o “hipótesis refutada”. Reservar afirmaciones causales fuertes para diseños de investigación que realmente permitan sostenerlas.

## 5. Escenarios de investigación

| Scenario | Questions to investigate |
| --- | --- |
| Inicio de una subida | ¿Qué cambió antes del movimiento? ¿Hubo anuncio verificable, ruptura con volumen, entrada de liquidez o un movimiento general del mercado? |
| Continuación alcista | ¿Se mantiene la demanda? ¿Aumenta la participación o solo se amplía el apalancamiento? ¿Qué evidencia contradice la continuación? |
| Subida detenida | ¿Hubo rechazo, toma de beneficios, pérdida de volumen, oferta nueva, unlock o noticia ya anticipada? |
| Inicio de una caída | ¿Hubo evento negativo, deterioro del mercado, presión vendedora, pérdida de liquidez o liquidaciones? |
| Caída detenida | ¿Se redujo la presión vendedora? ¿Hubo absorción, recuperación del mercado o un catalizador verificable? |
| Rango lateral | ¿Existe compresión de volatilidad, equilibrio temporal, baja actividad o resistencia repetida? ¿Qué evidencia confirmaría una ruptura real? |
| Reversión | ¿Cambió el contexto fundamental o de mercado? ¿Se confirmó un cambio de estructura y volumen? ¿Qué otras explicaciones existen? |

Estas categorías organizan la investigación; no son reglas deterministas de trading.

## 6. Registro mínimo de evidencia

Cada investigación debe almacenar, como mínimo, los siguientes campos o sus equivalentes:

| Field | Description |
| --- | --- |
| `case_id` | Identificador único de la investigación. |
| `asset_id` | Identificador inequívoco del criptoactivo; no depender solo del ticker. |
| `market_pair` | Par, exchange y fuente de precios. |
| `timeframe` | Resolución de las velas o datos utilizados. |
| `movement_start_utc` / `movement_end_utc` | Límites temporales del movimiento en UTC. |
| `observed_return_pct` | Retorno observado durante la ventana. |
| `detection_method` | Regla y parámetros usados para detectar el movimiento. |
| `event_id` | Identificador único del evento candidato. |
| `event_description` | Descripción neutral del acontecimiento. |
| `event_timestamp_utc` | Hora del evento subyacente, si se conoce. |
| `published_at_utc` | Hora de publicación original, si se conoce. |
| `first_observed_at_utc` | Primera disponibilidad verificable de la información. |
| `captured_at_utc` | Hora en que el sistema capturó el registro. |
| `source_url` / `source_type` | Referencia y clasificación de la fuente. |
| `verification_status` | Estado de verificación del evento. |
| `hypothesis` | Explicación que se evalúa. |
| `supporting_evidence` | Evidencia favorable con referencias. |
| `contradicting_evidence` | Evidencia contraria con referencias. |
| `benchmark` / `abnormal_return` | Benchmark y cálculo, cuando corresponda. |
| `confidence_level` | Evaluación documentada de confianza. |
| `limitations` | Limitaciones de datos, método o inferencia. |
| `analyst_notes` | Notas de revisión y preguntas abiertas. |

Los timestamps desconocidos deben almacenarse como desconocidos, no inventarse ni sustituirse por horas estimadas sin indicarlo.

## 7. Niveles de confianza

La confianza debe representar la calidad conjunta de la evidencia, no solo la fuerza de una narrativa. Se propone la siguiente escala interna, que no es una norma ISO ni una escala estadística universal:

- **High:** evento verificado con fuentes primarias o independientes; cronología consistente; varias observaciones apoyan la hipótesis y se han examinado alternativas relevantes.
- **Moderate:** existe evidencia creíble y una cronología plausible, pero persisten explicaciones alternativas o faltan datos importantes.
- **Low:** evidencia indirecta, fuente única poco independiente, timestamp incierto o soporte débil.
- **Undetermined:** no hay información suficiente para asignar una explicación responsable.
- **Refuted:** la evidencia disponible contradice la hipótesis concreta evaluada.

La confianza en que un evento ocurrió debe distinguirse de la confianza en que ese evento influyó materialmente en el precio.

## 8. Sesgos y controles de calidad

Antes de cerrar una investigación, revisar:

- **Hindsight bias:** no seleccionar únicamente noticias conocidas después del movimiento.
- **Selection bias:** registrar el criterio que hizo que el movimiento fuera investigado.
- **Survivorship bias:** no limitar el análisis a activos que sobrevivieron o tuvieron éxito.
- **Look-ahead bias:** en pruebas históricas, no utilizar datos publicados después del momento simulado.
- **Timestamp bias:** distinguir hora del evento, publicación, difusión y captura.
- **Duplicate reporting:** agrupar artículos que reproducen el mismo comunicado; no contarlos como fuentes independientes.
- **Confounding events:** considerar eventos simultáneos y movimientos del mercado general.
- **Liquidity and venue bias:** reconocer diferencias entre exchanges, pares y calidad de ejecución.
- **Multiple testing:** documentar cuántas ventanas, activos o hipótesis se probaron antes de seleccionar un resultado.
- **Data revisions:** conservar las revisiones relevantes y el momento en que cada dato estuvo disponible.

Cuando sea posible, usar reglas de detección y ventanas definidas antes de inspeccionar las noticias. Mantener un historial de las hipótesis iniciales y de las modificaciones posteriores.

## 9. Relación con estándares y referencias

Este documento define una metodología interna de CryptoDueDiligence; no es una norma ISO ni implica certificación.

Referencias relevantes:

- [ISO 31000:2018 — Risk management — Guidelines](https://www.iso.org/standard/65694.html): marco de gestión de riesgos.
- [ISO 8601-1:2019 — Date and time — Representations for information interchange](https://www.iso.org/standard/70907.html): representación interoperable de fechas y horas.
- [Cumulative Abnormal Returns and Event Studies](https://doi.org/10.1016/0304-405X(69)90010-1): referencia académica clásica sobre el enfoque de estudios de eventos. Su aplicación a criptoactivos requiere adaptación y validación.

Los estándares aportan principios y convenciones; no certifican que una explicación concreta del precio sea correcta ni que una inversión sea rentable.

## 10. Límites de uso

- La investigación retrospectiva no garantiza capacidad predictiva.
- Las fuentes públicas pueden ser incompletas, manipuladas, tardías o contradictorias.
- Los movimientos cripto pueden resultar de múltiples factores simultáneos o de flujos de órdenes no observables públicamente.
- Las relaciones estadísticas pueden cambiar según el régimen de mercado.
- No emitir una conclusión causal si la evidencia solo demuestra coincidencia temporal.
- No convertir el nivel de confianza en una probabilidad numérica sin calibración empírica.
- Los resultados deben tratarse como insumos para due diligence, no como instrucciones automáticas de compra o venta.

## 11. Estado de la metodología

Esta es la versión inicial del protocolo. Las futuras iteraciones podrán definir criterios cuantitativos de detección, fuentes de datos aprobadas, modelos de benchmark, formatos de salida y procedimientos de validación retrospectiva. Cada cambio metodológico deberá documentar su motivación, impacto y limitaciones.
