# Home Assistant Towel Warmer Plug Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

Integrate plug-controlled towel warmers into your Home Assistant. This integration allows you to automate their operation based on a configurable daily schedule and detect malfunctions via power monitoring.

- [Home Assistant Towel Warmer Plug Integration](#home-assistant-towel-warmer-plug-integration)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Entities](#entities)
  - [FAQ](#faq)

## Installation

This integration can be added as a custom repository in HACS. After installing it via HACS:

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Towel Warmer Plug**.
3. Follow the configuration wizard.

## Configuration

For each towel warmer you want to control, you must add a configuration entry. During the setup flow, you will be asked to select:

- A name for the towel warmer.
- The plug switch entity.
- The power sensor entity (used to detect operation and malfunction).
- The time range during which the towel warmer is allowed to operate.
- The minimum power threshold used to detect malfunction (e.g. 2W).

You can change the schedule or minimum power threshold later via the **Configure** button in the integration.

## Entities

For each configured towel warmer, the integration creates:

- `sensor.<name>_status`: shows one of the following states:
  - `Warming`
  - `Idle`
  - `Outside warming hours`
  - `Malfunction`

- `switch.<name>_control`: enables or disables automatic control logic for the towel warmer.

These entities are attached to the same device as the selected plug switch or power sensor.

## FAQ

### How is the "Malfunction" state detected?

When the plug is ON but power consumption stays below the configured threshold (e.g. 2W) for over 60 seconds, the integration assumes the towel warmer is unplugged or malfunctioning.

### What happens if I turn the towel warmer on manually?

The integration respects manual activation and will not turn it off automatically outside scheduled hours unless explicitly configured. This ensures flexibility for occasional use.

### Can I change the schedule or power threshold after setup?

Yes. Use the **Configure** option in the integration panel.

### Does the integration support multiple towel warmers?

Yes. You can add multiple config entries, each with their own independent settings and entities.
