# Sega Genesis Controller HAT

A passive Raspberry Pi HAT exposing two DB9 (DE-9) ports for original Sega
Genesis / Mega Drive controllers, wired directly to the Pi's 40-pin GPIO
header.

This board has no firmware of its own. The pin assignment and electrical
contract it implements are owned by the firmware repo,
[Bare-Metal-Sega-Genesis](../Bare-Metal-Sega-Genesis), specifically
`src/input/sega_board.h` and
`docs/superpowers/specs/2026-06-25-gpio-sega-controllers-design.md`. If
those ever disagree with this repo, the firmware repo wins — update this
board to match it, not the other way around.

See `docs/superpowers/specs/2026-07-21-controller-hat-v1-design.md` for the
full design rationale (why no ID EEPROM, no protection circuitry, no
stacking header) and `docs/superpowers/plans/2026-07-21-controller-hat-v1.md`
for how it was built.

## Files

- `genesis-controller-hat.kicad_pro` / `.kicad_sch` / `.kicad_pcb` — the
  KiCad 9 project.
- `scripts/` — the editing scripts used to build the schematic and PCB from
  KiCad's official `RaspberryPi-HAT` template. Not needed to open or modify
  the board in the KiCad GUI; kept for provenance/audit.

## Known limitation: PCB net table includes stale entries

The PCB's net table still lists nets for GPIO pins and the ID EEPROM/+5V
circuit that were deleted from the schematic (I2C, UART, I2S, the four
spare GPIOs, `ID_SDA`/`ID_SCL`, `+5V`). No footprint or track references
them, so they're inert, but a `kicad-cli pcb drc --schematic-parity` run
will flag the mismatch. There is no headless "update PCB from schematic"
command in this KiCad install — if you need full parity (e.g. before
opening this in the GUI to do further layout work), open the project in
the KiCad GUI once and run Tools → Update PCB from Schematic.

## Known limitation: J2/J3 routing needs manual cleanup before fabrication

`kicad-cli pcb drc --severity-all` on `genesis-controller-hat.kicad_pcb`
reports 32 errors / 6 warnings, not zero. 10 of those (9 `unconnected_items`
+ 1 `lib_footprint_mismatch`) are pre-existing in KiCad's own template since
before this HAT project touched it, and are unrelated to J2/J3. The
remaining 28 (2 `copper_edge_clearance`, 3 `shorting_items`, 5
`silk_edge_clearance`, 6 `solder_mask_bridge`, 12 `tracks_crossing` — the
exact split between `shorting_items` and `tracks_crossing` varies slightly
run to run; their combined count does not) come from routing J2/J3's 9 pins
each to their scattered, fixed target pins on J1 (the pin assignment is
fixed by `src/input/sega_board.h` — there's no freedom to reorder it for
easier routing). Each connector's 9 pins are packed into a 2.77-2.84mm-pitch
cluster and fan out to targets 40-50mm away; a scripted greedy two-layer
router (see `scripts/task6_pcb_layout.py`) gets close but can't fully match
what KiCad's interactive push-and-shove router or a real autorouter would
achieve. One of the `silk_edge_clearance` warnings is the "Player 2" text
label itself clipping the board's right edge (its anchor at `(161,74)` sits
close enough to the edge for the rendered text width to overlap
`Edge.Cuts`) — cosmetic, but worth nudging left during the same manual
cleanup pass. **Before fabricating this board, open it in the KiCad PCB
editor and manually clean up the flagged nets** (reroute with vias/jogs as
needed) and the "Player 2" label position, until DRC is fully clean apart
from the two pre-existing baseline items above.

## Verifying the board

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch
kicad-cli pcb drc --severity-all genesis-controller-hat.kicad_pcb
```

ERC should report 0 errors/0 warnings. DRC will report 32 errors/6 warnings
— see "Known limitation: J2/J3 routing needs manual cleanup before
fabrication" above for the exact breakdown and why this isn't a bug to fix
here; the schematic (electrical topology) is fully verified, the PCB's
routing needs one more manual pass in the KiCad GUI before this board goes
to fab.
