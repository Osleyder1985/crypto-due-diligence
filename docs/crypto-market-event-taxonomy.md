# Crypto Market Event Taxonomy

## 1. Propósito y estado

Este documento define una taxonomía interna para clasificar eventos que podrían estar relacionados con movimientos del precio de criptoactivos. Se utiliza junto con [Market Event Attribution](market-event-attribution.md) para que las investigaciones empleen categorías consistentes.

La taxonomía organiza qué ocurrió; no determina por sí misma si el evento causó una subida, una caída, un rango o una reversión. Los identificadores en inglés son claves estables para almacenamiento, consultas y futuras integraciones. Esta clasificación es una convención del proyecto, no una norma ISO ni un estándar financiero oficial.

## 2. Principios de clasificación

1. **Classify the event, not the price reaction.** La categoría describe el acontecimiento observado. El retorno y la reacción del precio se registran por separado.
2. **Allow multiple tags.** Un mismo caso puede incluir un anuncio de gobernanza, un cambio de oferta y una cotización en un exchange.
3. **Preserve source and time.** Cada evento debe tener referencias, timestamps y un estado de verificación.
4. **Separate event from hypothesis.** “El exchange anunció un listado” puede ser un hecho verificado; “el listado causó la subida” es una hipótesis que necesita evaluación.
5. **Use neutral direction labels.** No etiquetar un evento como positivo o negativo de forma universal. Su efecto depende del contexto y de las expectativas previas.
6. **Record no observed reaction.** Un evento puede estar confirmado sin que se observe una reacción de precio identificable.
7. **Represent uncertainty explicitly.** Los rumores, timestamps imprecisos y atribuciones no verificadas deben conservar ese estado.
8. **Avoid duplicate counting.** Varias publicaciones que repiten un comunicado original deben vincularse a un mismo evento subyacente cuando corresponda.

## 3. Categorías principales

### 3.1 PROJECT_FUNDAMENTALS

Eventos relativos al desarrollo, adopción, producto, alianzas y operación del proyecto.

- product_launch: lanzamiento de producto, aplicación o servicio.
- protocol_upgrade: actualización planificada o activación de una mejora.
- roadmap_milestone: entrega o retraso de un hito anunciado.
- partnership_announcement: alianza o integración comunicada.
- adoption_metric: cambio verificable en usuarios, transacciones, ingresos o uso.
- developer_activity: cambio relevante en actividad de desarrollo, revisiones o mantenimiento.
- treasury_action: decisión o movimiento divulgado de tesorería.
- project_shutdown: suspensión de producto, servicio o actividad del proyecto.

**Precauciones:** una alianza anunciada no implica adopción comercial material. Diferenciar una propuesta, una prueba piloto, una integración disponible y un uso real medido.

### 3.2 TOKENOMICS_SUPPLY

Eventos que afectan a la oferta, distribución o incentivos económicos del token.

- token_unlock: desbloqueo de tokens sujetos a vesting u otras restricciones.
- emission_change: cambio en emisión o recompensa.
- token_burn: quema verificable de tokens.
- staking_change: modificación de recompensas, requisitos o condiciones de staking.
- supply_schedule_change: modificación de la política de oferta.
- allocation_or_vesting_update: actualización de asignaciones o calendarios.
- treasury_or_foundation_transfer: transferencia de tesorería o fundación.
- airdrop_or_distribution: distribución o elegibilidad de tokens.
- buyback_or_repurchase: recompra anunciada o verificada.
- governance_token_economics: cambio en derechos o incentivos económicos.

**Precauciones:** un unlock programado no equivale a una venta. Distinguir oferta desbloqueada, tokens transferidos a un exchange y venta efectivamente ejecutada. Registrar cantidades y denominadores de forma consistente.

### 3.3 EXCHANGE_MARKET_ACCESS

Eventos relativos a la negociación, acceso al mercado y reglas de los venues.

