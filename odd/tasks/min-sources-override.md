# Min sources override

Goal: let a report declare a lower source minimum in `report.yml`
(`min_sources: <positive int>`) so an exercise whose teacher requires citing only
the base book can pass research and verify. Default stays 5.

Motivation: reports/metodos-numericos-ejercicio-1-5 must cite only Chapra & Canale
7th ed.; `content_check.py` requires >= 5 cited eligible sources.

## Tasks

- [ ] 1. `min_sources` override honored by `source_count.source_gate` (doc_status research gate) and `content_check` cited-source check, with tests (RED → GREEN) and skill docs updated.
- [ ] 2. Apply to the ejercicio 1.5 report and continue verify.
