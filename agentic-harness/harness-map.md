# Harness-Landkarte – Dateirollen und Ladewege

> - **Typ:** Index
> - **Status:** V4-Referenz; die Pfade der Zielstruktur sind noch nicht vollständig umgesetzt.
> - **Zuständigkeit:** Eigentümer der Themen und direkte Ladewege sichtbar machen.
> - **Gilt bei:** Einstieg in einen unbekannten Harness, Project Init oder Änderung von Dateirollen und Pfaden.
> - **Ladebeziehungen:** Markdown-Format: `agentic-harness/document-contract.md`. Im aktuellen V4-Repo zuerst `AGENTS.md` beachten.
> - **Nicht zuständig:** Projektentscheidungen treffen oder Regeln der verlinkten Dateien wiederholen.

## Pfadbasis

Die Tabelle zeigt Pfade **relativ zum geplanten Projekt-Root**. Derzeit liegen `harness/` und `docs/` noch unter `agentic-harness/`; `AGENTS.md` liegt bereits im Root. Vertrag und Landkarte liegen derzeit unter `agentic-harness/` und bleiben auch in der Zielstruktur im Harness (`harness/document-contract.md`, `harness/harness-map.md`). Beim Exportieren des versionierten Projektinhalts bleiben diese aktuellen Pfade gültig; die Tabelle ist keine Installationsanweisung. Die Root-`README.md` ist ein zunächst leeres Produktgerüst; `agentic-harness/README.md` bleibt die menschliche Harness-Anleitung im Zielprojekt. Bis zu einer Migration sind die tatsächlichen Pfade im Root-`AGENTS.md` maßgeblich.

## Universelle Dateien

| Geplanter Pfad | Eine Verantwortung | Direkter Ladeweg |
|---|---|---|
| `AGENTS.md` | Einstieg und Aufgaben-Routing | Immer → `harness/core.md` und `harness/project.md`; weitere Ziele nur nach Auslöser. |
| `harness/core.md` | Entscheidungen und Rücksprünge von Auftrag bis Übergabe | Mit `harness/project.md` über `AGENTS.md`; bei beauftragtem Init für ein leeres Produktprojekt oder erster Produktumsetzung mit `Pending Project Init` → `harness/init.md`; je nach Auftrag Ideas/Specs und Docs; vor Abschluss → `harness/verification/gate.md`. |
| `harness/init.md` | Leeres Projekt für ersten Schritt klären | Bei Init → `harness/harness-map.md` und `harness/document-contract.md`; danach Projektdateien befüllen. |
| `harness/harness-map.md` | Dateirollen und Ladewege | Bei Orientierung oder Änderungen der Dokumentstruktur; keine Projektfakten. |
| `harness/document-contract.md` | Format und Pflege neuer Markdown-Dateien | Beim Anlegen/Befüllen von Projekt-Docs und bei Pfadänderungen. |
| `harness/README.md` | Anleitung zum Harness für Menschen (aktuell `agentic-harness/README.md`) | Im neuen Projekt mitübernehmen; kein Agenten-Ladeweg. |
| `ideas/S000-readme.md`, `specs/S000-readme.md` | Einstiege und Statusregeln für Ideas bzw. Specs | Bedingt über `AGENTS.md`; betroffene Artefakte lesen, Templates nur bei Neuanlage. |
| `harness/templates/idea.md`, `harness/templates/spec.md` | Form der jeweiligen Artefakte | Nur beim Anlegen von Ideas bzw. Specs. |
| `harness/verification/gate.md` | Soll und belegtes Ist zur Abschlussentscheidung verbinden | Nach Änderung → `harness/verification/requirements.md` und `harness/verification/implementation.md`; bei Lücke → `harness/verification/fail.md`. |
| `harness/verification/requirements.md` | Verbindliches Soll aus Auftrag, Spec und Projektgrenzen bestimmen | Vom Gate geladen; `harness/project.md`, betroffene Specs und bei Strukturänderungen `docs/architecture.md` prüfen; Soll an Implementation und Gate. |
| `harness/verification/implementation.md` | Tatsächliche Änderung und Nachweise zum Soll prüfen | Vom Gate geladen; Prüfungen aus `harness/project.md`, Testpraxis bei Bedarf aus `docs/testing.md`; Ist und Belege ans Gate. |
| `harness/verification/fail.md` | Lücke eingrenzen, korrigieren oder blockiert melden | Nur bei Gate-Lücke; nach Korrektur betroffene Nachweise und Gate wiederholen. |

## Lokale Rückmeldungen zum universellen Harness

| Geplanter Pfad | Eine Verantwortung | Direkter Ladeweg |
|---|---|---|
| `harness/harness-learnings.md` | Übertragbare Stärken, Schwächen und offene Verbesserungsfragen aus einem Zielprojekt sammeln | Im aktuellen Repo: `agentic-harness/harness-learnings.md`; im geplanten Harness: `harness/harness-learnings.md`. Nur bei einer konkreten Harness-Beobachtung über `AGENTS.md`; keine automatisch geltende Regel oder Übernahme ins Quell-Repository. |

## Projektspezifisch durch Init zu befüllen

| Geplanter Pfad | Eine Verantwortung | Direkter Ladeweg |
|---|---|---|
| `harness/project.md` | Bestätigtes Ziel, Grenzen, Befehle, Prüfstatus | Immer mit Core; Architekturdetails → `docs/architecture.md`, Testpraxis → `docs/testing.md`. |
| `docs/architecture.md` | Bausteine, Schnittstellen und Datenfluss | Bei Architektur/Struktur; Codekonventionen → `docs/code.md`. |
| `docs/code.md` | Geltender Stack, Abhängigkeiten und Codekonventionen | Bei Codearbeit; Modulgrenzen → `docs/architecture.md`. |
| `docs/testing.md` | Auswahl von Testebenen/-arten, Ausführungsanlässen, Werkzeugen und Teststruktur | Bei Init und Testarbeit aus Ziel, Architektur und Stack; konkrete Befehle → `harness/project.md`. |
| `README.md` | Produktüberblick, Einrichtung und Start für Menschen | Root-Gerüst beim Init ohne Metakopf mit bestätigten Produktinformationen befüllen. |
| `ideas/`, `specs/` | Konkrete Ideen bzw. beauftragtes Soll | Nur betroffene Artefakte lesen; neue erst bei Bedarf anlegen. |

Bei `harness/project.md`, `docs/architecture.md`, `docs/code.md` und `docs/testing.md` bleiben Dokumentkopf und „Universeller Rahmen“ erhalten. Init füllt dort den Bereich „Projektspezifische Befüllung“; die Produkt-`README.md` ist ein menschlicher Einstieg ohne Metakopf. Die Root-`AGENTS.md` behält universelles Routing; zusätzliche Projektverweise stehen nur unter „Projektspezifische Ergänzungen“.

## Bei neuen oder verschobenen Dateien

Vor dem Ändern eingehende Verweise auf Pfad und Dateinamen suchen. Rollen und direkte Beziehungen hier aktualisieren; betroffene Einstiege, Links und Dokumentköpfe im selben Schritt abgleichen. Das gilt auch für neue Ladeauslöser ohne Dateiumzug. Danach reale Ziele prüfen. Geplante Pfade nicht als vorhanden ausgeben.
