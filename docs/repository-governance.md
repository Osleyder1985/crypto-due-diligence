# Gobernanza del repositorio

## Propósito

Este documento define las reglas operativas para mantener la trazabilidad, la calidad y la reproducibilidad de los cambios en CryptoDueDiligence.

## Regla de integración

Ningún cambio debe integrarse en `main` sin:
1. Un Issue previo con alcance y criterios de aceptación.
2. Una branch de trabajo separada.
3. Un Pull Request que enlace el Issue.
4. Revisión del cambio y resolución de los comentarios pertinentes.
5. Verificación de las comprobaciones aplicables.

Los cambios deben mantenerse dentro del alcance aprobado. Si el alcance cambia materialmente, actualizar el Issue antes de continuar.

## Reglas de GitHub verificadas

El repositorio dispone de un ruleset llamado `main-branch-protection`, con estado `active`, dirigido a la rama predeterminada mediante el patrón `~DEFAULT_BRANCH`. En el estado revisado, la rama predeterminada del repositorio es `main`.

Reglas que aparecen configuradas:
- `pull_request`: exige que los cambios se integren mediante Pull Request.
- `required_review_thread_resolution`: exige resolver las conversaciones de revisión.
- `non_fast_forward`: bloquea actualizaciones no fast-forward, incluidas las operaciones habituales de force push.
- `deletion`: bloquea la eliminación de la rama objetivo.

Limitaciones observadas al revisar el ruleset:
- `required_approving_review_count` está configurado en `0`; no exige una aprobación humana.
- `required_status_checks` existe, pero la lista `required_status_checks` está vacía; no hay checks obligatorios definidos por este ruleset.
- El ruleset no valida por sí solo que cada Pull Request esté enlazado a un Issue.

La configuración debe revisarse de nuevo cuando cambien las reglas, las ramas predeterminadas o los workflows. La existencia de un ruleset no sustituye la validación de su alcance ni de sus parámetros efectivos.

## Validación del vínculo Issue–Pull Request

Usar referencias de cierre de GitHub como `Closes #123` en el cuerpo del Pull Request. Esta convención mejora la trazabilidad, pero la documentación por sí sola no impone su cumplimiento. Para exigirlo técnicamente, deberá añadirse un workflow de GitHub Actions que falle cuando un Pull Request hacia `main` no incluya una referencia válida a un Issue.

Ese workflow debe implementarse mediante su propio Issue y Pull Request, con criterios de aceptación y pruebas explícitos.

## Convenciones lingüísticas

Los nombres técnicos (archivos, directorios, identificadores, código, branches y commits) se escriben en inglés. La documentación explicativa, las decisiones metodológicas y los informes del proyecto se escriben en español, salvo nombres oficiales o fragmentos técnicos cuya traducción reduzca la precisión.

## Cambio de las reglas

Cualquier cambio a estas reglas debe proponerse mediante Issue y Pull Request. Documentar el motivo, el impacto esperado y cómo se verificará.
