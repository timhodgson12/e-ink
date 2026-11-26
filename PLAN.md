# E-ink goals display — plan & checklist

Desk display: Waveshare 7.5" raw e-ink panel (800×480) + Raspberry Pi Zero 2 W, in a
printed frame-and-wedge stand, showing today's goals, time blocks and habits.

Status legend: [ ] todo · [x] done · [?] needs Tim

## 0. Proposals
- [x] UI mockup, native 800×480 1-bit — `design/ui_mockup.png` (`eink/render.py`)
- [x] Stand proposal — `design/stand_proposal.png`, STLs in `design/stl/`, `design/stand.step` (`cad/stand.py`)
- [x] Tim approved UI and stand direction (2026-11-23)

## 1. Hardware

### BOM
| Item | Qty | Status |
|---|---|---|
| Waveshare 7.5" raw e-ink panel, 800×480 | 1 | have |
| Waveshare Universal e-Paper Raw Panel Driver HAT (with FFC extension + adapter), wired to the Pi by its 9-wire jumper cable | 1 | have, wired |
| Raspberry Pi Zero 2 W with 2×20 header | 1 | have |
| PiSugar S, 1200 mAh UPS board (pogo pins under the Pi, charges over USB-C) | 1 | have |
| microSD ≥ 8 GB | 1 | have |
| USB-C cable + 5 V 2 A supply (charges the PiSugar, which powers the Pi) | 1 | ? |
| M2×6 self-tapping pan-head screws (2 plate, 4 foot) | 6 | ? |
| Double-sided foam tape, 1 mm (battery → plate, HAT → plate, behind panel) | 1 | ? |
| Printed: frame, back plate, foot | 1 each | designed, not printed |

The PiSugar's own four screws take the Pi's mounting holes, so the enclosure holds the stack
in a cradle instead of on standoffs (no M2.5 screws needed). The HAT is not stacked on the header:
it sits in its own cradle beside the Pi.

### Measured (Tim, calipers, 2026-11-26)
- Panel thickness 1.12 mm
- PiSugar + Pi + upright jumper housings: 36.1 mm (battery face → jumper tops)
- Pi length 65.48 mm, driver HAT length 65.69 mm, FFC adapter board 30.44 mm long
- PiSugar USB-C sits on the same long edge as the Pi's ports (seen in the stack photo)

### Still to verify
- [?] Panel variant on the label: plain B/W **V2** vs **(B)** tri-colour vs **(G)**/HD — decides the driver
- [?] Panel bottom border (assumed 8.9 mm), FPC tail position/width
- [?] Estimates inside the 36.1 mm stack: Pi PCB 16.5 mm above the battery face (sets the microSD
      window and port notch, both oversized to cover it); HAT thickness 13 mm
- [?] PiSugar power switch location

## 2. Prerequisites — access for Claude
- [?] **Interim: Pi 5 as the bridge** until the Zero 2 W's SD reader arrives (Wed 2026-11-25 evening).
      Same 40-pin header, so the driver HAT fits. Pi 5 needs the gpiozero/lgpio-based Waveshare driver
      (RPi.GPIO does not work on a Pi 5). Does not fit the printed foot — bench use only.
- [?] Pi flashed with Raspberry Pi OS Lite 64-bit, Wi-Fi + SSH key set in Imager,
      hostname (suggest `eink.local`), SPI enabled (`raspi-config`)
- [?] Passwordless `ssh eink.local` from this machine
- [?] Camera pointed at the screen and readable from this machine
      (USB webcam on the PC → `/dev/video*`, or Pi camera → capture over SSH)
- [?] Printer + filament choice (prusa-print skill → CORE One). Matte dark PETG/PLA suggested.

## 3. Decisions (Tim)
- [x] Goals / habits live in `data/goals.toml` (Tim, 2026-11-23). Open: how the file reaches the Pi (rsync/git pull from the PC, or edit on the Pi)
- [?] How are goals ticked off? (phone web page served by the Pi, physical button, or source app only)
- [?] Working-day window for the timeline (assumed 08:00–18:00)

## 4. Build phases
Phases A–C are independent and can go to parallel sub-agents once §0–3 are settled;
D and E need hardware on the desk.

### A. Display driver (`eink/display.py`, `eink/main.py`)
- [x] `EpdDisplay` wrapper (full + partial refresh, sleeps between updates) — **untested, no hardware yet**
- [x] Refresh policy: redraw each minute if changed, full refresh on start and hourly
- [x] Test pattern for the camera loop — `python -m eink.testpattern`, `design/testpattern.png`
- [x] `PngDisplay` backend so everything runs on a PC
- [ ] Confirm method names against the driver actually installed on the Pi; check polarity/rotation

### B. Data + rendering (`eink/render.py`, `eink/state.py`)
- [x] State loaded from a TOML file (`data/goals.example.toml` → copy to `data/goals.toml`); default until §3 is decided
- [x] Edge cases: no current block, >3 goals, long titles, blocks outside the window, empty day, unreadable file
- [x] Snapshot tests (`tests/`, goldens in `tests/golden/`)
- [x] Overlapping blocks are drawn on top of each other (not laid out side by side)
- [x] Approved design ported (2026-11-26, direction A + weather dock): day screen, morning / between /
      evening / empty / all-done states, weather dock under the timeline — `eink/render.py`
- [x] Weather: Pi-side cached Open-Meteo fetch (no key, hourly), degrades to no dock — `eink/weather.py`;
      goldens + state-selection tests regenerated

### C. Enclosure (`cad/`)
- [ ] Update constants from caliper measurements
- [x] Retention: plate hooks into the top wall on two tabs + 2× M2 into the chin; foot takes 4× M2 through the plate
- [x] Fit-test coupon — `design/stl/print_coupon_frame.stl`, `print_coupon_plate.stl`
- [ ] Print coupon, adjust clearances, then slice + print frame, plate, foot
- [x] Foot reworked from caliper measurements (2026-11-26): 155 wide × 53 deep, Pi stack and HAT side by side in cradles,
      port notch on top, microSD window, floor notches for the plate's ear screws
- [ ] microSD sits ~7 mm inside the foot's side window: tweezers
- [ ] FFC extension + adapter stow in the ~30 mm of free depth behind the HAT — check on assembly

### D. Integration (hardware needed)
- [ ] systemd service + timer on the Pi; boot-to-display < 60 s
- [ ] Camera loop: capture → deskew → diff against the rendered frame → fix ghosting/alignment
- [ ] Assemble; check window alignment and cable strain

### E. Polish
- [ ] Goal check-off input path
- [ ] Night mode / quiet hours, low-contrast-safe layout tweaks from camera review

## Commands
- UI on a PC: `.venv/bin/python -m eink.main --once --data data/goals.example.toml --at 2026-11-23T10:42 --out design/ui_mockup.png`
- Tests: `.venv/bin/python -m pytest -q` (regenerate goldens with `UPDATE_GOLDEN=1`)
- On the Pi: `python -m eink.main` (service file in `deploy/eink.service`)
- CAD + interference check: `.venv/bin/python cad/stand.py`
- Renders: `blender -b --python cad/render_blender.py`
