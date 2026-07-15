"""
Kreira placeholder TGA fajlove za Croatia, Bosnia, Serbia.
Svaka frakcija dobiva 3 TGA fajla:
  - data/ui/symbols/symbol_X.tga         (32x32, simbol frakcije)
  - data/ui/rebel_symbols/rebel_X.tga    (32x32, rebel simbol)
  - data/ui/loading_screen/symbols/symbol128_X.tga  (128x128, loading screen)
"""

import struct
import os

def create_tga(width, height, r, g, b, filepath):
    """Kreira solid-color uncompressed TGA (BGR format)."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # TGA header (18 bytes)
    header = struct.pack('<BBBHHBHHHHBB',
        0,          # ID length
        0,          # color map type (none)
        2,          # image type: uncompressed true-color
        0,          # color map first entry index
        0,          # color map length
        0,          # color map entry size
        0,          # x origin
        0,          # y origin
        width,      # width
        height,     # height
        24,         # bits per pixel (RGB, no alpha)
        0x20        # image descriptor: top-left origin
    )

    # Pixel data (BGR order for TGA)
    pixel = bytes([b, g, r])  # BGR
    pixels = pixel * (width * height)

    with open(filepath, 'wb') as f:
        f.write(header)
        f.write(pixels)

    print(f"  Created: {os.path.basename(filepath)} ({width}x{height}, RGB={r},{g},{b})")

mod = r"C:\Program Files (x86)\Steam\steamapps\common\Medieval II Total War\mods\croatia_overhaul"

# Faction color schemes (R, G, B)
factions = {
    'croatia': (200, 30, 30),    # red - Croatian flag
    'bosnia':  (30, 60, 160),    # blue - Bosnian flag
    'serbia':  (150, 20, 20),    # dark red - Serbian flag
}

for faction, (r, g, b) in factions.items():
    print(f"\n{faction.upper()} (R={r}, G={g}, B={b}):")

    # Symbol (32x32)
    create_tga(32, 32, r, g, b,
        f"{mod}/data/ui/symbols/symbol_{faction}.tga")

    # Rebel symbol (32x32) - slightly lighter
    rl, gl, bl = min(r+40, 255), min(g+40, 255), min(b+40, 255)
    create_tga(32, 32, rl, gl, bl,
        f"{mod}/data/ui/rebel_symbols/rebel_{faction}.tga")

    # Loading screen symbol (128x128)
    create_tga(128, 128, r, g, b,
        f"{mod}/data/ui/loading_screen/symbols/symbol128_{faction}.tga")

print("\nAll TGA banners created!")
print(f"\nPaths:")
for faction in factions:
    print(f"  {mod}/data/ui/symbols/symbol_{faction}.tga")
    print(f"  {mod}/data/ui/rebel_symbols/rebel_{faction}.tga")
    print(f"  {mod}/data/ui/loading_screen/symbols/symbol128_{faction}.tga")
