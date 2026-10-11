#!/usr/bin/env python3
"""Gera mouthpad_grid.kicad_pcb: grade capacitiva 6x6 em losangos (flex 2 camadas).

Linhas R0..R5 em F.Cu, colunas C0..C5 em B.Cu, cauda com 13 pads (pitch 1,0 mm)
na ordem R0..R5, GND, C0..C5. Rode: python3 gen_grid.py
"""
import uuid

P = 3.0          # pitch dos losangos (mm)
H = 1.3          # meia-diagonal do losango -> gap ~0,28 mm entre linha/coluna
N = 6
NECK = 0.3       # largura da ponte entre losangos
TW = 0.25        # largura das trilhas de saida
PAD_Y = 30.0
VIA_Y = 27.5

nets = ["", *[f"R{i}" for i in range(N)], "GND", *[f"C{i}" for i in range(N)]]
net = {n: i for i, n in enumerate(nets)}
out = []
u = lambda: f'(uuid "{uuid.uuid4()}")'


def seg(x1, y1, x2, y2, layer, n, w=TW):
    out.append(f'  (segment (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) '
               f'(width {w}) (layer "{layer}") (net {net[n]}) {u()})')


def path(pts, layer, n, w=TW):
    for a, b in zip(pts, pts[1:]):
        seg(*a, *b, layer, n, w)


def diamond(cx, cy, layer, n):
    pts = [(cx, cy - H), (cx + H, cy), (cx, cy + H), (cx - H, cy)]
    xy = " ".join(f"(xy {x:.3f} {y:.3f})" for x, y in pts)
    out.append(
        f'  (zone (net {net[n]}) (net_name "{n}") (layer "{layer}") {u()} (hatch edge 0.5)\n'
        f'    (connect_pads yes (clearance 0.2)) (min_thickness 0.1) (filled_areas_thickness no)\n'
        f'    (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.3))\n'
        f'    (polygon (pts {xy}))\n'
        f'    (filled_polygon (layer "{layer}") (pts {xy})))')


# --- grade ---
for j in range(N):                       # linhas (F.Cu)
    n = f"R{j}"
    for i in range(N):
        diamond(i * P, j * P, "F.Cu", n)
    seg(0, j * P, (N - 1) * P, j * P, "F.Cu", n, NECK)
for i in range(N):                       # colunas (B.Cu), deslocadas meio pitch
    n = f"C{i}"
    x = (i + 0.5) * P
    for j in range(N):
        diamond(x, (j + 0.5) * P, "B.Cu", n)
    seg(x, 0.5 * P, x, (N - 0.5) * P, "B.Cu", n, NECK)

pad_x = lambda k: 1.5 + k                # k = indice na cauda (0..12)

# --- roteamento das linhas: "L" aninhados pela esquerda ---
for j in range(N):
    lane = -2 - (N - 1 - j) * 0.6
    turn = 19 + (N - 1 - j) * 0.6
    path([(0, j * P), (lane, j * P), (lane, turn), (pad_x(j), turn), (pad_x(j), PAD_Y)],
         "F.Cu", f"R{j}")

# --- roteamento das colunas em B.Cu ate vias, depois F.Cu ate os pads ---
turns = [20.2, 19.6, 19.0, 18.5, 18.5, 19.0]
for i in range(N):
    x0, px = (i + 0.5) * P, pad_x(7 + i)
    ybot = (N - 0.5) * P
    path([(x0, ybot), (x0, turns[i]), (px, turns[i]), (px, VIA_Y)], "B.Cu", f"C{i}")
    out.append(f'  (via (at {px:.3f} {VIA_Y}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") '
               f'(net {net[f"C{i}"]}) {u()})')
    seg(px, VIA_Y, px, PAD_Y, "F.Cu", f"C{i}")

# --- conector (pads da cauda, para FPC ZIF 13p 1,0 mm ou solda direta) ---
order = [*[f"R{i}" for i in range(N)], "GND", *[f"C{i}" for i in range(N)]]
pads = "\n".join(
    f'    (pad "{k + 1}" smd rect (at {pad_x(k) - 7.5:.3f} 0) (size 0.6 2.0) '
    f'(layers "F.Cu" "F.Mask") (net {net[n]} "{n}") {u()})' for k, n in enumerate(order))
out.append(f'''  (footprint "MouthPad:FPC_Tail_13P_P1.0mm" (layer "F.Cu") {u()} (at 7.5 {PAD_Y})
    (property "Reference" "J1" (at 0 2.2 0) (layer "F.SilkS") {u()} (effects (font (size 0.8 0.8) (thickness 0.12))))
    (property "Value" "TAIL_13P" (at 0 -2.2 0) (layer "F.Fab") {u()} (effects (font (size 0.8 0.8) (thickness 0.12))))
{pads}
  )''')

# --- contorno: area da grade + cauda ---
outline = [(-6, -2.5), (18.5, -2.5), (18.5, 23), (14.5, 23), (14.5, 31.5),
           (0.5, 31.5), (0.5, 23), (-6, 23)]
for a, b in zip(outline, outline[1:] + outline[:1]):
    out.append(f'  (gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) '
               f'(stroke (width 0.1) (type default)) (layer "Edge.Cuts") {u()})')
out.append(f'  (gr_text "MouthPad DIY grid 6x6" (at 6.25 -1.8 0) (layer "F.SilkS") {u()} '
           f'(effects (font (size 0.7 0.7) (thickness 0.1))))')

header = f'''(kicad_pcb (version 20240108) (generator "mouthpad_gen_grid") (generator_version "8.0")
  (general (thickness 0.11) (legacy_teardrops no))
  (paper "A4")
  (layers
    (0 "F.Cu" signal) (31 "B.Cu" signal)
    (34 "B.Paste" user) (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user) (39 "F.Mask" user)
    (44 "Edge.Cuts" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user) (49 "F.Fab" user)
  )
  (setup
    (stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.018))
      (layer "dielectric 1" (type "core") (thickness 0.025) (material "Polyimide") (epsilon_r 3.2) (loss_tangent 0.004))
      (layer "B.Cu" (type "copper") (thickness 0.018))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
      (copper_finish "ENIG")
      (dielectric_constraints no)
    )
    (pad_to_mask_clearance 0)
  )
''' + "\n".join(f'  (net {i} "{n}")' for i, n in enumerate(nets)) + "\n"

with open("mouthpad_grid.kicad_pcb", "w") as f:
    f.write(header + "\n".join(out) + "\n)\n")
print("ok:", len(out), "itens")
