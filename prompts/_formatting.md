## Formatierungs-Keywords

Der Sprecher verwendet englische Schlüsselwörter um bestimmte Formatierungen auszulösen. Erkenne diese Keywords auch bei abweichender Groß-/Kleinschreibung oder Schreibweise durch die STT-Pipeline (z.B. "file path", "File Path", "File-Path", "filepath" meinen alle dasselbe Keyword).

### File

Das Keyword "File" (einzelnes Wort) markiert den NÄCHSTEN Begriff als Dateinamen. Setze den Dateinamen in Backticks. Der Sprecher buchstabiert "Punkt" als Trennzeichen für die Dateiendung.

Beispiele:
- "die File config punkt py anpassen" → "die `config.py` anpassen"
- "schau dir File index punkt ts an" → "schau dir `index.ts` an"
- "in der File readme punkt md" → "in der `readme.md`"

### File-Path

Das Keyword "File-Path" (oder "File Path", "Filepath") markiert die FOLGENDEN Begriffe als Dateipfad. Setze den gesamten Pfad in Backticks. Der Sprecher nutzt "Slash" als Verzeichnistrenner und "Punkt" für die Dateiendung.

Beispiele:
- "im File-Path src slash utils slash helper punkt ts" → "im `src/utils/helper.ts`"
- "öffne File Path app slash babel tower slash config punkt py" → "öffne `app/babel_tower/config.py`"

### Branch Name

Das Keyword "Branch Name" (oder "Branch-Name", "Branchname") markiert die FOLGENDEN Begriffe als Git-Branch-Name. Setze den Branch-Namen in Backticks. Wandle Leerzeichen zwischen Wörtern in Bindestriche um (Kebab-Case). Der Sprecher nutzt "Slash" als Präfix-Trenner (z.B. "feature slash").

Beispiele:
- "erstell den Branch Name feature slash add login page" → "erstell den `feature/add-login-page`"
- "auf Branch Name fix slash update config" → "auf `fix/update-config`"
- "merge Branch Name main" → "merge `main`"

### Allgemeine Regeln

- Keywords sind IMMER englisch und stehen im deutschen Satzfluss
- Das Keyword selbst wird NICHT in die Ausgabe übernommen
- "Punkt" → `.` (Dateiendung)
- "Slash" → `/` (Pfadtrenner)
- "Unterstrich" oder "Underscore" → `_`
- "Bindestrich" oder "Minus" → `-`
- Die Backtick-Formatierung greift ab dem Keyword bis zum nächsten natürlichen Satzbestandteil (erkennbar am Kontextwechsel zurück zu normalem Deutsch)
