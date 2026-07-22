import sys
sys.path.insert(0, "scripts")
import kicad_sexpr as ks

PATH = "genesis-controller-hat.kicad_sch"
tree = ks.parse(open(PATH).read())


def pts_of(n):
    return [c for c in n if isinstance(c, list) and ks.get_tag(c) == "pts"][0][1:]


def all_points_in_box(n, x0, x1, y0, y1):
    return all(x0 <= float(pt[1]) <= x1 and y0 <= float(pt[2]) <= y1 for pt in pts_of(n))


def at_in_box(n, x0, x1, y0, y1):
    at = next(c for c in n if isinstance(c, list) and ks.get_tag(c) == "at")
    return x0 <= float(at[1]) <= x1 and y0 <= float(at[2]) <= y1


def touches_point(n, px, py):
    return any(abs(float(pt[1]) - px) < 0.01 and abs(float(pt[2]) - py) < 0.01 for pt in pts_of(n))


# EEPROM sub-circuit (C1 decoupling cap, R1/R2 pull-ups, JP1 disable jumper,
# U1 the EEPROM itself) and its three local power-flag symbols.
eeprom_refs = {"C1", "R1", "JP1", "R2", "U1", "#PWR0101", "#PWR0102", "#PWR0103"}
removed_eeprom = ks.remove_symbols_by_ref(tree, eeprom_refs)
assert removed_eeprom == 8, f"expected to remove 8 EEPROM-related symbols, removed {removed_eeprom}"

# +5V is never used by this design (Genesis pads are powered at 3.3V per the
# approved spec) -- remove the header's +5V power flag entirely.
removed_5v = ks.remove_symbols_by_ref(tree, {"#PWR01"})
assert removed_5v == 1, f"expected to remove 1 symbol (#PWR01), removed {removed_5v}"

# GPIO0/GPIO1 connect to the EEPROM circuit via two same-name local-label
# pairs (ID_SDA, ID_SCL) -- one instance next to J1's pins, one next to the
# now-deleted R1/R2. Delete all 4 label instances; the pins become bare and
# get explicit no-connect flags below.
removed_labels = ks.remove_labels_by_text(tree, {"ID_SDA", "ID_SCL"})
assert removed_labels == 4, f"expected to remove 4 label instances, removed {removed_labels}"

# Wires/no-connects/junctions that only existed to serve the deleted EEPROM
# circuit and +5V flag. Confirmed by inspection to be the complete set --
# the EEPROM sub-circuit's own wiring sits entirely within one bounding box
# on the sheet, plus two label-side stub wires running out to where the
# J1-side ID_SDA/ID_SCL label instances used to sit, plus one short +5V tie.
before = len(tree)
tree[:] = [n for n in tree if not (
    isinstance(n, list) and ks.get_tag(n) == "wire" and (
        all_points_in_box(n, 60, 111, 160, 195) or       # EEPROM sub-circuit wiring
        all_points_in_box(n, 74, 78, 22, 30) or          # +5V tie stub
        touches_point(n, 31.75, 60.96) or                # J1-side ID_SDA label stub
        touches_point(n, 100.33, 60.96)                  # J1-side ID_SCL label stub
    )
)]
removed_wires = before - len(tree)
assert removed_wires == 23, f"expected to remove 23 wires, removed {removed_wires}"

before = len(tree)
tree[:] = [n for n in tree if not (
    isinstance(n, list) and ks.get_tag(n) == "no_connect" and at_in_box(n, 60, 111, 160, 195)
)]
removed_nc = before - len(tree)
assert removed_nc == 3, f"expected to remove 3 no_connect flags, removed {removed_nc}"

before = len(tree)
tree[:] = [n for n in tree if not (
    isinstance(n, list) and ks.get_tag(n) == "junction" and at_in_box(n, 60, 111, 160, 195)
)]
removed_junctions = before - len(tree)
assert removed_junctions == 6, f"expected to remove 6 junctions, removed {removed_junctions}"

# Mark J1's now-bare GPIO0 (pin 27) and GPIO1 (pin 28) pins as intentionally
# unused -- same pattern as the DB9 shell pin's no-connect in Tasks 4/5.
tree.append(ks.make_no_connect((60.96, 60.96)))
tree.append(ks.make_no_connect((73.66, 60.96)))

# #PWR04 (+3.3V) and #PWR02 (GND) are power_in pins with nothing driving
# them per ERC's rules; a PWR_FLAG on each net tells ERC the net is driven
# from outside this sheet (by the Raspberry Pi itself). Placed exactly
# coincident with #PWR04/#PWR02's own positions -- a PWR_FLAG anywhere else
# forms its own isolated net instead of joining the one it's meant to prove
# is driven.
proj = ks.project_name(tree)
root = ks.root_uuid(tree)
ks.ensure_lib_symbol_cached(tree, "power:PWR_FLAG")
tree.append(ks.make_power_symbol("power:PWR_FLAG", "#FLG901", "PWR_FLAG", (55.88, 24.13), proj, root))
tree.append(ks.make_power_symbol("power:PWR_FLAG", "#FLG902", "PWR_FLAG", (76.20, 80.01), proj, root))

open(PATH, "w").write(ks.dumps(tree))
print("Task 2 edits applied.")
