# app.py
# Flask app: invoices + QR + replace + delete + invoice/flight numbers

from flask import (
    Flask, request, send_from_directory, url_for,
    render_template_string, send_file, redirect
)
import os, uuid, io, zipfile, json
import qrcode

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'invoices')
QR_FOLDER = os.path.join(BASE_DIR, 'qr_codes')
DATA_FILE = os.path.join(BASE_DIR, 'data.json')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

# ---------- Languages ----------
LANG = {
    'ru': {
        'title': 'Инвойсы и QR-коды',
        'upload': 'Загрузить инвойс',
        'invoice_no': 'Номер инвойса',
        'flight_no': 'Номер рейса',
        'replace': 'Заменить PDF',
        'delete': 'Удалить',
        'download_zip': 'Скачать все QR-коды (ZIP)',
        'open_pdf': 'Открыть PDF',
        'table_title': 'Все инвойсы',
        'confirm': 'Вы уверены?'
    },
    'en': {
        'title': 'Invoices and QR Codes',
        'upload': 'Upload invoice',
        'invoice_no': 'Invoice No',
        'flight_no': 'Flight No',
        'replace': 'Replace PDF',
        'delete': 'Delete',
        'download_zip': 'Download all QR codes (ZIP)',
        'open_pdf': 'Open PDF',
        'table_title': 'All invoices',
        'confirm': 'Are you sure?'
    },
    'uz': {
        'title': 'Invoyslar va QR-kodlar',
        'upload': 'Invoys yuklash',
        'invoice_no': 'Invoys raqami',
        'flight_no': 'Reys raqami',
        'replace': 'PDF almashtirish',
        'delete': "O‘chirish",
        'download_zip': 'Barcha QR-kodlarni yuklash (ZIP)',
        'open_pdf': 'PDF ochish',
        'table_title': 'Barcha invoyslar',
        'confirm': 'Ishonchingiz komilmi?'
    }
}

# ---------- Helpers ----------
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ---------- HTML ----------
HTML = """
<!doctype html>
<html>
<head>
<meta charset="UTF-8">
<title>{{ t.title }}</title>
<style>
body{font-family:Arial;background:#f4f6f8}
.container{max-width:1200px;margin:40px auto;background:#fff;padding:30px;border-radius:10px}
button{padding:7px 12px;border:none;border-radius:6px;color:#fff;cursor:pointer}
.blue{background:#2563eb}
.green{background:#16a34a}
.red{background:#dc2626}
input[type=text]{padding:6px;width:180px}
select{padding:6px}
table{width:100%;border-collapse:collapse;margin-top:30px}
th,td{padding:10px;border-bottom:1px solid #ddd;text-align:center}
th{background:#f1f5f9}
.lang{float:right}
.actions form{display:inline-block;margin:2px}
</style>
</head>
<body>

<div class="container">

<div class="lang">
<form method="get">
<select name="lang" onchange="this.form.submit()">
<option value="ru" {% if lang=='ru' %}selected{% endif %}>RU</option>
<option value="en" {% if lang=='en' %}selected{% endif %}>EN</option>
<option value="uz" {% if lang=='uz' %}selected{% endif %}>UZ</option>
</select>
</form>
</div>

<h1>{{ t.title }}</h1>

<form method="post" enctype="multipart/form-data">
<input type="hidden" name="lang" value="{{ lang }}">

<input type="text" name="invoice_no" placeholder="{{ t.invoice_no }}" required>
<input type="text" name="flight_no" placeholder="{{ t.flight_no }}" required>

<input type="file" name="invoice" accept="application/pdf" required>
<button class="blue" type="submit">{{ t.upload }}</button>
</form>

<a href="/download-zip">
<button class="green" style="margin-top:15px">{{ t.download_zip }}</button>
</a>

<h2>{{ t.table_title }}</h2>

<table>
<tr>
<th>ID</th>
<th>{{ t.invoice_no }}</th>
<th>{{ t.flight_no }}</th>
<th>PDF</th>
<th>QR</th>
<th>Actions</th>
</tr>

{% for i in invoices %}
<tr>
<td>{{ i.id }}</td>
<td>{{ i.invoice_no }}</td>
<td>{{ i.flight_no }}</td>
<td><a href="{{ i.pdf }}" target="_blank">{{ t.open_pdf }}</a></td>
<td><img src="{{ i.qr }}" width="80"></td>
<td class="actions">

<form action="/replace/{{ i.id }}?lang={{ lang }}" method="post" enctype="multipart/form-data">
<input type="file" name="invoice" accept="application/pdf" required>
<button class="blue">{{ t.replace }}</button>
</form>

<form action="/delete/{{ i.id }}?lang={{ lang }}" method="post"
      onsubmit="return confirm('{{ t.confirm }}')">
<button class="red">{{ t.delete }}</button>
</form>

</td>
</tr>
{% endfor %}
</table>

</div>
</body>
</html>
"""

# ---------- Routes ----------
@app.route('/', methods=['GET', 'POST'])
def index():
    lang = request.values.get('lang', 'ru')
    t = LANG.get(lang, LANG['ru'])
    data = load_data()

    if request.method == 'POST':
        file = request.files.get('invoice')
        invoice_no = request.form.get('invoice_no')
        flight_no = request.form.get('flight_no')

        if file and file.filename.lower().endswith('.pdf'):
            uid = str(uuid.uuid4())[:8]

            file.save(os.path.join(UPLOAD_FOLDER, f"{uid}.pdf"))

            pdf_url = url_for('invoice', filename=f"{uid}.pdf", _external=True)
            qr_img = qrcode.make(pdf_url)
            qr_img.save(os.path.join(QR_FOLDER, f"{uid}.png"))

            data.append({
                'id': uid,
                'invoice_no': invoice_no,
                'flight_no': flight_no,
                'pdf': pdf_url,
                'qr': url_for('qr', filename=f"{uid}.png")
            })
            save_data(data)

        return redirect(url_for('index', lang=lang))

    return render_template_string(HTML, invoices=data, t=t, lang=lang)


@app.route('/replace/<invoice_id>', methods=['POST'])
def replace_invoice(invoice_id):
    lang = request.args.get('lang', 'ru')
    file = request.files.get('invoice')

    if file and file.filename.lower().endswith('.pdf'):
        file.save(os.path.join(UPLOAD_FOLDER, f"{invoice_id}.pdf"))

    return redirect(url_for('index', lang=lang))


@app.route('/delete/<invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    lang = request.args.get('lang', 'ru')
    data = load_data()

    for ext, folder in [('pdf', UPLOAD_FOLDER), ('png', QR_FOLDER)]:
        path = os.path.join(folder, f"{invoice_id}.{ext}")
        if os.path.exists(path):
            os.remove(path)

    data = [i for i in data if i['id'] != invoice_id]
    save_data(data)

    return redirect(url_for('index', lang=lang))


@app.route('/invoices/<filename>')
def invoice(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/qr/<filename>')
def qr(filename):
    return send_from_directory(QR_FOLDER, filename)


@app.route('/download-zip')
def download_zip():
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, 'w') as z:
        for f in os.listdir(QR_FOLDER):
            z.write(os.path.join(QR_FOLDER, f), f)
    memory.seek(0)
    return send_file(memory, as_attachment=True, download_name='qr_codes.zip')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)
