# Instalación

La raíz de este repositorio **es** la carpeta de la skill: quien lo clona en su carpeta de skills ya la tiene instalada, sin pasos de compilación.

## Requisitos

| Requisito | Cómo comprobarlo | Qué esperar |
|---|---|---|
| Orca con su CLI | `orca --version` | Una versión, por ejemplo `1.4.273` |
| Al menos un agente instalado en Orca | `orca agent installed --json` | JSON con `ok: true` y al menos un agente en `agents` (`claude`, `codex`, `opencode`, …) |
| Python 3.11 o superior | `python --version` | `Python 3.11` o mayor |

No hay dependencias que instalar: los scripts usan solo la biblioteca estándar.

## Instalar

```sh
git clone https://github.com/JDMoreu/ezorca.git ~/.agents/skills/ezorca
```

Esa ruta es la que leen Orca y la mayoría de los agentes compatibles.

**Claude Code.** Además de la anterior, reconoce `~/.claude/skills/`. Puedes clonar directo en esa carpeta o, mejor, dejar una sola copia y enlazarla, para que un `git pull` actualice todas las instalaciones a la vez:

```sh
git clone https://github.com/JDMoreu/ezorca.git ~/.claude/skills/ezorca
ln -s ~/.agents/skills/ezorca ~/.claude/skills/ezorca   # alternativa con una sola copia
```

**Windows.** Las mismas rutas bajo `%USERPROFILE%`: `%USERPROFILE%\.agents\skills\ezorca` y `%USERPROFILE%\.claude\skills\ezorca`. En PowerShell: `git clone https://github.com/JDMoreu/ezorca.git "$env:USERPROFILE\.agents\skills\ezorca"`. Si el enlace simbólico pide permisos de administrador, usa una copia o un enlace de directorio con `mklink /D`.

## Verificar

```sh
python ~/.agents/skills/ezorca/scripts/discover.py
```

Debe imprimir un JSON con `agents` y `models`, y terminar con exit 0. Si falla con exit 2, no pudo hablar con Orca o con `opencode models`: revisa que `orca` esté en el PATH y que haya al menos un agente instalado. En PowerShell: `python "$env:USERPROFILE\.agents\skills\ezorca\scripts\discover.py"`.

Prueba rápida de que la skill se carga: pide en un chat de Orca «Usa EzOrca para <una tarea pequeña>» y comprueba que responde con un plan por papel (los que la tarea necesite; son adaptativos) antes de tocar código.

## Actualizar

```sh
cd ~/.agents/skills/ezorca
git pull
```

Si usaste una copia en lugar de un enlace, repite el `git pull` en cada copia. Revisa [CHANGELOG.md](../CHANGELOG.md) antes de actualizar en medio de un Run: un cambio de reglas a mitad de trabajo descoloca los encargos ya escritos.

## Desinstalar

```sh
rm -rf ~/.agents/skills/ezorca
```

Si creaste un enlace en `~/.claude/skills/ezorca`, bórralo también; si clonaste dos veces, borra las dos copias. No queda nada más en el sistema: los scripts no escriben fuera de las rutas que les pasas.

En Windows: `rmdir /s /q "%USERPROFILE%\.agents\skills\ezorca"`.

## Ajustar la clasificación de modelos

`scripts/resources.py` traduce el precio de salida por millón a escalones usando los límites ordenados de `scripts/tiers.json`; el nombre no decide:

`discover.py` conserva el inventario, deja `tier: null` para precio desconocido y regenera cachés que usaban reglas por nombre. Esos modelos se muestran para diagnóstico, pero nunca se declaran elegibles.
