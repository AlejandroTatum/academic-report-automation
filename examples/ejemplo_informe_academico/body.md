# Tema

Estructura mínima de un informe académico construido con este pipeline.

# Antecedentes

Un trabajo se escribe en Markdown y se compone en LaTeX. La separación existe
para que la redacción no compita con el formato: el texto vive en `body.md`, las
fuentes en `sources.bib` y las decisiones de entrega en `report.yml`. La
plantilla institucional, los márgenes y la numeración quedan del lado de la
plantilla, no del autor.

Las citas se escriben con la clave de la entrada BibTeX entre corchetes, como en
este ejemplo, que remite al manual de estilo de la IEEE [@ieee-style]. El
validador comprueba que cada cita del cuerpo tenga su entrada y que ninguna
entrada quede sin citar.

# Desarrollo

La carpeta que se entrega contiene solo fuentes:

- `report.yml`: tipo, backend, ruta documental, metadata y destino del PDF final.
- `body.md`: el contenido, con títulos en Markdown (`#`, `##`) y no en negrita.
- `sources.bib`: las referencias citadas, en formato BibTeX.

Todo lo demás lo genera el pipeline. `build/` guarda el `.tex` y los registros de
compilación, `backups/` el reporte de calidad, y el PDF final se escribe en
`outputs/<materia>/` del árbol de contenido. Esa última regla es la que evita
duplicados: si el entregable también se copiara junto al trabajo, habría dos
archivos con el mismo nombre y ninguna forma de saber cuál se entregó.

# Conclusiones

Un ejemplo sirve como ejemplo solo si cumple las mismas reglas que cualquier
otro trabajo. Este las cumple sin excepciones: el nombre de la carpeta no lleva
prefijo especial, la ruta documental está declarada y el PDF final apunta al
único lugar que el validador acepta.
