# Historial de cambios

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y la
versión, [SemVer](https://semver.org/lang/es/).

## [1.4.0] – Sin publicar

### Cambiado

- El modo inteligente consulta presupuesto vivo antes de elegir y cubre los papeles con candidatos de `pick` ordenados por precio.
- `resources.py` clasifica por precio de salida; `discover.py` conserva el inventario y deja sin nivel los modelos sin precio.
- Evaluación A/B con proceso equivalente (T2, 3 pares): 9/9 pruebas ocultas en ambos brazos, diferencia del juez no concluyente (20,7 frente a 21,3); costo y tiempo medidos en US$ con precios de models.dev.

## [1.3.0] – 2026-11-25

### Agregado

- `choose_mode.py` elige el modo inteligente de menor costo que cumple los requisitos: directo, delegado o coordinado.
- Cualquier modelo puede ser el Elefante.
- Las tareas complejas pueden incorporar un planificador de frontera en una sesión nueva.
- Prueba real del modo inteligente con chats de menor nivel en `docs/evaluation.md`, con su gráfico de calidad y tokens.

### Corregido

- Los ejemplos de nivel del chat ahora están en `SKILL.md`.

## [1.2.0] – 2026-11-25

### Cambiado

- La skill decide entre modo directo y coordinado antes de planear.
- La regla que asigna la escritura de código a los Goldfish aplica solo en Runs coordinados.
- El README y la documentación reflejan los resultados del A/B justo.

### Corregido

- `check_spec.py` acepta variantes explícitas en plural de sus etiquetas («Ejemplos», «Métodos y límites») sin aceptar palabras que solo empiezan igual.
- `launch_wave.py` admite `new-top-level` con `repo` y `worktree_name`. Rechaza valores vacíos o con solo espacios.
- `discover.py --cache` interpreta rutas de Git Bash en Windows y sale con código 2 si no puede leer o escribir la caché.
- `discover.py` regenera la caché cuando contiene JSON inválido, incluidos valores `NaN` y JSON malformado.

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
