Simulacro de coordinación (evaluación de una skill). No ejecutes el encargo: escribe el plan.

Actúa como el coordinador («Elefante») que recibe el encargo del usuario de abajo. Sigue EXCLUSIVAMENTE la skill de esta carpeta: {{VARIANT}}/SKILL.md y los archivos que ella enlace dentro de esa misma carpeta. No cargues desde el sistema de skills `ezorca`, `orca-elephant-goldfish` ni `orchestration`: esas copias no son la que se evalúa. Si la skill de la carpeta te pide leer la guía de Orca u otras ayudas, puedes correr comandos de solo lectura como `orca skills get orchestration`, `orca skills get orchestration --reference references/<archivo>.md`, `orca agent installed --json` y `orca ... --help`.

Prohibido: `worker-start`, `run-create`, `task-create`, `send`, `reply`, `worktree create`, `git` que modifique algo y editar cualquier archivo salvo tu entregable. Las rutas y archivos del encargo pueden ser hipotéticos; no hace falta que existan ni que los leas. Si el encargo declara qué agentes o cuotas tiene el usuario, eso manda sobre el inventario real de esta máquina.

Encargo del usuario:
«{{PROMPT}}»

Entregable: escribe {{OUT}} con tu plan completo como coordinador, en español:
1. Modalidad elegida y por qué.
2. Agentes y papeles asignados, con el motivo de cada elección.
3. Comandos exactos en el orden en que los correrías (incluidos los de solo lectura).
4. Texto completo de cada spec de Goldfish.
5. Dónde terminas el turno y qué harás en cada despertar posible (worker_done con éxito o fallo, pregunta, escalada, fallo de arranque).
6. Cómo cierras: integración, comprobaciones e informe al usuario.
No menciones la ruta de la carpeta de la skill ni ningún nombre de variante o versión en el plan.

Reporta con worker_done solo una línea con la ruta del archivo.
