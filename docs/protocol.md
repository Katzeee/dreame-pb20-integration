# PB20 protocol

Supported model: `dreame.airp.u2605`.
Verified firmware: `2.0.27_1029`.

## Properties

| Service / property | Meaning | Values or conversion |
| --- | --- | --- |
| `2 / 1` | Power status, read only | 1 running, 2 standby |
| `2 / 3` | Mode | 0 AI Purify, 2 sleep, 3 custom |
| `2 / 4` | Fan speed | Levels 1–10 |
| `3 / 2` | Humidity | % |
| `3 / 3` | Temperature | °C |
| `3 / 4` | Air quality | 1 excellent, 2 good, 3 average, 4 poor; -1 unknown |
| `3 / 5` | PM2.5 | µg/m³ |
| `3 / 6` | PM10 | µg/m³ |
| `3 / 7` | Formaldehyde | Raw value / 1000, mg/m³ |
| `4 / 16` | All-in-one filter remaining | % |
| `4 / 17` | All-in-one filter days remaining | Days, despite the App model's Hours name |
| `3 / 12` | Dreame AQ index | Dimensionless, vendor-specific scale |
| `6 / 10` | Child lock | 0 off, 1 on |
| `6 / 15` | Continuous monitoring in standby | 0 off, 1 on |
| `6 / 21` | UVC | 0 off, 1 on |

The App formats formaldehyde to two decimal places. The integration preserves the
converted measurement and recommends two decimal places for display.

## Power action

Power uses `action`, with service `2`, action `1`, and input property `1`:

```json
{"did":"<device-id>","siid":2,"aiid":1,"in":[{"piid":1,"value":1}]}
```

The input uses `1` for on and `0` for standby. This differs from the readable power
status enumeration. Writing the power status property directly returns `-4002`.
The action sets an absolute state; it does not toggle.

## Filter maintenance

Replacing the all-in-one filter uses service `4`, action `8`, without an `in`
field. The action definition comes from the PB20 device plugin. The reset button
is disabled by default. Its command is not exercised on a used filter, so its
acknowledgement is not yet verified live. It remains an explicit maintenance action.
The App displays property `4 / 17 = 1076` as **1076 Days Remaining**.

## State and concurrency

The cloud envelope and inner command share a fresh correlation ID on each RPC.
The device lock serializes polling, command sequences, and their readback.
Setting a manual speed writes Custom mode and the selected level in one request.
Property write responses must account for every requested address and report success.
Power responses must identify the requested device, service, and action.
An accepted cloud envelope without a device result is a failure.

Each successful poll replaces the complete snapshot. Missing properties remain
unknown rather than retaining an earlier value. HA receives reported device state;
there are no optimistic control values.

Cloud authentication renewal has a separate lock. One HTTP authentication rejection
allows one renewal and retry. Other command failures are surfaced without resending
the write. A timeout can mean the device applies a command without returning its
response; HA therefore refreshes the state before reporting the command error.

## Verification

Definitions come from the official PB20 React Native device plugin and independent
cloud requests. The device plugin metadata identifies project version 41. The
device bundle has SHA-256
`89bdc652865912d85bfc3fe2445b78e8641c907b4d0a272077f8e196853b14e7`.
No App binaries, device bundles, account credentials, or account traces are distributed.

On 2026-11-21, the independent client successfully reads the listed measurements and
operates sleep mode, Custom at level 5, standby, power on, and AI Purify. Device
readback confirms each operation. It restores Custom mode at level 3. Mode and
speed reconnaissance also verifies the App's level 1, 3, and 10 readings.

The HA modules import successfully in Home Assistant 2026.11.1. Verification is
limited to the China mainland endpoint and the firmware above; other available
regions use the same endpoint format but do not have live verification here.

Child lock, continuous monitoring, and UVC each accept a 0-to-1 write and read back
1. Each setting restores to its initial 0 value. Continuous monitoring also
controls sensor availability during standby.

The AQ index exposes the vendor value directly, without pretending it uses a
standard AQI scale. Display brightness is not a PB20 setting in the device plugin.
Scheduling, App account management, city/time-zone configuration, and OTA updates
are outside the supported surface.
