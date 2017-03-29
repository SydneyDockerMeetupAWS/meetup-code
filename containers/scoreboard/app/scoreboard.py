from flask import Flask, render_template
from flask_cors import CORS
import requests
import boto3
import os
import uuid
from datetime import datetime, timedelta
from operator import itemgetter
import time

# Initialisation
app = Flask(__name__)

# Get the environment variables that aren't handled by Boto3 internally

# Enable CORS
ENABLE_CORS = os.environ.get('ENABLE_CORS')
if ENABLE_CORS is not None and ENABLE_CORS.lower() in ('true', 'yes', 'on'):
    CORS(app)

# Region
AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION')
if AWS_DEFAULT_REGION is None:
    try:
        r = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document',timeout=5)
        AWS_DEFAULT_REGION = r.json()['region']
    except Exception as e:
        AWS_DEFAULT_REGION = 'us-east-1'

# Table Name
AWS_DYNAMODB_TABLE_NAME = os.environ.get('AWS_DYNAMODB_TABLE_NAME')
if AWS_DYNAMODB_TABLE_NAME is None:
    raise ValueError('AWS_DYNAMODB_TABLE_NAME was not set')

# Create client
client = boto3.client('dynamodb',AWS_DEFAULT_REGION)

def appenditems(response, u_scores):
    for index, item in enumerate(response['Items']):
        l_item = {}
        l_item['username'] = item['username']['S']
        l_item['score'] = int(item['score']['N'])
        l_item['escore'] = int(item['score']['N'])
        l_item['completed'] = item['completed']['BOOL']
        if item['completed']['BOOL']:
            l_item['escore'] += 1001
        u_scores.append(l_item)
    return u_scores

def getscores():
    global g_scores
    global g_lock
    sec3 = timedelta(seconds=5)
    now = datetime.now()
    token = uuid.uuid4().hex
    if not 'g_scores' in globals() or (now - g_scores['updated']) > sec3:
        # We have determined that the scores need to be updated, let us try to acquire the lock
        if not 'g_lock' in globals() or g_lock is None:
            # We can get the lock
            g_lock = token
            time.sleep(0.05)
            if g_lock == token:
                # We have the lock
                # Make the API call
                response = client.scan(TableName=AWS_DYNAMODB_TABLE_NAME)

                l_scores = {}
                l_scores['updated'] = datetime.now()
                u_scores = appenditems(response,[])

                while('LastEvaluatedKey' in response):
                    response = client.scan(TableName=AWS_DYNAMODB_TABLE_NAME, ExclusiveStartKey=response['LastEvaluatedKey'])
                    u_scores = appenditems(response,u_scores)

                l_scores['scores'] = sorted(u_scores, key=itemgetter('escore'), reverse=True)
                # We're done
                g_scores = l_scores
                g_lock = None

    while(not 'g_scores' in globals()):
        # We need to wait for the object to exist before continuing
        time.sleep(0.1)

    # This will return the pointer to g_scores to be accessed
    return g_scores['scores']

@app.route('/')
def healthcheck():
    return 'This host is healthy!', 200

@app.route('/scores')
def scores():
    return render_template('scores.html',scores=getscores()[:20])

