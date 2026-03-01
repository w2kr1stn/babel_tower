## Formatierungs-Keywords

Wende diese Regeln IMMER an. Der Sprecher nutzt englische Keywords für Inline-Code-Formatierung.

Keyword → Aktion:
- "File" + Dateiname → `dateiname.ext` (Keyword entfernen)
- "File Path" + Pfadteile → `pfad/zur/datei.ext` (Keyword entfernen)
- "Branch Name" + Name → `prefix/kebab-case-name` (Keyword entfernen, Leerzeichen→Bindestriche)

Zeichenersetzung in Keyword-Spans:
- "punkt" → `.`, "slash" → `/`, "unterstrich"/"unter Strich" → `_`, "Bindestrich"/"Minus" → `-`

Beispiele:
- "die File config punkt py" → "die `config.py`"
- "File Path app slash babel tower slash config punkt py" → "`app/babel_tower/config.py`"
- "Branch Name feature slash add login" → "`feature/add-login`"
