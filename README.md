# Home Assistant Otodata BLE

Home Assistant integration for Otodata propane tank monitors. It reads the tank
level from the monitor's Bluetooth broadcasts.

Tested with a TM6030. Other Otodata monitors that broadcast the same packets
should work. Open an issue if yours doesn't.

## Requirements

- Home Assistant 2026.6.4 or newer
- A Bluetooth adapter or an ESPHome Bluetooth proxy within range of the tank

## Installation

1. In HACS, add `https://github.com/jterrace/ha-otodata-ble` as a custom
   repository with type Integration.
2. Download Otodata BLE and restart Home Assistant.

## Setup

Home Assistant finds the monitor on its own and shows it under Settings >
Devices & services as a discovered device. Click Add and confirm.

The monitor only broadcasts every few hours, so it can take a while to show
up. You can also add the integration by hand, which lists monitors Home
Assistant has already heard.

## Entities

| Entity          | Description                                                      |
| --------------- | ---------------------------------------------------------------- |
| Propane level   | Tank level in percent                                            |
| Signal strength | Bluetooth signal in dBm. Diagnostic, disabled by default.        |

The device's model and serial number fill in when the monitor sends its
device info packet, which can be some time after setup.

The level is for the tank the monitor is mounted on. If you have two tanks
plumbed together, only one is measured.

The sensors go unavailable if the monitor stops broadcasting for longer than
usual. Until Home Assistant learns how often your monitor broadcasts, it
allows 6 hours.

## Debug logging

Add this to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.otodata_ble: debug
```

Every Otodata packet is then logged with its raw bytes. Include these logs
when you open an issue.

## Protocol

The packet format is in [docs/tech-info.md](docs/tech-info.md).
