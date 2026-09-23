# Corpus de contextos (issue #13, R10/R11)

Seis contextos con nombre (spec `test_issue_13_context_matrix_is_deterministic`),
cada uno con su propia tabla dirigida, para demostrar selección end-to-end
y calidad renderizada across el pipeline HTML/PDF (WeasyPrint).

## Corto

<!-- table-style: corpus-short purpose=reference -->
| Nombre | Puntaje |
| ------ | ------- |
| Ana    | 9       |
| Luis   | 7       |

## Largo

<!-- table-style: corpus-long purpose=reference -->
| Código | Descripción | Estado |
| ------ | ------------ | ------ |
| Item-01 | Descripción de referencia larga para forzar el ajuste de línea en la fila 01 de esta tabla de demostración | Estado OK |
| Item-02 | Descripción de referencia larga para forzar el ajuste de línea en la fila 02 de esta tabla de demostración | Estado OK |
| Item-03 | Descripción de referencia larga para forzar el ajuste de línea en la fila 03 de esta tabla de demostración | Estado Pendiente |
| Item-04 | Descripción de referencia larga para forzar el ajuste de línea en la fila 04 de esta tabla de demostración | Estado OK |
| Item-05 | Descripción de referencia larga para forzar el ajuste de línea en la fila 05 de esta tabla de demostración | Estado OK |
| Item-06 | Descripción de referencia larga para forzar el ajuste de línea en la fila 06 de esta tabla de demostración | Estado Pendiente |
| Item-07 | Descripción de referencia larga para forzar el ajuste de línea en la fila 07 de esta tabla de demostración | Estado OK |
| Item-08 | Descripción de referencia larga para forzar el ajuste de línea en la fila 08 de esta tabla de demostración | Estado OK |

## Comparación

<!-- table-style: corpus-comparison purpose=comparison meaning=comparison emphasis=column emphasis_column=2 -->
| Criterio | Método A | Método recomendado |
| -------- | -------- | ------------------- |
| Costo    | Alto     | Bajo                |
| Tiempo   | Medio    | Bajo                |

## Estado

<!-- table-style: corpus-status purpose=status meaning=status -->
| Componente | Estado |
| ---------- | ------ |
| API        | [[status:ok]] |
| Cache      | [[status:fail]] |
| Cola       | [[status:warn]] |

## Denso

<!-- table-style: corpus-dense purpose=dense -->
| A | B | C | D | E | F |
| --- | --- | --- | --- | --- | --- |
| 1 | 2 | 3 | 4 | 5 | 6 |
| 7 | 8 | 9 | 10 | 11 | 12 |

## Multipágina

