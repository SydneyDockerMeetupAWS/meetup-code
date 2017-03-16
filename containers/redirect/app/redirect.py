from flask import Flask, redirect, request

# Initialisation
app = Flask(__name__)

# Get the environment variables that aren't handled by Boto3 internally

@app.route('/')
def root():
    return redirect("https://%s/" % request.headers['Host'], code=302)

@app.route('/<path:path>')
def path(path):
    return redirect("https://%s/%s" % (request.headers['Host'], path), code=302)


