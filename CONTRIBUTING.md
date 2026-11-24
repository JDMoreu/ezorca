# Cómo contribuir

## Pruebas

Desde la raíz del repo:

```sh
python -m unittest discover -s scripts/tests -v
```

Las pruebas crean repositorios git temporales; si tu equipo no tiene identidad
configurada, ejecuta antes `git config --global user.email` y `user.name`.

## Reglas de los scripts

- Solo biblioteca estándar de Python 3.11 o superior.
- Máximo 200 líneas por script.
- La salida por stdout es JSON; los diagnósticos van a stderr.
- Exit 0 si todo va bien, 1 si una comprobación sale negativa y 2 si el uso o los datos son inválidos.
- La ejecución de comandos pasa por `run_cmd`, sustituible en las pruebas.
- Nunca `shell=True` ni comandos armados como cadena.

## Proponer cambios a la skill

1. Añade o ajusta los casos fijos que cubran el cambio.
2. Corre las pruebas y deja el resultado en la descripción del cambio.
3. Si cambia el comportamiento de la skill, mide el cambio con una evaluación
   ciega y el comparador; el procedimiento está en `docs/evaluation.md`.
4. Envía el cambio con qué problema resuelve, qué evidencia lo respalda y qué
   queda pendiente.
