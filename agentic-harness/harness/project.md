# Projektprofil – Grenzen und Befehle

> - **Typ:** Projektdoku
> - **Status:** Project Init abgeschlossen; Produktumsetzung noch ausstehend.
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

Implementierung, Installationsbefehle und automatisierte Checks sind noch nicht eingerichtet. Nach der Umsetzung sollen gezielte Tests den Lifecycle-Handler und die Soundausgabe prüfen; ein manueller Smoke-Test erfolgt in einer echten Pi-Sitzung im PyCharm-Terminal. Befehle werden nach Einrichtung ergänzt.

### Nächster Schritt und offene Entscheidungen

Nächster Schritt: Extension, gebündelten kurzen Sound und Tests implementieren. Eine spätere plattformübergreifende Audioausgabe und konfigurierbare Soundoptionen bleiben vertagt.
