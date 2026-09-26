# Testing – Auswahl und Praxis der Produktprüfungen

> - **Typ:** Projektdoku
> - **Status:** Pending Project Init; noch keine Testpraxis oder Anwendungstests bestätigt.
> - **Zuständigkeit:** Universelle Auswahlhilfe für Tests bieten und die begründete Teststrategie des Projekts festhalten.
> - **Gilt bei:** Project Init sowie Testplanung, Teständerung und Testausführung.
> - **Ladebeziehungen:** Zuerst `agentic-harness/harness/project.md` für Ziel, Risiken und eingerichtete Befehle lesen. Für Bausteine und Grenzen bei Bedarf `agentic-harness/docs/architecture.md`, für Stack und Werkzeugwahl `agentic-harness/docs/code.md`, bei beauftragtem Verhalten die betroffene Spec unter `agentic-harness/specs/`. Zum Abschluss `agentic-harness/harness/verification/gate.md`.
> - **Nicht zuständig:** Produkt-Stack oder Akzeptanzkriterien festlegen, Befehle und Ergebnisse duplizieren oder über ein bestandenes Gate entscheiden.

## Universeller Rahmen

**Testebene** bezeichnet die geprüfte Grenze, **Testart** die geprüfte Eigenschaft oder Methode. Beides kombinieren: Ein Integrationstest kann z. B. einen Berechtigungsfehler prüfen. Projektgröße allein bestimmt keine Pflichtliste; Nutzerablauf, Fehlerrisiko, Daten und Architektur des **ersten Meilensteins** sind maßgeblich. Nicht benötigte Ebenen vertagen statt leere Testsuiten anzulegen.

### Auswahlgrundlage

1. Aus `agentic-harness/harness/project.md` Ziel, Betrieb, Daten, Rechte und Risiken entnehmen; aus betroffenen Specs die Akzeptanzkriterien. Ohne Spec den beauftragten Umfang prüfen.
2. Aus `agentic-harness/docs/architecture.md` die entschiedenen Bausteine und Schnittstellen ableiten; aus `agentic-harness/docs/code.md` Sprache, Laufzeit, Abhängigkeiten und Entwicklungsumgebung. Nicht bestätigte Entscheidungen bleiben offen.
3. Für wichtige Abläufe und relevante Fehlerfälle die kleinste aussagekräftige Kombination aus Ebenen und Arten wählen. Für den beauftragten Ablauf einen Nachweis an einer geeigneten beobachtbaren Grenze vorsehen; isolierte Tests allein belegen kein Zusammenspiel. Werkzeug, Aufwand und Nachweisgrenze begründen.

### Testebenen – wo wird geprüft?

| Ebene | Sinnvoll, wenn … | Belegt nicht allein … |
|---|---|---|
| **Unit** | Verzweigungen, Berechnungen oder Regeln isoliert prüfbar sind. | Zusammenarbeit mit Datenbank, Netzwerk oder UI. |
| **Komponente/Modul** | Ein Baustein über seine öffentliche Schnittstelle samt internem Verhalten geprüft werden soll. | Korrekte Integration mit realen Nachbarn. |
| **Integration** | Persistenz, externe Dienste oder das Zusammenspiel mehrerer Bausteine relevant sind. | Den vollständigen Nutzerablauf. |
| **Schnittstelle/Vertrag** | Zwei Seiten einer API, eines Datenformats oder eines Ereignisses kompatibel bleiben müssen. | Die interne Richtigkeit beider Seiten oder den Gesamtablauf. |
| **System/End-to-End** | Der erste Ablauf über die tatsächlich genutzten Grenzen hinweg funktionieren muss (z. B. CLI, API oder UI). | Alle seltenen Fehlerfälle oder nicht beobachtete Eigenschaften. |

Ebenen sind Auswahlmöglichkeiten, keine Ordnerpflicht. Ein kleines Projekt kann wenige, aber aussagekräftige Tests auf mehreren Grenzen brauchen; ein größeres Projekt trennt Suiten nur, wenn Organisation und Laufzeit es rechtfertigen.

### Testarten und Prüfperspektiven – was wird geprüft?

