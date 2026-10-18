# Guía de contribución

## Principio general

Todo cambio debe ser trazable y revisable. No se integrarán cambios en `main` sin un Issue que describa el trabajo y un Pull Request asociado.

## Flujo obligatorio

1. Crear o localizar un Issue antes de empezar.
2. Confirmar el objetivo, el alcance y los criterios de aceptación.
3. Crear una branch a partir de `main`. Usar nombres descriptivos en inglés, por ejemplo `docs/repository-governance`, `feat/token-risk-scoring` o `fix/data-validation`.
4. Implementar únicamente el alcance acordado en el Issue.
5. Ejecutar las pruebas y comprobaciones pertinentes; documentar las que no puedan ejecutarse.
6. Abrir un Pull Request hacia `main` y enlazar el Issue, preferiblemente con una referencia de cierre como `Closes #123`.
7. Resolver los comentarios de revisión y esperar a que se cumplan las reglas y comprobaciones aplicables.
8. Integrar el Pull Request solo después de la revisión final.

No se deben hacer commits directamente en `main`, ni eludir las protecciones del repositorio.

## Convenciones de idioma

- Usar inglés para nombres de archivos y carpetas, código, variables, funciones, clases, identificadores, branches, commits y términos técnicos propios del desarrollo.
- Usar español para la documentación explicativa del proyecto, las decisiones metodológicas, los análisis, los informes y la comunicación general.
- Mantener en inglés los nombres oficiales de tecnologías, APIs, comandos y elementos de GitHub cuando sea más preciso.

## Requisitos para un Issue

Todo Issue debe describir:
- Objetivo y motivación.
- Alcance y exclusiones, cuando corresponda.
- Criterios de aceptación verificables.
- Plan de verificación o pruebas, si aplica.
- Dependencias o riesgos conocidos, si los hay.

## Requisitos para un Pull Request

Todo Pull Request debe incluir:
- Resumen de los cambios y su justificación.
- Referencia al Issue correspondiente.
- Pruebas ejecutadas y sus resultados; indicar explícitamente las no ejecutadas.
- Riesgos, limitaciones o efectos sobre datos y configuración, cuando corresponda.
- Confirmación de que el alcance del Pull Request coincide con el Issue.

## Calidad y reproducibilidad

- Preferir cambios pequeños, atómicos y fáciles de revisar.
- No presentar resultados no verificados como hechos.
- Para datos, métricas y análisis, indicar fuentes, fechas, supuestos y limitaciones pertinentes.
- No incluir secretos, credenciales, claves privadas ni datos sensibles.
- No introducir dependencias, datasets o cambios de arquitectura sin justificar su necesidad en el Issue.

## Revisión y aceptación

Antes de integrar, comprobar los criterios de aceptación, revisar el diff completo, resolver las conversaciones de revisión y confirmar el estado de las comprobaciones automatizadas disponibles. La aprobación humana debe realizarse de acuerdo con las reglas efectivas del repositorio; la existencia de un Pull Request por sí sola no demuestra que el cambio sea correcto.
