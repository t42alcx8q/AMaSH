# Artifacts for Multi-Admin Smart Home Control-Surface Conflicts

This repository contains supporting artifacts for the paper **"Understanding and Categorizing Control Surface Conflicts and Attacks in Multi-Admin Smart Homes."** The materials document the role/permission surfaces exposed by major smart-home platforms, the attack demonstrations used in the study, and the auxiliary sound-sensor implementation used in the testbed.

## Repository Contents

| Path | Description |
| --- | --- |
| `role_specification.md` | Platform role and permission artifacts for HomeKit, SmartThings, and Google Home. This file links the role-to-surface capability table to screenshots of the platform UIs. |
| `attack_demo.md` | Attack-demo notes and screenshots for the evaluated scenarios. The file includes the testbed/device topology and per-attack evidence for demos A1-A16. |
| `images/` | Screenshots used by `role_specification.md`, including role settings for SmartThings, HomeKit, and Google Home. |
| `images/attack_demo/` | Screenshots used by `attack_demo.md`, including testbed figures and attack-specific UI evidence. |
| `C1-B_demo.gif` | Animated demonstration artifact for one control-surface conflict scenario. |
| `sound_sensor/` | Raspberry Pi sound-sensor code and SmartThings Edge driver used to expose ambient sound state to the smart-home testbed. |
| `LICENSE` | MIT license for the repository materials. |

## Role-Specification Artifacts

`role_specification.md` supports the paper's role-to-surface analysis. It records how each platform maps user roles to capabilities over people, devices, automations, observation/history, and settings/provenance-like surfaces.

- **HomeKit:** owner/resident model. Owners can manage people, accessories/devices, scenes, and automations. Residents have configurable `Control Accessories Remotely` and `Add and Edit Accessories` permissions.
- **SmartThings:** owner/member model. Members can be assigned `Full access` or `Control devices only`; full access includes device and routine management, while device-only access limits the member to device control.
- **Google Home:** admin/member model. Admins have full access to people, devices, and settings. Members cannot manage people or devices, but their access to activity/history and settings/automations can be configured.

## Attack-Demo Artifacts

`attack_demo.md` collects the experimental notes and screenshots for the attack demonstrations. Each demo describes the victim rule, attacker action, and relevant devices or platform surfaces. The screenshots under `images/attack_demo/` provide the UI evidence for the corresponding steps.

The documented demos cover control-surface conflicts such as rule disabling, rule editing, scene weakening, observation suppression, external service binding, role changes, activity-log manipulation, cross-platform Matter binding, and shadow automation/scene replacement.

## Sound Sensor Artifact

The `sound_sensor/` directory contains a small sound-sensing component used in the testbed:

- `sound_sensor/IoT_device/sound_sensor_device.py` runs on a Raspberry Pi with a USB microphone. It samples audio, computes an RMS-derived dB value, applies threshold/hysteresis/debounce logic, and exposes `/health` and `/state` HTTP endpoints.
- `sound_sensor/edge_driver/` contains a SmartThings Edge driver that polls the Raspberry Pi endpoint over the LAN and maps the result to SmartThings capabilities including `switch`, `soundSensor`, and `soundPressureLevel`.

Example Raspberry Pi command:

```bash
python sound_sensor/IoT_device/sound_sensor_device.py \
  --device plughw:2,0 \
  --threshold_db -63 \
  --hysteresis_db 6 \
  --debounce_on 2 \
  --debounce_off 4 \
  --chunk_ms 300 \
  --http_port 8787
```

The Edge driver preferences specify the Raspberry Pi host, port, HTTP path, poll interval, timeout, and dB offset used for display.

## How to Read the Artifacts

Start with `role_specification.md` to understand the permission model used in the paper's taxonomy. Then read `attack_demo.md` alongside `images/attack_demo/` to inspect the concrete demonstrations and UI evidence. The `sound_sensor/` code is only needed for reproducing the sound-triggered portions of the testbed.

## License

The artifacts are released under the MIT License. See `LICENSE` for details.
