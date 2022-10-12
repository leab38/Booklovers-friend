from flask import Flask, render_template,request

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/form')
def form():
    return render_template('index.html')

@app.route('/data/', methods = ['POST','GET'])
def data():
    if request.method == 'GET':
        return f"You are trying to access /data directly, try going to /form instead to submit form."
    if request.method == 'POST':
        form_data = request.form
        return render_template('data.html',form_data = form_data)