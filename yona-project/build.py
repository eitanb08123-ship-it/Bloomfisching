import html

OUT = "./game.html"

storm = [
    ("רוח גדולה", 3, "״וה׳ הטיל רוח גדולה אל הים״ (א, ד)", ""),
    ("סער גדול", 3, "״ויהי סער גדול בים״ (א, ד)", ""),
    ("גל שובר", 3, "", ""),
    ("גל ענק מכה בדופן", 2, "", ""),
    ("מים חודרים לבטן האונייה", 2, "", ""),
    ("התורן נסדק", 2, "", "בסיבוב הזה אי אפשר לחתור."),
    ("המפרש נקרע", 2, "", ""),
    ("גשם זלעפות", 2, "", ""),
    ("החבלים נקרעים", 2, "", ""),
    ("ברק", 1, "", "מי שהפך את הקלף מפסיד את הפעולה שלו בסיבוב הזה."),
    ("הכלים מתגלגלים", 1, "", "מטען אחד נופל לים. מורידים אותו בלי להוריד סדקים."),
    ("המלחים מתייאשים", 1, "", "בסיבוב הזה כל התפילות ״איש אל אלוהיו״ נכשלות."),
    ("רב החובל צועק", 1, "״מה לך נרדם?״ (א, ו)", "רב החובל מקבל פעולה נוספת בסיבוב הזה."),
    ("הים הולך וסוער", 1, "״כי הים הולך וסוער״ (א, יא)", "מזיזים את סמן הסערה צעד נוסף קדימה."),
    ("ענן שחור", 1, "", "קלף הסערה הבא מוסיף סדק אחד נוסף."),
    ("שקט רגעי", 0, "", "נשימה עמוקה. אין סדקים חדשים."),
]

dilemmas = [
    "יונה ברח ממשימה שלא רצה לעשות. נזכרתם במשימה שרציתם לברוח ממנה? ברחתם או התמודדתם, ומה קרה אחר כך?",
    "בזמן הסערה יונה ירד לבטן האונייה ונרדם. קרה לכם שהתעלמתם מבעיה וקיוויתם שהיא תיעלם לבד?",
    "המלחים סבלו בגלל ההחלטה של יונה. תנו דוגמה להחלטה של אדם אחד שפוגעת בכל ״האונייה״: בכיתה, בקבוצה או במשפחה.",
    "יונה אמר: ״בשלי הסער הגדול הזה״. למה כל כך קשה להגיד ״זו אשמתי״? מה מרוויחים כשאומרים את זה?",
    "המלחים ניסו לחתור ליבשה במקום לזרוק את יונה מיד. מתי נכון לבחור בדרך הקשה כדי לא לפגוע במישהו?",
    "רב החובל, איש זר, הוא שהעיר את הנביא. ממי למדתם פעם משהו חשוב, ממש לא ממי שציפיתם?",
    "המלחים הפילו גורלות כדי לגלות מי אשם. האם הוגן להחליט בהגרלה מי אשם? איך כדאי לבדוק מי אחראי לבעיה?",
    "״ויתן שכרה״: יונה שילם כסף כדי לברוח. מה ״המחיר״ שאנחנו משלמים כשאנחנו בורחים מאחריות?",
    "אפשר לברוח ממקום. אפשר גם לברוח מעצמכם? איך זה נראה בחיים של בני נוער?",
    "אילו הייתם מלחים: הייתם זורקים את יונה לים ברגע שביקש? למה?",
    "יונה סיפר את האמת על עצמו גם כשזה היה מסוכן לו: ״עברי אנכי ואת ה׳ אני ירא״. מתי קשה לכם להגיד את האמת?",
    "המלחים פחדו אבל לא נכנסו לפאניקה: הם פעלו, התפללו ושאלו שאלות. איך מתנהגים נכון בזמן ״סערה״ בחיים?",
]

