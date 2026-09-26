# [Spec – beauftragtes Verhalten]

> **Vorlage:** Konkreter Auftrag mit überprüfbarem Soll; ausgefüllte Specs liegen unter `agentic-harness/specs/`.

- **State:** Modified
- **Ziel und Nutzer:** [Wozu wird die Änderung benötigt?]
- **Beschreibung:** [Beobachtbares Verhalten, ohne technischen Lösungsplan.]
- **Nicht im Umfang:** [Bewusste Abgrenzung.]

## Akzeptanzkriterien

- **AK1:** [Ein einzeln prüfbares Verhalten mit klarem Pass/Fail.]
- **AK2:** [Ein relevanter Erfolgs- oder Fehlerfall, falls benötigt.]

## Nachweise

- **AK1:** [Test oder begründete manuelle Prüfung; nach Ausführung Ergebnis festhalten.]
- **AK2:** [Nachweis, falls vorhanden.]
- **Gate:** [Tatsächlich ausgeführter Projektbefehl und Ergebnis.]

Bei inhaltlicher Änderung an einer bereits implementierten Spec zunächst `Modified`. `Implemented` erst nach belegten **allen** betroffenen AK und bestandenem `agentic-harness/harness/verification/gate.md`; sonst `Modified` und Blocker offen berichten. Bei verhaltensgleichem Refactor ohne Spec-Änderung keinen künstlichen Statuswechsel auslösen. Vorlagen-Platzhalter nicht als bestandene Nachweise übernehmen.
