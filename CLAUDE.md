# E-ink goals display

Waveshare 7.5" raw e-ink panel (800×480, 1-bit) + Pi Zero 2 W in a printed stand.
`PLAN.md` is the live checklist: read it first, tick items as they land.

- `eink/` — Python package that runs on the Pi. `render.py` draws the exact panel image,
  `state.py` loads `data/goals.toml`, `display.py` has the panel and PNG backends.
- `cad/stand.py` — parametric CadQuery model; prints an interference check and writes `design/stl/`.
  Constants marked VERIFY/assumed are unmeasured.
- `cad/render_blender.py` — headless renders into `design/`.

Commands are at the bottom of `PLAN.md`. Run pytest after any render change; a deliberate
visual change needs `UPDATE_GOLDEN=1`.