roles = [
    ("רב החובל", "״ויקרב אליו רב החובל״ (א, ו)",
     "רק רב החובל יכול להעיר את יונה. פעם אחת במשחק מותר לו לבצע שתי פעולות באותו סיבוב."),
    ("המלח החזק", "״ויטלו את הכלים... אל הים״ (א, ה)",
     "כשהוא מטיל כלים לים, יורדים 3 סדקים במקום 2."),
    ("החותר", "״ויחתרו האנשים להשיב אל היבשה״ (א, יג)",
     "כשהוא חותר ויוצאים 5 או 6 בקובייה, יורד גם סדק אחד."),
    ("המלח המתפלל", "״ויזעקו איש אל אלוהיו״ (א, ה)",
     "כשהוא זועק אל אלוהיו, התפילה מצליחה ב־4, 5 או 6 (ולא רק ב־5 או 6)."),
    ("הנווט", "״ויהי סער גדול בים״ (א, ד)",
     "פעם אחת בכל סיבוב מותר לו לבטל את ההוראה המיוחדת של קלף סערה. הסדקים של הקלף נשארים."),
]

def e(s):
    return html.escape(s)

def storm_card(t, v, verse, special):
    cracks = "🌊" * v if v else "—"
    return f'''<div class="card storm">
  <div class="ctype">קלף סערה</div>
  <div class="ctitle">{e(t)}</div>
  <div class="cval">+{v} סדקים</div>
  <div class="cwaves">{cracks}</div>
  {f'<div class="cverse">{e(verse)}</div>' if verse else ''}
  {f'<div class="cspecial">{e(special)}</div>' if special else ''}
</div>'''

def dilemma_card(i, q):
    return f'''<div class="card dil">
  <div class="ctype">קלף דילמה · {i}</div>
  <div class="ctitle small">שאלה מהחיים</div>
  <div class="cq">{e(q)}</div>
  <div class="cfoot">דקה לדיון. כל שחקן עונה במשפט אחד.</div>
</div>'''

def role_card(t, verse, power):
    return f'''<div class="card role">
  <div class="ctype">קלף מלח</div>
  <div class="ctitle">{e(t)}</div>
  <div class="cverse">{e(verse)}</div>
  <div class="cspecial">{e(power)}</div>
</div>'''

jonah_cards = [
    '''<div class="card jonah"><div class="ctype">קלף יונה · צד א</div><div class="ctitle">יונה ישן</div>
    <div class="big">💤</div><div class="cverse">״וישכב וירדם״ (א, ה)</div></div>''',
    '''<div class="card jonah"><div class="ctype">קלף יונה · צד ב</div><div class="ctitle">יונה ער</div>
    <div class="big">👁️</div><div class="cverse">״קום קרא אל אלוהיך״ (א, ו)</div>
    <div class="cspecial">עכשיו מותר להפיל גורלות.</div></div>''',
    '''<div class="card jonah"><div class="ctype">קלף יונה · צד ג</div><div class="ctitle">הגורל נפל</div>
    <div class="big">🎲</div><div class="cverse">״ויפל הגורל על יונה״ (א, ז)</div>
    <div class="cspecial">עכשיו מותר לשאול את יונה ולחתור אל היבשה.</div></div>''',
    '''<div class="card jonah"><div class="ctype">קלף יונה · צד ד</div><div class="ctitle">״שאוני והטילוני״</div>
    <div class="big">🌊</div><div class="cverse">״כי יודע אני כי בשלי הסער הגדול הזה עליכם״ (א, יב)</div>
    <div class="cspecial">עכשיו מותר לקרוא אל ה׳ ולהטיל את יונה לים.</div></div>''',
]

tokens = "".join(f'<div class="token cargo">📦<span>מטען</span></div>' for _ in range(8)) + \
         "".join(f'<div class="token row">🚣<span>חתירה</span></div>' for _ in range(6)) + \
         "".join(f'<div class="token pray">🙏<span>תפילה</span></div>' for _ in range(3)) + \
         '<div class="token marker">⚠️<span>סדקים</span></div><div class="token marker">⛈️<span>סערה</span></div>'

all_cards = [storm_card(*s) for s in storm] + \
            [dilemma_card(i + 1, q) for i, q in enumerate(dilemmas)] + \
            [role_card(*r) for r in roles] + jonah_cards
