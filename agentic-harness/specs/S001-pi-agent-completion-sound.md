# Pi Agent Completion Sound

- **State:** Modified
- **Ziel und Nutzer:** Eine Person, die Pi vorwiegend im PyCharm-Terminal nutzt, soll durch einen kurzen Ton bemerken, wenn der Coding Agent vollständig fertig ist.
- **Beschreibung:** Die Extension spielt auf macOS nach Abschluss eines Pi-Agent-Laufs genau einen kurzen lokalen Sound ab.
- **Nicht im Umfang:** PyCharm-Plugin, Modell-/Provider-spezifische Integration, Desktop-Popup, Sound bei Zwischen-Turns oder Berechtigungsfragen, Netzwerkzugriff und plattformübergreifende Audioausgabe.

## Akzeptanzkriterien

- **AK1:** Ein vollständig abgeschlossener Agent-Lauf spielt genau einen kurzen Ton ab.
- **AK2:** Ein Turn-Ende mit automatischer Fortsetzung spielt noch keinen Abschluss-Ton; der Ton kommt erst nach dem endgültigen Settling.
- **AK3:** Ein Fehler beim Starten des Audio-Players beendet oder beeinträchtigt die Pi-Agent-Sitzung nicht.
- **AK4:** Das Verhalten ist unabhängig vom gewählten Modell oder Provider; die Extension liest oder verändert keine Prompt- oder Transcript-Inhalte.

## Nachweise

- **AK1:** Unit-Test des registrierten Handlers bestanden; direkter macOS-`afplay`-Smoke-Test bestanden. Live-Pi-Abschluss in PyCharm noch offen.
- **AK2:** Unit-Test bestätigt, dass ausschließlich `agent_settled` registriert wird.
- **AK3:** Unit-Test mit synchron fehlschlagendem Audioadapter bestanden; asynchrone Playerfehler werden geloggt.
- **AK4:** Codeprüfung bestätigt Lifecycle-only Verhalten ohne Modell-/Transcript-Zugriff.
- **Gate:** Noch offen, bis AK1 im vollständigen Pi-/PyCharm-Lauf manuell nachgewiesen ist.
