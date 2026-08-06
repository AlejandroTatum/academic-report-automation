#!/usr/bin/env python3
"""Build the SO class-work PDF: Máquinas Virtuales y Contenedores.

Sequential test for the academic-visual-builder flow:
- requires generated visuals
- builds HTML intermediate in backups
- exports final PDF to outputs/sistemas-operativos/
- validates final text and figures
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from report_config import CONTENT_ROOT

ROOT = Path(__file__).resolve().parents[1]
# Institutional logo ships with the code; figures, deliverables and backups are content.
LOGO = ROOT / "assets" / "unl-logo-aa1-transparent.png"
ASSETS = CONTENT_ROOT / "assets" / "generated" / "sistemas-operativos" / "maquinas-virtuales-contenedores"
OUTPUTS = CONTENT_ROOT / "outputs" / "sistemas-operativos"
BACKUPS = CONTENT_ROOT / "backups"
FINAL_NAME = "trabajo_clase_vm_contenedores.pdf"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"FAILED: {' '.join(cmd)}")
    if proc.stdout.strip():
        print(proc.stdout.strip())
    return proc


def require(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Missing {label}: {path}")


def figure_html(filename: str, caption: str) -> str:
    path = ASSETS / filename
    require(path, f"figure {filename}")
    return f"""
    <figure>
      <img src="{path.as_uri()}" alt="{html.escape(caption)}">
      <figcaption>{html.escape(caption)}</figcaption>
    </figure>
    """


def logo_uri() -> str:
    require(LOGO, "UNL logo")
    return LOGO.as_uri()


def html_document() -> str:
    fig1 = figure_html("figura-1-arquitectura-vm-contenedor.png", "Figura 1. Arquitectura comparativa entre una máquina virtual y un contenedor.")
    fig2 = figure_html("figura-2-comparativa-vm-contenedor.png", "Figura 2. Comparativa relativa de ventajas y desventajas entre máquinas virtuales y contenedores.")
    fig3 = figure_html("figura-3-arbol-decision-vm-contenedor.png", "Figura 3. Árbol de decisión para elegir entre máquina virtual y contenedor según el contexto.")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Trabajo intra-clase - Máquinas Virtuales y Contenedores</title>
<style>
@page {{ size: A4; margin: 2.5cm; }}
body {{ margin: 0; font-family: 'Times New Roman', 'Liberation Serif', Arial, serif; color: #111; font-size: 12pt; line-height: 1.24; }}
.cover {{ height: 23.2cm; page-break-after: always; display: flex; flex-direction: column; justify-content: space-between; align-items: stretch; }}
.logo {{ text-align: center; margin-top: .25cm; }}
.logo img {{ width: 3.15cm; height: auto; }}
.uni {{ text-align: center; font-weight: 700; font-size: 14pt; line-height: 1.28; margin-bottom: 12px; }}
.title {{ text-align: center; font-weight: 700; font-size: 15.5pt; text-transform: uppercase; margin: 18px 0; }}
table.meta {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
table.meta td {{ border: 1px solid #333; padding: 7px 9px; vertical-align: top; }}
table.meta td:first-child {{ width: 28%; font-weight: 700; background: #f2f2f2; }}
h1 {{ font-size: 14pt; margin: 13px 0 6px; }}
h2 {{ font-size: 12.3pt; margin: 10px 0 5px; }}
p {{ text-align: justify; margin: 0 0 6px; text-indent: 1.27cm; }}
ul {{ margin-top: 4px; }}
figure {{ margin: 7px auto 9px; page-break-inside: avoid; text-align: center; }}
figure img {{ max-width: 100%; max-height: 8.15cm; object-fit: contain; }}
figure.compact img {{ max-height: 7.35cm; }}
figcaption {{ font-size: 10pt; font-style: italic; margin-top: 4px; }}
table.compare {{ width: 100%; border-collapse: collapse; margin: 7px 0 9px; page-break-inside: avoid; font-size: 10.5pt; }}
table.compare th, table.compare td {{ border: 1px solid #333; padding: 5px; vertical-align: top; }}
table.compare th {{ background: #eaeaea; text-align: center; }}
.refs p {{ text-align: left; padding-left: 1.1cm; text-indent: -1.1cm; font-size: 10.8pt; }}
.footer-note {{ text-align: center; margin-top: 30px; font-size: 10pt; text-indent: 0; }}
</style>
</head>
<body>
<section class="cover">
  <div>
  <div class="logo"><img src="{logo_uri()}" alt="Logo Universidad Nacional de Loja"></div>
  <div class="uni">UNIVERSIDAD NACIONAL DE LOJA<br>FACULTAD DE LA ENERGÍA, LAS INDUSTRIAS Y LOS RECURSOS NATURALES NO RENOVABLES<br>CARRERA DE COMPUTACIÓN</div>
  <div class="title">Trabajo intra-clase<br>Máquinas Virtuales y Contenedores</div>
  <table class="meta">
    <tr><td>Nombre:</td><td>Alejandro Emanuel Padilla Espinoza</td></tr>
    <tr><td>Paralelo:</td><td>A</td></tr>
    <tr><td>Fecha:</td><td>3 de mayo de 2026</td></tr>
    <tr><td>Asignatura:</td><td>Sistemas Operativos</td></tr>
    <tr><td>Docente:</td><td>Ing. Hernán Leonardo Torres Carrión M.Sc.</td></tr>
  </table>
  </div>
  <p class="footer-note">Ciudad Universitaria “Guillermo Falconí Espinosa”</p>
</section>

<h1>1. Tema</h1>
<p>Máquinas virtuales y contenedores: análisis de ventajas, desventajas, comparación técnica y criterio de uso recomendado en Sistemas Operativos.</p>

<h1>2. Antecedentes</h1>
<p>El presente trabajo intra-clase analiza dos mecanismos usados para ejecutar aplicaciones de forma aislada: las máquinas virtuales y los contenedores. Ambos conceptos pertenecen al campo de la virtualización, pero no resuelven el problema de la misma manera. Una máquina virtual abstrae hardware y permite ejecutar un sistema operativo invitado completo; en cambio, un contenedor aísla procesos y dependencias de una aplicación usando el kernel del sistema anfitrión.</p>
<p>En Sistemas Operativos, esta diferencia es importante porque afecta recursos, seguridad, compatibilidad, administración y despliegue. El texto base de Silberschatz, Galvin y Gagne incluye virtualización, VMM/hypervisors y contenedores como temas relacionados con la organización moderna de los sistemas operativos [1]. Docker define los contenedores como procesos aislados que empaquetan lo necesario para ejecutar componentes de una aplicación, y resalta su portabilidad e independencia [2]. Microsoft, por su parte, compara ambas tecnologías indicando que las máquinas virtuales ejecutan un sistema operativo completo, mientras que los contenedores usan menos recursos al apoyarse en el kernel del host [3].</p>

<h1>3. Descripción</h1>
<h2>3.1 Máquinas virtuales</h2>
<p>Una máquina virtual es un entorno que simula una computadora completa sobre hardware físico. Para lograrlo, utiliza un monitor de máquina virtual o hipervisor, encargado de crear, ejecutar y administrar sistemas operativos invitados. La principal ventaja es el aislamiento fuerte: cada VM tiene su propio sistema operativo, su kernel, sus servicios y sus recursos virtualizados. Esto permite ejecutar sistemas operativos distintos sobre un mismo equipo físico y mantener separados entornos con diferentes requisitos de seguridad o compatibilidad.</p>
<p>Sus desventajas aparecen en el consumo de recursos y en el tiempo de administración. Al ejecutar un sistema operativo completo por cada instancia, una VM requiere más memoria, almacenamiento y tiempo de arranque. También exige actualizar y administrar cada sistema operativo invitado, lo cual puede aumentar el esfuerzo operativo cuando existen muchas instancias.</p>
{fig1}

<h2>3.2 Contenedores</h2>
<p>Un contenedor empaqueta una aplicación con sus dependencias y la ejecuta como un proceso aislado. A diferencia de una VM, no incluye un kernel propio completo, sino que comparte el kernel del sistema anfitrión. Por eso suele iniciar más rápido, ocupar menos espacio y permitir mayor densidad de aplicaciones en la misma infraestructura.</p>
<p>Sus ventajas principales son portabilidad, rapidez de despliegue, facilidad para reproducir entornos y eficiencia en el uso de recursos. Sin embargo, su aislamiento normalmente es más ligero que el de una VM, y su compatibilidad depende más del sistema operativo anfitrión y del runtime usado. Por esta razón, los contenedores no sustituyen completamente a las máquinas virtuales; más bien se complementan.</p>

<h2>3.3 Comparativa técnica</h2>
<table class="compare">
<tr><th>Criterio</th><th>Máquina virtual</th><th>Contenedor</th></tr>
<tr><td>Aislamiento</td><td>Fuerte, porque cada VM tiene un sistema operativo invitado completo.</td><td>Ligero, porque comparte kernel con el host, aunque puede reforzarse con mecanismos adicionales.</td></tr>
<tr><td>Consumo de recursos</td><td>Mayor consumo de CPU, memoria y almacenamiento.</td><td>Menor consumo relativo; permite ejecutar más aplicaciones en la misma infraestructura.</td></tr>
<tr><td>Compatibilidad</td><td>Permite ejecutar sistemas operativos diferentes.</td><td>Depende del kernel y del sistema operativo base compatible.</td></tr>
<tr><td>Arranque y despliegue</td><td>Más lento, porque inicia un sistema operativo completo.</td><td>Más rápido, porque inicia procesos aislados y dependencias empaquetadas.</td></tr>
<tr><td>Uso recomendado</td><td>Entornos legacy, laboratorios completos, aislamiento fuerte y sistemas operativos distintos.</td><td>Microservicios, despliegue continuo, portabilidad de aplicaciones y escalado rápido.</td></tr>
</table>
{fig2}

<h2>3.4 Criterio de uso recomendado</h2>
<p>La mejor opción depende del objetivo técnico. Si se necesita ejecutar otro sistema operativo, mantener una frontera de seguridad fuerte o reproducir un entorno completo, conviene usar una máquina virtual. Si la prioridad es desplegar aplicaciones de forma rápida, portable y con menor consumo de recursos, conviene usar contenedores. En escenarios modernos es común combinarlos: la infraestructura puede estar compuesta por VMs, y dentro de ellas ejecutarse múltiples contenedores.</p>
{fig3}

<h1>4. Conclusiones</h1>
<p>Las máquinas virtuales son la opción más segura cuando el trabajo exige ejecutar un sistema operativo completo, conservar compatibilidad con plataformas distintas o aislar entornos que no deben compartir kernel. Su mayor consumo de memoria, almacenamiento y tiempo de arranque se justifica cuando la prioridad es separar fallos, permisos y configuraciones.</p>
<p>Los contenedores resultan más convenientes para desplegar aplicaciones modernas con rapidez, portabilidad y menor uso de recursos. Su valor aparece especialmente en microservicios, pruebas reproducibles y escalado frecuente, porque encapsulan dependencias sin cargar un sistema operativo completo por cada instancia.</p>
<p>Elegir entre ambas tecnologías no debe plantearse como una competencia absoluta. Una infraestructura bien diseñada puede usar máquinas virtuales como base de aislamiento y, dentro de ellas, contenedores para distribuir aplicaciones; lo importante es reconocer si el problema necesita aislar un sistema operativo completo o solamente una aplicación con sus dependencias.</p>

<h1>5. Bibliografía</h1>
<section class="refs">
<p>[1] A. Silberschatz, P. B. Galvin, and G. Gagne, <em>Operating System Concepts</em>, 10th ed. Hoboken, NJ, USA: Wiley, 2018.</p>
<p>[2] Docker Inc., “What is a container?,” Docker Docs, 2026. [En línea]. Disponible: https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/</p>
<p>[3] Microsoft, “Containers vs. virtual machines,” Microsoft Learn, actualizado el 22 de enero de 2025. [En línea]. Disponible: https://learn.microsoft.com/en-us/virtualization/windowscontainers/about/containers-vs-vm</p>
</section>
</body>
</html>"""


