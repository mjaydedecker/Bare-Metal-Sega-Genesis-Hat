import sys
sys.path.insert(0, "/usr/lib/python3/dist-packages")
import pcbnew

PATH = "genesis-controller-hat.kicad_pcb"
FP_LIB = "/usr/share/kicad/footprints/Connector_Dsub.pretty"
FP_NAME = "DSUB-9_Socket_Vertical_P2.77x2.84mm_MountingHoles"
BREAKOUT_Y = pcbnew.FromMM(80.0)  # clears both pin rows (y=84.0, 86.84) before angling to J1

board = pcbnew.LoadBoard(PATH)
netinfo = board.GetNetInfo()


def net_by_name(name):
    for i in range(netinfo.GetNetCount()):
        ni = netinfo.GetNetItem(i)
        if ni.GetNetname() == name:
            return ni
    raise KeyError(f"net {name!r} not found in {PATH} -- did Tasks 2-5 run first?")


# DB9 pin -> (net name, J1 pad number to route to). Pin "0" (shell/mounting
# pad, appears twice in the footprint) intentionally gets no net, matching
# the schematic's no-connect flag.
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


def place(ref, at_mm, rotation_deg):
    fp = pcbnew.FootprintLoad(FP_LIB, FP_NAME)
    fp.SetReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I_MM(*at_mm))
    fp.SetOrientationDegrees(rotation_deg)
    board.Add(fp)
    return fp


# Both connectors on the bottom edge (opposite J1, which runs along the top),
# side by side, clearing the bottom mounting holes (103.5,96.5)/(161.5,96.5)
# and the camera-flex slot -- validated by rendering with
# `kicad-cli pcb render --side top` before this script was finalized.
j2 = place("J2", (118, 84), 0)
j3 = place("J3", (161, 84), 0)


def seg_intersect(p1, p2, p3, p4):
    def cross(o, a, b):
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
    d1 = cross(p3, p4, p1)
    d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3)
    d4 = cross(p1, p2, p4)
    return ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))


# Collect every (start, end, net) pair before routing, then greedily assign
# each a copper layer -- whichever of F.Cu/B.Cu has fewer crossings with
# tracks already placed on it. A breakout waypoint (own X, BREAKOUT_Y) is
# inserted for every net so it exits its own pin cluster vertically first,
# rather than cutting diagonally across the OTHER pin row on the same
# connector (this is what "shorting_items" and most early crossings turned
# out to be during validation -- not track-vs-track, but track-vs-neighboring
# -pad).
nets_info = []
for conn_fp, pin_nets in ((j2, PIN_NETS), (j3, PIN_NETS_J3)):
    for pin, (net_name, j1_pin) in pin_nets.items():
        pad = conn_fp.FindPadByNumber(pin)
        pad.SetNet(net_by_name(net_name))
        j1_pad = j1.FindPadByNumber(j1_pin)
        nets_info.append((pad.GetPosition(), j1_pad.GetPosition(), net_name))

layer_segs = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
placements = []
for start, end, net_name in nets_info:
    waypoint = pcbnew.VECTOR2I(start.x, BREAKOUT_Y)
    segs = [(start, waypoint), (waypoint, end)]
    best = None
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        existing = layer_segs[layer]
        crossings = sum(1 for a, b in segs for s2, e2 in existing if seg_intersect(a, b, s2, e2))
        if best is None or crossings < best[0]:
            best = (crossings, layer)
    layer = best[1]
    layer_segs[layer].extend(segs)
    placements.append(([start, waypoint, end], net_name, layer))

for points, net_name, layer in placements:
    for i in range(len(points) - 1):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(points[i])
        track.SetEnd(points[i + 1])
        track.SetWidth(pcbnew.FromMM(0.4))
        track.SetLayer(layer)
        track.SetNet(net_by_name(net_name))
        board.Add(track)

pcbnew.SaveBoard(PATH, board)
print("J2/J3 placed, wired, and routed.")
