# MouthPad DIY - mouse Bluetooth controlado pela lingua
# CircuitPython 9.x | Seeed XIAO nRF52840 + MPR121 (grade 6x6 de eletrodos)
# Libs: adafruit_ble, adafruit_hid, adafruit_mpr121 (circup install ...)
import time
import board
import busio
import adafruit_mpr121
import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_hid.mouse import Mouse

ROWS = (0, 1, 2, 3, 4, 5)    # eletrodos E0..E5 = linhas
COLS = (6, 7, 8, 9, 10, 11)  # eletrodos E6..E11 = colunas
SENSIBILIDADE = 6.0          # ganho do cursor
LIMIAR = 12                  # delta minimo (baseline - filtrado) p/ considerar toque
TAP_MAX = 0.25               # s: toque curto = clique esquerdo
HOLD_MIN = 0.8               # s: toque longo parado = clique direito
SUAVIZACAO = 0.4             # filtro exponencial (0 = sem filtro)

i2c = busio.I2C(board.SCL, board.SDA)
mpr = adafruit_mpr121.MPR121(i2c)

hid = HIDService()
ble = adafruit_ble.BLERadio()
ble.name = "MouthPad DIY"
adv = ProvideServicesAdvertisement(hid)
adv.appearance = 962  # HID mouse
mouse = Mouse(hid.devices)


def deltas(canais):
    out = []
    for c in canais:
        d = mpr.baseline_data(c) * 4 - mpr.filtered_data(c)
        out.append(max(0, d - LIMIAR))
    return out


def centroide(pesos):
    total = sum(pesos)
    if total == 0:
        return None
    return sum(i * p for i, p in enumerate(pesos)) / total


def ler_posicao():
    y = centroide(deltas(ROWS))
    x = centroide(deltas(COLS))
    if x is None or y is None:
        return None
    return x, y


while True:
    if not ble.connected:
        ble.start_advertising(adv)
        while not ble.connected:
            time.sleep(0.1)
        ble.stop_advertising()

    ultimo = None
    fx = fy = 0.0
    t0 = 0
    andou = 0.0
    while ble.connected:
        pos = ler_posicao()
        agora = time.monotonic()
        if pos and ultimo is None:            # inicio do toque
            t0, andou = agora, 0.0
            ultimo = pos
        elif pos:                              # arrastando
            dx = (pos[0] - ultimo[0]) * SENSIBILIDADE * 10
            dy = (pos[1] - ultimo[1]) * SENSIBILIDADE * 10
            fx = SUAVIZACAO * fx + (1 - SUAVIZACAO) * dx
            fy = SUAVIZACAO * fy + (1 - SUAVIZACAO) * dy
            andou += abs(fx) + abs(fy)
            if int(fx) or int(fy):
                mouse.move(x=int(fx), y=int(fy))
            ultimo = pos
            if agora - t0 > HOLD_MIN and andou < 15:
                mouse.click(Mouse.RIGHT_BUTTON)
                t0 = agora + 10                # evita repetir
        elif ultimo is not None:               # fim do toque
            if agora - t0 < TAP_MAX and andou < 15:
                mouse.click(Mouse.LEFT_BUTTON)
            ultimo = None
            fx = fy = 0.0
        time.sleep(0.01)
