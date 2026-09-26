# Architektur – Bausteine und Datenfluss

> - **Typ:** Projektdoku
> - **Status:** Sound und Tabtitel-Indikator implementiert; Unit-Tests bestanden; echter PyCharm-Tab-Smoke-Test noch offen.
> - **Zuständigkeit:** Entschiedene Bausteine, ihre Aufgaben und Abhängigkeiten für den aktuellen Meilenstein erklären.
> - **Gilt bei:** Project Init sowie Architektur-, Schnittstellen- oder Strukturfragen.
> - **Ladebeziehungen:** Vorher `agentic-harness/harness/project.md` für Ziel und Grenzen lesen. Bei Codekonventionen zusätzlich `agentic-harness/docs/code.md`; bei Teststruktur `agentic-harness/docs/testing.md`.
> - **Nicht zuständig:** Agentenablauf, Code-Stil oder beauftragtes Nutzerverhalten festlegen.

## Universeller Rahmen

Ist, entschiedenes Ziel und offene Möglichkeiten nicht verwechseln. Bausteine nur für einen geklärten Bedarf vorsehen; Paket- und Technologieentscheidungen dieses Projekts hier begründen.

## Projektspezifische Befüllung

### Bausteine und Verantwortlichkeiten

- **Pi lifecycle handler:** setzt bei `agent_start` den Terminaltitel auf einen neutralen Punkt und bei `agent_settled` auf einen gelben Punkt. Das endgültige Ereignis wird statt `agent_end` verwendet, weil Zwischenläufe automatisch fortgesetzt werden können.
- **Audio adapter:** startet `/usr/bin/afplay` mit `/System/Library/Sounds/Pop.aiff` bei halber Lautstärke.
- **Terminal title API:** `ctx.ui.setTitle()` setzt den OSC-Terminaltitel, den PyCharm als Titel des jeweiligen Terminal-Tabs anzeigen kann.

Die Extension ist ein TypeScript-Modul, das Pi lädt; ein eigenes PyCharm-Plugin oder eine IPC-Verbindung ist dafür nicht nötig.

### Datenfluss und Schnittstellen

```text
agent_start ──────────────→ ⚪ Projekt · Pi (Terminaltitel)
                                  │
agent_settled ────────────→ 🟡 Projekt · Pi + kurzer macOS-Sound
```

Der Titelindikator gilt nur für den interaktiven TUI-Modus. Es werden keine Prompt-, Transcript- oder Modellinformationen benötigt. Fehler beim Audio oder Setzen des Titels dürfen den Agent-Lauf nicht beeinflussen.

### Entscheidungen und offene Punkte

Die Implementation liegt in `extensions/agent-sound-notifier.ts` und wird als persönliches Pi-Paket geladen. Audioausgabe ist im ersten Meilenstein auf macOS begrenzt. Windows/Linux, Remote-Audio-Relay und Benutzereinstellungen sind vertagt.
