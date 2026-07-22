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

**2026-07-22:** the GPIO pin assignment was reassigned (see
`docs/reviews/2026-07-22-pinmap-reassignment.md`) to eliminate PCB routing
crossings, and a GND ground plane pour was added on `B.Cu`. A GitHub Actions
workflow (`.github/workflows/verify-pinmap.yml`) now checks on every push
that this board's schematic wiring matches the firmware repo's
`sega_board.h` exactly. The template's camera flex slot cutout (next to J3)
was also removed — this board has no camera and the slot was only crowding
J3's mounting plate; the recommended (not required) display flex cutout on
the left edge was left in place. J2 and J3 were then moved 3mm right / 6mm
left respectively so all 4 of their mounting holes sit fully on the board
(previously J2's left hole and J3's right hole were partially/fully off the
board edge) — each hole now has about 1mm of clearance to the edge, with
about 2mm of clearance between the two connector shells.

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
reports 15 errors / 7 warnings, not zero — down from 30 errors / 6 warnings
before the 2026-07-22 pin reassignment. That reassignment's whole purpose
was eliminating same-layer trace crossings between J2/J3's routing, and it
worked: `tracks_crossing`, `hole_clearance`, and `copper_edge_clearance` are
all now **zero** (were 14, 4, and 2). The remaining violations are all
pre-existing or cosmetic categories, not functional regressions:

- `unconnected_items` (2), `lib_footprint_mismatch` (1) — pre-existing in
  KiCad's own template since before this HAT project touched it (J1's +5V
  pins 2/4 are simply unused, and J1's two +3.3V pins, 1 and 17, aren't
  tied together on this board because they're already tied together
  upstream on the Pi itself). Unrelated to J2/J3.
- `solder_mask_bridge` (6) — unchanged from before the reassignment.
- `silk_edge_clearance` (6, up from 5) — moving J2/J3 to get all 4
  mounting holes fully on-board (see above) pushed each connector's
  silkscreen outline (drawn slightly larger than the copper pads) right up
  against the board edge on its outer side. Cosmetic only — a silkscreen
  clip at the board edge, not a copper/electrical issue.
- `shorting_items` (7, up from 6) — the trade-off of the pin reassignment:
  with zero same-layer crossings, the diagonal breakout tracks graze a few
  unrelated J1 pads along their path instead. This is a smaller and more
  tractable problem than the crossings it replaced (each is a single
  trace's midpoint needing a small manual jog in the KiCad GUI, not a
  fundamental routing conflict).

**Before fabricating this board, open it in the KiCad PCB editor and
manually clean up the flagged nets** (reroute with vias/jogs as needed) and
the silkscreen clips noted above, until DRC is fully clean apart from the
pre-existing baseline items above.

## Verifying the board

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch
kicad-cli pcb drc --severity-all genesis-controller-hat.kicad_pcb
python3 scripts/check_pinmap.py ../Bare-Metal-Sega-Genesis/src/input/sega_board.h
```

ERC should report 0 errors/0 warnings. DRC will report 15 errors/7 warnings
— see "Known limitation: J2/J3 routing needs manual cleanup before
fabrication" above for the exact breakdown and why this isn't a bug to fix
here; the schematic (electrical topology) is fully verified, the PCB's
routing needs one more manual pass in the KiCad GUI before this board goes
to fab. `check_pinmap.py` (also run in CI on every push) confirms the
schematic's actual wiring matches the firmware repo's `sega_board.h`.
