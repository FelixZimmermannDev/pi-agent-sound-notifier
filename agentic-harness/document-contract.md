# Dokumentenvertrag – Markdown-Aufbau und Pflege

> - **Typ:** Designregel
> - **Zuständigkeit:** Einheitlicher, lesbarer Aufbau einzelner Markdown-Dateien.
> - **Gilt bei:** Neue oder inhaltlich befüllte Steuerungs- und Projekt-MD-Dateien; bestehende Dateien werden schrittweise angepasst.
> - **Ladebeziehungen:** Vor dem Schreiben Rollen und Ladewege in `agentic-harness/harness-map.md` prüfen; aktuelle Pfade über `AGENTS.md`.
> - **Nicht zuständig:** Den gesamten Dateibaum oder den Arbeitsablauf des Agenten festlegen.

## Vor dem Schreiben

1. Bestimme die **eine Hauptaufgabe** der Datei. Was gehört ausdrücklich woanders hin?
2. Kläre ihren **Auslöser**: Wann wird sie gelesen, und über welchen Einstieg erreicht?
3. Kläre ihre **direkten Beziehungen**: Was muss vorher, nur bedingt oder danach gelesen werden?
4. Trage neue Dateien und geänderte Beziehungen zuerst in `agentic-harness/harness-map.md` ein. Kennzeichne geplante Pfade als geplant.
5. Nutze konkrete Pfade ab Repo-Root; kürze sie nur bei echten relativen Markdown-Links, deren Ziel geprüft wurde.

## Standard-Kopf für Steuerungs- und Projektdokumente

Vorlagen und Idea-/Spec-Artefakte einschließlich ihrer `S000-readme.md`-Einstiege behalten ihr eigenes Format. Auch die für Menschen geschriebene `README.md` braucht keinen Metakopf.

```markdown
# {Titel}

> - **Typ:** {Einstieg | Prozess | Projektdoku | Designregel | Index | Lernnotiz}
> - **Status:** {nur wenn Entwurf, Platzhalter oder Artefaktstatus wichtig ist}
> - **Zuständigkeit:** {eine Aufgabe und ihr Ergebnis}
> - **Gilt bei:** {konkreter Auslöser}
> - **Ladebeziehungen:** {vorher / wenn … / danach: Pfad und Zweck; sonst „Keine“}
> - **Nicht zuständig:** {Abgrenzung, falls Verwechslung möglich}
```

## Inhalt und Prüfung

- Hauptteil passend zum Typ gliedern, nicht überall dieselben Kapitel erzwingen.
- Kurze Sätze und kleine Listen schreiben. Eine Regel pro Gedanke.
- Nur direkte Ladebeziehungen nennen; kein „alle Docs bei Bedarf“ und keine Kopie der Landkarte.
- **Lesen** ist nicht **Ändern**: Ein Link überträgt keine Zuständigkeit.
- Vor Übernahme Auslöser, Pfade, Erreichbarkeit und doppelte Zuständigkeiten prüfen.

## Projektspezifische Gerüste

In `agentic-harness/harness/project.md` und den Projekt-Docs bleiben Kopf und „Universeller Rahmen“ erhalten. `agentic-harness/harness/init.md` ersetzt die Platzhalter unter „Projektspezifische Befüllung“ durch bestätigte Inhalte. Die zunächst leere Root-`README.md` wird für Menschen ohne Metakopf mit bestätigten Produktinformationen befüllt; vorhandene Produktinhalte werden ergänzt.

Beim Befüllen dieser Gerüste auch den Kopf gegen das Projekt prüfen: Stimmen **Zuständigkeit, Auslöser, Ladebeziehungen und Abgrenzung** noch? Status nur ändern, wenn die Datei tatsächlich befüllt ist. Offene Entscheidungen ausdrücklich offen lassen. Neue Projekt-Docs brauchen einen erreichbaren Leseauslöser; eine geänderte Dateirolle ist Harness-Arbeit.

## Bei neuen, umbenannten oder entfernten Dateien

1. **Vorher:** Suche repo-weit nach dem alten Pfad, Dateinamen und relativen Markdown-Links. Prüfe, welche Dateien darauf angewiesen sind.
2. **Gemeinsam ändern:** Passe diese Verweise, den Einstieg und die Landkarte an. Entferne Verweise nur, wenn die Beziehung wirklich entfällt.
3. **Nachher:** Prüfe alle verbliebenen Verweise und die Ladebeziehungen in betroffenen Dokumentköpfen gegen reale Dateien. Geplante Pfade bleiben ausdrücklich als geplant markiert.

Ändern sich Rollen oder Ladeauslöser ohne Umbenennung, gilt derselbe Abgleich für die betroffenen Köpfe, den Einstieg und die Landkarte. Prüfe sie bei solchen Änderungen, nicht pauschal bei jeder Produktaufgabe.

Auch eine manuelle Löschung kann bestehende Verweise brechen. Beim nächsten Harness-Änderungsauftrag zuerst den aktuellen Baum prüfen; Markdown aktualisiert sich nicht selbst.

Der Vertrag bleibt im Harness für spätere Projekt-Docs verfügbar. Er beschreibt Schreibformat und Pfadpflege; `AGENTS.md` und `agentic-harness/harness/init.md` regeln, wann er zu laden ist.
