# Architektur – Bausteine und Datenfluss

> - **Typ:** Projektdoku
> - **Status:** Erster Meilenstein implementiert; echter `afplay`-Test bestanden; vollständiger Pi-Smoke-Test noch offen.
> - **Zuständigkeit:** Entschiedene Bausteine, ihre Aufgaben und Abhängigkeiten für den aktuellen Meilenstein erklären.
> - **Gilt bei:** Project Init sowie Architektur-, Schnittstellen- oder Strukturfragen.
> - **Ladebeziehungen:** Vorher `agentic-harness/harness/project.md` für Ziel und Grenzen lesen. Bei Codekonventionen zusätzlich `agentic-harness/docs/code.md`; bei Teststruktur `agentic-harness/docs/testing.md`.
> - **Nicht zuständig:** Agentenablauf, Code-Stil oder beauftragtes Nutzerverhalten festlegen.

## Universeller Rahmen

Ist, entschiedenes Ziel und offene Möglichkeiten nicht verwechseln. Bausteine nur für einen geklärten Bedarf vorsehen; Paket- und Technologieentscheidungen dieses Projekts hier begründen.

## Projektspezifische Befüllung

### Bausteine und Verantwortlichkeiten

- **Pi lifecycle handler:** registriert einen Listener für `agent_settled`; beendet Agent-Arbeit wird damit zuverlässiger erkannt als über `agent_end`, das vor möglichen automatischen Fortsetzungen ausgelöst werden kann.
- **Audio adapter:** startet `/usr/bin/afplay` mit dem macOS-Systemton `/System/Library/Sounds/Pop.aiff` bei halber Lautstärke. Das vermeidet ein gebündeltes Audio-Asset und zusätzliche Laufzeitabhängigkeiten.

Die Extension ist ein TypeScript-Modul, das Pi lädt; PyCharm dient als Entwicklungsumgebung und stellt keine eigene Extension-Schnittstelle bereit, die hier gebraucht wird.

### Datenfluss und Schnittstellen

```text
Pi agent lifecycle
  → agent_settled handler
  → lokaler Audio-Player (macOS)
  → kurzer Completion-Sound
```

Der Handler benötigt keine Prompt-, Transcript- oder Modellinformationen. Fehler des Audio-Players dürfen den Agent-Lauf nicht beeinflussen.

### Entscheidungen und offene Punkte

Die Implementation liegt in `extensions/agent-sound-notifier.ts` und wird als persönliches Pi-Paket geladen. Audioausgabe ist im ersten Meilenstein auf macOS begrenzt. Windows/Linux, Remote-Audio-Relay und Benutzereinstellungen sind vertagt.
