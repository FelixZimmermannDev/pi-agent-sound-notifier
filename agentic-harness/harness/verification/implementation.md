# Implementation – Änderung und Nachweise prüfen

> - **Typ:** Prozess
> - **Zuständigkeit:** Das tatsächlich geänderte Verhalten und ausgeführte Prüfungen gegen das ermittelte Soll belegen.
> - **Gilt bei:** Abschlussprüfung durch `agentic-harness/harness/verification/gate.md` nach einer Änderung.
> - **Ladebeziehungen:** Vom Gate geladen; Soll aus `agentic-harness/harness/verification/requirements.md`, aktive Befehle und Grenzen aus `agentic-harness/harness/project.md`. Bei Codearbeit `agentic-harness/docs/code.md`, bei Produkt- oder Teständerungen `agentic-harness/docs/testing.md`, bei Strukturänderungen `agentic-harness/docs/architecture.md` lesen. Ergebnis ans Gate.
> - **Nicht zuständig:** Teststrategie oder Projektbefehle festlegen; Abschluss und Spec-Status entscheidet das Gate.

## Ist und Belege ermitteln

1. Prüfe die tatsächliche Änderung (Code, Tests, Konfiguration, Doku) gegen Auftrag und Soll aus `agentic-harness/harness/verification/requirements.md`: Was wurde umgesetzt, ausgelassen oder zusätzlich geändert? Bei Strukturänderungen auch den tatsächlichen Baum und betroffene Abhängigkeiten prüfen.
2. Bei Produkt- oder Teständerungen: Wähle aus `agentic-harness/docs/testing.md` die für die betroffenen Risiken und Kriterien vorgesehenen Ebenen, Arten, Ausführungsanlässe und Testorte. Führe die dafür **tatsächlich eingerichteten** Befehle aus `agentic-harness/harness/project.md` gemäß Anlass und spätestens vor der Gate-Entscheidung aus; fehlende Checks bleiben offen. Prüfe den Ablauf und relevante Fehlerfälle über die geeignete Grenze; schütze echte Daten.
3. Ordne jedem betroffenen AK oder sonstigen Prüfpunkt einen Test oder eine begründete manuelle Prüfung zu, die den aktuellen Änderungsstand tatsächlich geprüft hat; halte Ergebnis und Nachweisgrenzen fest. Bei reiner Doku- oder Prozesspflege prüfe insbesondere geänderte Verweise und Widersprüche. Ein Build, eine leere Suite oder ein geplanter, aber nicht eingerichteter Befehl belegt Nutzerverhalten nicht.

**Ergebnis an das Gate:** Beobachtetes Ist, ausgeführte Prüfungen mit Ergebnis sowie nicht ausgeführte oder fehlende Nachweise. Kennzeichne fehlende, leere oder nicht ausführbare Checks als **nicht verifiziert**, nicht als `PASS`. Eine positive Abschlussentscheidung trifft nur `agentic-harness/harness/verification/gate.md`.