- exchange_listing: nuevo listado spot o de derivados.
- exchange_delisting: retirada de cotización.
- trading_pair_added_or_removed: alta o baja de un par.
- market_maker_change: cambio divulgado de proveedor de liquidez.
- deposit_withdrawal_suspension: suspensión o reanudación de depósitos o retiros.
- exchange_outage: interrupción o degradación de una plataforma.
- trading_rule_change: cambio de margen, límites, tick size u otras reglas.
- custody_or_wallet_support_change: incorporación o retirada de soporte de custodia o wallet.

**Precauciones:** especificar exchange, producto y par. Un anuncio de listado no garantiza liquidez, volumen sostenible ni disponibilidad en todas las jurisdicciones.

### 3.4 MARKET_MICROSTRUCTURE

Eventos y condiciones observables en la estructura de mercado y el flujo de órdenes.

- volume_anomaly: volumen inusual según un baseline documentado.
- liquidity_shift: cambio medible de profundidad, spread o liquidez.
- large_order_or_trade: operación grande verificada en un venue.
- order_book_imbalance: desequilibrio medido del libro de órdenes.
- cross_exchange_dislocation: divergencia relevante entre venues.
- price_gap_or_fast_move: salto o movimiento rápido de precio.
- support_resistance_break: ruptura o rechazo de nivel definido por un método explícito.
- volatility_regime_change: cambio en volatilidad conforme a una regla documentada.
- market_manipulation_allegation: alegación de manipulación; requiere etiqueta de verificación separada.

**Precauciones:** indicadores técnicos describen patrones y condiciones; no identifican automáticamente una causa fundamental. No calificar una operación como manipulación sin evidencia apropiada.

### 3.5 DERIVATIVES_LEVERAGE

Eventos relacionados con derivados, apalancamiento y liquidaciones.

- open_interest_change: variación del interés abierto.
- funding_rate_extreme: tasa de financiación extrema frente a un baseline definido.
- long_liquidation_cluster: grupo temporal de liquidaciones de posiciones largas.
- short_liquidation_cluster: grupo temporal de liquidaciones de posiciones cortas.
- basis_change: cambio en la base entre spot y derivados.
- options_expiry: vencimiento de opciones relevante.
- margin_requirement_change: cambio de requisitos de margen.
- leverage_product_launch_or_removal: incorporación o retirada de un producto apalancado.

**Precauciones:** el open interest no revela por sí solo si el mercado está netamente alcista o bajista. Los datos de liquidación pueden variar entre proveedores y venues; registrar cobertura y fuente.

### 3.6 ONCHAIN_ACTIVITY

Eventos observados en una blockchain o red.

- large_transfer: transferencia de gran tamaño según umbral documentado.
- exchange_inflow_or_outflow: flujo hacia o desde direcciones atribuidas a exchanges.
- whale_concentration_change: cambio de concentración entre direcciones o entidades estimadas.
- network_activity_change: variación relevante en actividad de la red.
- active_addresses_change: cambio en direcciones activas según definición del proveedor.
- transaction_fee_change: cambio de comisiones.
- network_congestion: congestión observada.
- bridge_flow: flujo entre cadenas mediante bridge.
- validator_or_miner_behavior: cambio verificable en actividad de validadores o mineros.
- protocol_contract_interaction: cambio notable en interacciones con contratos.

**Precauciones:** una dirección no equivale necesariamente a una persona, organización o intención. Las etiquetas de entidades pueden ser incompletas y las métricas de proveedores pueden usar definiciones distintas.

### 3.7 SECURITY_INCIDENT

Incidentes o vulnerabilidades que afectan al activo, protocolo, infraestructura o custodios.

- smart_contract_exploit: explotación confirmada de contrato.
- vulnerability_disclosure: divulgación de vulnerabilidad.
- bridge_or_oracle_incident: incidente de bridge u oráculo.
- private_key_or_custody_breach: compromiso de claves o custodia.
- consensus_or_network_attack: ataque o interrupción de consenso/red.
- chain_halt_or_reorg: parada de cadena o reorganización relevante.
- funds_frozen_or_recovered: congelación o recuperación verificable de fondos.
- security_patch_or_mitigation: parche o mitigación.
- incident_postmortem: publicación de análisis posterior al incidente.

