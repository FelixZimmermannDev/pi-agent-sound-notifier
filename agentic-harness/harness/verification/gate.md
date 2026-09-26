# Gate – Soll und belegtes Ist zusammenführen

> - **Typ:** Prozess
> - **Zuständigkeit:** Entscheiden, ob eine konkrete Änderung innerhalb des Auftrags ausreichend nachgewiesen ist.
> - **Gilt bei:** Abschluss einer Änderung nach dem Ablauf in `agentic-harness/harness/core.md`.
> - **Ladebeziehungen:** Vorher `agentic-harness/harness/project.md` für Grenzen und aktive Prüfungen; dann `agentic-harness/harness/verification/requirements.md` für das Soll und `agentic-harness/harness/verification/implementation.md` für Ist und Nachweise. Bei einer Lücke `agentic-harness/harness/verification/fail.md`.
> - **Nicht zuständig:** Projekt-Tests festlegen oder selbst ausführen; Anforderungen und Nachweise stehen in den jeweils zuständigen Dateien.

## Entscheidungsweg

Schematische Übersicht mit verkürzten Dateinamen. Bei Änderungen an Harness-Rollen oder Ladewegen auch dieses Diagramm gegen `AGENTS.md` und `agentic-harness/harness-map.md` prüfen.

```text
AGENTS.md → core.md + project.md (Ziel, Grenzen, aktive Befehle)
                 │
                 ├→ bei Produkt-/Testarbeit: testing.md
                 │    ← Risiken/AK; bei Bedarf architecture.md + code.md
                 │    → gewählte Tests, Testorte und Anlässe
                 ↓
core.md: Änderung umsetzen; ggf. Tests entwickeln und Checks ausführen
                 ↓
gate.md: ein Abschlussdurchlauf
       ├─ requirements.md ← Auftrag + project.md; ggf. Spec/Architektur
       │                     → Soll (AK/Prüfpunkte)
       └─ implementation.md ← Soll + Änderung + project.md (Befehle)
                               ← testing.md (bei Produkt-/Teständerung)
                               → Ist, Checks auf aktuellem Stand, Nachweisgrenzen
                 ↓
      Soll durch Ist und Nachweise belegt?
       ├─ ja   → Ergebnis berichten; ggf. Spec „Implemented“
       └─ nein → fail.md → Ursache: Soll/Spec, Teststrategie, Setup/Befehl,
                          Umsetzung/Test oder fehlender Nachweis
                          → an betroffener Stelle korrigieren; Checks + Gate
                            erneut prüfen oder Blocker berichten
```

## Entscheidung

Requirements und Implementation lesen `agentic-harness/harness/project.md` und öffnen die für ihre Prüfung nötigen Specs oder Projekt-Docs nach den jeweiligen Auslösern – auch wenn diese bei der Umsetzung noch nicht geladen waren.

- Gleiche das Soll aus `agentic-harness/harness/verification/requirements.md` mit der beobachteten Änderung und den tatsächlich ausgeführten Nachweisen aus `agentic-harness/harness/verification/implementation.md` ab. Ein grüner Build oder Testlauf allein belegt nicht, dass der beauftragte Ablauf und die Projektgrenzen erfüllt sind. Nach `agentic-harness/docs/testing.md` für betroffene Risiken vorgesehene, aber nicht nachgewiesene Checks bleiben Lücken.
- Bei beauftragtem Nutzerverhalten: Jedes betroffene Akzeptanzkriterium muss belegt sein; erforderliche Prüfungen müssen bestanden sein. Nur dann darf die betroffene Spec `Implemented` werden.
- Ist keine Produktspec erforderlich (z. B. bei verhaltensgleichem Refactor oder Dokuänderung), prüfe den beauftragten Umfang und passende Nachweise ohne künstliche Spec. Für reine Doku- oder Prozesspflege kein bestandenes Produkt-Gate behaupten.
- Bei fehlendem Soll, fehlenden Nachweisen, gescheiterten Checks oder Abweichungen: kein vollständiger Abschluss. Folge `agentic-harness/harness/verification/fail.md` und berichte, was offen oder blockiert ist. Diese Datei führt keine Checks aus und setzt keinen Status automatisch.
- Übergib das Ergebnis mit einer knappen Übersicht der geänderten Dateien; bei Dokumentationsarbeit nenne insbesondere die bearbeiteten Markdown-Dateien. Berichte außerdem passende Prüfergebnisse und offene Punkte.
