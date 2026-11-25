# Evaluación de llamadas de herramientas

Estos cinco retos separan la propuesta de una llamada de su ejecución. Cada escenario de `cases.json` tiene un `id` estable, contexto y una respuesta esperada solo en los fixtures del verificador; la entrada que recibe el modelo no contiene esas respuestas.

Obtén el prompt público (título, contexto y contrato, sin `expected`) con:

```text
python eval/tools/prompt.py wave
```

## Uso

Pide al modelo cargar esta versión de la skill, sin darle soluciones, y producir un archivo JSON por escenario o sesión con esta forma:

```json
{"argv": ["python", "scripts/...py", "..."], "files": {"nombre.md": "contenido"}}
```

`files` solo se usa cuando el reto lo pide. Validar una propuesta no ejecuta la llamada propuesta: `verify.py` compara semántica, invoca los validadores reales con argumentos fijados y temporales controlados, y en wave exige `--dry-run`; nunca llama `worker-start` ni `orca`.

```text
python eval/tools/verify.py resources respuesta.json
```

Exit 0 significa que pasa; 1, respuesta válida pero conducta incorrecta; 2, uso o datos mal formados. No se pasan argumentos de la respuesta a una shell. Para una matriz modelo × escenario, conserva una fila por modelo, escenario, repetición, código y evidencia; `RESULTADOS.md` se escribirá después con datos vivos.