**Precauciones:** separar incidente confirmado, vulnerabilidad potencial, sospecha y alegación. Registrar hora de explotación, detección, divulgación y mitigación por separado cuando se conozcan.

### 3.8 GOVERNANCE_DECENTRALIZATION

Eventos de gobernanza, control y toma de decisiones.

- governance_proposal: propuesta formal.
- governance_vote: votación o resultado.
- governance_execution: ejecución de una decisión aprobada.
- validator_set_change: cambio material de conjunto de validadores.
- centralization_concern: evidencia o alegación sobre concentración de control.
- key_person_departure: salida de persona clave.
- foundation_or_leadership_change: cambio de liderazgo o fundación.
- emergency_admin_action: acción administrativa de emergencia.
- dispute_or_fork: disputa de gobernanza o bifurcación.

**Precauciones:** una propuesta no es una decisión ejecutada. Documentar poder de voto, participación, quorum y condiciones de implementación si son relevantes.

### 3.9 REGULATORY_LEGAL

Eventos jurídicos, regulatorios o de cumplimiento.

- regulatory_guidance_or_statement: orientación o declaración oficial.
- enforcement_action: medida de ejecución o sanción.
- lawsuit_filing_or_ruling: presentación, resolución o sentencia judicial.
- asset_classification: decisión o declaración sobre clasificación legal.
- exchange_or_product_approval: autorización o denegación regulatoria.
- jurisdiction_access_change: cambio de disponibilidad por jurisdicción.
- compliance_or_sanctions_action: acción de cumplimiento o sanciones.
- tax_policy_change: cambio fiscal relevante.
- legal_opinion_or_advisory: opinión jurídica identificada, sin tratarla como decisión vinculante.

**Precauciones:** distinguir propuesta legislativa, declaración pública, investigación, acusación, resolución y sentencia firme. Registrar jurisdicción, organismo, fecha y alcance del acto.

### 3.10 MACROECONOMIC_GEOPOLITICAL

Eventos macroeconómicos o geopolíticos que pueden afectar al conjunto del mercado.

- central_bank_decision: decisión de política monetaria.
- inflation_or_employment_release: publicación macroeconómica.
- interest_rate_expectation_change: cambio de expectativas de tipos, si está respaldado por datos.
- market_risk_off_or_risk_on: cambio amplio de apetito por riesgo medido con referencias.
- geopolitical_escalation: evento geopolítico verificable.
- sovereign_or_bank_stress: estrés financiero o soberano.
- traditional_market_dislocation: movimiento relevante en mercados tradicionales.
- commodity_or_currency_shock: shock en materias primas o divisas.

**Precauciones:** usar timestamps oficiales y comparar con activos de referencia. Evitar atribuir movimientos de una criptomoneda a un evento macroeconómico sin evaluar el comportamiento del mercado general.

### 3.11 SENTIMENT_INFORMATION

Eventos relacionados con difusión de información, atención pública y expectativas.

- official_announcement: anuncio oficial que debe enlazarse además a su categoría sustantiva.
- media_report: noticia publicada por un medio.
- social_media_attention_spike: aumento medido de atención social.
- rumor_or_unverified_claim: rumor o afirmación no verificada.
- public_statement_or_interview: declaración pública.
- influencer_or_promotional_campaign: campaña promocional identificada.
- misinformation_or_fake_announcement: información falsa o anuncio fraudulento verificado.
- sentiment_metric_change: cambio en una métrica de sentimiento con proveedor y método documentados.

**Precauciones:** popularidad, sentimiento y volumen de publicaciones pueden ser manipulados o no representar demanda real. El contenido social debe conservar procedencia, timestamp y estado de verificación.

### 3.12 COMPETITOR_ECOSYSTEM

Eventos de ecosistemas, competidores, integraciones y activos relacionados.

