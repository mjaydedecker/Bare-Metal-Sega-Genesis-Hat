# Sega Genesis Controller HAT v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a KiCad 9 schematic + PCB for a passive Raspberry Pi HAT carrying two DB9 Sega Genesis controller ports, wired to the Pi's 40-pin GPIO header exactly per `src/input/sega_board.h` in the firmware repo, starting from KiCad's own official `RaspberryPi-HAT` template so the mechanical spec (65×56.5mm outline, mounting holes, GPIO header position) is correct by construction rather than hand-derived.

**Architecture:** Copy KiCad's bundled `RaspberryPi-HAT` template (already mechanically correct per the Raspberry Pi Foundation's `hat-board-mechanical.pdf`), strip the parts of it we don't want (ID EEPROM circuit, 5V), then add two `DE9_Socket_MountingHoles` connectors and wire them to the header using KiCad's existing per-pin net labels. All schematic edits are done with a small, tested S-expression parser/serializer script (not hand-edited text) because KiCad's file format is whitespace-sensitive enough that naive string edits can silently corrupt the file — verified empirically during design (a naive text-splice edit produced a file that segfaulted `kicad-cli`). Every task ends with a `kicad-cli sch erc` or `kicad-cli pcb drc` run against a known-good violation count.

**Tech Stack:** KiCad 9.0.8 (`kicad-cli` for ERC/DRC/SVG export), Python 3. Schematic edits go through a custom S-expression parser (`scripts/kicad_sexpr.py`) since no equivalent scripting module for `eeschema` is available. PCB edits go through the real `pcbnew` Python module (`/usr/lib/python3/dist-packages/pcbnew.py`, installed alongside the `kicad` apt package) — confirmed working during planning, and preferred over hand-written S-expressions for the PCB because it manages the net table for you instead of requiring manual net-code bookkeeping.

## Global Constraints

- Electrical contract is fixed by `docs/superpowers/specs/2026-07-21-controller-hat-v1-design.md` in this repo: DB9 pin 5 = +3.3V (not 5V), pin 8 = GND, data/SELECT direct to GPIO, no protection components, no ID EEPROM, no stacking header, no LEDs.
- Pin map is fixed by the firmware repo's `src/input/sega_board.h` (BCM numbering) — this plan is not the source of truth for pin choices, it only implements the already-approved table.
- Every schematic-editing task must leave `kicad-cli sch erc` reporting the exact violation count stated in that task (not "fewer" or "roughly") — the counts were measured empirically against the real template during planning and are exact targets, not estimates.
- All schematic edits (Tasks 2-5) go through `scripts/kicad_sexpr.py`, never hand-typed raw S-expression text pasted into `.kicad_sch` directly. PCB edits (Task 6) go through the real `pcbnew` Python module instead — discovered mid-planning to be installed and working in this environment, and preferred for the PCB specifically because it manages net-table bookkeeping for you rather than requiring it be replicated by hand. Neither task hand-edits file text directly.

---

## Reference data (used by every task below)

**Raspberry Pi 40-pin header (BCM numbering) — physical pin ↔ GPIO, confirmed against the label text already embedded in KiCad's own `RaspberryPi-HAT` template schematic:**

