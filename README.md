# Sega Genesis Controller HAT

A passive Raspberry Pi HAT exposing two DB9 (DE-9) ports for original Sega
Genesis / Mega Drive controllers, wired directly to the Pi's 40-pin GPIO
header.

<p align="center">
  <img src="docs/images/board-top.png" alt="Board top render" width="49%">
  <img src="docs/images/board-bottom.png" alt="Board bottom render" width="49%">
</p>

Licensed under [CERN-OHL-S v2](LICENSE) — see [License](#license) below.

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

A GitHub Actions workflow (`.github/workflows/verify-pinmap.yml`) checks on
every push that this board's schematic wiring matches the firmware repo's
`sega_board.h` exactly.

## Files

- `genesis-controller-hat.kicad_pro` / `.kicad_sch` / `.kicad_pcb` — the
  KiCad 10 project.
- `design_files/` — source design assets (currently the Bare-Metal Genesis
  logo handoff package); not needed to open or modify the board, kept for
  provenance.
- `scripts/` — the editing scripts used to build the schematic and PCB from
  KiCad's official `RaspberryPi-HAT` template. Not needed to open or modify
  the board in the KiCad GUI; kept for provenance/audit.

## Verifying the board

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch
kicad-cli pcb drc --severity-all genesis-controller-hat.kicad_pcb
python3 scripts/check_pinmap.py ../Bare-Metal-Sega-Genesis/src/input/sega_board.h
```

`check_pinmap.py` (also run in CI on every push) confirms the schematic's
actual wiring matches the firmware repo's `sega_board.h`.

## License

Licensed under the [CERN Open Hardware Licence Version 2 - Strongly
Reciprocal (CERN-OHL-S v2)](LICENSE). Anyone may use, study, modify, and
distribute this design, including commercially — derivatives that are
distributed (as hardware or as design files) must be released under the
same license, with source design files made available. See the
[CERN-OHL-S FAQ](https://ohwr.org/project/cernohl/wikis/faq) for a plain-
language summary; the `LICENSE` file is the authoritative text.
