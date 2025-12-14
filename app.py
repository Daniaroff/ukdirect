# app.py
# Flask app: invoices + flights folders + QR + replace + delete + ZIP QR only

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
        'filter': 'Фильтр по рейсу',
        'all': 'Все рейсы',
        'replace': 'Заменить PDF',
        'delete': 'Удалить',
        'open_pdf': 'Открыть PDF',
        'download_zip': 'Скачать все QR-коды (ZIP)',
        'confirm': 'Вы уверены?'
    },
    'en': {
        'title': 'Invoices and QR Codes',
        'upload': 'Upload invoice',
        'invoice_no': 'Invoice No',
        'flight_no': 'Flight No',
        'filter': 'Filter by flight',
        'all': 'All flights',
        'replace': 'Replace PDF',
        'delete': 'Delete',
        'open_pdf': 'Open PDF',
        'download_zip': 'Download all QR codes (ZIP)',
        'confirm': 'Are you sure?'
    },
    'uz': {
        'title': 'Invoyslar va QR-kodlar',
        'upload': 'Invoys yuklash',
        'invoice_no': 'Invoys raqami',
        'flight_no': 'Reys raqami',
        'filter': 'Reys bo‘yicha filter',
        'all': 'Barcha reyslar',
        'replace': 'PDF almashtirish',
        'delete': "O‘chirish",
        'open_pdf': 'PDF ochish',
        'download_zip': 'Barcha QR-kodlarni yuklash (ZIP)',
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
button{padding:6px 12px;border:none;border-radius:6px;color:#fff;cursor:pointer}
.blue{background:#2563eb}
.green{background:#16a34a}
.red{background:#dc2626}
input,select{padding:6px;margin:4px}
table{width:100%;border-collapse:collapse;margin-top:20px}
th,td{padding:10px;border-bottom:1px solid #ddd;text-align:center}
th{background:#f1f5f9}
.actions form{display:inline-block}
.lang{float:right}
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

<!-- Фильтр по рейсу -->
<form method="get">
<label>{{ t.filter }}:</label>
<select name="flight" onchange="this.form.submit()">
<option value="">{{ t.all }}</option>
{% for f in flights %}
<option value="{{ f }}" {% if f==current_flight %}selected{% endif %}>{{ f }}</option>
{% endfor %}
</select>
<input type="hidden" name="lang" value="{{ lang }}">
</form>

<!-- Загрузка инвойса -->
<form method="post" enctype="multipart/form-data">
<input type="hidden" name="lang" value="{{ lang }}">
<input type="text" name="invoice_no" placeholder="{{ t.invoice_no }}" required>
<input type="text" name="flight_no" placeholder="{{ t.flight_no }}" required>
<input type="file" name="invoice" accept="application/pdf" required>
<button class="blue">{{ t.upload }}</button>
</form>

<!-- Скачать все QR-коды -->
<a href="/download-zip">
<button class="green">{{ t.download_zip }}</button>
</a>

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
<td><img src="{{ i.qr }}" width="70"></td>
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
        invoice_no = request.form['invoice_no']
        flight_no = request.form['flight_no']
        file = request.files['invoice']

        uid = str(uuid.uuid4())[:8]

        flight_dir = os.path.join(UPLOAD_FOLDER, flight_no)
        os.makedirs(flight_dir, exist_ok=True)

        pdf_path = os.path.join(flight_dir, f"{uid}.pdf")
        file.save(pdf_path)

        pdf_url = url_for('invoice', flight=flight_no, filename=f"{uid}.pdf", _external=True)
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

    current_flight = request.args.get('flight')
    flights = sorted(set(i['flight_no'] for i in data))

    if current_flight:
        data = [i for i in data if i['flight_no'] == current_flight]

    return render_template_string(
        HTML,
        invoices=data,
        flights=flights,
        current_flight=current_flight,
        t=t,
        lang=lang
    )

@app.route('/invoices/<flight>/<filename>')
def invoice(flight, filename):
    return send_from_directory(os.path.join(UPLOAD_FOLDER, flight), filename)

@app.route('/qr/<filename>')
def qr(filename):
    return send_from_directory(QR_FOLDER, filename)

@app.route('/replace/<invoice_id>', methods=['POST'])
def replace_invoice(invoice_id):
    lang = request.args.get('lang', 'ru')
    data = load_data()

    for i in data:
        if i['id'] == invoice_id:
            flight = i['flight_no']
            path = os.path.join(UPLOAD_FOLDER, flight, f"{invoice_id}.pdf")
            request.files['invoice'].save(path)
            break

    return redirect(url_for('index', lang=lang))

@app.route('/delete/<invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    lang = request.args.get('lang', 'ru')
    data = load_data()

    for i in data:
        if i['id'] == invoice_id:
            flight = i['flight_no']
            pdf = os.path.join(UPLOAD_FOLDER, flight, f"{invoice_id}.pdf")
            qr = os.path.join(QR_FOLDER, f"{invoice_id}.png")

            if os.path.exists(pdf):
                os.remove(pdf)
            if os.path.exists(qr):
                os.remove(qr)

            flight_dir = os.path.join(UPLOAD_FOLDER, flight)
            if os.path.isdir(flight_dir) and not os.listdir(flight_dir):
                os.rmdir(flight_dir)

    data = [i for i in data if i['id'] != invoice_id]
    save_data(data)

    return redirect(url_for('index', lang=lang))

# ---------- ZIP только с QR ----------
@app.route('/download-zip')
def download_zip():
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in os.listdir(QR_FOLDER):
            if f.lower().endswith('.png'):
                z.write(os.path.join(QR_FOLDER, f), f)
    memory.seek(0)
    return send_file(
        memory,
        as_attachment=True,
        download_name='qr_codes.zip',
        mimetype='application/zip'
    )

if __name__ == '__main__':
    app.run(debug=False)
