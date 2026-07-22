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


def pts_of(n):
    return [c for c in n if isinstance(c, list) and ks.get_tag(c) == "pts"][0][1:]


def matches_pair(n, p1, p2):
    pts = pts_of(n)
    coords = {(round(float(p[1]), 2), round(float(p[2]), 2)) for p in pts}
    return coords == {(round(p1[0], 2), round(p1[1], 2)), (round(p2[0], 2), round(p2[1], 2))}


# Each deleted label sat at one end of a short wire whose other end is J1's
# actual pin. Confirmed by inspection against the pre-removal file (each pair
# below is (label-side endpoint, pin-side endpoint)); deleting the label
# without also deleting this wire leaves a dangling stub.
WIRE_PAIRS = [
    ((73.66, 76.2), (100.33, 76.2)), ((31.75, 71.12), (60.96, 71.12)),
    ((31.75, 43.18), (60.96, 43.18)), ((31.75, 73.66), (60.96, 73.66)),
    ((73.66, 35.56), (100.33, 35.56)), ((73.66, 38.1), (100.33, 38.1)),
    ((60.96, 30.48), (31.75, 30.48)), ((73.66, 53.34), (100.33, 53.34)),
    ((31.75, 33.02), (60.96, 33.02)), ((73.66, 40.64), (100.33, 40.64)),
    ((73.66, 73.66), (100.33, 73.66)), ((73.66, 48.26), (100.33, 48.26)),
]
# The pin-side endpoint of each pair above -- where a no-connect flag goes
# once the label and its wire are gone, so J1's now-bare pin reads as
# intentionally unused rather than a dangling connection.
PIN_SIDE_POINTS = [
    (60.96, 30.48), (60.96, 33.02), (73.66, 35.56), (73.66, 38.1), (73.66, 40.64),
    (73.66, 48.26), (60.96, 43.18), (73.66, 53.34), (60.96, 71.12), (73.66, 73.66),
    (60.96, 73.66), (73.66, 76.2),
]

before = len(tree)
tree[:] = [n for n in tree if not (
    isinstance(n, list) and ks.get_tag(n) == "wire" and
    any(matches_pair(n, a, b) for a, b in WIRE_PAIRS)
)]
removed_wires = before - len(tree)
assert removed_wires == 12, f"expected to remove 12 wires, removed {removed_wires}"

for point in PIN_SIDE_POINTS:
    tree.append(ks.make_no_connect(point))

open(PATH, "w").write(ks.dumps(tree))
print("Task 3 edits applied.")
