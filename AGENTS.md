# Agentic Harness – Einstieg

> - **Typ:** Einstieg
> - **Zuständigkeit:** Aufgaben den zuständigen Harness-Dateien zuordnen.
> - **Gilt bei:** Arbeit in diesem Repository und später in Projekten mit diesem Harness.
> - **Ladebeziehungen:** Immer `agentic-harness/harness/core.md` und `agentic-harness/harness/project.md` lesen; weitere Dateien nur nach den Auslösern unten.
> - **Nicht zuständig:** Den Arbeitsablauf, Produktfakten oder Qualitätsregeln hier erneut erklären.

## Wohin mit der Aufgabe?

| Auslöser | Zusätzlich lesen | Zweck |
|---|---|---|
| Project Init für ein neues, leeres Produktprojekt beauftragt oder erste Produktumsetzung bei `Pending Project Init` | `agentic-harness/harness/init.md` | Projektziel und Grenzen klären; nicht allein wegen Harness-Engineering ausführen. |
| Produktarchitektur, Produktbausteine oder deren Dateistruktur | `agentic-harness/docs/architecture.md` | Produktaufbau und Abhängigkeiten prüfen. |
| Codeänderung oder Refactor | `agentic-harness/docs/code.md` | Projektbezogene Codekonventionen prüfen. |
| Testplanung, Teständerung oder Testlauf | `agentic-harness/docs/testing.md` | Testkonventionen prüfen; Befehle stehen im Projektprofil. |
| Größere offene Idee | `agentic-harness/ideas/S000-readme.md` | Idee klären; bei Neuanlage `agentic-harness/harness/templates/idea.md` verwenden. |
| Neues oder geändertes Nutzerverhalten | `agentic-harness/specs/S000-readme.md` und betroffene Spec | Beauftragtes Soll prüfen; bei Neuanlage `agentic-harness/harness/templates/spec.md` verwenden. |
| Abschluss einer Änderung | `agentic-harness/harness/verification/gate.md` | Auftrag und Nachweise prüfen; bei Fehlschlag `agentic-harness/harness/verification/fail.md`. |
| Harness erstmals einordnen oder Project Init durchführen | `agentic-harness/harness-map.md` | Dateirollen und geplante Ladewege verstehen; tatsächliche Pfade prüfen. |
| Markdown-Datei neu anlegen oder befüllen | `agentic-harness/document-contract.md`; bei neuer Datei oder Rolle auch `agentic-harness/harness-map.md` | Passende Form, Verweise und gegebenenfalls Kopf gegen tatsächliche Rollen und Pfade prüfen. |
| Harness-Pfade, Dateirollen oder Ladeauslöser ändern | `agentic-harness/harness-map.md` und `agentic-harness/document-contract.md` | Betroffene Dokumentköpfe, Einstieg und Verweise gemeinsam abgleichen. |
| Beim Einsatz im Zielprojekt fällt eine möglicherweise universelle Stärke, Schwäche oder Unklarheit des Harnesses auf | `agentic-harness/harness-learnings.md` | Beobachtung lokal als Kandidat festhalten; Projektfakten bleiben in den zuständigen Projektdateien. |

Treffen mehrere Auslöser zu, lies die betreffenden Dateien. Lade nicht alle Docs auf Vorrat. Neue thematische Projekt-Docs brauchen einen klaren Auslöser im Einstieg; verweise auf Regeln statt sie hier zu kopieren.

Vor dem Umbenennen, Verschieben oder Löschen einer Harness-Datei suche repo-weit nach Verweisen auf Pfad und Dateinamen. Aktualisiere betroffene Verweise und Ladewege im selben Schritt. Prüfe danach verbliebene Pfade **und die Köpfe der betroffenen Dateien** gegen den tatsächlichen Baum. Dasselbe gilt, wenn sich Zuständigkeit oder Ladeauslöser ohne Dateiumzug ändern. Nach manuellen Änderungen zuerst den Ist-Stand prüfen; Markdown aktualisiert sich nicht selbst.

## Aktiver Stand und Pfade

`agentic-harness/harness/core.md` regelt den Arbeits- und Entscheidungsfluss. Landkarte und Dokumentenvertrag sind Referenzen für Orientierung und Markdown-Pflege. Die Landkarte zeigt geplante Root-Pfade; bis zur Migration sind die tatsächlichen `agentic-harness/`-Pfade in dieser Datei maßgeblich.

Produktcode und Produkttests liegen außerhalb der Harness-Dokumente. Bei Widersprüchen zwischen Auftrag, bestehenden Projektanweisungen und Harness kläre die Zuständigkeit vor riskanten Änderungen. Ändere nicht stillschweigend weitere Dateien, nur weil sie verlinkt sind.

Bei Commits beschreibt der Betreff in einem kurzen, konkreten Satz die tatsächliche Änderung. Vermeide ungenaue Betreffe wie „Update files“.

Bei Project Init nur nötige zusätzliche Projektverweise unter der folgenden Überschrift eintragen. Universelle Regeln oben nicht kopieren.

## Projektspezifische Ergänzungen
