
from flask import Flask, request, render_template_string, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  "word2number_v3.db")

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def database():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT NOT NULL,
            original TEXT NOT NULL,
            result TEXT NOT NULL,
            created TEXT NOT NULL
        )
    """)
    return con


def save_history(mode, original, result):
    con = database()
    con.execute(
        "INSERT INTO history(mode,original,result,created) VALUES(?,?,?,?)",
        (mode, original, result,
         datetime.now().strftime("%d %b %Y, %I:%M %p"))
    )
    con.commit()
    con.close()


def word_to_number(value):
    words = value.upper().split()

    if not words or any(
        not word.isascii() or not word.isalpha() for word in words
    ):
        raise ValueError("Enter English alphabets A-Z only.")

    lines = []
    for word in words:
        nums = [ord(char) - 64 for char in word]
        total = sum(nums)
        lines.append(f"{word}: {' + '.join(map(str, nums))} = {total}")

    grand_total = sum(
        ord(char) - 64 for word in words for char in word
    )
    if len(words) > 1:
        lines.append(f"\nGrand total = {grand_total}")

    return "\n".join(lines)


def number_to_word(value):
    if not value or not all(c.isdigit() or c.isspace() for c in value):
        raise ValueError("Enter numbers from 1 to 26.")

    # Space-separated numbers have one unambiguous interpretation.
    if " " in value.strip():
        parts = value.split()
        if any(
            not p.isdigit() or not 1 <= int(p) <= 26
            for p in parts
        ):
            raise ValueError("Every number must be from 1 to 26.")
        return ["".join(chr(int(p) + 64) for p in parts)]

    # Continuous digits can have several valid interpretations.
    if len(value) > 20:
        raise ValueError("Enter no more than 20 continuous digits.")

    answers = []

    def decode(pos, word):
        if len(answers) >= 100:
            return
        if pos == len(value):
            answers.append(word)
            return

        for size in (1, 2):
            part = value[pos:pos + size]
            if not part or part.startswith("0"):
                continue
            number = int(part)
            if 1 <= number <= 26:
                decode(pos + size, word + chr(number + 64))

    decode(0, "")

    if not answers:
        raise ValueError("No valid alphabet combination found.")

    return answers


def make_explanation(mode, value, results):
    if mode == "letters":
        lines = []
        for word in value.upper().split():
            nums = [ord(c) - 64 for c in word]
            lines.append(
                f"{word}\n"
                f"{' + '.join(map(str, nums))} = {sum(nums)}"
            )
        if len(lines) > 1:
            total = sum(
                ord(c) - 64 for c in value.upper() if c.isalpha()
            )
            lines.append(f"Overall total = {total}")
        return "\n\n".join(lines)

    if " " in value.strip():
        parts = value.split()
        letters = [chr(int(n) + 64) for n in parts]
        steps = [f"{n} → {ch}" for n, ch in zip(parts, letters)]
        return "\n".join(steps) + f"\n\nResult: {''.join(letters)}"

    lines = [
        "Split the digits into numbers from 1 to 26.",
        "Each valid number represents one alphabet.",
        "",
        "Possible combinations:"
    ]
    lines.extend(results[:10])
    if len(results) > 10:
        lines.append(f"... and more (up to 100 shown)")
    return "\n".join(lines)


HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Word2Number | A-Z Converter</title>
<style>
*{box-sizing:border-box}
body{
 margin:0;background:#0b1220;color:#e5edf9;
 font-family:Arial,sans-serif;font-size:14px
}
.wrap{max-width:850px;margin:14px auto;padding:0 14px}
header{
 display:flex;align-items:center;justify-content:space-between;
 margin-bottom:12px
}
.logo{font-size:20px;font-weight:bold;color:#60a5fa}
nav a{color:#cbd5e1;text-decoration:none;margin-left:15px}
nav a:hover{color:#60a5fa}
.card{
 background:#151f32;border:1px solid #2b3a52;
 border-radius:12px;padding:14px;margin-bottom:10px
}
h1{font-size:20px;margin:0 0 4px}
h2{font-size:15px;color:#93c5fd;margin:0 0 7px}
.sub{color:#9eacc3;font-size:12px;margin:0 0 12px}
label{display:block;color:#cbd5e1;font-weight:bold;margin-bottom:6px}
input{
 width:100%;padding:10px;border-radius:8px;
 border:1px solid #39465c;background:#0b1425;color:white;
 font-size:14px
}
input::placeholder{color:#718096}
.mode-options{
 display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px
}
.mode-card{
 display:flex;flex-direction:column;gap:5px;padding:11px;
 background:#0c1729;border:1px solid #34435e;border-radius:9px;
 cursor:pointer;transition:.15s
}
.mode-card:hover{border-color:#60a5fa;background:#172640}
.mode-card.active{border:2px solid #3478ed;background:#172b4b;padding:10px}
.mode-card input{display:none}
.mode-icon{font-size:18px;font-weight:bold;color:#60a5fa}
.mode-title{font-size:13px;font-weight:bold;color:#e5edf9}
.mode-desc{font-size:11px;color:#9eacc3}
button{
 background:#3478ed;border:0;border-radius:8px;color:white;
 padding:10px 16px;font-weight:bold;cursor:pointer;font-size:13px
}
button:hover{background:#2563d7}
.result{
 margin-top:10px;padding:10px;border-radius:8px;
 background:#0c1729;border:1px solid #34435e;color:#a5f3c5;
 white-space:pre-wrap;overflow-wrap:anywhere;
 font-family:Consolas,monospace;font-size:13px;line-height:1.55
}
.error{margin-top:10px;background:#351d29;color:#fca5a5;
 padding:9px;border-radius:7px}
.help{white-space:pre-wrap;overflow-wrap:anywhere;
 color:#d0d9e8;font-size:12px;line-height:1.55}
.az-grid{
 display:grid;grid-template-columns:repeat(13,minmax(0,1fr));gap:5px
}
.az-item{
 display:flex;flex-direction:column;align-items:center;
 justify-content:center;gap:2px;padding:5px 1px;
 background:#0c1729;border:1px solid #34435e;border-radius:6px
}
.az-item span{font-size:12px;color:#60a5fa;font-weight:bold}
.az-item strong{font-size:11px;color:#e5edf9}
table{width:100%;border-collapse:collapse;font-size:12px}
td,th{text-align:left;padding:8px 5px;border-bottom:1px solid #29364c;
 overflow-wrap:anywhere;vertical-align:top}
th{color:#93c5fd}
.small{color:#94a3b8;font-size:11px}
.danger{background:#b93848;padding:6px 9px;font-size:11px}
.danger:hover{background:#982e3d}
.inline{display:inline}
.search{margin-bottom:8px}
@media(max-width:520px){
 .wrap{margin:10px auto;padding:0 9px}
 .card{padding:11px}
 .logo{font-size:17px}
 .mode-options{gap:7px}
 .mode-card{padding:8px}
 .mode-card.active{padding:7px}
 .mode-title{font-size:12px}
 .mode-desc{font-size:10px}
 .az-grid{grid-template-columns:repeat(7,minmax(0,1fr))}
}
</style>
</head>
<body>
<div class="wrap">
<header>
 <div class="logo">A–Z | Word2Number</div>
 <nav><a href="/">Converter</a><a href="/history">History</a></nav>
</header>

{% if page == "home" %}
<div class="card">
 <h1>Word2Number Converter</h1>
 <p class="sub">Convert alphabets to numbers and numbers to alphabets.</p>

 <form method="post" action="/convert">
  <label>Conversion type</label>
  <div class="mode-options">
   <label class="mode-card {% if mode == 'letters' %}active{% endif %}">
    <input type="radio" name="mode" value="letters"
           {% if mode == 'letters' %}checked{% endif %}>
    <span class="mode-icon">A → 1</span>
    <span class="mode-title">Alphabet to Number</span>
    <span class="mode-desc">Convert words into numbers</span>
   </label>
   <label class="mode-card {% if mode == 'numbers' %}active{% endif %}">
    <input type="radio" name="mode" value="numbers"
           {% if mode == 'numbers' %}checked{% endif %}>
    <span class="mode-icon">1 → A</span>
    <span class="mode-title">Number to Alphabet</span>
    <span class="mode-desc">Convert numbers into letters</span>
   </label>
  </div>

  <label for="value">Enter word or number</label>
  <input id="value" name="value" value="{{ value }}"
         placeholder="Example: PRINCE or 161891435" required>
  <button type="submit">Convert →</button>
 </form>

 {% if error %}<div class="error">{{ error }}</div>{% endif %}
 {% if result %}
 <h2 style="margin-top:13px">Conversion result</h2>
 <div class="result">{{ result }}</div>
 {% endif %}
</div>

<div class="card">
 <h2>How it works</h2>
 <div class="help">{% if explanation %}{{ explanation }}{% else %}Enter a word or number and click Convert.
This section will explain your conversion here.{% endif %}</div>
</div>

<div class="card">
 <h2>A–Z Number Reference</h2>
 <p class="sub">Every alphabet and its assigned number.</p>
 <div class="az-grid">
 {% for i in range(1,27) %}
  <div class="az-item">
   <span>{{ "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[i-1] }}</span>
   <strong>{{ i }}</strong>
  </div>
 {% endfor %}
 </div>
</div>

{% else %}
<div class="card">
 <h1>Conversion History</h1>
 <p class="sub">Search and manage previous conversions.</p>
 <form method="get" action="/history">
  <input class="search" name="q" value="{{ query }}"
         placeholder="Search history">
  <button type="submit">Search</button>
 </form>

 {% if records %}
 <table>
  <tr><th>Type / Input</th><th>Result</th><th>Action</th></tr>
  {% for r in records %}
  <tr>
   <td>{{ r[1] }}<br>{{ r[2] }}<br>
    <span class="small">{{ r[4] }}</span>
   </td>
   <td>{{ r[3] }}</td>
   <td>
    <form class="inline" method="post" action="/delete/{{ r[0] }}">
     <button class="danger" type="submit">Delete</button>
    </form>
   </td>
  </tr>
  {% endfor %}
 </table>
 <form method="post" action="/clear" style="margin-top:12px"
       onsubmit="return confirm('Clear all history?')">
  <button class="danger" type="submit">Clear History</button>
 </form>
 {% else %}
 <p class="small">No history found.</p>
 {% endif %}
</div>
{% endif %}
</div>
<script>
document.querySelectorAll('.mode-card input').forEach(input=>{
 input.addEventListener('change',()=>{
  document.querySelectorAll('.mode-card').forEach(card=>{
   card.classList.toggle('active',card.querySelector('input').checked);
  });
 });
});
</script>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(
        HTML, page="home", mode="letters", value="",
        result="", error="", explanation=""
    )


@app.route("/convert", methods=["POST"])
def convert():
    mode = request.form.get("mode", "letters")
    value = request.form.get("value", "").strip()
    result = ""
    error = ""
    how = ""

    try:
        if mode == "letters":
            result = word_to_number(value)
            label = "Alphabet to Number"
            how = make_explanation(mode, value, result)
        elif mode == "numbers":
            answers = number_to_word(value)
            result = "\n".join(answers)
            label = "Number to Alphabet"
            how = make_explanation(mode, value, answers)
        else:
            raise ValueError("Select a valid conversion type.")

        save_history(label, value, result)
    except (ValueError, TypeError) as e:
        error = str(e)

    return render_template_string(
        HTML, page="home", mode=mode, value=value,
        result=result, error=error, explanation=how
    )


@app.route("/history")
def history():
    query = request.args.get("q", "").strip()
    con = database()
    if query:
        records = con.execute(
            """SELECT id,mode,original,result,created FROM history
            WHERE original LIKE ? OR result LIKE ?
            ORDER BY id DESC LIMIT 100""",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
    else:
        records = con.execute(
            "SELECT id,mode,original,result,created FROM history "
            "ORDER BY id DESC LIMIT 100"
        ).fetchall()
    con.close()
    return render_template_string(
        HTML, page="history", records=records, query=query
    )


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    con = database()
    con.execute("DELETE FROM history WHERE id=?", (item_id,))
    con.commit()
    con.close()
    return redirect(url_for("history"))


@app.route("/clear", methods=["POST"])
def clear():
    con = database()
    con.execute("DELETE FROM history")
    con.commit()
    con.close()
    return redirect(url_for("history"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)