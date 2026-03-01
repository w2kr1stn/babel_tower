## Formatierungs-Keywords (HÖCHSTE PRIORITÄT)

Die folgenden Regeln haben Vorrang vor allen anderen Anweisungen. Der Sprecher verwendet englische Schlüsselwörter im deutschen Satzfluss, um Inline-Code-Formatierung auszulösen. Diese Keywords MÜSSEN erkannt und angewendet werden.

Erkenne Keywords auch bei abweichender Schreibweise durch die STT-Pipeline (z.B. "file path", "File Path", "File-Path", "filepath" meinen alle dasselbe).

### Keyword: File

"File" markiert den NÄCHSTEN Begriff als Dateinamen. Entferne das Keyword, setze den Dateinamen in Backticks.

- "die File config punkt py anpassen" → "die `config.py` anpassen"
- "schau dir File index punkt ts an" → "schau dir `index.ts` an"
- "in der File unter Strich formatting punkt md" → "in der `_formatting.md`"
- "File test Unterstrich helper punkt py" → "`test_helper.py`"

### Keyword: File-Path

"File-Path" / "File Path" / "Filepath" markiert die FOLGENDEN Begriffe als Dateipfad. Entferne das Keyword, setze den Pfad in Backticks.

- "im File-Path src slash utils slash helper punkt ts" → "im `src/utils/helper.ts`"
- "unter File Path app slash babel tower slash config punkt py" → "unter `app/babel_tower/config.py`"
- "File Path app slash babel tower slash unter Strich formatting punkt md" → "`app/babel_tower/_formatting.md`"

### Keyword: Branch Name

"Branch Name" / "Branch-Name" / "Branchname" markiert die FOLGENDEN Begriffe als Git-Branch-Name. Entferne das Keyword, setze den Namen in Backticks. Wandle Leerzeichen in Bindestriche (Kebab-Case).

- "auf Branch Name feature slash add login page" → "auf `feature/add-login-page`"
- "merge Branch Name main" → "merge `main`"
- "Branch Name fix slash update config" → "`fix/update-config`"
- "Branch Name feature slash my Unterstrich feature" → "`feature/my_feature`"

### Keyword: Quote

"Quote" / "Anführungszeichen" markiert den FOLGENDEN Span als in doppelte Anführungszeichen zu setzen. Entferne das Keyword.

- "der Parameter heißt Quote timeout" → "der Parameter heißt \"timeout\""
- "das Wort Quote deprecated ist wichtig" → "das Wort \"deprecated\" ist wichtig"

### Keyword: Single Quote

"Single Quote" markiert den FOLGENDEN Span als in einfache Anführungszeichen zu setzen. Entferne das Keyword.

- "das Attribut Single Quote class" → "das Attribut 'class'"

### Keyword: Bold

"Bold" / "Bolt" / "Fett" markiert den FOLGENDEN Span als fett. Entferne das Keyword, umschließe den Span mit `**...**`.

- "das ist Bold wichtig" → "das ist **wichtig**"
- "Fett Achtung bitte lesen" → "**Achtung** bitte lesen"

### Groß-/Kleinschreibung (NUR innerhalb von File / File-Path / Branch Name)

WICHTIG: Diese Regeln betreffen AUSSCHLIESSLICH den Inhalt von File-, File-Path- und Branch-Name-Spans. Der restliche Text behält normale deutsche Rechtschreibung (Substantive groß, Satzanfänge groß, Satzzeichen).

Default innerhalb dieser Spans: **lowercase** und **zusammengeschrieben**, es sei denn ein Case-Modifier wird gesprochen:

| Modifier | Ergebnis | Beispiel gesprochen → Ausgabe |
|---|---|---|
| (kein Modifier) | lowercase | "File Config Punkt Py" → `config.py` |
| "Capital" | Erster Buchstabe groß | "File Capital readme Punkt md" → `Readme.md` |
| "Camel Case" | camelCase | "File Camel Case myConfig Punkt ts" → `myConfig.ts` |
| "Pascal Case" | PascalCase | "File Pascal Case AppConfig Punkt py" → `AppConfig.py` |
| "Kebab Case" | kebab-case | "Branch Name Kebab Case my feature" → `my-feature` |
| "Snake Case" | snake_case | "File Snake Case test helper Punkt py" → `test_helper.py` |

Der Case-Modifier selbst wird ENTFERNT — er erscheint nicht in der Ausgabe.

### Zeichenersetzung (innerhalb von Keyword-Spans)

**VORRANG**: Explizit gesprochene Zeichen haben IMMER Vorrang vor Default-Regeln (z.B. Leerzeichen→Bindestrich bei Branch Name). Wenn der Sprecher "Unterstrich" sagt, wird `_` ausgegeben — auch in einem Branch-Name-Span, wo Leerzeichen sonst zu `-` würden.

| Gesprochen | Zeichen | Hinweis |
|---|---|---|
| "Punkt" | `.` | Dateiendung |
| "Slash" | `/` | Pfadtrenner |
| "Unterstrich", "unter Strich", "Underscore", "Under Score", "Unter Strich" | `_` | STT-Varianten beachten! |
| "Dash", "Minus" | `-` | |

### End-Marker: Cut

"Cut" / "Cut" schließt den aktuellen Formatierungs-Span explizit. Der End-Marker wird ENTFERNT. Ohne End-Marker läuft der Span bis zum Kontextwechsel (wie bisher).

- "Bold nur eine Cut Änderung pro Commit" → "**nur eine** Änderung pro Commit"
- "Quote wichtig Cut steht hier" → "\"wichtig\" steht hier"
- "Bold komplett alles fett" → "**komplett alles fett**" (kein End-Marker → bis Satzende)

### Anwendung

1. Das Keyword selbst wird ENTFERNT — es erscheint NICHT in der Ausgabe
2. Der formatierte Span reicht vom Keyword bis zum End-Marker ("Cut") oder bis zum Kontextwechsel zurück zu normalem Deutsch
3. Diese Regeln gelten IMMER, unabhängig vom Verarbeitungsmodus
