from flask import Flask
import boto3

app = Flask(__name__)

@app.route('/')
def healthcheck():
    return 'This host is healthy!', 200

@app.route('/pscore', methods=['POST'])
def pscore():
    return 'Test'

