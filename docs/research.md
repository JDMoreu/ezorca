# Investigación

EzOrca tomó ideas de papers y herramientas existentes, sin dependencias nuevas.
Se leyó documentación en noviembre de 2026; no se ejecutaron ni se reprodujeron
sus benchmarks, y las cifras son de las fuentes; las entradas sin enlace son
principios de skills instaladas. Los papeles citados son ejemplos; cada Run
define los suyos. Desde 1.4.0 la meta es calidad validada: los modelos de
frontera planifican y validan, el ejecutor llega como máximo a nivel medio y el
costo solo desempata, dentro de los topes de cada plan.

## Papers

- **FrugalGPT (2023).** https://arxiv.org/abs/2305.05176 — Una cascada de modelos
  puede igualar al mejor con mucho menos costo en sus experimentos. **En EzOrca:**
  registrar el costo real por tarea (`cost_report.py`) sin prometer ahorro: el
  costo es tope y desempate, no la meta.
- **RouteLLM (2024).** https://arxiv.org/abs/2406.18665 — Enruta entre un
  modelo fuerte y uno débil según preferencias y costo. **En EzOrca:** el
  selector fija el nivel por tamaño y riesgo, con la calidad primero; el costo
  solo desempata entre candidatos del mismo nivel. El enrutamiento por historial
  quedó fuera.
- **AutoMix (2023; NeurIPS 2024).** https://arxiv.org/abs/2310.12963 — Verifica la
  respuesta del modelo pequeño y decide si escala, contemplando el ruido de la
  autoverificación. **En EzOrca:** escalar por fallo comprobable, falta de
  evidencia o riesgo alto, nunca por la confianza que declara el ejecutor.
- **ReWOO (2023).** https://arxiv.org/abs/2305.18323 — Separa planificación,
  herramientas y síntesis para no repetir contexto. **En EzOrca:** dar al
  ejecutor solo el contexto y los criterios que necesita, agrupar lecturas
  independientes y permitir replantear cuando aparece evidencia nueva.
- **AgentCoder (2023).** https://arxiv.org/abs/2312.13010 — Separa programador,
  diseñador de pruebas y ejecutor de pruebas en un ciclo iterativo. **En EzOrca:**
  en lógica de riesgo alto, describir los casos de aceptación antes de
  implementar y dejar que QA compruebe su cobertura.
- **PairCoder (2026).** https://aclanthology.org/2026.findings-acl.149.pdf —
  Reporta menos tokens y mejoras con dos agentes frente a equipos más grandes en
  sus benchmarks. **En EzOrca:** comparar junior + QA antes de crear papeles
  nuevos; no extrapolar las cifras a repositorios reales.
- **Judging the Judges (2024; publicación 2025).**
  https://arxiv.org/abs/2406.07791 — Mide sesgo de posición variable según juez y
  tarea. **En EzOrca:** orden aleatorio en el cribado; en decisiones sensibles,
  repetir con el orden invertido y tratar el desacuerdo como incierto.
- **Beyond the Surface: Measuring Self-Preference (2025).**
  https://aclanthology.org/2025.emnlp-main.86/ — La autopreferencia y el estilo
  sobreviven al anonimizar. **En EzOrca:** etiquetas ciegas y, en decisiones
  críticas, contraste con otra familia de modelos.
- **GEPA (2025).** https://arxiv.org/abs/2507.19457 — Evoluciona prompts con
  trazas y reflexión; reporta menos rollouts que RL en sus experimentos, no
  necesariamente menos costo absoluto. **En EzOrca:** el editor recibe fallos con
  evidencia y hace pocas ediciones dirigidas; se reservan casos que no ve.
- **Do Prompt Optimizers Break Requirements They Are Not Scored On? (2026).**
  https://arxiv.org/abs/2610.13287 — Optimizar exactitud ocultó regresiones de
  formato y contrato. **En EzOrca:** incluir formato y restricciones entre los
  criterios, conservar casos de regresión y contar un truncamiento como medición
  incompleta.
- **Revisiting OPRO (2024).** https://arxiv.org/pdf/2405.10276 — Encuentra
  sensibilidad al meta-prompt y búsqueda cara frente a prompts simples.
  **En EzOrca:** nada de búsquedas automáticas extensas con pocos casos;
  presupuesto fijo y costo de la optimización medido aparte.
- **Lost in the Middle (2024).**
  https://cs.stanford.edu/~nfliu/papers/lost-in-the-middle.tacl2023.pdf — El
  rendimiento cae cuando la evidencia relevante queda en medio de un contexto
  largo. **En EzOrca:** criterios y límites críticos en un bloque breve y visible,
  con enlace a la evidencia original.
- **CompactionBench (2026).**
  https://www.microsoft.com/en-us/research/wp-content/uploads/2026/10/CompactionBench_preprint.pdf —
  Propone evaluar la compactación repetida con tareas ejecutables. **En EzOrca:**
  registro persistente que se relee al retomar o tras compactar; el caso largo
  ejecutable que la fuente propone sigue pendiente.

## Herramientas

- **BMAD Method.** https://docs.bmad-method.org/start/how-bmad-works — Reparto
  PM/arquitecto/dev/QA con historias como fuente de verdad. **En EzOrca:** se
  mantuvo el reparto de papeles; no se añadió la cascada de documentos ni el
  criterio de tamaño por historia.
- **Aider (architect/editor).** https://aider.chat/docs/usage/modes.html — Un
  modelo razona y otro convierte la decisión en ediciones. **En EzOrca:** la
  frontera fija interfaces y criterios; un ejecutor de nivel medio como máximo
  escribe el código y las pruebas.
