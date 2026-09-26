# Projektprofil – Grenzen und Befehle

> - **Typ:** Projektdoku
> - **Status:** Erster Meilenstein umgesetzt; manueller Pi-Smoke-Test noch offen.
> - **Zuständigkeit:** Den aktuellen Meilenstein, Projektgrenzen und ausführbare Befehle festhalten.
> - **Gilt bei:** Einordnung jeder Aufgabe über `AGENTS.md`; projektspezifisches Befüllen bei `agentic-harness/harness/init.md`.
> - **Ladebeziehungen:** Einstieg über `AGENTS.md` und `agentic-harness/harness/core.md`. Architektur bei Bedarf: `agentic-harness/docs/architecture.md`; Testpraxis: `agentic-harness/docs/testing.md`.
> - **Nicht zuständig:** Architekturdetails, Codekonventionen oder Akzeptanzkriterien wiederholen.

## Universeller Rahmen

Dieses Profil bleibt kurz und nennt nur bestätigte Grenzen und tatsächlich verfügbare Befehle. Details liegen in den zuständigen Projekt-Docs. Ein geklärtes Init ist kein bestandenes Produkt-Gate.

## Projektspezifische Befüllung

### Ziel und erster Meilenstein

`pi-agent-sound-notifier` ist eine kleine Pi-Extension für Nutzer, die Pi im PyCharm-Terminal einsetzen. Beim endgültigen Abschluss eines Agent-Laufs soll sie einen kurzen Sound abspielen.

Erster Meilenstein: TypeScript-Extension für Pi, die `agent_settled` verarbeitet und einen lokalen Sound abspielt. Zunächst ist macOS der Zielhost. Ein PyCharm-Plugin, modellabhängige Integration, Desktop-Popups und zusätzliche Sounds für andere Ereignisse sind nicht Teil des ersten Meilensteins.

### Betrieb, Daten und Freigaben

Die Extension läuft im Pi-Prozess und nutzt dessen Lifecycle-API. Audio wird lokal auf dem Rechner abgespielt, auf dem Pi läuft. Es werden keine Gesprächsinhalte oder Nutzerdaten übertragen. Pi-Extensions laufen mit den Rechten des Pi-Prozesses; nur vertrauenswürdiger Code darf geladen werden.

### Start und Prüfstatus

Am Projektroot:

- `npm install` — Abhängigkeiten installiert.
- `npm test` — PASS: 2 Unit-Tests.
- `npm run typecheck` — PASS: TypeScript-Prüfung.
- `pi install "$(pwd)"` — persönliche Pi-Installation ausgeführt; `pi list` zeigt das Paket `../../Code/python/chess-coach`.

Node.js 26.8.1, Pi 0.87.1 und macOS `/usr/bin/afplay` wurden lokal festgestellt. Direkter Soundplayer-Smoke-Test `afplay -v 0.5 /System/Library/Sounds/Pop.aiff` — PASS. Der vollständige Lifecycle-zu-Audio-Smoke-Test in einer echten Pi-Sitzung im PyCharm-Terminal bleibt offen.

### Nächster Schritt und offene Entscheidungen

Pi nach der Installation neu starten und einen Agent-Lauf im PyCharm-Terminal abschließen, um die tatsächliche Lifecycle-zu-Audio-Kette manuell zu prüfen. Windows/Linux, Remote-Audio-Relay und konfigurierbare Sounds bleiben vertagt.
