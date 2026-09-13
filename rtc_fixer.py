#!/usr/bin/env python3
"""Pokémon Unbound NPC Time Fixer Reset.

Clears bit 0x20 at section 4 + 0xE89 in the newest save generation.
Always keep an untouched backup.
"""

from __future__ import annotations
import argparse
from pathlib import Path
import struct
import sys

SAVE_BODY_LEN = 0x20000
SECTION_SIZE = 0x1000
SECTION_ID_OFF = 0xFF4
SAVE_INDEX_OFF = 0xFFC
TARGET_SECTION_ID = 4
TARGET_REL_OFF = 0xE89
TARGET_MASK = 0x20

def u16le(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]

def u32le(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]

def section4_copies(data: bytes):
    if len(data) < SAVE_BODY_LEN:
        raise ValueError(f"Save is too small ({len(data)} bytes); expected at least {SAVE_BODY_LEN} bytes.")
    copies = []
    for off in range(0, SAVE_BODY_LEN, SECTION_SIZE):
        sid = u16le(data, off + SECTION_ID_OFF)
        idx = u32le(data, off + SAVE_INDEX_OFF)
        if sid == TARGET_SECTION_ID and idx > 0:
            copies.append((idx, off))
    copies.sort(reverse=True)
    return copies

def patch(data: bytes, all_copies: bool = False):
    copies = section4_copies(data)
    if not copies:
        raise ValueError("Could not locate a valid section-4 copy.")
    chosen = copies if all_copies else copies[:1]
    out = bytearray(data)
    changes = []
    for idx, off in chosen:
        pos = off + TARGET_REL_OFF
        before = out[pos]
        after = before & (~TARGET_MASK & 0xFF)
        out[pos] = after
        changes.append((idx, pos, before, after))
    return bytes(out), changes, copies

def main():
    ap = argparse.ArgumentParser(description="Re-enable Pokémon Unbound's one-time Frozen Heights RTC Time Fixer.")
    ap.add_argument("save", type=Path, help="Input .sav file")
    ap.add_argument("-o", "--output", type=Path, help="Output .sav file")
    ap.add_argument("--all-copies", action="store_true", help="Patch every valid section-4 copy instead of only the newest (not recommended by default).")
    args = ap.parse_args()
    data = args.save.read_bytes()
    try:
        patched, changes, copies = patch(data, args.all_copies)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2)
    out = args.output or args.save.with_name(args.save.stem + ".npc-timefixer-reset.sav")
    out.write_bytes(patched)
    print(f"Input:  {args.save}")
    print(f"Output: {out}")
    print("Section-4 copies:", ", ".join(f"idx={idx}@0x{off:X}" for idx, off in copies))
    for idx, pos, before, after in changes:
        print(f"Patched save index {idx}: 0x{pos:X}: 0x{before:02X} -> 0x{after:02X}")
    if all(before == after for _, _, before, after in changes):
        print("Note: target bit was already clear; output is effectively unchanged at the target byte.")
    else:
        print("Next: load the save, use the Frozen Heights Time Fixer NPC, save in-game, then restart.")

if __name__ == "__main__":
    main()
