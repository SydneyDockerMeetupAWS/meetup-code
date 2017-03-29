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
STACK_NAME = os.getenv('STACK_NAME') or 'AlexaDeployedStack'
STACK_REGION = os.getenv('STACK_REGION') or 'ap-southeast-2'
STACK_ENVIRONNAME = os.getenv('STACK_ENVIRONNAME') or 'DockerMeetup'
SCORE_TABLE_NAME = os.getenv('SCORE_TABLE_NAME')
MAX_SCORE = os.getenv('MAX_SCORE')

dclient = boto3.client('dynamodb',DYNAMO_REGION)
sclient = boto3.client('dynamodb',STACK_REGION)
cclient = boto3.client('cloudformation',STACK_REGION)

# Max score is to filter results to help find second place.
if MAX_SCORE is not None and not MAX_SCORE.is_digit():
    MAX_SCORE = None

def dedupdict(l):
    return [dict(t) for t in set([tuple(d.items()) for d in l])]

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

def appenditems(response, u_scores):
    for index, item in enumerate(response['Items']):
        l_item = {}
        l_item['username'] = item['username']['S']
        l_item['score'] = int(item['score']['N'])
        l_item['escore'] = int(item['score']['N'])
        l_item['completed'] = item['completed']['BOOL']
        if item['completed']['BOOL']:
            l_item['escore'] += 1001
        if not MAX_SCORE or l_item['escore'] <= int(MAX_SCORE):
            u_scores.append(l_item)
    return u_scores

def getscores():
    if not SCORE_TABLE_NAME:
        return None

    response = sclient.scan(TableName=SCORE_TABLE_NAME)

    u_scores = appenditems(response,[])

    while('LastEvaluatedKey' in response):
        response = sclient.scan(TableName=SCORE_TABLE_NAME, ExclusiveStartKey=response['LastEvaluatedKey'])
        u_scores = appenditems(response,u_scores)

    # dedup as well so that multiple entries of same score result in one value
    scores = sorted(dedupdict(u_scores), key=itemgetter('escore'), reverse=True)
    return scores

def topscores():
    scores = getscores()
    if not scores:
        return None

    h_scores = []
    h_score = scores.pop(0)
    h_scores.append(h_score)
    while scores:
        c_score = scores.pop(0)
        if h_score['escore'] == c_score['escore']:
            h_scores.append(c_score)
        else:
            break

    return h_scores

@alexa.default
def default(request):
    ''' The default handler gets invoked if Alexa doesn't understand the request '''
    return alexa.respond(message="I'm sorry. I'm afraid I can't do that. Please try another request.", end_session=True)

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
        stackFilter = StackStatusFilter=['CREATE_COMPLETE','ROLLBACK_COMPLETE','UPDATE_COMPLETE','UPDATE_ROLLBACK_COMPLETE']
        response = cclient.list_stacks(StackStatusFilter=stackFilter)
        stacks = response['StackSummaries']
        while ('NextToken' in response):
            response = cclient.list_stacks(NextToken=response['NextToken'],StackStatusFilter=stackFilter)
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

@alexa.intent("YesIntent")
def affirmative(request):
    return confirm(request)

@alexa.intent("AMAZON.YesIntent")
def confirm_request(request):
    return confirm(request)

@alexa.intent("DeployBase")
def deploy_base(request):
    return deploy(request,TEMPLATE_PATH_BASE,"The Game")

@alexa.intent("DeployPscore")
def deploy_pscore(request):
    return deploy(request,TEMPLATE_PATH_PSCORE,"Score Submit Container")

@alexa.intent("DeployScores")
def deploy_scores(request):
    return deploy(request,TEMPLATE_PATH_SCORES,"High Scores Page")

@alexa.intent("DeployInfo")
def deploy_info(request):
    return deploy(request,TEMPLATE_PATH_INFO,"Info Page")

@alexa.intent("CheckScores")
def check_scores(request):
    scores = topscores()
    if not scores:
        return alexa.respond(message="There are no current top scores.", end_session=True)

    if len(scores) == 1:
        return alexa.respond(message="The winner is %s with a score of %d where they %s." % (scores[0]['username'], scores[0]['score'], 'survived' if scores[0]['completed'] else 'died'), end_session=True)

    names = 'and %s.' % scores[0]['username']
    for index, item in enumerate(scores):
        if not index == 0:
            names = '%s, ' % item['username'] + names
    message = 'There are multiple winners with a score of %d where they %s. Their names are %s' % (scores[0]['score'], 'survived' if scores[0]['completed'] else 'died', names)
    return alexa.respond(message=message, end_session=True)

@alexa.intent("AMAZON.NoIntent")
def deny(request):
    return alexa.respond(message="Goodbye!", end_session=True)

@alexa.intent("AMAZON.StopIntent")
def stop(request):
    return alexa.respond(message="Goodbye!", end_session=True)

@alexa.intent("AMAZON.CancelIntent")
def cancel(request):
    return alexa.respond(message="Goodbye!", end_session=True)