<!-- table-style: corpus-multipage purpose=reference -->
| Código | Descripción | Estado |
| ------ | ------------ | ------ |
| Item-01 | Descripción de referencia larga para forzar el ajuste de línea en la fila 01 de esta tabla de demostración | Estado OK |
| Item-02 | Descripción de referencia larga para forzar el ajuste de línea en la fila 02 de esta tabla de demostración | Estado OK |
| Item-03 | Descripción de referencia larga para forzar el ajuste de línea en la fila 03 de esta tabla de demostración | Estado Pendiente |
| Item-04 | Descripción de referencia larga para forzar el ajuste de línea en la fila 04 de esta tabla de demostración | Estado OK |
| Item-05 | Descripción de referencia larga para forzar el ajuste de línea en la fila 05 de esta tabla de demostración | Estado OK |
| Item-06 | Descripción de referencia larga para forzar el ajuste de línea en la fila 06 de esta tabla de demostración | Estado Pendiente |
| Item-07 | Descripción de referencia larga para forzar el ajuste de línea en la fila 07 de esta tabla de demostración | Estado OK |
| Item-08 | Descripción de referencia larga para forzar el ajuste de línea en la fila 08 de esta tabla de demostración | Estado OK |
| Item-09 | Descripción de referencia larga para forzar el ajuste de línea en la fila 09 de esta tabla de demostración | Estado Pendiente |
| Item-10 | Descripción de referencia larga para forzar el ajuste de línea en la fila 10 de esta tabla de demostración | Estado OK |
| Item-11 | Descripción de referencia larga para forzar el ajuste de línea en la fila 11 de esta tabla de demostración | Estado OK |
| Item-12 | Descripción de referencia larga para forzar el ajuste de línea en la fila 12 de esta tabla de demostración | Estado Pendiente |
| Item-13 | Descripción de referencia larga para forzar el ajuste de línea en la fila 13 de esta tabla de demostración | Estado OK |
| Item-14 | Descripción de referencia larga para forzar el ajuste de línea en la fila 14 de esta tabla de demostración | Estado OK |
| Item-15 | Descripción de referencia larga para forzar el ajuste de línea en la fila 15 de esta tabla de demostración | Estado Pendiente |
| Item-16 | Descripción de referencia larga para forzar el ajuste de línea en la fila 16 de esta tabla de demostración | Estado OK |
| Item-17 | Descripción de referencia larga para forzar el ajuste de línea en la fila 17 de esta tabla de demostración | Estado OK |
| Item-18 | Descripción de referencia larga para forzar el ajuste de línea en la fila 18 de esta tabla de demostración | Estado Pendiente |
| Item-19 | Descripción de referencia larga para forzar el ajuste de línea en la fila 19 de esta tabla de demostración | Estado OK |
| Item-20 | Descripción de referencia larga para forzar el ajuste de línea en la fila 20 de esta tabla de demostración | Estado OK |
| Item-21 | Descripción de referencia larga para forzar el ajuste de línea en la fila 21 de esta tabla de demostración | Estado Pendiente |
| Item-22 | Descripción de referencia larga para forzar el ajuste de línea en la fila 22 de esta tabla de demostración | Estado OK |
| Item-23 | Descripción de referencia larga para forzar el ajuste de línea en la fila 23 de esta tabla de demostración | Estado OK |
| Item-24 | Descripción de referencia larga para forzar el ajuste de línea en la fila 24 de esta tabla de demostración | Estado Pendiente |
| Item-25 | Descripción de referencia larga para forzar el ajuste de línea en la fila 25 de esta tabla de demostración | Estado OK |
| Item-26 | Descripción de referencia larga para forzar el ajuste de línea en la fila 26 de esta tabla de demostración | Estado OK |
| Item-27 | Descripción de referencia larga para forzar el ajuste de línea en la fila 27 de esta tabla de demostración | Estado Pendiente |
| Item-28 | Descripción de referencia larga para forzar el ajuste de línea en la fila 28 de esta tabla de demostración | Estado OK |
| Item-29 | Descripción de referencia larga para forzar el ajuste de línea en la fila 29 de esta tabla de demostración | Estado OK |
| Item-30 | Descripción de referencia larga para forzar el ajuste de línea en la fila 30 de esta tabla de demostración | Estado Pendiente |
| Item-31 | Descripción de referencia larga para forzar el ajuste de línea en la fila 31 de esta tabla de demostración | Estado OK |
| Item-32 | Descripción de referencia larga para forzar el ajuste de línea en la fila 32 de esta tabla de demostración | Estado OK |
| Item-33 | Descripción de referencia larga para forzar el ajuste de línea en la fila 33 de esta tabla de demostración | Estado Pendiente |
| Item-34 | Descripción de referencia larga para forzar el ajuste de línea en la fila 34 de esta tabla de demostración | Estado OK |
| Item-35 | Descripción de referencia larga para forzar el ajuste de línea en la fila 35 de esta tabla de demostración | Estado OK |
| Item-36 | Descripción de referencia larga para forzar el ajuste de línea en la fila 36 de esta tabla de demostración | Estado Pendiente |
| Item-37 | Descripción de referencia larga para forzar el ajuste de línea en la fila 37 de esta tabla de demostración | Estado OK |
| Item-38 | Descripción de referencia larga para forzar el ajuste de línea en la fila 38 de esta tabla de demostración | Estado OK |
| Item-39 | Descripción de referencia larga para forzar el ajuste de línea en la fila 39 de esta tabla de demostración | Estado Pendiente |
| Item-40 | Descripción de referencia larga para forzar el ajuste de línea en la fila 40 de esta tabla de demostración | Estado OK |
