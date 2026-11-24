# Historial de cambios

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y la
versión, [SemVer](https://semver.org/lang/es/).

## [1.1.0] – 2026-11-24

### Agregado

- `scripts/cost_report.py`: tokens por sesión de Claude Code, Codex y OpenCode; en OpenCode se leen los registros `session_v2`.
- Diagramas SVG del flujo, la escalera de modelos y los resultados del A/B en `docs/img/`.
- Resultados del A/B real con y sin EzOrca en el README y en `docs/evaluation.md`.

### Corregido

- Compatibilidad con Python 3.11 en `fingerprint.py`.

## [1.0.0] – 2026-11-24

### Agregado

- Por defecto, la frontera que dirige no escribe código (el usuario puede indicar otra cosa): planifica, revisa y acepta; el código lo escriben los Goldfish.
- Escalera de modelos con «avisa y sigue»: tras dos fallos en un modelo económico, el Elefante sube un nivel y avisa, sin detener el Run.
- Papeles PM, senior, junior y QA repartidos según el riesgo del encargo y el costo de cada sesión.
- Conversación con el usuario en una sola tanda: todas las preguntas juntas al inicio, no una por una.
- Entrega normal con un solo pase de QA y entrega verificada con dos pases y huella del conjunto verificable.
- Registro `run.md` con plan, tandas, recibos, puertas y costo real por sesión.
- Siete scripts: `discover.py`, `launch_wave.py`, `stalled.py`, `check_spec.py`, `check_scope.py`, `fingerprint.py` y `compare_skill_results.py`.
- Evaluación ciega de skills con `eval_kit.py` y comparador contra la versión base.

### Cambiado

- Principios Ponytail (el cambio mínimo completo) integrados en los encargos y las revisiones.
- ub-mode (el usuario decide) como opción explícita frente al modo autónomo.
