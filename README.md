# Panasonic Aquarea – Home Assistant Integration

A custom Home Assistant integration for connecting Panasonic Aquarea heat pumps via the **Aquarea Service Cloud** (aquarea-service.panasonic.com).

---

## Features

| Platform | Entity | Description |
|----------|--------|-------------|
| `climate` | Zone 1 / Zone 2 | Heating, cooling, auto – including target temperature |
| `water_heater` | Domestic hot water tank | Operating mode & target temperature of the tank |
| `sensor` | Outdoor temperature | Current outdoor temperature of the heat pump |
| `sensor` | Zone water temperature | Actual flow temperature per zone |
| `sensor` | Zone room temperature | Room temperature (if room sensor is available) |
| `sensor` | Tank temperature | Actual temperature of the hot water tank |
| `sensor` | Operating mode | Current mode (heating, cooling, hot water, …) |
| `sensor` | Error status | Active error code of the unit |
| `switch` | Tank quick charge | Boost heating for the hot water tank |
| `switch` | Auxiliary heater | Enable backup/auxiliary heating element |
| `switch` | Holiday mode | Turn holiday timer on/off |

---

## Prerequisites

- Home Assistant **2024.1** or newer
- An account at the **Panasonic Aquarea Service Cloud** (aquarea-service.panasonic.com)
- The heat pump is registered in the app/cloud and online

---

## Installation

### Option A – HACS (recommended)

1. HACS → *Custom Repositories* → Add the URL of this repo
2. Search for *Panasonic Aquarea* and install it
3. Restart Home Assistant

### Option B – Manual Installation

1. Copy the `custom_components/panasonic_aquarea` folder into your Home Assistant config directory (`<config>/custom_components/`)
2. Restart Home Assistant

---

## Setup

1. **Settings → Devices & Services → Add Integration**
2. Search for *Panasonic Aquarea*
3. Enter the email address and password of your Aquarea Service Cloud account
4. If you have multiple devices, select the desired one
5. Done – all entities will be created automatically

---

## Entity Overview

### Climate (Heating Zone)

Each configured heating zone appears as its own `climate` entity:

- **HVAC mode**: `heat` | `cool` | `auto` | `off`
- **Target temperature**: Water or room temperature depending on the control mode
- Supports `TURN_ON` / `TURN_OFF`

### Water Heater (Domestic Hot Water Tank)

- **Operating modes**: `eco` (Normal), `performance` (Boost), `off`
- **Holiday mode** (Away Mode): Saves energy during extended absences
- Target temperature adjustable (40–75 °C)

### Sensors

All temperature sensors support `state_class: measurement` for long-term statistics in Home Assistant.

### Switches

- **Tank quick charge**: Immediately heats the tank to maximum temperature
- **Auxiliary heater**: Activates the electric backup heater (if available)
- **Holiday mode**: Corresponds to the Holiday Timer in the Aquarea app

---

## Update Interval

Data is fetched every **60 seconds** by default. The Aquarea Service Cloud does not recommend shorter intervals.

---

## Known Limitations

- Write access to the cloud API is limited to the official protocol; some device models do not support all control commands.
- For devices without a room sensor, the room temperature entity is not available.
- Performance data (kW, COP) is only available if the unit reports these values.

---

## Troubleshooting

Enable logging for the integration in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.panasonic_aquarea: debug
```

---

## License

MIT License – see the `LICENSE` file for details.
