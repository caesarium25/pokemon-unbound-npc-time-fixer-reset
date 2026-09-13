# Technical notes — Pokémon Unbound NPC Time Fixer Reset

## Save structure used by this tool

The relevant save body is the first `0x20000` bytes (128 KiB), divided into `0x1000`-byte blocks.

For each block:

- section ID: `block + 0xFF4`, little-endian `u16`
- stored checksum: `block + 0xFF6`, little-endian `u16`
- save index/generation: `block + 0xFFC`, little-endian `u32`

The tool scans all blocks, selects those with section ID `4`, and chooses the one with the greatest save index.

## Time Fixer-used flag candidate

Target:

```text
section ID = 4
relative offset = 0xE89
mask = 0x20
```

Repair:

```text
byte &= ~0x20
```

No other byte is changed by the default repair.

## Why this is believed to be the one-time-use flag

A known broken → NPC-fixed comparison in [PUSE](https://zannael.github.io/PUSE/)'s RTC manifest contains:

```text
section 4
relative offset 3721 / 0xE89
0x08 -> 0x28
```

The difference is exactly bit `0x20`.

In the reproduced case:

- GBAdhoc save before TempGBA migration: bit `0x20` set
- TempGBA save after the clock became correct: bit `0x20` still set
- clearing only this bit in the newest generation:
  - save loaded successfully,
  - Frozen Heights Time Fixer became available again,
  - NPC repair completed under correct TempGBA RTC,
  - after reset, RTC tampering warning disappeared.

That sequence is stronger evidence than merely observing the byte difference.

## Why the tool does not edit the RTC timestamp directly

The successful workflow lets Pokémon Unbound itself rebuild its RTC bookkeeping. This avoids guessing multiple RTC metadata fields.

The tool therefore performs the smallest intervention required to restore access to the game's own repair path.

## Why only the latest generation is patched

Pokémon GBA saves retain multiple generations/copies. Leaving the older generation untouched gives the game a fallback if the edited current generation is rejected.

In the reproduced test, newest-generation-only editing worked.

## Section-4 checksum behavior

[PUSE](https://zannael.github.io/PUSE/) treats section IDs `0`, `4`, and `13` as opaque for its RTC workflow. For section 4 it preserves/uses known checksum metadata rather than applying the standard section checksum routine.

The successful one-byte repair also left the section-4 footer/checksum unchanged.

Therefore this tool intentionally does not recalculate section 4's checksum.

## Scope

This tool is intentionally narrow. It is for the scenario where:

1. the RTC source is now correct;
2. the game still reports RTC tampering;
3. the Time Fixer NPC was consumed previously while the RTC was wrong.

It does not attempt to repair a genuinely broken emulator RTC, set the clock, or remove every possible RTC/tamper state.

## Reproduced GBAdhoc → TempGBA recovery case

```text
PSP date/time correct
  -> GBAdhoc/Unbound calendar observed around 2070
  -> RTC tampering warning
  -> Frozen Heights Time Fixer used while RTC state still wrong
  -> save migrated to TempGBA4PSP-Mod
  -> TempGBA supplies correct PSP date/time
  -> save screen date becomes correct
  -> RTC warning persists
  -> PUSE Quick Fix candidate tested in this case is rejected and game falls back
  -> clear section 4 + 0xE89 bit 0x20 in newest generation
  -> Time Fixer NPC becomes available again
  -> NPC repairs save using correct TempGBA RTC
  -> normal in-game save and restart
  -> RTC warning gone
```

The ~2070 observation is documented here as an observed GBAdhoc/Unbound RTC-calendar failure mode. The exact upstream mechanism has not been proven, so it should not be generalized to every GBAdhoc version or game.