| Art | Auslöser / Leitfrage |
|---|---|
| **Funktional und Grenzfälle** | Erfüllt der Ablauf sein Soll auch bei ungültigen, leeren oder extremen Eingaben? |
| **Regression und Smoke** | Bleibt betroffenes Verhalten nach Änderungen erhalten? Startet der wichtigste Ablauf überhaupt? Ein Smoke-Check ersetzt keine tieferen Nachweise. |
| **Berechtigung und Sicherheit** | Können Rollen nur Erlaubtes tun; sind Eingaben, Secrets und sensible Daten geschützt? Nur relevante Bedrohungen prüfen. |
| **Datenintegrität und Zustand** | Bleiben Daten bei Speichern, Wiederholen, Abbruch und Fehler konsistent? Nur bei zustandsbehaftetem Verhalten. |
| **Ausfall, Wiederanlauf und Parallelität** | Was passiert bei Timeouts, Teilausfällen, Wiederholung oder konkurrierenden Zugriffen? Nur bei entsprechendem Risiko. |
| **Leistung und Kapazität** | Gibt es eine begründete Latenz-, Last- oder Ressourcenanforderung? Keine pauschalen Lasttests. |
| **Barrierefreiheit und Nutzbarkeit** | Ist eine relevante Oberfläche für die vorgesehenen Nutzer bedienbar? Automatische Checks ggf. durch menschliche Prüfung ergänzen. |
| **Kompatibilität** | Müssen ausdrücklich mehrere Umgebungen, Plattformen oder Versionen unterstützt werden? |
| **Eigenschaftsbasiert/Fuzzing** | Gibt es komplexe Invarianten oder breite Eingaberäume, die Beispieltests schlecht abdecken? |
| **Fachliche Akzeptanz/Exploration** | Muss ein Mensch den Nutzerablauf beurteilen oder einen noch unklaren Fehler erkunden? Schritte und beobachtetes Ergebnis festhalten; manuell ist eine Methode, keine eigene Testebene. |

Lint, Typprüfung und Build sind ergänzende Qualitätschecks, aber allein kein Nachweis für Nutzerverhalten. Coverage-Zahlen zeigen geprüften Code, nicht automatisch erfüllte Akzeptanzkriterien.

### Werkzeuge, Struktur und Isolation auswählen

Werkzeuge anhand des **gewählten** Stacks, der zu prüfenden Grenze und verfügbarer Versionen auswählen; es gibt keine allgemeine Testsprache oder ein verpflichtendes Framework. Erst nach Prüfung und Einrichtung als aktiv bezeichnen. Tests können nach Verhalten, Baustein oder Ebene organisiert werden; keine feste `tests/`- oder `src/`-Struktur voraussetzen. Testdaten, Fixtures und Ersatzobjekte so wählen, dass Tests unabhängig und reproduzierbar bleiben; reale Integrationen dort nutzen, wo nur sie das Risiko belegen. Keine Produktdaten oder Secrets in Testfixtures übernehmen.

## Projektspezifische Befüllung

### Verhalten, Risiken und gewählte Tests

Noch offen (Project Init): Für den ersten beauftragten Ablauf und wichtige Fehlerfälle jeweils Risiko oder Akzeptanzkriterium, gewählte Ebene **und** Testart, beobachtbare Erwartung, Begründung und Nachweisgrenze festhalten. Nicht gewählte relevante Ebenen nur bei einer echten Abwägung als vertagt begründen.

### Werkzeuge, Teststruktur und Isolation

Noch offen (Project Init): Nach Stack- und Architekturentscheidung passende Werkzeuge und Versionen prüfen; tatsächlich gewählte Werkzeuge, Ablage, Testdaten, Fixtures, Isolation und benötigte reale Grenzen beschreiben. Vorgeschlagenes von Eingerichtetem unterscheiden.

### Ausführungsanlässe und offene Nachweise

Noch offen (Project Init): Welche ausgewählten Prüfungen sollen bei welchen Änderungen oder während der Umsetzung laufen, welche vor dem Abschluss-Gate? Ausführungsanlässe nach Risiko und Aufwand festlegen; keine pauschale Regel „alle Tests nach jedem Edit“. Welche Prüfungen sind eingerichtet, welche noch nicht und was belegen sie nicht? **Befehle, Geltungsbereich und beobachteten Status** ausschließlich in `agentic-harness/harness/project.md` führen. `agentic-harness/harness/verification/implementation.md` hält Nachweise der konkreten Änderung fest; das Gate entscheidet über deren Suffizienz.