| Physical pin | GPIO | Template label text (verbatim, `{slash}` is KiCad's literal escape for `/`) |
|---|---|---|
| 7  | GPIO4  | `GPIO4{slash}GPCLK0` |
| 29 | GPIO5  | `GPIO5` |
| 31 | GPIO6  | `GPIO6` |
| 26 | GPIO7  | `GPIO7{slash}SPI0.CE1` |
| 24 | GPIO8  | `GPIO8{slash}SPI0.CE0` |
| 21 | GPIO9  | `GPIO9{slash}SPI0.MISO` |
| 19 | GPIO10 | `GPIO10{slash}SPI0.MOSI` |
| 23 | GPIO11 | `GPIO11{slash}SPI0.SCLK` |
| 32 | GPIO12 | `GPIO12{slash}PWM0` |
| 33 | GPIO13 | `GPIO13{slash}PWM1` |
| 36 | GPIO16 | `GPIO16` |
| 11 | GPIO17 | `GPIO17` |
| 15 | GPIO22 | `GPIO22` |
| 16 | GPIO23 | `GPIO23` |

**Unused GPIO pins to strip (their template labels get deleted, not wired):** GPIO2, GPIO3, GPIO14, GPIO15, GPIO18, GPIO19, GPIO20, GPIO21, GPIO24, GPIO25, GPIO26, GPIO27 (physical pins 3, 5, 8, 10, 12, 35, 38, 40, 18, 22, 37, 13). GPIO0/GPIO1 (physical pins 27/28) have no separate label in the template — they're wired directly to the ID EEPROM sub-circuit, removed in Task 2.

**Genesis DB9 pinout (from `src/input/sega_board.h` / the approved HAT spec):**

| DB9 pin | Signal | Port 1 (J2) → GPIO | Port 2 (J3) → GPIO |
|---|---|---|---|
| 1 | Up | GPIO5 | GPIO12 |
| 2 | Down | GPIO6 | GPIO13 |
| 3 | Left | GPIO7 | GPIO16 |
| 4 | Right | GPIO8 | GPIO17 |
| 5 | +3.3V | local +3.3V symbol | local +3.3V symbol |
| 6 | TL (B/A) | GPIO9 | GPIO22 |
| 7 | SELECT | GPIO4 | GPIO11 |
| 8 | GND | local GND symbol | local GND symbol |
| 9 | TR (C/Start) | GPIO10 | GPIO23 |
| 0 (shell/mounting pad) | — | no-connect | no-connect |

**KiCad library identifiers confirmed present on this system (`kicad-cli version` → 9.0.8):**
- GPIO header (already placed correctly by the template): `Connector_Generic:Conn_02x20_Odd_Even`, footprint `Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical`.
- DB9 socket: symbol `Connector:DE9_Socket_MountingHoles`, footprint `Connector_Dsub:DSUB-9_Socket_Vertical_P2.77x2.84mm_MountingHoles`. Symbol pins 1–9 map straight to DB9 pins 1–9; pin `"0"` is the shell/mounting-hole pad.
- Power flags: `power:+3.3V`, `power:GND`, `power:PWR_FLAG` (the last has a `power_out` pin and is how you tell ERC "this net is driven from outside the sheet" — required because `power:+3.3V`/`power:GND` symbols themselves have `power_in` pins, not `power_out`).

**Empirically measured baseline** (untouched copy of `/usr/share/kicad/template/RaspberryPi-HAT`, after fixing this machine's KiCad library tables — see Task 0):
- `kicad-cli sch erc`: **31 violations = 29 errors + 2 warnings.**
  - 26 errors: `label_dangling` (one per unused/unwired GPIO label — 14 of these are pins we'll wire, 12 are pins we'll delete).
  - 3 errors: `power_pin_not_driven` (`#PWR04` = +3.3V, `#PWR01` = +5V, `#PWR02` = one of the two GND flags).
  - 2 warnings: `lib_symbol_mismatch` on `R1`/`R2` (`R_Small` footprint fields differ from the library copy — cosmetic, disappears once those parts are deleted in Task 2).
- `kicad-cli pcb drc`: 1 warning (`lib_footprint_mismatch` on J1, cosmetic/pre-existing) + 9 unconnected-pad errors (GPIO header's GND/+3.3V/+5V pins aren't copper-tied together yet — expected, nothing is routed in a blank template).

---

### Task 0: Fix this machine's KiCad library tables (one-time, environment-only — not a repo change)

KiCad was just installed via apt and has never been run interactively, so its global `sym-lib-table` doesn't exist yet (only a partial `fp-lib-table` gets auto-created the first time `kicad-cli` touches a project). Without this, `kicad-cli sch erc` reports spurious `lib_symbol_issues` warnings for every standard library (`power`, `Device`, `Connector_Generic`, ...) because it can't resolve them, and edits that add new library symbols (the `PWR_FLAG` fix in Task 2) will fail to resolve at all.

**Files:** none in the repo — this only touches `~/.config/kicad/9.0/`.

- [ ] **Step 1: Copy KiCad's default global symbol table into place**

```bash
mkdir -p ~/.config/kicad/9.0
cp /usr/share/kicad/template/sym-lib-table ~/.config/kicad/9.0/sym-lib-table
```

- [ ] **Step 2: Verify the fp-lib-table already exists and is the full default (not an empty stub)**

```bash
wc -l ~/.config/kicad/9.0/fp-lib-table
```

Expected: **157** (matches `/usr/share/kicad/template/fp-lib-table` line count). If it's much shorter (e.g. 1-2 lines), copy the template version the same way as Step 1, substituting `fp-lib-table` for `sym-lib-table`.

- [ ] **Step 3: Confirm the fix with a scratch copy of the vanilla template**

```bash
rm -rf /tmp/hat-baseline-check && cp -r /usr/share/kicad/template/RaspberryPi-HAT /tmp/hat-baseline-check
cd /tmp/hat-baseline-check
kicad-cli sch erc --severity-all RaspberryPi-HAT.kicad_sch
grep -c "; error" RaspberryPi-HAT-erc.rpt
grep -c "; warning" RaspberryPi-HAT-erc.rpt
```

Expected: `29` errors, `2` warnings (matches the baseline table above — if you see extra `lib_symbol_issues` warnings, the library table isn't picked up yet; double check the path is exactly `~/.config/kicad/9.0/` and matches the version `kicad-cli version` reports).

- [ ] **Step 4: Clean up the scratch copy**

```bash
rm -rf /tmp/hat-baseline-check
```

No commit for this task — it's a local machine fix, not a repo change.

---

### Task 1: Scaffold the project from KiCad's official HAT template

**Files:**
- Create: `genesis-controller-hat.kicad_pro`
- Create: `genesis-controller-hat.kicad_sch`
- Create: `genesis-controller-hat.kicad_pcb`
- Create: `scripts/kicad_sexpr.py`

**Interfaces:**
- Produces: `scripts/kicad_sexpr.py` exposes `parse(text) -> tree`, `dumps(tree) -> text`, `find_symbols_by_ref(tree, refs: set[str]) -> list[list]`, `get_property(symbol_node, name) -> str|None`, `remove_symbols_by_ref(tree, refs: set[str]) -> int` (returns count removed), `remove_labels_by_text(tree, texts: set[str]) -> int`, `root_uuid(tree) -> str`, `make_power_symbol(lib_id, ref, value, at_xy, project, root_uuid_str) -> list`, `make_db9_symbol(ref, value, at_xy, project, root_uuid_str) -> list`, `make_label(text, at_xy, angle=180) -> list`, `make_no_connect(at_xy) -> list`. Every later schematic task imports this module.

- [ ] **Step 1: Copy the template into the repo under a new name**

```bash
cp /usr/share/kicad/template/RaspberryPi-HAT/RaspberryPi-HAT.kicad_pro genesis-controller-hat.kicad_pro
cp /usr/share/kicad/template/RaspberryPi-HAT/RaspberryPi-HAT.kicad_sch genesis-controller-hat.kicad_sch
cp /usr/share/kicad/template/RaspberryPi-HAT/RaspberryPi-HAT.kicad_pcb genesis-controller-hat.kicad_pcb
```

- [ ] **Step 2: Write the S-expression helper module**

Create `scripts/kicad_sexpr.py`:

```python
"""Round-trip-safe S-expression parser/serializer for KiCad 9 files, plus
helpers for the specific find/remove/create operations this project's
schematic-editing scripts need. Not a general KiCad API replacement — no
pcbnew module is installed in this environment, so file-format editing is
the only scripting path available."""

import uuid as _uuid


class Sym(str):
    """A bare (unquoted) token, as opposed to a quoted string."""
    pass


def parse(text):
    pos = 0
    n = len(text)

    def skip_ws(p):
        while p < n and text[p] in " \t\r\n":
            p += 1
        return p

    def parse_atom(p):
        if text[p] == '"':
            p += 1
            buf = []
            while text[p] != '"':
                if text[p] == '\\':
                    buf.append(text[p:p + 2])
                    p += 2
                else:
                    buf.append(text[p])
                    p += 1
            return "".join(buf), p + 1
        start = p
        while p < n and text[p] not in " \t\r\n()":
            p += 1
        return Sym(text[start:p]), p

    def parse_expr(p):
        p = skip_ws(p)
        assert text[p] == '(', f"expected '(' at {p}"
        p += 1
        items = []
        while True:
            p = skip_ws(p)
            if text[p] == ')':
                return items, p + 1
            if text[p] == '(':
                sub, p = parse_expr(p)
                items.append(sub)
            else:
                atom, p = parse_atom(p)
                items.append(atom)

    tree, _ = parse_expr(skip_ws(0))
    return tree


def serialize(node):
    if isinstance(node, Sym):
        return str(node)
    if isinstance(node, str):
        return '"' + node.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return "(" + " ".join(serialize(c) for c in node) + ")"


def dumps(tree):
    return serialize(tree)


def get_tag(node):
    return node[0] if isinstance(node, list) and node else None


def get_property(symbol_node, name):
    for child in symbol_node:
        if isinstance(child, list) and get_tag(child) == "property" and child[1] == name:
            return child[2]
    return None


def find_symbols_by_ref(tree, refs):
    return [n for n in tree if isinstance(n, list) and get_tag(n) == "symbol"
            and get_property(n, "Reference") in refs]


def remove_symbols_by_ref(tree, refs):
    before = len(tree)
    tree[:] = [n for n in tree if not (isinstance(n, list) and get_tag(n) == "symbol"
                                        and get_property(n, "Reference") in refs)]
    return before - len(tree)


def remove_labels_by_text(tree, texts):
    before = len(tree)
    tree[:] = [n for n in tree if not (isinstance(n, list) and get_tag(n) == "label"
                                        and n[1] in texts)]
    return before - len(tree)


def root_uuid(tree):
    for node in tree:
        if isinstance(node, list) and get_tag(node) == "uuid":
            return node[1]
    raise ValueError("no top-level uuid found")


def project_name(tree):
    for node in tree:
        if isinstance(node, list) and get_tag(node) == "symbol":
            for child in node:
                if isinstance(child, list) and get_tag(child) == "instances":
                    for proj in child[1:]:
                        return proj[1]
    raise ValueError("no instances/project block found to infer project name")


def _effects(size=1.27):
    return [Sym("effects"), [Sym("font"), [Sym("size"), str(size), str(size)]]]


def make_power_symbol(lib_id, ref, value, at_xy, project, root_uuid_str):
    x, y = at_xy
    new_uuid = str(_uuid.uuid4())
    return [
        Sym("symbol"),
        [Sym("lib_id"), lib_id],
        [Sym("at"), str(x), str(y), "0"],
        [Sym("unit"), "1"],
        [Sym("exclude_from_sim"), Sym("no")],
        [Sym("in_bom"), Sym("yes")],
        [Sym("on_board"), Sym("yes")],
        [Sym("dnp"), Sym("no")],
        [Sym("uuid"), new_uuid],
        [Sym("property"), "Reference", ref, [Sym("at"), str(x), str(y + 3.81), "0"],
         [Sym("effects"), [Sym("font"), [Sym("size"), "1.27", "1.27"]], [Sym("hide"), Sym("yes")]]],
        [Sym("property"), "Value", value, [Sym("at"), str(x), str(y - 4.32), "0"], _effects()],
        [Sym("property"), "Footprint", "", [Sym("at"), str(x), str(y), "0"], _effects()],
        [Sym("property"), "Datasheet", "", [Sym("at"), str(x), str(y), "0"], _effects()],
        [Sym("pin"), "1", [Sym("uuid"), str(_uuid.uuid4())]],
        [Sym("instances"), [Sym("project"), project,
                             [Sym("path"), "/" + root_uuid_str,
                              [Sym("reference"), ref], [Sym("unit"), "1"]]]],
    ]


def make_db9_symbol(ref, value, at_xy, project, root_uuid_str):
    x, y = at_xy
    new_uuid = str(_uuid.uuid4())
    return [
        Sym("symbol"),
        [Sym("lib_id"), "Connector:DE9_Socket_MountingHoles"],
        [Sym("at"), str(x), str(y), "0"],
        [Sym("unit"), "1"],
        [Sym("exclude_from_sim"), Sym("no")],
        [Sym("in_bom"), Sym("yes")],
        [Sym("on_board"), Sym("yes")],
        [Sym("dnp"), Sym("no")],
        [Sym("uuid"), new_uuid],
        [Sym("property"), "Reference", ref, [Sym("at"), str(x), str(y - 17.78), "0"], _effects()],
        [Sym("property"), "Value", value, [Sym("at"), str(x), str(y - 15.875), "0"], _effects()],
        [Sym("property"), "Footprint",
         "Connector_Dsub:DSUB-9_Socket_Vertical_P2.77x2.84mm_MountingHoles",
         [Sym("at"), str(x), str(y), "0"], [Sym("effects"), [Sym("font"), [Sym("size"), "1.27", "1.27"]], [Sym("hide"), Sym("yes")]]],
        [Sym("property"), "Datasheet", "~", [Sym("at"), str(x), str(y), "0"],
         [Sym("effects"), [Sym("font"), [Sym("size"), "1.27", "1.27"]], [Sym("hide"), Sym("yes")]]],
        [Sym("instances"), [Sym("project"), project,
                             [Sym("path"), "/" + root_uuid_str,
                              [Sym("reference"), ref], [Sym("unit"), "1"]]]],
    ]


def make_label(text, at_xy, angle=180):
    x, y = at_xy
    return [Sym("label"), text, [Sym("at"), str(x), str(y), str(angle)],
            [Sym("effects"), [Sym("font"), [Sym("size"), "1.27", "1.27"]],
             [Sym("justify"), Sym("left"), Sym("bottom")]],
            [Sym("uuid"), str(_uuid.uuid4())]]


def make_no_connect(at_xy):
    x, y = at_xy
    return [Sym("no_connect"), [Sym("at"), str(x), str(y)], [Sym("uuid"), str(_uuid.uuid4())]]
```

- [ ] **Step 3: Verify the module parses and round-trips the copied schematic without corruption**

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
import kicad_sexpr as ks
tree = ks.parse(open('genesis-controller-hat.kicad_sch').read())
open('/tmp/roundtrip-check.kicad_sch', 'w').write(ks.dumps(tree))
print('top-level items:', len(tree))
"
kicad-cli sch erc --severity-all /tmp/roundtrip-check.kicad_sch
grep -c "; error" /tmp/roundtrip-check-erc.rpt
rm -f /tmp/roundtrip-check.kicad_sch /tmp/roundtrip-check-erc.rpt
```

Expected: `top-level items: 144`, and `kicad-cli sch erc` runs to completion without crashing (a parser bug would either raise a Python exception or produce a file `kicad-cli` can't parse — either is a hard failure here, not a violation-count question).

- [ ] **Step 4: Verify the freshly copied project reports the known baseline**

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch
grep -c "; error" genesis-controller-hat-erc.rpt
grep -c "; warning" genesis-controller-hat-erc.rpt
```

Expected: `29` errors, `2` warnings (same as Task 0's baseline check — confirms the copy is unmodified).

- [ ] **Step 5: Commit**

```bash
git add genesis-controller-hat.kicad_pro genesis-controller-hat.kicad_sch genesis-controller-hat.kicad_pcb scripts/kicad_sexpr.py
git commit -m "$(cat <<'EOF'
Scaffold KiCad project from official RaspberryPi-HAT template

Starting from KiCad's own mechanically-correct HAT template (65x56.5mm
outline, mounting holes, GPIO header position) instead of re-deriving the
board outline by hand eliminates an entire class of dimensional mistakes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Strip the ID EEPROM circuit and +5V, fix the power-flag ERC errors

The template targets full official HAT certification (ID EEPROM on GPIO0/1). Per the approved design spec this board skips that — bare-metal kernel, no device-tree consumer. This task removes that sub-circuit and the unused +5V rail, and fixes the two remaining "power pin not driven" errors that are inherent to how the template represents +3.3V/GND (their power symbols have `power_in` pins, not `power_out` — a `PWR_FLAG` is the standard KiCad idiom for telling ERC the net is driven from off-sheet).

**Files:**
- Create: `scripts/task2_strip_unused.py`
- Modify: `genesis-controller-hat.kicad_sch`

**Interfaces:**
- Consumes: `scripts/kicad_sexpr.py`'s `parse`, `dumps`, `remove_symbols_by_ref`, `make_power_symbol`, `root_uuid`, `project_name`.
- Produces: schematic with EEPROM/+5V circuitry gone and `+3.3V`/`GND` nets validly driven, ready for Task 3 to prune unused GPIO labels.

- [ ] **Step 1: Write the strip script**

Create `scripts/task2_strip_unused.py`:

```python
import sys
sys.path.insert(0, "scripts")
import kicad_sexpr as ks

PATH = "genesis-controller-hat.kicad_sch"
tree = ks.parse(open(PATH).read())

# EEPROM sub-circuit (C1 decoupling cap, R1/R2 pull-ups, JP1 disable jumper,
# U1 the EEPROM itself) and its three local power-flag symbols.
eeprom_refs = {"C1", "R1", "JP1", "R2", "U1", "#PWR0101", "#PWR0102", "#PWR0103"}
removed_eeprom = ks.remove_symbols_by_ref(tree, eeprom_refs)
assert removed_eeprom == 8, f"expected to remove 8 EEPROM-related symbols, removed {removed_eeprom}"

# +5V is never used by this design (Genesis pads are powered at 3.3V per the
# approved spec) — remove the header's +5V power flag entirely.
removed_5v = ks.remove_symbols_by_ref(tree, {"#PWR01"})
assert removed_5v == 1, f"expected to remove 1 symbol (#PWR01), removed {removed_5v}"

# #PWR04 (+3.3V) and #PWR02 (GND) are power_in pins with nothing driving
# them per ERC's rules; a PWR_FLAG on each net tells ERC the net is driven
# from outside this sheet (by the Raspberry Pi itself).
proj = ks.project_name(tree)
root = ks.root_uuid(tree)
tree.append(ks.make_power_symbol("power:PWR_FLAG", "#FLG901", "PWR_FLAG", (55.88, 30.0), proj, root))
tree.append(ks.make_power_symbol("power:PWR_FLAG", "#FLG902", "PWR_FLAG", (76.20, 85.0), proj, root))

open(PATH, "w").write(ks.dumps(tree))
print("Task 2 edits applied.")
```

- [ ] **Step 2: Run it**

```bash
python3 scripts/task2_strip_unused.py
```

Expected output: `Task 2 edits applied.` (the two `assert` lines are the real check — if either count is wrong the script raises `AssertionError` and exits nonzero before writing anything).

- [ ] **Step 3: Verify against the exact expected ERC count**

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch
grep -c "; error" genesis-controller-hat-erc.rpt
grep -c "; warning" genesis-controller-hat-erc.rpt
```

Expected: **26 errors, 0 warnings.** (29 baseline errors − 3 `power_pin_not_driven` = 26, all now `label_dangling`; the 2 `R_Small` mismatch warnings vanished because `R1`/`R2` are gone.)

If the count is off, check the report contents directly (`cat genesis-controller-hat-erc.rpt`) before re-running — do not just re-run the script, since it isn't idempotent (running it twice will fail the `assert` on the second pass because the symbols are already gone; that failure is itself expected/correct, not a bug).

- [ ] **Step 4: Commit**

```bash
git add genesis-controller-hat.kicad_sch scripts/task2_strip_unused.py
git commit -m "$(cat <<'EOF'
Strip ID EEPROM circuit and +5V from the HAT schematic

This board is not chasing official HAT certification (bare-metal kernel,
no device-tree consumer for the EEPROM) and never uses 5V (Genesis pads
are powered at 3.3V per the approved design spec), so both are removed
rather than left as dead weight. PWR_FLAG symbols replace the ERC
correctness those deleted parts incidentally provided for the +3.3V/GND
nets.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Remove the unused GPIO pin labels

Twelve of the header's 26 labeled GPIO pins aren't part of the Genesis pin map (I2C, UART, I2S, and four spares) — per the approved spec these stay unpopulated on the HAT, so their dangling labels should be deleted rather than left as permanent ERC noise.

**Files:**
- Create: `scripts/task3_remove_unused_labels.py`
- Modify: `genesis-controller-hat.kicad_sch`

**Interfaces:**
- Consumes: `kicad_sexpr.remove_labels_by_text`.
- Produces: schematic with exactly the 14 labels this design uses remaining, ready for Task 4/5 to wire them.

- [ ] **Step 1: Write the removal script**

Create `scripts/task3_remove_unused_labels.py`:

```python
import sys
sys.path.insert(0, "scripts")
import kicad_sexpr as ks

PATH = "genesis-controller-hat.kicad_sch"
tree = ks.parse(open(PATH).read())

UNUSED_LABELS = {
    "GPIO2{slash}SDA1", "GPIO3{slash}SCL1",
    "GPIO14{slash}TXD0", "GPIO15{slash}RXD0",
    "GPIO18{slash}PCM.CLK", "GPIO19{slash}PCM.FS",
    "GPIO20{slash}PCM.DIN", "GPIO21{slash}PCM.DOUT",
    "GPIO24", "GPIO25", "GPIO26", "GPIO27",
}

removed = ks.remove_labels_by_text(tree, UNUSED_LABELS)
assert removed == 12, f"expected to remove 12 labels, removed {removed}"

open(PATH, "w").write(ks.dumps(tree))
print("Task 3 edits applied.")
```

- [ ] **Step 2: Run it**

```bash
python3 scripts/task3_remove_unused_labels.py
```

Expected: `Task 3 edits applied.`

- [ ] **Step 3: Verify against the exact expected ERC count**

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch
grep -c "; error" genesis-controller-hat-erc.rpt
grep -c "; warning" genesis-controller-hat-erc.rpt
```

Expected: **14 errors, 0 warnings** — exactly the 14 `label_dangling` errors for the pins this design does use (GPIO4/5/6/7/8/9/10/11/12/13/16/17/22/23), unresolved until Tasks 4–5 wire them.

- [ ] **Step 4: Commit**

```bash
git add genesis-controller-hat.kicad_sch scripts/task3_remove_unused_labels.py
git commit -m "$(cat <<'EOF'
Remove header labels for GPIO pins this HAT does not use

I2C, UART, I2S, and the four spare GPIOs are reserved by the firmware
repo's electrical contract but not populated on this board; deleting
their dangling labels turns permanent ERC noise into a clean signal for
the pins that remain.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Add the Player 1 DB9 connector (J2) and wire it

**Files:**
- Create: `scripts/task4_add_j2.py`
- Modify: `genesis-controller-hat.kicad_sch`

**Interfaces:**
- Consumes: `kicad_sexpr.make_db9_symbol`, `make_power_symbol`, `make_label`, `make_no_connect`, `root_uuid`, `project_name`.
- Produces: `J2` symbol instance wired to GPIO4/5/6/7/8/9/10 via matching-text labels (KiCad connects same-named labels anywhere on one sheet without a drawn wire between them — this is why no explicit wire objects back to J1 are needed).

`DE9_Socket_MountingHoles`'s local pin coordinates (from `Connector.kicad_sym`, pins 1-9 in a single column at local x=-7.62, pin 0/PAD at local (0,-15.24)) mean that placing the symbol's own `at` anchor at (50, 250) with rotation 0 puts pin *N*'s absolute connection point at (50 - 7.62, 250 + local_y). Rather than re-deriving that transform by hand for two connectors, the script below hardcodes the nine already-computed absolute pin points per connector — cheaper and less error-prone than doing rotation math in the script for a fixed, one-time placement.

- [ ] **Step 1: Write the wiring script**

Create `scripts/task4_add_j2.py`:

```python
import sys
sys.path.insert(0, "scripts")
import kicad_sexpr as ks

PATH = "genesis-controller-hat.kicad_sch"
tree = ks.parse(open(PATH).read())
proj = ks.project_name(tree)
root = ks.root_uuid(tree)

# J2 anchor at (50, 250) rotation 0 -> pin N absolute = (50 - 7.62, 250 + local_y)
J2_PINS = {
    "1": (42.38, 260.16),  # Up      -> GPIO5
    "6": (42.38, 257.62),  # TL      -> GPIO9
    "2": (42.38, 255.08),  # Down    -> GPIO6
    "7": (42.38, 252.54),  # SELECT  -> GPIO4
    "3": (42.38, 250.00),  # Left    -> GPIO7
    "8": (42.38, 247.46),  # GND
    "4": (42.38, 244.92),  # Right   -> GPIO8
    "9": (42.38, 242.38),  # TR      -> GPIO10
    "5": (42.38, 239.84),  # +3.3V
    "0": (50.00, 234.76),  # shell/mounting pad -> NC
}

PIN_TO_LABEL = {
    "1": "GPIO5",
    "2": "GPIO6",
    "3": "GPIO7{slash}SPI0.CE1",
    "4": "GPIO8{slash}SPI0.CE0",
    "6": "GPIO9{slash}SPI0.MISO",
    "7": "GPIO4{slash}GPCLK0",
    "9": "GPIO10{slash}SPI0.MOSI",
}

tree.append(ks.make_db9_symbol("J2", "DE9_Socket_MountingHoles", (50, 250), proj, root))

for pin, label_text in PIN_TO_LABEL.items():
    tree.append(ks.make_label(label_text, J2_PINS[pin]))

tree.append(ks.make_power_symbol("power:+3.3V", "#PWR901", "+3V3", J2_PINS["5"], proj, root))
tree.append(ks.make_power_symbol("power:GND", "#PWR902", "GND", J2_PINS["8"], proj, root))
tree.append(ks.make_no_connect(J2_PINS["0"]))

open(PATH, "w").write(ks.dumps(tree))
print("Task 4 edits applied.")
```

- [ ] **Step 2: Run it**

```bash
python3 scripts/task4_add_j2.py
```

Expected: `Task 4 edits applied.`

- [ ] **Step 3: Verify against the exact expected ERC count**

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch
grep -c "; error" genesis-controller-hat-erc.rpt
grep -c "; warning" genesis-controller-hat-erc.rpt
```

Expected: **7 errors, 0 warnings** (14 − 7 pins J2 just wired = 7 remaining `label_dangling` errors, for the Port 2 pins Task 5 wires next). Read `genesis-controller-hat-erc.rpt` and confirm the remaining 7 are exactly `GPIO11{slash}SPI0.SCLK`, `GPIO12{slash}PWM0`, `GPIO13{slash}PWM1`, `GPIO16`, `GPIO17`, `GPIO22`, `GPIO23` — if a *different* label shows up as still-dangling, J2's wiring landed on the wrong physical pin and must be fixed before continuing.

- [ ] **Step 4: Commit**

```bash
git add genesis-controller-hat.kicad_sch scripts/task4_add_j2.py
git commit -m "$(cat <<'EOF'
Wire Player 1 DB9 connector (J2) to the GPIO header

Up/Down/Left/Right/TL/SELECT/TR land on GPIO5/6/7/9/4/10 respectively per
sega_board.h; +3.3V and GND are local power symbols that merge onto the
header's existing +3.3V/GND nets by KiCad's global-power-symbol naming
rule, and the shell/mounting pad is explicitly marked no-connect per the
approved no-extra-protection design.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Add the Player 2 DB9 connector (J3) and wire it

**Files:**
- Create: `scripts/task5_add_j3.py`
- Modify: `genesis-controller-hat.kicad_sch`

**Interfaces:**
- Consumes: same `kicad_sexpr` helpers as Task 4.
- Produces: fully wired schematic — every net the design needs is complete, and ERC should report zero errors and zero warnings.

- [ ] **Step 1: Write the wiring script**

Create `scripts/task5_add_j3.py`:

```python
import sys
sys.path.insert(0, "scripts")
import kicad_sexpr as ks

PATH = "genesis-controller-hat.kicad_sch"
tree = ks.parse(open(PATH).read())
proj = ks.project_name(tree)
root = ks.root_uuid(tree)

# J3 anchor at (110, 250) rotation 0 -> pin N absolute = (110 - 7.62, 250 + local_y)
J3_PINS = {
    "1": (102.38, 260.16),  # Up      -> GPIO12
    "6": (102.38, 257.62),  # TL      -> GPIO22
    "2": (102.38, 255.08),  # Down    -> GPIO13
    "7": (102.38, 252.54),  # SELECT  -> GPIO11
    "3": (102.38, 250.00),  # Left    -> GPIO16
    "8": (102.38, 247.46),  # GND
    "4": (102.38, 244.92),  # Right   -> GPIO17
    "9": (102.38, 242.38),  # TR      -> GPIO23
    "5": (102.38, 239.84),  # +3.3V
    "0": (110.00, 234.76),  # shell/mounting pad -> NC
}

PIN_TO_LABEL = {
    "1": "GPIO12{slash}PWM0",
    "2": "GPIO13{slash}PWM1",
    "3": "GPIO16",
    "4": "GPIO17",
    "6": "GPIO22",
    "7": "GPIO11{slash}SPI0.SCLK",
    "9": "GPIO23",
}

tree.append(ks.make_db9_symbol("J3", "DE9_Socket_MountingHoles", (110, 250), proj, root))

for pin, label_text in PIN_TO_LABEL.items():
    tree.append(ks.make_label(label_text, J3_PINS[pin]))

tree.append(ks.make_power_symbol("power:+3.3V", "#PWR903", "+3V3", J3_PINS["5"], proj, root))
tree.append(ks.make_power_symbol("power:GND", "#PWR904", "GND", J3_PINS["8"], proj, root))
tree.append(ks.make_no_connect(J3_PINS["0"]))

open(PATH, "w").write(ks.dumps(tree))
print("Task 5 edits applied.")
```

- [ ] **Step 2: Run it**

```bash
python3 scripts/task5_add_j3.py
```

Expected: `Task 5 edits applied.`

- [ ] **Step 3: Verify ERC is fully clean**

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch
cat genesis-controller-hat-erc.rpt
```

Expected: the report's final line reads `** ERC messages: 0  Errors 0  Warnings **` — every dangling label from the baseline is now either wired or deleted, and both power flags are resolved. If anything nonzero remains, do not proceed to Task 6 — the PCB task assumes a schematic with no outstanding connectivity problems.

- [ ] **Step 4: Commit**

```bash
git add genesis-controller-hat.kicad_sch scripts/task5_add_j3.py
git commit -m "$(cat <<'EOF'
Wire Player 2 DB9 connector (J3) to the GPIO header

Mirrors Task 4's Player 1 wiring onto GPIO12/13/16/17/22/11/23 per
sega_board.h. Schematic ERC is now fully clean (0 errors, 0 warnings).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: PCB layout — place J2/J3, route, silkscreen

**Files:**
- Create: `scripts/task6_pcb_layout.py`
- Modify: `genesis-controller-hat.kicad_pcb`

**Interfaces:**
- Consumes: the **`pcbnew` Python module directly** (`/usr/lib/python3/dist-packages/pcbnew.py`, installed alongside the `kicad` apt package — confirmed working during planning: `LoadBoard`, `FootprintLoad`, `board.Add`, per-pad `SetNet` by net-name lookup, `PCB_TRACK`, and `SaveBoard` all round-trip cleanly through `kicad-cli pcb drc` on a scratch copy of this exact template). This is a deliberate change from Tasks 2–5's hand-rolled S-expression approach: for the PCB, going through KiCad's real object model avoids re-implementing net-table bookkeeping (net codes, pad-to-net linking) by hand, which is a much easier place to introduce a subtle, silent mismatch than the schematic edits were.
- Produces: a routed, DRC-clean PCB. Placement is the one part of this plan that can't be fully pre-asserted the way the schematic tasks were — DB9 shell courtyards are ~32mm wide and two side-by-side barely fit inside the board's 65mm width — so it's verified visually (SVG export, since this environment has no display) in addition to DRC, and adjusted if needed.

**Important scoping note:** `kicad-cli pcb drc --schematic-parity` is **not** used as this task's gate. The vanilla template's `.kicad_pcb` ships with net-table entries for every pin the original (EEPROM-inclusive) schematic ever labeled, including the 12 GPIO nets and the EEPROM/+5V nets Tasks 2–3 deleted from the schematic. There is no `kicad-cli` subcommand to re-sync a PCB's net table from a modified schematic headlessly (that's normally the GUI's "Update PCB from Schematic" action). Leaving those now-stale, zero-pad net-table entries in place is harmless — DRC's default checks don't flag an unused net — so this task verifies plain `kicad-cli pcb drc` (which does catch anything that actually matters: unrouted pads, clearance, courtyard overlaps) rather than parity, and the README (Task 7) notes this explicitly so nobody mistakes it for full schematic/PCB sync.

Confirmed reference geometry: the board's `Edge.Cuts` outline occupies absolute (page) coordinates x=100..165, y=44..100.5 (65×56.5mm, 3mm corner radius, offset `(100,44)` from the board's own local origin). The four mounting holes sit at absolute `(103.5,47.5)`, `(103.5,96.5)`, `(161.5,47.5)`, `(161.5,96.5)` — matches `hat-board-mechanical.pdf`'s 58mm×49mm/3.5mm-inset spec exactly. J1 (GPIO header) is already placed by the template at absolute `(108.37, 48.77)`, rotated -90°, on `B.Cu` — leave it untouched. Net names confirmed by loading the template board with `pcbnew.LoadBoard`: local-label-derived nets carry a leading `/` (e.g. `/GPIO5`, `/GPIO4{slash}GPCLK0`), while power-symbol nets don't (`GND`, `+3V3`).

- [ ] **Step 1: Write the layout + routing script**

Create `scripts/task6_pcb_layout.py`:

```python
import sys
sys.path.insert(0, "/usr/lib/python3/dist-packages")
import pcbnew

PATH = "genesis-controller-hat.kicad_pcb"
FP_LIB = "/usr/share/kicad/footprints/Connector_Dsub.pretty"
FP_NAME = "DSUB-9_Socket_Vertical_P2.77x2.84mm_MountingHoles"

board = pcbnew.LoadBoard(PATH)
netinfo = board.GetNetInfo()


def net_by_name(name):
    for i in range(netinfo.GetNetCount()):
        ni = netinfo.GetNetItem(i)
        if ni.GetNetname() == name:
            return ni
    raise KeyError(f"net {name!r} not found in {PATH} -- did Tasks 2-5 run first?")


# DB9 pin -> (net name, J1 pad number to route to). Pin "0" (shell/mounting
# pad) intentionally gets no net, matching the schematic's no-connect flag.
PIN_NETS = {
    "1": ("/GPIO5", "29"),
    "2": ("/GPIO6", "31"),
    "3": ("/GPIO7{slash}SPI0.CE1", "26"),
    "4": ("/GPIO8{slash}SPI0.CE0", "24"),
    "5": ("+3V3", "1"),
    "6": ("/GPIO9{slash}SPI0.MISO", "21"),
    "7": ("/GPIO4{slash}GPCLK0", "7"),
    "8": ("GND", "9"),
    "9": ("/GPIO10{slash}SPI0.MOSI", "19"),
}

PIN_NETS_J3 = {
    "1": ("/GPIO12{slash}PWM0", "32"),
    "2": ("/GPIO13{slash}PWM1", "33"),
    "3": ("/GPIO16", "36"),
    "4": ("/GPIO17", "11"),
    "5": ("+3V3", "17"),
    "6": ("/GPIO22", "15"),
    "7": ("/GPIO11{slash}SPI0.SCLK", "23"),
    "8": ("GND", "34"),
    "9": ("/GPIO23", "16"),
}

j1 = board.FindFootprintByReference("J1")


def place_and_wire(ref, at_mm, rotation_deg, pin_nets):
    fp = pcbnew.FootprintLoad(FP_LIB, FP_NAME)
    fp.SetReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I_MM(*at_mm))
    fp.SetOrientationDegrees(rotation_deg)
    board.Add(fp)

    for pin, (net_name, j1_pin) in pin_nets.items():
        pad = fp.FindPadByNumber(pin)
        net = net_by_name(net_name)
        pad.SetNet(net)

        j1_pad = j1.FindPadByNumber(j1_pin)
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(pad.GetPosition())
        track.SetEnd(j1_pad.GetPosition())
        track.SetWidth(pcbnew.FromMM(0.4))
        track.SetLayer(pcbnew.F_Cu)
        track.SetNet(net)
        board.Add(track)

    return fp


# Player 1 left of center, Player 2 right of center, both along the top edge
# (absolute y=44) between the two top mounting holes (absolute x=103.5..161.5).
# Rotation 180 starting guess: shell projects off the top edge, pins land
# on-board. Re-check with Step 2's SVG export and change if backwards.
place_and_wire("J2", (118, 44), 180, PIN_NETS)
place_and_wire("J3", (148, 44), 180, PIN_NETS_J3)

pcbnew.SaveBoard(PATH, board)
print("J2/J3 placed, wired, and routed.")
```

- [ ] **Step 2: Run it and export an SVG to visually check placement**

```bash
python3 scripts/task6_pcb_layout.py
kicad-cli pcb export svg --layers "F.Cu,B.Cu,F.SilkS,Edge.Cuts" -o /tmp/hat-layout-check.svg genesis-controller-hat.kicad_pcb
```

Read `/tmp/hat-layout-check.svg` (it's an image — use the Read tool, not `cat`). Confirm: both DB9 shells project outward past the board's top edge rather than into the board or off a side; J2 and J3 don't overlap each other, the GPIO header, or the mounting holes; the straight-line tracks from Step 1 don't visibly cut through unrelated pads. If the shell points the wrong way, change the `180` rotation argument to `0` in the two `place_and_wire` calls; if footprints or tracks overlap something, adjust the `(118, 44)` / `(148, 44)` X coordinates. After any change, delete the two added footprints before re-running — simplest way is `git checkout -- genesis-controller-hat.kicad_pcb` to reset to Task 5's committed state, then re-run Step 1.

- [ ] **Step 3: Add silkscreen labels**

```python
import sys
sys.path.insert(0, "/usr/lib/python3/dist-packages")
import pcbnew

PATH = "genesis-controller-hat.kicad_pcb"
board = pcbnew.LoadBoard(PATH)

for ref, label, at_mm in (("J2", "Player 1", (118, 36)), ("J3", "Player 2", (148, 36))):
    text = pcbnew.PCB_TEXT(board)
    text.SetText(label)
    text.SetPosition(pcbnew.VECTOR2I_MM(*at_mm))
    text.SetLayer(pcbnew.F_SilkS)
    text.SetTextSize(pcbnew.VECTOR2I_MM(1.5, 1.5))
    board.Add(text)

pcbnew.SaveBoard(PATH, board)
print("Silkscreen labels added.")
```

Run it, then re-export the SVG (Step 2's command) and confirm both labels are legible and don't overlap the mounting holes or connector bodies.

- [ ] **Step 4: Verify DRC**

```bash
kicad-cli pcb drc --severity-all genesis-controller-hat.kicad_pcb
cat genesis-controller-hat-drc.rpt
```

Expected: **0 errors.** The pre-existing `lib_footprint_mismatch` warning on J1 (inherited from the template, cosmetic) is the only acceptable remaining item — confirm nothing else shows up. An `unconnected_items` error means a net from Step 1 wasn't actually routed (check the `PIN_NETS`/`PIN_NETS_J3` table against the pin-map reference table at the top of this plan); a `clearance` or `courtyard_overlaps_*` error means Step 1's placement needs adjusting per Step 2's instructions.

- [ ] **Step 5: Commit**

```bash
git add genesis-controller-hat.kicad_pcb scripts/task6_pcb_layout.py
git commit -m "$(cat <<'EOF'
Place, wire, and route J2/J3 DB9 connectors on the PCB

Both DB9 sockets sit along the board's top edge, shells projecting off
the board per the approved vertical-panel-mount decision. Built with the
pcbnew Python API (not hand-written S-expressions) so net assignment goes
through KiCad's own net table by name rather than manual bookkeeping. DRC
is clean apart from the template's own pre-existing J1 footprint-mismatch
warning.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: README and final verification

**Files:**
- Create: `README.md`

**Interfaces:** none — this is documentation plus a final combined check.

- [ ] **Step 1: Write the README**

Create `README.md`:

```markdown
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

## Verifying the board

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch
kicad-cli pcb drc --severity-all genesis-controller-hat.kicad_pcb
```

ERC should report 0 errors/0 warnings. DRC should report 0 errors (one
pre-existing cosmetic `lib_footprint_mismatch` warning on J1, inherited
from KiCad's own template, is expected and harmless).
```

- [ ] **Step 2: Run the full verification suite one more time end to end**

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch --exit-code-violations; echo "ERC exit: $?"
kicad-cli pcb drc --severity-all genesis-controller-hat.kicad_pcb --exit-code-violations; echo "DRC exit: $?"
```

Expected: ERC report shows 0/0; DRC exit code may be nonzero only due to the known pre-existing J1 warning (confirm by reading the report, not just the exit code).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
Add README pointing to the firmware repo's pin-map source of truth

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```
