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

El workflow `.github/workflows/validate-pr-issue.yml` valida Pull Requests cuando se abren, editan, reabren, reciben nuevos commits o pasan a estar listos para revisión. Exige al menos una referencia explícita como `Closes #123`, `Fixes #123`, `Resolves #123` o `Refs #123`, y consulta la API de GitHub para comprobar que cada número referenciado corresponde a un Issue existente del mismo repositorio, no a otro Pull Request.

El check informa de errores accionables si falta una referencia o si una referencia no se puede validar. Usa permisos de solo lectura para Issues y Pull Requests. No fusiona cambios automáticamente.

**Limitación importante:** crear el workflow no bloquea por sí solo la integración. Para hacerlo obligatorio, hay que ejecutar el workflow al menos una vez y configurar el check `validate-issue-link` como requerido en el ruleset que protege `main`. Hasta completar ese paso, el control reporta fallos pero puede no impedir un merge.

La implementación se gestiona mediante el Issue #3 y el Pull Request asociado, conforme al flujo de gobernanza.

## Convenciones lingüísticas

Los nombres técnicos (archivos, directorios, identificadores, código, branches y commits) se escriben en inglés. La documentación explicativa, las decisiones metodológicas y los informes del proyecto se escriben en español, salvo nombres oficiales o fragmentos técnicos cuya traducción reduzca la precisión.

## Cambio de las reglas

Cualquier cambio a estas reglas debe proponerse mediante Issue y Pull Request. Documentar el motivo, el impacto esperado y cómo se verificará.