pages = [all_cards[i:i + 9] for i in range(0, len(all_cards), 9)]
cards_html = "".join(
    f'<section class="page cards"><div class="cuthint">✂️ לגזור לאורך הקווים. כדאי להדביק על קרטון.</div><div class="grid">{"".join(p)}</div></section>'
    for p in pages[:-1])
cards_html += f'<section class="page cards"><div class="cuthint">✂️ לגזור לאורך הקווים. אסימונים: אפשר גם פקקים או מטבעות.</div><div class="grid">{"".join(pages[-1])}</div><div class="tokens">{tokens}</div></section>'

track = [
    ("1", "״וירד יפו״", "א, ג", 0),
    ("2", "״וירד בה״", "א, ג", 0),
    ("3", "״ירד אל ירכתי הספינה״", "א, ה", 1),
    ("4", "״וישכב וירדם״", "א, ה", 1),
    ("5", "״הים הולך וסוער״", "א, יא", 2),
    ("6", "״הולך וסוער עליהם״", "א, יג", 2),
    ("7", "״חשבה להישבר״", "א, ד", 3),
    ("8", "סיבוב אחרון!", "", 3),
]
track_html = "".join(
    f'<div class="tcell lvl{b}"><div class="tnum">{n}</div><div class="ttxt">{e(t)}</div>'
    f'<div class="tref">{e(r)}</div><div class="tbonus">{"+" + str(b) + " סדקים" if b else "אין תוספת"}</div></div>'
    for n, t, r, b in track)

cracks_html = "".join(
    f'<div class="crack{" danger" if i >= 9 else ""}{" broken" if i == 12 else ""}">{"💥" if i == 12 else i}</div>'
    for i in range(13))

actions = [
    ("להטיל כלים", "א, ה", "תמיד", "מורידים מטען אחד ← <b>2− סדקים</b>"),
    ("לזעוק איש אל אלוהיו", "א, ה", "תמיד", "זורקים קובייה: 5–6 ← <b>1− סדק</b>. סופרים תפילה."),
    ("להעיר את יונה", "א, ו", "רב החובל בלבד. רק אחרי שהוטל כלי אחד וזעקו תפילה אחת.", "הופכים את קלף יונה ל״יונה ער״."),
    ("להפיל גורלות", "א, ז", "יונה ער", "הגורל תמיד נופל על יונה. הופכים ל״הגורל נפל״."),
    ("לשאול את יונה", "א, ח", "אחרי הגורל", "שולפים קלף דילמה ודנים בו. אחרי 2 דילמות יונה אומר ״שאוני והטילוני״."),
    ("לחתור אל היבשה", "א, יג", "אחרי הגורל", "״ולא יכלו״: החתירה לא מצליחה, אבל לוקחים אסימון חתירה. ב־6 בקובייה ← 1− סדק."),
    ("לקרוא אל ה׳", "א, יד", "אחרי ״שאוני״", "בלי קובייה ← <b>1− סדק</b>, ולוקחים אסימון תפילה."),
    ("להטיל את יונה", "א, טו", "אחרי ״שאוני״", "״ויעמוד הים מזעפו״: המשחק נגמר וניצלתם!"),
]
actions_html = "".join(
    f'<tr><td class="an">{i + 1}. {e(a)}<div class="aref">({e(r)})</div></td><td>{e(c)}</td><td>{d}</td></tr>'
    for i, (a, r, c, d) in enumerate(actions))

