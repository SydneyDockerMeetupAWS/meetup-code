from flask import Flask, request
from flask_cors import CORS
import boto3
import json
import re
import requests
import os
import uuid

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

def inInput(input, keys):
    for index, item in enumerate(keys):
        if item not in input:
            return False, item
    return True, None

def throwBadRequestError(message):
    return json.dumps({ 'Error' : '400 Bad Request: ' + message }), 400

def throwServiceUnavailableError(message):
    return json.dumps({ 'Error' : '503 Service Unavailable: ' + message}), 503

@app.route('/')
def healthcheck():
    return 'This host is healthy!', 200

@app.route('/pscore', methods=['POST'])
def pscore():
    # Attempt to get the JSON object
    try:
        input = request.get_json()
    except Exception as e:
        returnJSON =  {
                    'Error' : str(e)
                }
        return json.dumps(returnJSON), 400

    # Validate User Input - Fields
    inInputTest, missingField = inInput(input, ["Username","Score","Completed"])
    if not inInputTest:
        return throwBadRequestError('Missing field: \'%s\'' % missingField)

    # Validate User Input - Field Username
    if not re.match("^[a-zA-Z0-9]{3,10}$", str(input['Username'])):
        return throwBadRequestError('Field \'Username\' has invalid value \'%s\', should match regex \'^[a-zA-Z0-9]{3,10}$\'' % str(input['Username']))
    username = str(input['Username'])

    # Validate User Input - Field Score
    if isinstance(input['Score'], int):
        if input['Score'] < 0:
            return throwBadRequestError('Field \'Score\' has invalid value \'%d\', should be a positive integer' % input['Score'])
        score = input['Score']
    elif not str(input['Score']).isdigit():
        return throwBadRequestError('Field \'Score\' has invalid value \'%s\', should be a positive integer.' % str(input['Score']))
    else:
        score = int(input['Score'])

    # Validate User Input - Field Completed
    if input['Completed'] in (True, False):
        if input['Completed']:
            completed = True
        else:
            completed = False
    elif str(input['Completed']).lower() in ('true', 'yes', 'on'):
        completed = True
    elif str(input['Completed']).lower() in ('false', 'no', 'off'):
        completed = False
    else:
        return throwBadRequestError('Field \'Completed\' has invalid value \'%s\', should be a boolean value: True | False' % str(input['Completed']))

    # Prepare Confirmation Message
    returnJSON = {
                'Id' : uuid.uuid4().hex,
                'Username' : username,
                'Score' : score,
                'Completed' : completed
            }

    # Attempt PutItem
    try:
        response = client.put_item(
                TableName=AWS_DYNAMODB_TABLE_NAME,
                Item={
                    'id'       : { 'S' : returnJSON['Id'] },
                    'username' : { 'S' : returnJSON['Username']},
                    'score' : { 'N' : str(returnJSON['Score'])},
                    'completed' : { 'BOOL' : returnJSON['Completed']}
                    },
                )
    except Exception as e:
        return throwServiceUnavailableError('Attempted to put item into DynamoDB, got the following error: %s' % str(e))

    return json.dumps(returnJSON), 200

