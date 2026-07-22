import sys
sys.path.insert(0, "/usr/lib/python3/dist-packages")
import pcbnew

PATH = "genesis-controller-hat.kicad_pcb"
board = pcbnew.LoadBoard(PATH)

for ref, label, at_mm in (("J2", "Player 1", (118, 74)), ("J3", "Player 2", (161, 74))):
    text = pcbnew.PCB_TEXT(board)
    text.SetText(label)
    text.SetPosition(pcbnew.VECTOR2I_MM(*at_mm))
    text.SetLayer(pcbnew.F_SilkS)
    text.SetTextSize(pcbnew.VECTOR2I_MM(1.5, 1.5))
    board.Add(text)

pcbnew.SaveBoard(PATH, board)
print("Silkscreen labels added.")
