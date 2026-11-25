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

## Matriz final auditada

Se repitieron únicamente las 13 celdas fallidas de la reevaluación. Con el verificador de c6a3209, esas repeticiones dieron 7/13; la auditoría posterior reconoce tres paráfrasis válidas de spec y obtiene 10/13. La reevaluación auditada de las 25 respuestas originales conserva 12/25 pases. Al combinar sus 12 pases arrastrados con las 13 repeticiones se obtienen 22/25 pases; no es un nuevo recuento histórico.

P = pase, F1 = rechazo con código 1; A = respuesta original arrastrada, R = repetición. Cada celda muestra el resultado auditado de la respuesta seleccionada.

| Modelo | resources | choose | wave | spec | done |
|---|---|---|---|---|---|
| gpt-5.6-luna | P R | P A | F1 R | F1 R | P A |
| gpt-6-luna | P R | P R | F1 R | P R | P A |
| gpt-6.1-sol | P A | P A | P R | P R | P A |
| gpt-6.1-terra | P A | P A | P R | P R | P A |
| gpt-6.2-sol | P A | P A | P R | P R | P A |

Los tres rechazos restantes son reproducibles: gpt-5.6-luna omite `python` en wave y spec; además su spec asigna 80 al día, 95 a la semana y 90 al mes. gpt-6-luna propone en wave un nombre de archivo distinto del que proporciona. En este diseño, tras dos intentos insuficientes, ninguno de los dos Luna debe asumir tandas sin validación; gpt-5.6-luna tampoco debe asumir encargos spec sin validación. Estas observaciones se limitan a los casos medidos.

El ajuste acepta reservas y dos exclusiones sintéticas expresadas por separado, 5h, 5 h o 5 horas y la negación explícita de acceso a la red. Se mantienen las asociaciones de topes y el control de forma con check_spec; ninguna llamada propuesta se ejecutó.
