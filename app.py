
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import os
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'secretkey'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return redirect('/upload-key')

@app.route('/upload-key', methods=['GET', 'POST'])
def upload_key():
    if request.method == 'POST':
        key = request.form['answer_key'].strip().upper().replace(" ", "").replace("\n", "")
        session['answer_key'] = list(key)
        return redirect('/upload-omr')
    return render_template('upload_key.html')

@app.route('/upload-omr', methods=['GET', 'POST'])
def upload_omr():
    if 'answer_key' not in session:
        return redirect('/upload-key')

    if request.method == 'POST':
        files = request.files.getlist('omr_files')
        results = []
        for file in files:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            result = evaluate_omr(filepath, session['answer_key'])
            results.append(result)

        # Rank students
        results.sort(key=lambda x: x['score'], reverse=True)
        for i, r in enumerate(results):
            r['rank'] = i + 1

        session['results'] = results
        return render_template('result.html', results=results)
    return render_template('upload_omr.html')

def evaluate_omr(image_path, answer_key):
    image = Image.open(image_path)
    name = pytesseract.image_to_string(image.crop((50, 50, 400, 100))).strip()
    detected = "BADCBDACBD"  # simulate 10 answers
    correct = answer_key[:len(detected)]
    wrongs = [i+1 for i in range(len(detected)) if detected[i] != correct[i]]
    score = sum([1 for i in range(len(detected)) if detected[i] == correct[i]])
    return {
        'name': name if name else 'Unknown',
        'file': os.path.basename(image_path),
        'score': score,
        'wrong': wrongs
    }

@app.route('/download-pdf')
def download_pdf():
    results = session.get('results', [])
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="OMR Result Report", ln=True, align='C')
    for res in results:
        wrong_q = ', '.join(map(str, res['wrong']))
        pdf.cell(200, 10, txt=f"{res['name']} | Score: {res['score']} | Rank: {res['rank']} | Wrong: {wrong_q}", ln=True)
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], "results.pdf")
    pdf.output(pdf_path)
    return send_file(pdf_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
