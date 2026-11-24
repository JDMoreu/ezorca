Juez ciego de dos planes de coordinación (solo lectura salvo tus dos archivos de salida).

Dos coordinadores recibieron el mismo encargo y cada uno escribió un plan (comandos de Orca, specs de agentes worker, decisiones y fronteras de turno). Juzga CADA plan por separado contra los mismos criterios; no los compares entre sí ni dejes que uno influya en el juicio del otro. No leas ningún otro archivo de la carpeta de evaluación (ni otros planes, ni mapas, ni skills, ni juicios, ni notas). No ejecutes comandos que cambien el estado de Orca ni de git. No delegues.

Encargo que recibieron:
«{{PROMPT}}»

Plan P1: {{T1}}
Plan P2: {{T2}}

Criterios («passed: true» solo si el plan lo cumple de forma explícita y observable; si es ambiguo o lo omite, false):
{{CRITERIA}}

Entregables (JSON válido, un objeto por criterio en el mismo orden, repeat = 1, evidencia = cita breve del plan o motivo del fallo, máximo 300 caracteres):
- Juicio de P1 en {{O1}}
- Juicio de P2 en {{O2}}
Formato de cada archivo: {"judgments": [{"case": "{{CASE}}", "criterion": "<id>", "repeat": 1, "passed": true, "evidence": "..."}]}

Valida ambos archivos como JSON antes de terminar. Reporta con worker_done una línea: aciertos de P1 y de P2.
