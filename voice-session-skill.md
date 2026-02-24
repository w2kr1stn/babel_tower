# Voice Session Skill

Du befindest dich in einer Voice-Session mit dem Nutzer. Alle Interaktion erfolgt ueber das `converse` MCP-Tool von Babel Tower.

## Regeln

1. **Nutze IMMER `converse()` fuer Rueckfragen** — NIEMALS `AskUserQuestion` oder `EnterPlanMode`
2. **Kommuniziere Ergebnisse ueber `converse(message="...")`** — der Nutzer liest keine langen Terminal-Ausgaben
3. **Nutze `converse(message="...", wait_for_response=False)` fuer Status-Updates** — wenn du gerade arbeitest und keine Antwort brauchst
4. **Halte deine Messages kurz** — der Nutzer hoert/liest sie als Notification, nicht als Essay
5. **Frage aktiv nach** wenn du unsicher bist — ein `converse(message="Soll ich X oder Y?")` ist besser als eine falsche Annahme

## Ablauf

1. Starte mit `converse()` oder `converse(message="Was soll ich tun?")` um die erste Anweisung zu erhalten
2. Arbeite an der Aufgabe, nutze `converse(message="Status...", wait_for_response=False)` fuer Zwischenstände
3. Wenn fertig oder Rueckfrage: `converse(message="Ergebnis/Frage")` und warte auf Antwort
4. Wiederhole bis der Nutzer "fertig", "stop", "danke" oder aehnliches sagt
5. Beende die Voice-Session mit einer kurzen Zusammenfassung (als normaler Text, kein converse)

## Sprache

- Der Nutzer spricht Deutsch mit englischen Fachbegriffen
- Deine `message`-Texte in Notifications: Deutsch, kurz und praegnant
- Deine Arbeit (Code, Commits, etc.): wie gewohnt (Englisch fuer Code, Deutsch wenn angefragt)

## Wichtig

- Die Voice-Pipeline hat eine kurze Verzoegerung (STT + LLM-Postprocessing) — das ist normal
- Bei "Keine Sprache erkannt" (leerer String): frage nochmal nach mit `converse(message="Ich habe nichts verstanden. Kannst du das wiederholen?")`
- Bei STT-Fehlern: informiere den Nutzer und arbeite mit dem was du hast
