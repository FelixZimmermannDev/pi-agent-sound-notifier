# Project Init – leeres Projekt beginnen

> - **Typ:** Prozess
> - **Zuständigkeit:** Ein neues, leeres Produktprojekt für den ersten beauftragten Arbeitsschritt vorbereiten.
> - **Gilt bei:** Beauftragtem Project Init für ein neues, leeres Produktprojekt oder vor der ersten Produktumsetzung, wenn `agentic-harness/harness/project.md` noch `Pending Project Init` enthält. Nicht bei Harness-Engineering.
> - **Ladebeziehungen:**
>   - Vorher: `AGENTS.md` → `agentic-harness/harness/core.md` und `agentic-harness/harness/project.md`.
>   - Für Dateirollen und Format: `agentic-harness/harness-map.md` und `agentic-harness/document-contract.md`.
>   - Danach: betroffene Projektdateien befüllen; Abschluss nach Abschnitt 4.
> - **Nicht zuständig:** Bestehende Anwendungen analysieren, spätere Features planen oder eine Produktspec als umgesetzt erklären.

## 1. Ersten Schritt klären

Kläre Nutzer, Problem und den ersten sichtbaren Ablauf. Halte Umfang und Nicht-Ziele des ersten Meilensteins fest.

Frage nur nach Daten, Betrieb, Integrationen und Freigaben, die diesen Schritt beeinflussen. Erfinde keine Antworten.

Leite für den ersten Ablauf passende Bausteine, Stack- und Testkandidaten ab. Prüfe entscheidungsrelevante Versionen und Voraussetzungen anhand verfügbarer Quellen oder Werkzeuge. Vergleiche echte Alternativen kurz mit Nutzen und Kosten.

Technische Möglichkeiten bleiben **Vorschläge**, bis sie entschieden sind. Vertage nicht benötigte Technik.

Fasse den ersten Schritt und offene Entscheidungen zusammen. Hole die nötige fachliche Bestätigung ein, bevor du Vorschläge als Projektfakten festhältst.

## 2. Bestätigtes an die richtige Stelle schreiben

Lies die Inhaltsvorgaben von `agentic-harness/harness/project.md` und den Projekt-Docs. Behalte dort Dokumentkopf und „Universeller Rahmen“, aber prüfe den Kopf beim Befüllen: Stimmen Zuständigkeit, Auslöser, Ladebeziehungen und Abgrenzung zum bestätigten Projekt und zu den tatsächlichen Pfaden?

Ersetze „Noch offen (Project Init)“ unter „Projektspezifische Befüllung“ durch bestätigte Inhalte. Ist ein Bereich nicht entscheidbar oder nicht relevant, kennzeichne ihn ausdrücklich. Entferne den Platzhalterstatus erst nach tatsächlicher Befüllung.

- `agentic-harness/harness/project.md`: bestätigtes Nutzerziel, Umfang, Grenzen und Freigaben; Start- und Prüfbefehle mit tatsächlichem Status.
- `agentic-harness/docs/architecture.md`: bestätigte erste Bausteine, Zuständigkeiten und Datenfluss; Geplantes und Offenes gesondert kennzeichnen.
- `agentic-harness/docs/code.md`: nur geltende Konventionen für den gewählten Stack.
- `agentic-harness/docs/testing.md`: aus Ablauf, Risiken, Architektur und Stack passende Testebenen und -arten wählen; Werkzeuge, Teststruktur und Grenzen für den ersten Meilenstein begründen.
- Root-`AGENTS.md`: bei Bedarf zusätzliche Projekt-Docs mit konkretem Leseauslöser unter „Projektspezifische Ergänzungen“ verlinken; keine Detailregeln kopieren.

Befülle die zunächst leere Root-`README.md` des Zielprojekts ohne Metakopf mit bestätigtem Produktzweck und geprüften Startschritten; ergänze statt zu überschreiben, falls bereits Produktinformationen vorliegen. Die menschliche Harness-Anleitung in `agentic-harness/README.md` bleibt davon getrennt. Erfinde keine Produktfakten.

## 3. Prüf-Einstieg und Verweise prüfen

Richte passende Checks ein, sobald sie ausführbar sind. Führe sie tatsächlich aus. Prüfe bei Bedarf, ob sie einen absichtlichen Fehler erkennen.

Eine leere Testsuite oder ein geplanter Befehl gilt nicht als bestanden. Halte nicht eingerichtete Checks im Projektprofil offen.

Prüfe auch die Ladebeziehungen in den befüllten Dokumentköpfen. Ergänzte Verweise müssen vom Repo-Root aus auf vorhandene Dateien zeigen. Wenn sich Rollen oder Ladeauslöser geändert haben, passe `AGENTS.md` und `agentic-harness/harness-map.md` gezielt an.

## 4. Übergabe

Entferne `Pending Project Init` erst, wenn Ziel, Grenzen und erster Schritt ausreichend geklärt sind. Das bedeutet **nicht**: Produkt-Gate bestanden oder Spec `Implemented`.

Für beauftragtes Nutzerverhalten nutze `agentic-harness/specs/S000-readme.md` und `agentic-harness/harness/templates/spec.md`.

Eine Idea nach `agentic-harness/ideas/S000-readme.md` ist nur bei offenem Klärungsbedarf nötig. Nach dem Init lies das aktualisierte `agentic-harness/harness/project.md` und kehre für den aktuellen Auftrag zu `agentic-harness/harness/core.md` zurück. Init allein ist keine Implementierungsfreigabe. Bleibt eine dafür nötige Entscheidung offen, berichte den Blocker statt auf einer Annahme umzusetzen. Übertragbare Beobachtungen zum Harness, die beim Init auffallen, gehören als offene Kandidaten nach `agentic-harness/harness-learnings.md`, nicht in die Produktdateien.