doc = f'''<!DOCTYPE html>
<html lang="he" dir="rtl"><head><meta charset="utf-8"><title>הים הולך וסוער: משחק קופסה על ספר יונה</title>
<style>
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "Liberation Sans", "DejaVu Sans", Arial, sans-serif; color: #10233a; }}
.page {{ width: 210mm; height: 297mm; padding: 14mm 15mm; page-break-after: always; position: relative; overflow: hidden; }}
h1 {{ font-size: 26pt; margin: 0 0 2mm; color: #0b3c66; }}
h2 {{ font-size: 15pt; margin: 5mm 0 2mm; color: #0b3c66; border-bottom: 2px solid #f2b705; padding-bottom: 1mm; }}
h3 {{ font-size: 12pt; margin: 3mm 0 1mm; color: #0b3c66; }}
p, li {{ font-size: 10.5pt; line-height: 1.5; margin: 1mm 0; }}
ul, ol {{ margin: 1mm 0; padding-right: 6mm; }}
.sub {{ font-size: 12pt; color: #44607a; margin-bottom: 4mm; }}
.fill {{ background: #fff6d6; border: 1px dashed #d1a000; padding: 1mm 2mm; }}
.quote {{ background: #eef5fb; border-right: 4px solid #0b6fb8; padding: 2mm 3mm; margin: 1.5mm 0; font-size: 10.5pt; line-height: 1.5; }}
.quote b {{ color: #0b3c66; }}
/* cover */
.cover {{ background: linear-gradient(#0b3c66 0%, #1b6aa5 55%, #0e4a7a 100%); color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }}
.cover h1 {{ color: white; font-size: 46pt; }}
.cover .sub {{ color: #dbeaf7; font-size: 16pt; }}
.cover .ship {{ width: 140mm; }}
.cover .meta {{ margin-top: 10mm; font-size: 13pt; color: #fff; line-height: 1.8; }}
/* board */
.board {{ background: #e7f1f9; padding: 10mm; }}
.board h1 {{ text-align: center; font-size: 30pt; }}
.board .sub {{ text-align: center; }}
.boardsec {{ background: white; border-radius: 4mm; padding: 3mm 4mm; margin-bottom: 4mm; box-shadow: 0 0.5mm 1.5mm rgba(0,0,0,.15); }}
.boardsec h3 {{ margin-top: 0; }}
.cracks {{ display: flex; gap: 1.5mm; direction: rtl; }}
.crack {{ flex: 1; height: 14mm; border: 2px solid #0b3c66; border-radius: 2mm; display: flex; align-items: center; justify-content: center; font-size: 15pt; font-weight: bold; background: #f4f9fd; }}
.crack.danger {{ background: #ffe1d6; border-color: #c0392b; color: #c0392b; }}
.crack.broken {{ background: #c0392b; color: white; font-size: 18pt; }}
.track {{ display: grid; grid-template-columns: repeat(8, 1fr); gap: 1.5mm; }}
.tcell {{ border: 2px solid #0b3c66; border-radius: 2mm; padding: 1.5mm; text-align: center; min-height: 30mm; display: flex; flex-direction: column; justify-content: space-between; }}
.tcell.lvl0 {{ background: #dff0fb; }} .tcell.lvl1 {{ background: #b9dcf3; }} .tcell.lvl2 {{ background: #7fb6de; }} .tcell.lvl3 {{ background: #2f6fa3; color: white; }}
.tnum {{ font-size: 16pt; font-weight: bold; }}
.ttxt {{ font-size: 9pt; font-weight: bold; }}
.tref {{ font-size: 7.5pt; opacity: .8; }}
.tbonus {{ font-size: 8pt; background: rgba(255,255,255,.7); color: #10233a; border-radius: 1mm; }}
.zones {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 3mm; }}
.zone {{ border: 2px dashed #0b3c66; border-radius: 3mm; height: 38mm; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; font-weight: bold; font-size: 11pt; color: #0b3c66; background: #fbfdff; }}
.zone small {{ font-weight: normal; font-size: 8.5pt; }}
table.act {{ width: 100%; border-collapse: collapse; font-size: 9pt; }}
table.act th {{ background: #f2b705; padding: 1.2mm; }}
table.act td {{ border: 1px solid #9bb3c9; padding: 1.2mm; vertical-align: top; line-height: 1.35; }}
td.an {{ font-weight: bold; white-space: nowrap; }}
.aref {{ font-weight: normal; font-size: 7.5pt; color: #557; }}
/* cards */
.cards {{ padding: 10mm 12mm; }}
.cuthint {{ font-size: 9pt; color: #777; margin-bottom: 2mm; }}
.grid {{ display: grid; grid-template-columns: repeat(3, 60mm); grid-auto-rows: 88mm; gap: 0; justify-content: center; }}
.card {{ border: 1px dashed #888; padding: 4mm; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 2mm; }}
.card .ctype {{ font-size: 8pt; letter-spacing: .5px; color: #666; }}
.card .ctitle {{ font-size: 15pt; font-weight: bold; }}
.card .ctitle.small {{ font-size: 12pt; }}
.card .cval {{ font-size: 13pt; font-weight: bold; color: #c0392b; }}
.card .cwaves {{ font-size: 18pt; }}
.card .cverse {{ font-size: 9.5pt; font-style: italic; color: #0b3c66; }}
.card .cspecial {{ font-size: 9.5pt; background: #fff3c4; border-radius: 2mm; padding: 2mm; margin-top: auto; }}
.card .cq {{ font-size: 10.5pt; line-height: 1.45; flex: 1; display: flex; align-items: center; }}
.card .cfoot {{ font-size: 8pt; color: #555; }}
.card .big {{ font-size: 36pt; }}
.storm {{ background: linear-gradient(#ffffff 60%, #dbeaf7); }}
.dil {{ background: linear-gradient(#ffffff 60%, #fdf0c9); }}
.role {{ background: linear-gradient(#ffffff 60%, #dff3e3); }}
.jonah {{ background: linear-gradient(#ffffff 60%, #ecdff5); }}
.tokens {{ display: grid; grid-template-columns: repeat(7, 25mm); gap: 2mm; justify-content: center; margin-top: 4mm; }}
.token {{ width: 25mm; height: 25mm; border: 1.5px dashed #555; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 16pt; }}
.token span {{ font-size: 8pt; }}
.cargo {{ background: #f5e6cc; }} .row {{ background: #dbeaf7; }} .pray {{ background: #ecdff5; }} .marker {{ background: #ffd6d6; }}
.score td, .score th {{ border: 1px solid #9bb3c9; padding: 1.2mm 2mm; font-size: 10pt; }}
.score {{ border-collapse: collapse; width: 100%; }}
.score th {{ background: #f2b705; }}
.rules p, .rules li {{ font-size: 9.6pt; line-height: 1.4; margin: 0.6mm 0; }}
.rules h2 {{ font-size: 13pt; margin: 3mm 0 1mm; }}
.two {{ columns: 2; column-gap: 7mm; }}
.two h2, .two h3 {{ break-after: avoid; }}
.box {{ break-inside: avoid; }}
</style></head><body>

<!-- ===== COVER ===== -->
<section class="page cover">
  <svg class="ship" viewBox="0 0 400 260" xmlns="http://www.w3.org/2000/svg">
    <path d="M30 70 q20-25 40 0 q20-25 40 0" stroke="#cfe4f5" stroke-width="4" fill="none"/>
    <path d="M250 50 l-10 25 h12 l-12 28" stroke="#f2b705" stroke-width="5" fill="none"/>
    <line x1="200" y1="40" x2="200" y2="170" stroke="#3b2a1a" stroke-width="6"/>
    <path d="M200 50 L290 150 L200 150 Z" fill="#f4efe3"/>
    <path d="M196 60 L130 150 L196 150 Z" fill="#e8dfc9"/>
    <path d="M90 165 L310 165 L280 205 L120 205 Z" fill="#6b4423"/>
    <path d="M0 210 q25-20 50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 V260 H0 Z" fill="#7fb6de"/>
    <path d="M0 230 q25-20 50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 V260 H0 Z" fill="#2f6fa3"/>
  </svg>
  <h1>הים הולך וסוער</h1>
  <div class="sub">ספר יונה, פרק א</div>
  <div class="meta">משימת סיכום, ספר יונה, שכבה ט׳<br>
  <span style="color:#fff">הוכן על ידי: איתן ______ &nbsp;·&nbsp; כיתה ט׳__</span></div>
</section>

<!-- ===== EXPLANATION PAGE (שלב 3) ===== -->
<section class="page">
  <h1 style="font-size:20pt">דף הסבר</h1>
  <p><b>מגיש:</b> איתן ______ &nbsp;|&nbsp; <b>הסצנה:</b> הבריחה והסערה בים (פרק א) &nbsp;|&nbsp; <b>התוצר:</b> משחק קופסה</p>

  <h2>הפסוקים</h2>
  <div class="quote">״ויקם יונה לברח תרשישה מלפני ה׳ וירד יפו... וירד בה״ (א, ג)</div>
  <div class="quote">״ויונה ירד אל ירכתי הספינה וישכב וירדם״ (א, ה)</div>
  <div class="quote">״שאוני והטילני אל הים... כי יודע אני כי בשלי הסער הגדול הזה עליכם״ (א, יב)</div>

  <h2>מה למדתי</h2>
  <p>יונה כל הזמן "יורד": ליפו, לאונייה, לבטן הספינה, ובסוף נרדם. הוא בורח, אבל הסערה מגיעה אליו בכל מקרה. אי אפשר לברוח מאחריות.</p>
  <p>הים נרגע רק אחרי שיונה אומר "בשלי". כלומר, הפתרון מתחיל כשמודים בטעות.</p>
  <p>המלחים התנהגו יפה: הם ניסו לחתור ליבשה ולא רצו לזרוק את יונה. בגלל זה במשחק השחקנים הם המלחים, ומקבלים נקודות אם ניסו להציל את יונה לפני שזרקו אותו.</p>

  <h2>תהליך העבודה</h2>
  <p>עבדתי לבד. בחרתי בסצנת הסערה כי יש בה הרבה פעולה והחלטות קשות, ובחרתי במשחק קופסה כי רציתי שמי שמשחק ירגיש כמו המלחים. כשהמשחק היה מוכן, נתתי לאמא שלי לקרוא את ההוראות. היא לא הבינה אותן, בעיקר מה עושים עם העיגולים של המטען, החתירה והתפילה. אז כתבתי את ההוראות מחדש: הוספתי הסבר על כל חלק בלוח ועל כל עיגול, ודוגמה של סיבוב שלם. הדבר הכי קשה היה להסביר את המשחק כך שגם מי שלא מכיר אותו יבין.</p>
</section>

<!-- ===== RULES ===== -->
<section class="page rules">
  <h1 style="font-size:22pt">חוקי המשחק</h1>
  <p><b>מה המטרה?</b> כל השחקנים הם מלחים על האונייה של יונה, ומשחקים <b>יחד נגד הסערה</b>. אתם צריכים לזרוק את יונה לים לפני שהאונייה נשברת. כולם מנצחים יחד או מפסידים יחד.</p>

  <h2>מה יש על הלוח</h2>
  <ul>
  <li><b>מד הסדקים (0 עד 12):</b> מראה כמה האונייה נפגעה. מתחילים ב־0. אם מגיעים ל־12, האונייה נשברת והפסדתם.</li>
  <li><b>מסלול הסערה (1 עד 8):</b> סופר את הסיבובים. בכל סיבוב הסערה מתחזקת: במשבצות 3 ומעלה כל קלף סערה מוסיף עוד סדקים.</li>
  <li><b>טבלת הפעולות:</b> מה מותר לעשות בתור שלכם.</li>
  </ul>

  <h2>מה עושים עם העיגולים</h2>
  <ul>
  <li><b>📦 מטען (8 עיגולים):</b> כשמטילים כלים לים, מוציאים עיגול מטען אחד מהמשחק. כשהמטענים נגמרים, אי אפשר להטיל עוד כלים.</li>
  <li><b>🚣 חתירה:</b> כל פעם שמישהו חותר, הוא לוקח עיגול חתירה. החתירה לא מצילה את האונייה, אבל כל עיגול שווה נקודה בסוף.</li>
  <li><b>🙏 תפילה:</b> כשקוראים אל ה׳, לוקחים עיגול תפילה. בסוף זה שווה 2 נקודות.</li>
  <li><b>⚠️ סדקים ו־⛈️ סערה:</b> שני סמנים שמזיזים על הלוח, אחד על מד הסדקים ואחד על מסלול הסערה.</li>
  </ul>

  <h2>הכנה</h2>
  <ol>
  <li>כל שחקן לוקח קלף מלח אחד וקורא את הכוח המיוחד שלו. (בשני שחקנים: כל אחד לוקח שני מלחים ומשחק בשניהם.)</li>
  <li>שמים סמן על 0 במד הסדקים, וסמן על משבצת 1 במסלול הסערה.</li>
  <li>שמים את קלף יונה על "יונה ישן" ומניחים 8 מטענים ליד הלוח.</li>
  <li>מערבבים את קלפי הסערה ואת קלפי הדילמה ומניחים אותם הפוכים.</li>
  </ol>

  <h2>איך משחקים סיבוב</h2>
  <p><b>שלב 1: הסערה.</b> הופכים את קלף הסערה העליון. מקדמים את סמן הסדקים לפי המספר שעל הקלף, ועוד התוספת שכתובה במשבצת שבה נמצא סמן הסערה.</p>
  <p><b>שלב 2: המלחים.</b> כל שחקן, אחד אחרי השני, עושה <b>פעולה אחת</b> מהטבלה שעל הלוח. מותר להתייעץ לפני שבוחרים.</p>
  <p><b>שלב 3: הסערה מתקדמת.</b> מזיזים את סמן הסערה משבצת אחת קדימה ומתחילים סיבוב חדש.</p>

  <h2>הסדר של הסיפור</h2>
  <p>אי אפשר לזרוק את יונה מיד. צריך לעבור את השלבים לפי הסדר, כמו בפסוקים:</p>
  <p style="font-weight:bold; text-align:center">מטילים כלים וזועקים ← מעירים את יונה ← מפילים גורלות ← שואלים את יונה פעמיים ← יונה אומר "שאוני" ← זורקים את יונה</p>
  <p>כשיונה מתעורר, אחרי הגורל ואחרי "שאוני", הופכים את קלף יונה למצב הבא.</p>

  <h2>דוגמה</h2>
  <p>סמן הסערה על 3. הפכנו "גל ענק" (2 סדקים) ומשבצת 3 מוסיפה 1, אז מוסיפים 3 סדקים. אחר כך דני מטיל מטען (2 סדקים פחות), ורותי זועקת וזורקת 5 בקובייה (סדק אחד פחות).</p>

  <h2>סוף המשחק</h2>
  <p><b>ניצחון:</b> זרקתם את יונה לים. <b>הפסד:</b> הגעתם ל־12 סדקים, או שנגמר סיבוב 8 ויונה עדיין באונייה.</p>
  <p><b>ניקוד בונוס (אם ניצחתם):</b> כל חתירה: נקודה (עד 3). קראתם אל ה׳: 2 נקודות. כל דילמה: נקודה. זרקתם את יונה באותו סיבוב שבו אמר "שאוני": מורידים 2. אם הגעתם ל־6 ומעלה, אתם מלחים מצוינים!</p>
</section>
<!-- ===== BOARD ===== -->
<section class="page board">
  <h1>הים הולך וסוער</h1>
  <div class="sub">״והאניה חשבה להשבר״ (יונה א, ד)</div>

  <div class="boardsec"><h3>⚠️ מד הסדקים: בסדק 12 האונייה נשברת</h3><div class="cracks">{cracks_html}</div></div>

  <div class="boardsec"><h3>⛈️ מסלול הסערה: מזיזים בסוף כל סיבוב. התוספת נוספת לכל קלף סערה.</h3><div class="track">{track_html}</div></div>

  <div class="boardsec"><h3>⚓ פעולות המלחים: פעולה אחת לכל שחקן בכל סיבוב</h3>
  <table class="act"><tr><th>פעולה</th><th>מתי מותר</th><th>מה קורה</th></tr>{actions_html}</table></div>

  <div class="zones">
    <div class="zone">קלפי סערה<small>מערבבים ומניחים הפוך</small></div>
    <div class="zone">🧍 קלף יונה<small>ישן ← ער ← הגורל נפל ← ״שאוני״</small></div>
    <div class="zone">קלפי דילמה<small>״הגידה נא לנו...״ (א, ח)</small></div>
  </div>
  <div class="zones" style="margin-top:3mm">
    <div class="zone" style="height:24mm">📦 מטען (8)</div>
    <div class="zone" style="height:24mm">🚣 חתירה · 🙏 תפילה</div>
    <div class="zone" style="height:24mm">🗑️ קלפים שהשתמשו בהם</div>
  </div>
</section>

{cards_html}

</body></html>'''

open(OUT, "w").write(doc)
print("written", len(all_cards), "cards", len(pages), "card pages")