- **obra/superpowers.** https://github.com/obra/superpowers — Preflight que
  detecta requisitos sin tarea o prueba, línea base limpia y registro durable.
  **En EzOrca:** `run.md`, chequeo de cobertura criterio → tarea → prueba, línea
  base y reproducción antes de editar.
- **GitHub Spec Kit.** https://github.github.com/spec-kit/quickstart.html —
  Especificar, planear, dividir tareas y converger, revalidando artefactos.
  **En EzOrca:** si cambia un criterio, se actualizan las specs dependientes
  antes de lanzarlas.
- **Roo Code Boomerang/Orchestrator.**
  https://docs.roocode.com/features/boomerang-tasks — Instrucciones completas
  hacia abajo y un resumen accionable hacia arriba. **En EzOrca:** ya existía:
  `worker_done` breve y detalle en un reporte por ruta.
- **Kilo Code Orchestrator.**
  https://docs.kilocode.ai/docs/code-with-ai/agents/orchestrator-mode — Su modo
  orquestador está descontinuado; contexto aislado no implica archivos aislados.
  **En EzOrca:** sin orquestador intermedio y con un worktree por editor
  concurrente.
- **Cline Plan/Act.** https://docs.cline.bot/core-workflows/plan-and-act — Plan y
  Act son un ciclo, no una compuerta de un solo sentido. **En EzOrca:** si una
  tarea invalida un supuesto, se pausa esa línea, se replantea y se actualizan
  las tareas dependientes.
- **Claude Code, Codex y OpenCode (subagentes).**
  https://code.claude.com/docs/en/sub-agents ·
  https://developers.openai.com/codex/agent-configuration/subagents ·
  https://opencode.ai/docs/agents/ — Subagentes con contexto, permisos y modelo
  propios; los contratos útiles son ejecutables. **En EzOrca:** un nivel de
  anidamiento, permisos de solo lectura para QA y comprobaciones con salida
  esperada; no se adoptaron hipótesis rivales ni equipos para tareas de rutina.
- **Taskmaster.** https://github.com/eyaltoledano/claude-task-master — Convierte
  un PRD en tareas con dependencias y una cola lista. **En EzOrca:** estados y
  dependencias por tarea en `run.md`; la cola automática no se implementó.
- **Agentless.** https://github.com/OpenAutoCoder/Agentless — Localiza, reproduce,
  parchea y valida; la prueba nueva corre primero sobre el código original.
  **En EzOrca:** reproducción en rojo y localización antes del parche, más cero
  fallos nuevos frente a la línea base.
- **poteto-mode/pstack.**
  https://github.com/backnotprop/pstack — Un hallazgo de comportamiento solo
  sobrevive si un comando lo demuestra. **En EzOrca:** todo hallazgo se corrige
  con comando, salida actual y salida esperada; no se adoptó el debate entre
  modelos.
- **Claude Squad.** https://github.com/smtg-ai/claude-squad — Sesión, rama,
  worktree y diff revisable como unidad de trabajo. **En EzOrca:** ya existía en
  Orca; la puerta de integración añade la revisión del diff antes de aceptar.
- **Vibe Kanban.** https://github.com/BloopAI/vibe-kanban — Revisar el diff y
  devolver el comentario al mismo ejecutor (el proyecto está en cierre).
  **En EzOrca:** los hallazgos vuelven al implementador; otra sesión se usa solo
  para QA independiente o escalado.
- **Overstory.** https://github.com/jayminwest/overstory — Controles mecánicos
  antes que triaje con IA; archivado y sin mantenimiento. **En EzOrca:** puerta
  de integración que compara los archivos tocados con la lista permitida.
- **Gas Town.** https://github.com/gastownhall/gastown — Estado durable y una
  puerta de merge que prueba el resultado combinado. **En EzOrca:** `run.md` y
  comprobaciones del conjunto tras cada integración, retirando el cambio que
  rompe.
- **JITSO.** https://github.com/upex-galaxy/jitso — Lanza cada sesión desde un
  build validado y registra eventos. **En EzOrca:** se tomaron las ideas en
  scripts propios (validar spec, lanzar por tandas, detectar cuelgues, huella y
  alcance); no se adoptó la herramienta porque su lanzamiento no funciona en
  Windows nativo y sus presupuestos no se imponen.
- **Ponytail.** El cambio más pequeño que resuelve todo: reutilizar lo que ya
  existe, no agregar opciones que nadie pidió y nombrar lo omitido y los riesgos.
  **En EzOrca:** plantilla de implementación y orden de revisión de QA (correcto,
  seguro, aguanta la carga, probado, rápido, sin líneas sobrantes).
- **ub-mode.** Prueba primero, unidades pequeñas verificables y probar
  comportamiento, no implementación. **En EzOrca:** se adoptó ese subconjunto;
  el worker no hace commit ni push, porque la integración la hace el Elefante.

## Qué se descartó

No se adoptó ninguna herramienta completa: Orca ya aporta sesiones y worktrees.
Quedaron fuera el debate multi-modelo para tareas rutinarias, la búsqueda
automática de prompts, los equipos de investigadores salvo en bugs ambiguos, un
manager jerárquico (CrewAI, https://docs.crewai.com/en/learn/hierarchical-process)
y un supervisor intermedio (LangGraph,
https://reference.langchain.com/python/langgraph-supervisor/supervisor/create_supervisor):
EzOrca tiene un solo Elefante que acepta y Orca devuelve solo el reporte final.
Los topes de cuota sí son un corte duro: `resources.py` bloquea el plan que
supera el tope de su ventana (5 h, semanal o mensual). Las ideas que sí entraron
están en la skill como reglas cortas o en `scripts/` como comprobaciones
ejecutables.
