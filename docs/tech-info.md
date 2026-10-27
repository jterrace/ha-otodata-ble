# Otodata BLE Advertisement Format (Propane Tank Monitor)

Reverse-engineered from captures of a TM6030 monitor.

## Identifiers

- **Company ID:** `0x03B1` (945), sent little-endian as `b1 03`.
- The BLE address stays the same across captures, so it can be used as the device's unique ID.

## Payload Format

**All offsets below are into the payload.** The payload is what bleak and Home
Assistant expose as `manufacturer_data[945]`, i.e. with the company ID already
removed.

Every payload starts with a 7-character ASCII packet type:

| Type      | Length | Contents                          |
| --------- | ------ | --------------------------------- |
| `OTO3281` | 23     | Device info: serial, model number |
| `OTOTELE` | 24     | Telemetry: tank level             |
| `OTOSTAT` | 24     | Status: not yet decoded           |

## OTO3281: device info

| Offset  | Type   | Meaning       | Example                    |
| ------- | ------ | ------------- | -------------------------- |
| `0:7`   | ASCII  | `OTO3281`     |                            |
| `7:11`  | u32 LE | Serial number | `9d 7c 38 01` → `20479133` |
| `11:19` | ?      | Unknown       | `0d 12 10 03 64 04 02 1a`  |
| `19:21` | u16 LE | Model number  | `8e 17` → `6030` (TM6030)  |
| `21:23` | ?      | Unknown       | `00 04`                    |

## OTOTELE: telemetry

| Offset  | Type   | Meaning                                                               | Example                   |
| ------- | ------ | --------------------------------------------------------------------- | ------------------------- |
| `0:7`   | ASCII  | `OTOTELE`                                                             |                           |
| `7`     | u8     | Unknown, always `02`                                                  |                           |
| `8`     | u8     | Unknown, always `00`                                                  |                           |
| `9:11`  | u16 LE | **Tank level, hundredths of %**                                       | `c0 0c` → `3264` → 32.64% |
| `11`    | u8     | Unknown, always `00`                                                  |                           |
| `12`    | u8     | Unknown, maybe status (`05`, `00`)                                    |                           |
| `13`    | u8     | Unknown (`70`, `71`)                                                  |                           |
| `14`    | u8     | Counter? Goes up ~1 per packet (`54`→`5a`→`6e`→…→`77` over one night) |                           |
| `15:24` | ?      | Constant so far: `06 18 00 00 ff 00 00 00 00`                         |                           |

**Tank level = `u16_le(payload[9:11]) / 100`.**

## OTOSTAT: status (not decoded)

| Offset  | Type   | Observed                                                                            |
| ------- | ------ | ----------------------------------------------------------------------------------- |
| `0:7`   | ASCII  | `OTOSTAT`                                                                           |
| `7`     | u8     | Always `01`                                                                         |
| `8:10`  | u16 LE | Varies a lot, not monotonic: 115, 117, 137, 346, 1004, 1091, 1324, 2483, 3988, 5471 |
| `10:12` | u16 LE | Always equal to `8:10`                                                              |
| `12:16` | u32 LE | Constant `8a bc 04 00` (310410). Not the serial.                                    |
| `16`    | u8     | Always `07`                                                                         |
| `17`    | u8     | `b3`, `b6` or `b7`. Maybe battery or temperature.                                   |
| `18:24` | —      | Always zero                                                                         |

## Device name (scan response)

The local name is sent only in the scan response, so it's seen only with
active scanning. A passive ESPHome proxy never sees it. The name rotates
between:

- `TM6030 <serial>`
- `level: <x.x> % vertical`: level rounded to 0.1%
- `unit sleeping`
- `trbl:ACC (<x.x>)`: a trouble state, probably the accelerometer. It has
  been seen for many hours at a time, during which the device stopped
  advertising the other names. It recovered on its own.

bleak caches the name separately from the manufacturer data, so the name shown
next to a packet may come from an earlier advertisement. The name has been seen
saying `level: 32.6 % vertical` while the payload had already dropped to
31.44–31.45%, so the name lags behind the payload.

**Integrations should not depend on the name.** Everything they need is in the
payload.

## Sample payloads (hex)

```
OTO3281  4f544f333238319d7c38010d1210036404021a8e170004
OTOTELE  4f544f54454c450200121d0005703606180000ff00000000   74.42%
OTOTELE  4f544f54454c450200c00c0000715406180000ff00000000   32.64%
OTOSTAT  4f544f5354415401730073008abc040007b7000000000000
```
