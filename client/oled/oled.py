from PIL import ImageFont

BUS, ADDR = 1, 0x3C
W, H = 128, 64
COL_OFFSET = 0

# some vodoo oled initialization shit
INIT = [0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40, 0xAD, 0x8B,
        0xA1, 0xC8, 0xDA, 0x12, 0x81, 0xCF, 0xD9, 0x22, 0xDB, 0x40,
        0xA4, 0xA6, 0xAF]


def cmd(bus, *c):
    bus.write_i2c_block_data(ADDR, 0x00, list(c))


def init(bus):
    cmd(bus, *INIT)
    clear(bus)


def off(bus):
    cmd(bus, 0xAE)


def clear(bus):
    for page in range(H // 8):
        cmd(bus, 0xB0 + page, 0x00, 0x10)
        for n in (32, 32, 32, 32, 4):
            bus.write_i2c_block_data(ADDR, 0x40, [0] * n)


def show(bus, img):
    px = img.convert("1").load()
    for page in range(H // 8):
        cmd(bus, 0xB0 + page, 0x00 + (COL_OFFSET & 0x0F), 0x10 + (COL_OFFSET >> 4))
        row = [sum((1 << b) for b in range(8) if px[x, page * 8 + b]) for x in range(W)]
        for i in range(0, W, 32):
            bus.write_i2c_block_data(ADDR, 0x40, row[i:i + 32])


def font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()