- competitor_launch_or_upgrade: lanzamiento o actualización de un competidor.
- ecosystem_incentive_program: programa de incentivos o subvenciones.
- cross_chain_integration: integración entre cadenas.
- ecosystem_migration: migración de usuarios, activos o aplicaciones.
- related_asset_shock: evento de un activo relacionado con posible efecto de contagio.
- market_share_change: cambio de cuota calculado con método documentado.

**Precauciones:** definir por qué se considera relevante la relación entre activos. No inferir causalidad por pertenecer al mismo sector.

### 3.13 DATA_QUALITY_OPERATIONAL

Eventos y problemas que afectan a la confiabilidad de la propia investigación.

- market_data_outage: interrupción de fuente de datos.
- provider_methodology_change: cambio metodológico de proveedor.
- timestamp_correction: corrección de timestamps.
- data_revision: revisión de datos históricos.
- ticker_or_asset_identity_conflict: conflicto de identificación del activo.
- chain_or_contract_migration: migración que requiere mapear identidades.
- source_unavailable_or_removed: fuente retirada o inaccesible.
- investigation_gap: limitación material de cobertura de fuentes.

**Precauciones:** los problemas de datos pueden crear anomalías aparentes. Resolver identidad de activo, par, exchange y timestamps antes de formular conclusiones de mercado.

## 4. Campos normalizados del evento

Cada evento debe poder representarse con un registro que incluya:

| Field | Required | Description |
| --- | --- | --- |
| event_id | Sí | Identificador único y estable. |
| primary_category | Sí | Categoría principal de esta taxonomía. |
| subcategory | Sí | Identificador de subcategoría. |
| title | Sí | Descripción breve y neutral. |
| description | Sí | Resumen factual separado de la interpretación. |
| asset_ids | Cuando aplique | Activos afectados, usando identificadores inequívocos. |
| entities | No | Proyecto, exchange, regulador u otras entidades relevantes. |
| event_time_utc | Si se conoce | Hora del evento subyacente. |
| published_at_utc | Si se conoce | Hora de publicación original. |
| first_observed_at_utc | Si se conoce | Primera disponibilidad verificable de la información. |
| captured_at_utc | Sí para ingesta | Hora en que el sistema registró la evidencia. |
| source_refs | Sí | Referencias a una o más fuentes. |
| verification_status | Sí | Estado de verificación normalizado. |
| event_status | Sí | Estado temporal del evento. |
| observed_price_effect | Después del análisis | Reacción observada, sin implicar causalidad. |
| case_ids | Si se investiga | Investigaciones que incluyen el evento. |
| notes_and_limitations | Cuando aplique | Incertidumbre, contexto y límites. |

Los timestamps se expresan en UTC en formato inequívoco. Cuando una hora no se conozca, se almacena como nula o desconocida; no se sustituye por una hora estimada sin etiquetarla como estimación.

### 4.1 verification_status

Valores permitidos propuestos:

- confirmed: respaldado por evidencia primaria fiable o corroboración suficiente.
- partially_confirmed: parte del evento está verificada, pero detalles materiales siguen abiertos.
- unverified: evidencia insuficiente para confirmar.
- disputed: fuentes creíbles presentan versiones contradictorias.
- refuted: la afirmación del evento fue contradicha por evidencia suficiente.
- retracted: la fuente retiró o corrigió la afirmación; conservar historial.

Este campo describe el estado de la afirmación factual, no su impacto en el precio.

### 4.2 event_status

Valores sugeridos:

- rumored
- announced
- scheduled
- in_progress
- occurred
- completed
- cancelled
- delayed
- corrected
- unknown

No todos los estados aplican a todas las categorías.

### 4.3 observed_price_effect

Usar valores neutrales y descriptivos:

- positive_observed
- negative_observed
- mixed_or_reversing
- no_material_move_detected
- inconclusive
- not_assessed

Registrar aparte el retorno, la ventana de medición y el benchmark. La etiqueta describe el efecto observado dentro de esa ventana, no una causalidad confirmada ni una expectativa futura.

