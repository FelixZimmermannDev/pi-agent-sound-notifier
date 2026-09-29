# Pi Agent Completion Sound

- **State:** Modified
- **Ziel und Nutzer:** Eine Person, die Pi vorwiegend im PyCharm-Terminal nutzt, soll durch einen kurzen Ton bemerken, wenn der Coding Agent vollständig fertig ist.
- **Beschreibung:** Die Extension spielt auf macOS nach Abschluss eines Pi-Agent-Laufs genau einen kurzen lokalen Sound ab und markiert den zugehörigen PyCharm-Terminal-Tab vorübergehend mit einem gelben Punkt im Titel.
- **Nicht im Umfang:** PyCharm-Plugin, Modell-/Provider-spezifische Integration, Desktop-Popup, Sound bei Zwischen-Turns oder Berechtigungsfragen, Netzwerkzugriff und plattformübergreifende Audioausgabe.

## Akzeptanzkriterien

- **AK1:** Ein vollständig abgeschlossener Agent-Lauf spielt genau einen kurzen Ton ab.
- **AK2:** Ein Turn-Ende mit automatischer Fortsetzung spielt noch keinen Abschluss-Ton; der Ton kommt erst nach dem endgültigen Settling.
- **AK3:** Ein Fehler beim Starten des Audio-Players beendet oder beeinträchtigt die Pi-Agent-Sitzung nicht.
- **AK4:** Das Verhalten ist unabhängig vom gewählten Modell oder Provider; die Extension liest oder verändert keine Prompt- oder Transcript-Inhalte.
- **AK5:** Im interaktiven TUI wird beim Arbeiten ein neutraler Punkt im Terminaltitel und nach dem endgültigen Settling ein gelber Punkt angezeigt.
- **AK6:** Beim Start des nächsten Agent-Laufs wechselt die Tab-Markierung vom gelben Abschluss-Punkt zurück zum neutralen Arbeitspunkt.
- **AK7:** In Claude Code spielt ein `Stop`-Hook (`hooks/claude-stop-sound.sh`) nach jeder abgeschlossenen Antwort denselben Ton ab; ein Fehler des Players blockiert Claude Code nicht. Die Tab-Markierung bleibt Pi-spezifisch.

## Nachweise

- **AK1:** Unit-Test des registrierten Handlers bestanden; direkter macOS-`afplay`-Smoke-Test bestanden. Live-Pi-Abschluss in PyCharm noch offen.
- **AK2:** Unit-Test bestätigt, dass ausschließlich `agent_settled` registriert wird.
- **AK3:** Unit-Test mit synchron fehlschlagendem Audioadapter bestanden; asynchrone Playerfehler werden geloggt.
- **AK4:** Codeprüfung bestätigt Lifecycle-only Verhalten ohne Modell-/Transcript-Zugriff.
- **AK5/AK6:** Unit-Tests prüfen TUI-Titelwechsel und dass andere Modi keinen Terminaltitel ändern; der echte PyCharm-Tab muss noch manuell geprüft werden.
- **AK7:** Hook-Skript per Pipe-Test ausgeführt (Exit 0, Ton hörbar); Hook-Eintrag per `jq` validiert. Live-Test in einer neuen Claude-Code-Sitzung offen.
- **Gate:** Noch offen, bis Audio und Tabtitel in einem vollständigen Pi-/PyCharm-Lauf manuell nachgewiesen sind.