def validate_inputs() -> None:
    for filename in [
        "figura-1-arquitectura-vm-contenedor.png",
        "figura-2-comparativa-vm-contenedor.png",
        "figura-3-arbol-decision-vm-contenedor.png",
        "figures.yml",
    ]:
        require(ASSETS / filename, filename)


def validate_pdf(pdf: Path) -> None:
    require(pdf, "final PDF")
    info = run(["pdfinfo", str(pdf)]).stdout
    pages_match = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
    if not pages_match:
        raise SystemExit("PDF validation failed: page count unavailable")
    page_count = int(pages_match.group(1))
    if page_count < 2:
        raise SystemExit("PDF validation failed: cover is not separated from body")
    images = run(["pdfimages", "-list", str(pdf)]).stdout
    if not re.search(r"^\s*1\s+\d+\s+image\s+", images, re.MULTILINE):
        raise SystemExit("PDF validation failed: UNL logo/image not embedded on cover page")
    text = run(["pdftotext", "-layout", str(pdf), "-"]).stdout
    if "\f1. Tema" not in text:
        raise SystemExit("PDF validation failed: body does not start after cover page")
    lower = text.lower()
    banned = ["se concluye", "en conclusión", "en conclusion"]
    found_banned = [item for item in banned if item in lower]
    if found_banned:
        raise SystemExit("PDF validation failed, banned conclusion opener: " + ", ".join(found_banned))
    required = [
        "MÁQUINAS VIRTUALES Y CONTENEDORES",
        "1. Tema",
        "2. Antecedentes",
        "3. Descripción",
        "4. Conclusiones",
        "5. Bibliografía",
        "Figura 1",
        "Figura 2",
        "Figura 3",
        "Operating System Concepts",
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit("PDF validation failed, missing: " + ", ".join(missing))
    if not LOGO.exists():
        raise SystemExit("PDF validation failed: missing UNL logo asset")


def main() -> None:
    validate_inputs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUPS / f"vm_contenedores_{ts}"
    staging = backup_dir / "staging"
    validation = backup_dir / "validation_pages"
    staging.mkdir(parents=True, exist_ok=True)
    validation.mkdir(parents=True, exist_ok=True)

    html_path = staging / "trabajo_clase_vm_contenedores.html"
    pdf_staging = staging / FINAL_NAME
    html_path.write_text(html_document(), encoding="utf-8")

    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise SystemExit("Falta WeasyPrint en el entorno Python local") from exc

    HTML(filename=str(html_path)).write_pdf(pdf_staging)
    validate_pdf(pdf_staging)
    run(["pdftoppm", "-png", "-r", "120", str(pdf_staging), str(validation / "page")])

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    final_pdf = OUTPUTS / FINAL_NAME
    if final_pdf.exists():
        shutil.move(str(final_pdf), str(backup_dir / final_pdf.name))
    shutil.copy2(pdf_staging, final_pdf)
    validate_pdf(final_pdf)
    print(f"FINAL_PDF={final_pdf}")
    print(f"BACKUP_DIR={backup_dir}")


if __name__ == "__main__":
    main()