## 5. Relaciones entre eventos y movimientos

Un movimiento puede estar relacionado con múltiples eventos y un evento puede coincidir con movimientos de varios activos. Modelar esa relación de muchos a muchos mediante una entidad de análisis, no incorporando una causa definitiva en el registro factual.

Campos sugeridos para la relación:

- case_id
- event_id
- hypothesis_id
- temporal_relation (antes, durante, después o incierta)
- evidence_for
- evidence_against
- alternative_explanations
- attribution_assessment
- confidence_level
- reviewed_at_utc

No añadir una relación de atribución confirmada únicamente porque los timestamps estén próximos.

## 6. Reglas para casos complejos

### Eventos simultáneos

Registrar cada evento por separado y crear relaciones entre ellos si existe dependencia demostrable. Evaluar el mercado general y reconocer cuando no sea posible separar efectos.

### Anuncios anticipados o rumores previos

Distinguir el acontecimiento subyacente, la primera noticia pública, los rumores previos y el anuncio oficial. El precio puede reaccionar antes del comunicado formal.

### Noticias duplicadas

Agrupar las publicaciones que repiten el mismo evento subyacente, manteniendo cada fuente individual. No contar republicaciones como corroboración independiente.

### Eventos con impacto ambiguo

No forzar una etiqueta alcista o bajista. Registrar reacción mixta, ausencia de movimiento material o resultado inconcluso, junto con la ventana evaluada.

### Eventos previstos y ejecutados

Un evento programado —como un unlock o actualización— debe diferenciarse de su ejecución efectiva. Registrar cambios de horario y resultados inesperados.

### Información falsa o corregida

Conservar la afirmación original, la fuente, la hora de difusión, la corrección o refutación y su cronología. No borrar el historial necesario para explicar cómo pudo circular la información.

### Activos con identidad ambigua

Resolver la identidad mediante cadena, dirección de contrato, emisor y exchange. El ticker por sí solo no es una clave fiable.

## 7. Relación con las fases del movimiento

Las fases de movimiento no son categorías de evento. Se registran en la investigación que estudia el precio:

- initiation
- continuation
- acceleration
- exhaustion
- rejection
- reversal
- consolidation

De este modo, un token_unlock puede ser investigado como evento candidato durante una reversal, pero el tipo de evento no determina por sí mismo esa fase ni prueba que la haya causado.

## 8. Uso en la investigación

Flujo recomendado:

1. Detectar y delimitar un movimiento según criterios documentados.
2. Buscar eventos de todas las categorías pertinentes dentro de una ventana predefinida.
3. Registrar eventos candidatos y fuentes sin asignar causalidad.
4. Verificar identidad, cronología, estado y duplicados.
5. Comparar el movimiento con benchmarks y datos de mercado disponibles.
6. Formular hipótesis y documentar evidencia favorable y contradictoria.
7. Asignar la evaluación de atribución en el expediente de investigación, no en el evento factual.
8. Registrar lagunas y permitir el resultado inconclusive.

## 9. Límites

- La taxonomía no es una lista exhaustiva de todas las causas posibles.
- La clasificación puede evolucionar; los cambios deben documentar compatibilidad con registros históricos.
- Los datos públicos no siempre revelan órdenes privadas, participantes o motivos.
- Una categoría o etiqueta no sustituye el análisis cuantitativo ni la revisión humana.
- La coincidencia temporal, el sentimiento social y los patrones gráficos no bastan por sí solos para establecer causalidad.
- La metodología no constituye asesoramiento financiero ni garantiza capacidad predictiva.

## 10. Control de cambios

La taxonomía debe versionarse. Cuando se cambie un identificador existente, preferir mantenerlo y marcarlo como obsoleto antes que reutilizarlo con otro significado. Para cambios incompatibles, documentar la versión de esquema, la regla de migración y el impacto en los registros históricos.

Esta taxonomía es una propuesta interna inicial para CryptoDueDiligence y deberá revisarse a medida que se incorporen datos reales y se validen casos históricos.
