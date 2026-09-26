# Core – Arbeitsablauf von Auftrag bis Übergabe

> - **Typ:** Prozess
> - **Zuständigkeit:** Entscheidungen und Rücksprünge zwischen Klärung, Umsetzung, Verifikation und Übergabe steuern.
> - **Gilt bei:** Jeder Aufgabe nach dem Einstieg über `AGENTS.md`, auch bei Harness-Arbeit.
> - **Ladebeziehungen:** Vorher `AGENTS.md` und `agentic-harness/harness/project.md`; bei beauftragtem Project Init für ein leeres Produktprojekt oder vor erster Produktumsetzung mit `Pending Project Init` → `agentic-harness/harness/init.md`. Bei offener Idee → `agentic-harness/ideas/S000-readme.md`, bei beauftragtem Nutzerverhalten → `agentic-harness/specs/S000-readme.md` und betroffene Specs. Weitere Docs nach dem Auslöser in `AGENTS.md`; vor Abschluss → `agentic-harness/harness/verification/gate.md`.
> - **Nicht zuständig:** Aufgabenrouting, Dokumentformat, Produktfakten, Testbefehle oder die Entscheidung des Verification-Gates duplizieren.

## Entscheidungsfluss

```text
AGENTS.md → core.md + project.md
                 │
                 ├─ Init beauftragt / erste Produktumsetzung bei Pending?
                 │     └─ init.md → Projektdateien → zurück zum Auftrag
                 └─ Ziel, Umfang und Freigaben klären
                       ├─ größeres Vorhaben noch offen? → Idea → Klärung → zurück
                       ├─ neues/geändertes Nutzerverhalten beauftragt? → Spec
                       └─ sonst → beauftragten Umfang ohne künstliche Spec festhalten
                                  ↓
                      Docs nach Auslöser in AGENTS.md lesen:
                      architecture.md / code.md / testing.md
                      (testing.md: Auswahl, Testorte und Anlässe)
                                  ↓
                      Schritt 3: beauftragte Änderung umsetzen;
                      bei Bedarf Produktcode/Tests ändern und
                      passende Checks schon während der Arbeit ausführen
                                  ↓
                      verification/gate.md: Soll ↔ Ist/Nachweise
                       ├─ ausreichend → Ergebnis übergeben; ggf. Spec „Implemented“
                       └─ Lücke → fail.md → je nach Ursache zurück zu
                            Klärung / Docs / Setup / Umsetzung / Checks
                            → betroffene Nachweise + Gate erneut
```

Die Dateinamen im Bild sind verkürzt; maßgeblich sind die Pfade im Kopf und das Routing in `AGENTS.md`. Bei geänderten Ladewegen dieses Bild mitprüfen.

## 1. Auftrag einordnen

Lies das Projektprofil für bestätigte Grenzen und tatsächlich eingerichtete Prüfungen. Ist Project Init für ein neues, leeres Produktprojekt beauftragt oder steht vor der ersten Produktimplementierung noch `Pending Project Init` im Profil, nutze `agentic-harness/harness/init.md`. Allein Harness- oder Dokumentationsarbeit löst kein Init aus. Erfinde keine fehlenden Projektfakten.

Kläre das gewünschte Ergebnis, den Umfang und Nicht-Ziele. Bei fehlender Entscheidung oder Freigabe nicht stillschweigend eine Annahme zur Projektregel machen.

## 2. Klärung in beauftragtes Soll überführen

Ist ein größeres Vorhaben noch offen, kläre es als Idea nach `agentic-harness/ideas/S000-readme.md`. Auch eine `Ready`-Idea ist ohne gesonderten Umsetzungsauftrag keine Freigabe. Nach Klärung kehre zur Einordnung des Auftrags zurück.

Bei beauftragtem neuem oder geändertem Nutzerverhalten prüfe betroffene Specs nach `agentic-harness/specs/S000-readme.md`; erstelle oder ändere die nötige Spec mit prüfbaren Kriterien. Für verhaltensgleiche Refactors, Struktur- und Dokumentationsaufträge hält der Auftrag den Umfang fest; sie brauchen nicht pauschal eine neue Produktspec.

Lade die durch den Aufgabeninhalt ausgelösten Docs über `AGENTS.md`. Bei überlappenden Auslösern gelten die betroffenen Dateien gemeinsam, nicht die gesamte Dokumentation auf Vorrat.

## 3. Änderung ausführen und Umfang nachführen

Setze die kleinste Änderung um, die den **ganzen beauftragten Umfang** erfüllt. Wenn sich dabei neue Architektur-, Code- oder Testfragen ergeben, prüfe die Auslöser in `AGENTS.md` erneut und lies die jetzt betroffenen Docs vor dem Eingriff. Beachte bestätigte Projektgrenzen; kläre Rechte, echte Daten und irreversible Aktionen vor dem Eingriff.

Erfordert die Arbeit eine neue Produktentscheidung oder ändert sich das Soll, gehe zur Klärung zurück und aktualisiere betroffene Projektdateien oder Specs, bevor du auf der neuen Annahme weiterarbeitest. Bei Strukturänderungen prüfe Ziel, tatsächlichen Baum und Folgen für Abhängigkeiten und Tests; übernimm keine projektspezifische Ordnerstruktur als allgemeine Pflicht.

## 4. Verifizieren und übergeben

Folge vor dem Abschluss `agentic-harness/harness/verification/gate.md`. Es verbindet Auftrag und Projektgrenzen mit Änderung und tatsächlichen Nachweisen. Bei einer Lücke folge dem dort geladenen `agentic-harness/harness/verification/fail.md`: kläre oder korrigiere die Ursache und durchlaufe das Gate erneut. Fehlt eine erforderliche Entscheidung oder ein Nachweis, berichte die Blockade statt Erfolg zu behaupten.

Berichte den erreichten Umfang, beobachtete Prüfergebnisse und offene Punkte. Ändere den Status einer Produktspec nur gemäß der Gate-Entscheidung; ohne Produktspec kein künstlicher Statuswechsel und bei reiner Prozess-/Dokuänderung kein behauptetes Produkt-Gate.

Ergänze bei der Übergabe eine **Mini-Spur im Chat** (wenige Zeilen, kein neues Artefakt): Welcher Entscheidungszweig galt, welche dafür relevanten Markdown-Dateien wurden tatsächlich gelesen, welche Dateien geändert und welche Prüfungen wirklich ausgeführt oder offen gelassen? Trenne Lesen von Ändern und prüfe, ob ein für diesen Zweig nötiger Schritt fehlt; behaupte weder ungelesene Dateien noch ein nicht durchlaufenes Produkt-Gate. Die Mini-Spur dokumentiert den Ablauf, ersetzt aber keine Prüfung und löst keinen zusätzlichen Verification-Durchlauf aus.
