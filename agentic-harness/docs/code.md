# Code – Stack und Konventionen

> - **Typ:** Projektdoku
> - **Status:** TypeScript/Pi-Extension als Stack festgelegt; Implementierung noch ausstehend.
> - **Zuständigkeit:** Den gewählten Stack und geltende Regeln für Anwendungscode beschreiben.
> - **Gilt bei:** Project Init sowie Codeänderungen und Refactorings.
> - **Ladebeziehungen:** Vorher `agentic-harness/harness/project.md` lesen. Bei Modulgrenzen `agentic-harness/docs/architecture.md`; bei Testcode `agentic-harness/docs/testing.md` zusätzlich lesen.
> - **Nicht zuständig:** Produktarchitektur oder ausführbare Gate-Befehle duplizieren.

## Universeller Rahmen

Nur Regeln für den tatsächlich gewählten Stack festhalten. Kandidaten sind keine Konventionen; aktive Werkzeuge brauchen reale Einrichtung. Befehle und Ergebnisse gehören in das Projektprofil.

## Projektspezifische Befüllung

### Stack und Abhängigkeiten

Die Extension wird in TypeScript für Pi geschrieben und verwendet die Pi Extension API. Pi lädt lokale TypeScript-Extensions direkt; der genaue Mindeststand der Pi-Laufzeit ist bei der Implementierung zu prüfen. Das Zielsystem für den ersten Meilenstein ist macOS. Eine zusätzliche Audio-Bibliothek ist nicht vorgesehen.

### Codekonventionen

Kleiner, klar abgegrenzter Extension-Einstieg. Aufruf des Audio-Players mit festgelegtem ausführbarem Programm und Argumenten, ohne Shell-Interpolation. Audiofehler abfangen, damit sie den Pi-Agent-Lauf nicht stören. Abhängigkeiten nur ergänzen, falls ein konkreter Bedarf entsteht.

### Qualitätswerkzeuge

TypeScript-Typprüfung und automatisierte Tests sind vorgesehen, aber noch nicht eingerichtet. Versionen und konkrete Werkzeuge werden bei der Implementierung festgelegt.
