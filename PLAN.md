# E-ink goals display — plan & checklist

Desk display: Waveshare 7.5" raw e-ink panel (800×480) + Raspberry Pi Zero 2 W, in a
printed frame-and-wedge stand, showing today's goals, time blocks and habits.

Status legend: [ ] todo · [x] done · [?] needs Tim

## 0. Proposals
- [x] UI mockup, native 800×480 1-bit — `design/ui_mockup.png` (`eink/render.py`)
- [x] Stand proposal — `design/stand_proposal.png`, STLs in `design/stl/`, `design/stand.step` (`cad/stand.py`)
- [x] Tim approved UI and stand direction (2026-11-23)

## 1. Prerequisites — hardware (Tim)
- [?] **Driver board.** The listing is the *raw panel without PCB*: it has only a 24-pin
      0.5 mm FPC tail and cannot plug into a Pi. Needs a **Waveshare e-Paper Driver HAT**
      (Rev 2.3, includes FFC extension + adapter). Nothing works without it.
- [?] Pi Zero 2 **WH** (pre-soldered header), or solder a 2×20 header onto the 2 W
- [?] microSD ≥ 8 GB, 5 V ≥ 2 A micro-USB supply, ideally a right-angle micro-USB cable
- [?] 4× M2.5×6 self-tapping screws (Pi), 6× M2×6 self-tapping pan head (2 plate, 4 foot), 1 mm foam tape
- [?] Confirm panel variant printed on the FPC/back label: plain B/W **V2** vs **(B)** red
      tri-colour vs **(G)**/HD — decides the driver (`epd7in5_V2` assumed) and refresh time
- [?] Calipers on arrival: panel thickness, bottom border (assumed 8.9 mm), FPC tail
      position/width/length, and where the FPC connector sits on the HAT.
      These are the `VERIFY`/`assumed` constants at the top of `cad/stand.py`.

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
