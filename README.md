# Panasonic Aquarea – Home Assistant Integration

Eine benutzerdefinierte Home-Assistant-Integration zur Einbindung von Panasonic Aquarea Wärmepumpen über die **Aquarea Service Cloud** (aquarea-service.panasonic.com).

---

## Funktionsumfang

| Plattform | Entität | Beschreibung |
|-----------|---------|--------------|
| `climate` | Zone 1 / Zone 2 | Heizen, Kühlen, Auto – inkl. Solltemperatur |
| `water_heater` | Warmwasserspeicher | Betriebsmodus & Solltemperatur des Speichers |
| `sensor` | Außentemperatur | Aktuelle Außentemperatur der Wärmepumpe |
| `sensor` | Zone Wassertemperatur | Ist-Vorlauftemperatur je Zone |
| `sensor` | Zone Raumtemperatur | Raumtemperatur (falls Raumfühler vorhanden) |
| `sensor` | Speichertemperatur | Ist-Temperatur des Warmwasserspeichers |
| `sensor` | Betriebsmodus | Aktueller Modus (Heizen, Kühlen, Warmwasser …) |
| `sensor` | Fehlerstatus | Aktiver Fehlercode der Anlage |
| `switch` | Speicher-Schnellladung | Boost-Heizung für den Warmwasserspeicher |
| `switch` | Zusatzheizung | Zuheizer / Backup-Heizstab aktivieren |
| `switch` | Urlaubsmodus | Holiday Timer ein-/ausschalten |

---

## Voraussetzungen

- Home Assistant **2024.1** oder neuer
- Ein Konto bei der **Panasonic Aquarea Service Cloud** (aquarea-service.panasonic.com)
- Die Wärmepumpe ist in der App/Cloud registriert und online

---

## Installation

### Option A – HACS (empfohlen)

1. HACS → *Benutzerdefinierte Repositories* → URL dieses Repos hinzufügen
2. Integration *Panasonic Aquarea* suchen und installieren
3. Home Assistant neu starten

### Option B – Manuelle Installation

1. Den Ordner `custom_components/panasonic_aquarea` in dein Home-Assistant-Verzeichnis (`<config>/custom_components/`) kopieren
2. Home Assistant neu starten

---

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen**
2. Nach *Panasonic Aquarea* suchen
3. E-Mail-Adresse und Passwort der Aquarea Service Cloud eingeben
4. Bei mehreren Geräten das gewünschte auswählen
5. Fertig – alle Entitäten werden automatisch angelegt

---

## Entitäten im Überblick

### Climate (Heizzone)

Jede konfigurierte Heizzone erscheint als eigene `climate`-Entität:

- **HVAC-Modus**: `heat` | `cool` | `auto` | `off`
- **Solltemperatur**: Je nach Regelungsmodus Wasser- oder Raumtemperatur
- Unterstützt `TURN_ON` / `TURN_OFF`

### Water Heater (Warmwasserspeicher)

- **Betriebsmodi**: `eco` (Normal), `performance` (Boost), `off`
- **Urlaubsmodus** (Away Mode): Spart Energie bei längerer Abwesenheit
- Solltemperatur einstellbar (40–75 °C)

### Sensoren

Alle Temperatursensoren unterstützen `state_class: measurement` für die Langzeitstatistik in Home Assistant.

### Schalter

- **Speicher-Schnellladung**: Ladet den Speicher sofort auf maximale Temperatur
- **Zusatzheizung**: Aktiviert den elektrischen Zuheizer (falls vorhanden)
- **Urlaubsmodus**: Entspricht dem Holiday Timer in der Aquarea App

---

## Aktualisierungsintervall

Daten werden standardmäßig alle **60 Sekunden** abgerufen. Die Aquarea Service Cloud empfiehlt keine kürzeren Intervalle.

---

## Bekannte Einschränkungen

- Schreibzugriff auf die Cloud-API ist auf das offizielle Protokoll beschränkt; einige Gerätemodelle unterstützen nicht alle Steuerbefehle.
- Für Geräte ohne Raumfühler ist die Raumtemperatur-Entität nicht verfügbar.
- Leistungsdaten (kW, COP) stehen nur zur Verfügung, wenn die Anlage diese Werte meldet.

---

## Fehlerbehebung

Logging für die Integration in `configuration.yaml` aktivieren:

```yaml
logger:
  logs:
    custom_components.panasonic_aquarea: debug
```

---

## Lizenz

MIT License – Details in der Datei `LICENSE`.
