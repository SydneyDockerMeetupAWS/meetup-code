import boto3
from ask import alexa
import os
from datetime import datetime, timedelta
from time import mktime as unixtime, sleep
from operator import itemgetter
import uuid

DYNAMO_TABLE = os.getenv('DYNAMO_TABLE') or "LambdaSessions"
DYNAMO_REGION = os.getenv('DYNAMO_REGION') or "us-east-1"
TEMPLATE_PATH_BASE = os.getenv('TEMPLATE_PATH_BASE')
TEMPLATE_PATH_PSCORE = os.getenv('TEMPLATE_PATH_PSCORE')
TEMPLATE_PATH_SCORES = os.getenv('TEMPLATE_PATH_SCORES')
TEMPLATE_PATH_INFO = os.getenv('TEMPLATE_PATH_INFO')
STACK_NAME = os.getenv('STACK_NAME') or 'LambdaDeployedStack'
STACK_REGION = os.getenv('STACK_REGION') or 'ap-southeast-2'
STACK_ENVIRONNAME = os.getenv('STACK_ENVIRONNAME') or 'DockerMeetup'

dclient = boto3.client('dynamodb',DYNAMO_REGION)
cclient = boto3.client('cloudformation',STACK_REGION)

def handler(request_obj, context={}):
    ''' All requests start here '''
    return alexa.route_request(request_obj)

def queryOnSessionKey(request,startkey=None):
    if startkey is None:
        return dclient.query(TableName=DYNAMO_TABLE,
                         ExpressionAttributeValues={
                            ':v1' : { 'S' : request.session_id() }
                         },
                         KeyConditionExpression='sessionId = :v1')

    return dclient.query(TableName=DYNAMO_TABLE,
                         ExpressionAttributeValues={
                            ':v1' : { 'S' : request.session_id() }
                         },
                         KeyConditionExpression='sessionId = :v1',
                         ExclusiveStartKey=startkey)

def deploy(request,path,msg):
    if path is None:
        return alexa.respond(message="Could not prepare the deployment request to create the %s" % msg, end_session=True)
    response = dclient.put_item(TableName=DYNAMO_TABLE,
                                Item={
                                    'sessionId' : { 'S' : request.session_id() },
                                    'templatePath' : { 'S' : path },
                                    'message' : { 'S' : msg },
                                    'time' : { 'N' : str(int(unixtime(datetime.now().timetuple()))) },
                                    'expires' : { 'N' : '3600' }
                                })
    return alexa.respond(message="Please confirm you would like to deploy the %s" % msg)

@alexa.default
def default(request):
    ''' The default handler gets invoked if Alexa doesn't understand the request '''
    return alexa.respond(message="I'm sorry. I'm afraid I can't do that. Please try another request.", end_session=True)

@alexa.intent("YesIntent")
def affirmative(request):
    return confirm(request)

@alexa.intent("AMAZON.YesIntent")
def confirm(request):
    ''' This handler will confirm requests and execute them '''
    response = queryOnSessionKey(request)
    if response['Count'] == 0:
        return alexa.respond(message="I am not sure what you would like to do.", end_session=True)

    r_items = response['Items']
    while ('LastEvaluatedKey' in response):
        response = queryOnSessionKey(request, response['LastEvaluatedKey'])
        r_items += response['Items']

    p_items = []
    for index, item in enumerate(r_items):
        n_item = {}
        n_item['templatePath'] = item['templatePath']['S']
        n_item['message'] = item['message']['S']
        n_item['time'] = int(item['time']['N'])
        p_items.append(n_item)

    s_items = sorted(p_items, key=itemgetter('time'), reverse=True)

    s_request = s_items[0]

    try:
        response = cclient.list_stacks()
        stacks = response['StackSummaries']
        while ('NextToken' in response):
            response = cclient.list_stacks(NextToken=response['NextToken'])
            stacks += response['StackSummaries']

        found = False
        for index, item in enumerate(stacks):
            if item['StackName'] == STACK_NAME:
                found = True
        if found:
            response = cclient.update_stack(StackName=STACK_NAME,
                                 TemplateURL=s_request['templatePath'],
                                 Parameters=[
                                    {
                                        'ParameterKey' : 'EnvironmentName',
                                        'ParameterValue' : STACK_ENVIRONNAME
                                    }
                                 ],
                                 Capabilities=['CAPABILITY_IAM'])
        else:
            response = cclient.create_stack(StackName=STACK_NAME,
                                 TemplateURL=s_request['templatePath'],
                                 Parameters=[
                                    {
                                        'ParameterKey' : 'EnvironmentName',
                                        'ParameterValue' : STACK_ENVIRONNAME
                                    }
                                 ],
                                 Capabilities=['CAPABILITY_IAM'])
    except Exception as e:
        print str(e)
        return alexa.respond(message="I was unable to complete creating the %s" % s_request['message'], end_session=True)
    return alexa.respond(message="I am creating the %s" % s_request['message'], end_session=True)

@alexa.intent("DeployBase")
def deploy_base(request):
    return deploy(request,TEMPLATE_PATH_BASE,"Base Infrastructure")

@alexa.intent("DeployPscore")
def deploy_pscore(request):
    return deploy(request,TEMPLATE_PATH_PSCORE,"Score Request Container")

@alexa.intent("DeployScores")
def deploy_scores(request):
    return deploy(request,TEMPLATE_PATH_SCORES,"High Scores Container")

@alexa.intent("DeployInfo")
def deploy_info(request):
    return deploy(request,TEMPLATE_PATH_INFO,"Info Scores Container")

@alexa.intent("AMAZON.NoIntent")
def deny(request):
    return alexa.respond(message="Goodbye!", end_session=True)

@alexa.intent("AMAZON.StopIntent")
def stop(request):
    return deny(request)

@alexa.intent("AMAZON.CancelIntent")
def cancel(request):
    return deny(request)
