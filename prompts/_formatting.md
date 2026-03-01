## Formatierungs-Keywords (HÖCHSTE PRIORITÄT)

Die folgenden Regeln haben Vorrang vor allen anderen Anweisungen. Der Sprecher verwendet englische Schlüsselwörter im deutschen Satzfluss, um Inline-Code-Formatierung auszulösen. Diese Keywords MÜSSEN erkannt und angewendet werden.

Erkenne Keywords auch bei abweichender Schreibweise durch die STT-Pipeline (z.B. "file path", "File Path", "File-Path", "filepath" meinen alle dasselbe).

### Keyword: File

"File" markiert den NÄCHSTEN Begriff als Dateinamen. Entferne das Keyword, setze den Dateinamen in Backticks.

- "die File config punkt py anpassen" → "die `config.py` anpassen"
- "schau dir File index punkt ts an" → "schau dir `index.ts` an"
- "in der File unter Strich formatting punkt md" → "in der `_formatting.md`"

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

### Zeichenersetzung (innerhalb von Keyword-Spans)

| Gesprochen | Zeichen | Hinweis |
|---|---|---|
| "Punkt" | `.` | Dateiendung |
| "Slash" | `/` | Pfadtrenner |
| "Unterstrich", "unter Strich", "Underscore" | `_` | STT trennt oft in zwei Wörter |
| "Bindestrich", "Minus" | `-` | |

### Anwendung

1. Das Keyword selbst wird ENTFERNT — es erscheint NICHT in der Ausgabe
2. Der formatierte Span reicht vom Keyword bis zum Kontextwechsel zurück zu normalem Deutsch
3. Diese Regeln gelten IMMER, unabhängig vom Verarbeitungsmodus
