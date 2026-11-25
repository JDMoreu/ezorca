# Resultados de evaluación

En la ronda inicial del CLI se iniciaron 25 combinaciones con esfuerzo low; cada sesión terminó por incompatibilidad del modelo con la cuenta disponible antes de producir una respuesta. No se ejecutaron los argv propuestos.

La ronda Orca produjo 25 respuestas independientes. La reevaluación examinó los mismos archivos congelados sin volver a ejecutar candidatos. Cada celda muestra el veredicto original → reevaluado: P pasa, F1 falla con código 1 y F2 indica datos o uso inválidos con código 2. Las celdas con F1 o F2 reevaluado se deben repetir.

| Modelo | resources | choose | wave | spec | done |
|---|---|---|---|---|---|
| gpt-5.6-luna | F1 → F1 | F1 → P | F1 → F1 | F1 → F1 | P → P |
| gpt-6-luna | F2 → F1 | F2 → F2 | F2 → F1 | F2 → F1 | F2 → P |
| gpt-6.1-sol | P → P | P → P | F1 → F1 | F1 → F1 | P → P |
| gpt-6.1-terra | P → P | P → P | F1 → F1 | F1 → F1 | P → P |
| gpt-6.2-sol | P → P | P → P | F1 → F1 | F1 → F1 | P → P |

El veredicto original registró 10/25 pases; la reevaluación registró 12/25 pases y 13 fallos (12 con código 1 y uno con código 2). Los datos en bruto se conservaron localmente.
