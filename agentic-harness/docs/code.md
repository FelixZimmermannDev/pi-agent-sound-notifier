# Code – Stack und Konventionen

> - **Typ:** Projektdoku
> - **Status:** TypeScript/Pi-Extension implementiert; Node.js 22.19+ vorgesehen.
> - **Zuständigkeit:** Den gewählten Stack und geltende Regeln für Anwendungscode beschreiben.
> - **Gilt bei:** Project Init sowie Codeänderungen und Refactorings.
> - **Ladebeziehungen:** Vorher `agentic-harness/harness/project.md` lesen. Bei Modulgrenzen `agentic-harness/docs/architecture.md`; bei Testcode `agentic-harness/docs/testing.md` zusätzlich lesen.
> - **Nicht zuständig:** Produktarchitektur oder ausführbare Gate-Befehle duplizieren.

## Universeller Rahmen

Nur Regeln für den tatsächlich gewählten Stack festhalten. Kandidaten sind keine Konventionen; aktive Werkzeuge brauchen reale Einrichtung. Befehle und Ergebnisse gehören in das Projektprofil.

## Projektspezifische Befüllung

### Stack und Abhängigkeiten

Die Extension ist TypeScript für die Pi Extension API. Sie wurde mit Pi 0.87.1 geladen und Node.js 26.8.1 entwickelt; `package.json` verlangt Node.js 22.19 oder neuer. Pi lädt die TypeScript-Extension aus dem lokalen Paket. Zielsystem ist macOS; ein Audio-Framework oder weitere Laufzeitabhängigkeiten werden nicht benötigt.

### Codekonventionen

Kleiner, klar abgegrenzter Extension-Einstieg. Aufruf des Audio-Players mit festgelegtem ausführbarem Programm und Argumenten, ohne Shell-Interpolation. Den Terminaltitel nur im `tui`-Modus über `ctx.ui.setTitle()` setzen; Audio- und UI-Fehler abfangen, damit sie den Pi-Agent-Lauf nicht stören. Abhängigkeiten nur ergänzen, falls ein konkreter Bedarf entsteht.

### Qualitätswerkzeuge

TypeScript 5.9.3, `tsx` 4.23.15 und Node.js `node:test` werden als Entwicklungswerkzeuge verwendet. Die Befehle `npm run typecheck` und `npm test` sind eingerichtet.
