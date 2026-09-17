# JARVIS — עוזר AI אישי (MVP)

עוזר AI מקומי בהשראת JARVIS מ־Iron Man: שיחה בשפה טבעית, כלים לשליטה בסיסית
במחשב, זיכרון מקומי, וממשק עתידני עם כדור חלקיקים אנימטיבי. גרסה זו היא ה־MVP
הראשון — עובד מקצה לקצה, ומיועד להתרחבות בהדרגה.

## הפעלה מהירה (Windows)

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

(קול הוא הרחבה נפרדת ואופציונלית — ראה "קול (אופציונלי)" למטה — כדי שהתקנה
בסיסית תמיד תצליח גם למי שאין לו כלי קומפילציה מותקנים.)

בהרצה ראשונה נוצר הקובץ `jarvis/config/settings.json` (עותק של
`settings.example.json`). זה הקובץ שעורכים כדי להגדיר מפתח API, שפת קול וכו' —
הוא לא נכנס ל-git.

חלון JARVIS ייפתח אוטומטית (חלון אפליקציה עצמאי דרך `pywebview`, ואם החבילה
לא מותקנת — ייפתח בדפדפן ברירת המחדל בכתובת `http://127.0.0.1:8756`).

### הפעלה בלי מפתח API (מצב Echo)

אין צורך במפתח כדי לבדוק שהמערכת עובדת. במצב הזה JARVIS מבין פקודות פשוטות
בלבד (לא שיחה חופשית), למשל:

```
system info
search <טקסט>
read file <נתיב מלא>
open <שם תוכנה / קובץ>
open website <כתובת>
close <שם תהליך>
remember <key> = <value>
recall
forget <key>
```

### הפעלה עם Claude (שיחה חופשית + הבנת כוונות)

ב-`jarvis/config/settings.json`:

```json
{
  "ai_provider": "anthropic",
  "anthropic_api_key": "sk-ant-...",
  "anthropic_model": "claude-sonnet-5"
}
```

ואז JARVIS ינהל שיחה טבעית מלאה ויחליט בעצמו מתי להשתמש בכלים.

### הפעלה עם Groq (שיחה חופשית + הבנת כוונות, חינמי/מהיר)

מפתח מקבלים ב-[console.groq.com](https://console.groq.com/keys). ב-
`jarvis/config/settings.json`:

```json
{
  "ai_provider": "groq",
  "groq_api_key": "gsk_...",
  "groq_model": "llama-3.3-70b-versatile"
}
```

זה עובד בדיוק כמו מצב Anthropic (tool use אמיתי דרך ה-API), רק עם מודל אחר
ברקע. אפשר להחליף את `groq_model` לכל מודל אחר שזמין בחשבון ה-Groq שלך
(שים לב שלא כל מודל תומך ב-function calling).

### קול (אופציונלי)

זה תלוי בחבילות נוספות שלא נכללות בהתקנה הרגילה (כי `PyAudio` דורש קומפיילר
ב-Windows ועלול להיכשל אצל חלק מהמשתמשים). כדי להפעיל קול:

```powershell
pip install -r requirements-voice.txt
```

אם ההתקנה נכשלת על `PyAudio` עם שגיאה על "Microsoft Visual C++ 14.0 required",
יש שתי אפשרויות: להתקין את [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
(רק את "Desktop development with C++"), או לנסות
`pip install pipwin && pipwin install pyaudio` כתחליף.

אחרי שההתקנה הצליחה, ב-`settings.json` תחת `"voice": {"enabled": true, ...}`,
ולחיצה על כפתור 🎙 בממשק תפעיל האזנה חד-פעמית מהמיקרופון (Google Speech
Recognition) ותקריא את התשובה בקול (SAPI5 של Windows דרך `pyttsx3`).

## מה נבנה

```
run.py                        נקודת הכניסה — מרים שרת + פותח חלון
jarvis/
  core/ai_core.py             התזמור: היסטוריה → מודל → כלים → תשובה
  core/providers/             Echo (בלי API), Anthropic ו-Groq (שניהם עם tool use אמיתי)
  tools/                      כל כלי הוא מודול נפרד + רמת הרשאה
  permissions/manager.py      שער האישורים בין AI לכלים
  memory/memory_store.py      זיכרון מקומי (data/memory.json, קריא לעריכה ידנית)
  voice/                      זיהוי דיבור + טקסט-לדיבור (נכשל בעדינות אם לא מותקן)
  server/app.py               FastAPI + WebSocket שמחבר הכול לממשק
  server/static/              index.html / style.css / app.js / particles.js
  utils/                      קונפיג ולוגים (jarvis/logs/jarvis.log)
```

## מודל הרשאות

כל כלי מסומן ברמה:

- **READ** — פעולות קריאה בלבד (מידע מערכת, חיפוש/קריאת קבצים) → רץ מיד.
- **ACTION** — משנה משהו (פתיחת אפליקציה/אתר, שמירת/מחיקת פתק) → קופץ אישור
  בממשק עם שם הכלי, תיאור והפרמטרים המדויקים לפני ביצוע.
- **CRITICAL** — השפעה משמעותית/בלתי הפיכה (כרגע: סגירה כפויה של אפליקציה,
  שעלולה לאבד עבודה לא שמורה) → דורש אישור כפול ומפורש.

JARVIS לא עוקף UAC, הרשאות קבצים או כל בקרת אבטחה של Windows — הוא רק קורא
לפעולות רגילות של המערכת (subprocess, os.startfile וכו'), כך שאם Windows
עצמו יבקש אישור, הוא עדיין יבקש.

## מגבלות ידועות של ה-MVP הזה

- הבנת השפה הטבעית ותכנון קריאות-כלים אוטומטי (tool use) עובדים רק במצב
  Anthropic או Groq; במצב Echo זה מבוסס מילות-מפתח פשוטות בלבד.
- קלט קול תלוי בחיבור אינטרנט (Google Speech Recognition); אין עדיין מנוע
  offline.
- אין עדיין: תזמון משימות, אינטגרציה עם יומן/מייל, זיהוי דובר, wake-word
  ("Hey JARVIS").
- נבדק ונכתב בסביבת פיתוח לינוקס (אין כאן מכונת Windows); לפני שימוש אמיתי
  יש להריץ פעם אחת על Windows ולוודא שפתיחת/סגירת אפליקציות ו-PyAudio עובדים
  אצלך.

זו נקודת התחלה מודולרית — כל שיפור הבא (זיכרון חכם יותר, כלים נוספים, wake
word, שיפור עיצוב) נכנס כמודול חדש או תוספת לכלי קיים, בלי לגעת בשאר המערכת.
