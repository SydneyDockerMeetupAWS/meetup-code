from flask import Flask, render_template

# Initialisation
app = Flask(__name__)

@app.route('/')
def healthcheck():
    return 'This host is healthy!', 200

@app.route('/info')
def scores():
    return render_template('info.html')

