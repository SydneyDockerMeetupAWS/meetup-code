#!/bin/bash -e
if ! test -z $1
then
    AWS_PROFILE="--profile $1"
fi
if test -e fullkey.pub
then
     grep -v "PUBLIC KEY" fullkey.pub > key.pub
fi
if ! test -e key.pub
then
    echo 'Generatoring public key as file key.pub does not exist, key will be found under "key.pem"...'
    if ! test -e key.pem
    then
        openssl genrsa -out key.pem 2048
    fi
    openssl rsa -in key.pem -pubout > fullkey.pub
    grep -v "PUBLIC KEY" fullkey.pub > key.pub
fi
echo 'Getting and deploying VPC IPv6 helper template...'
wget https://s3-ap-southeast-2.amazonaws.com/vpc-ipv6-cfn-code-ap-southeast-2/template.yml
aws cloudformation deploy --region ap-southeast-2 --template-file template.yml --stack-name vpc-ipv6-cfn --capabilities CAPABILITY_IAM $AWS_PROFILE || true
aws cloudformation deploy --region ap-southeast-1 --template-file template.yml --stack-name vpc-ipv6-cfn --capabilities CAPABILITY_IAM $AWS_PROFILE || true
rm -f template.yml

echo 'Deploying base infrastructure template...'
echo 'NOTE: You may receive approval emails for certificates, please approve to allow CFN to complete'
aws cloudformation deploy --region ap-southeast-2 --template-file cftemplates/00-base.yaml --stack-name DockerMeetupBase --capabilities CAPABILITY_IAM --parameter-overrides  DNSHostedZone=aws.nkh.io ValidationDomain=nkh.io KeyPayload="$(cat key.pub | tr -d '\n')" $AWS_PROFILE || true
aws cloudformation deploy --region ap-southeast-1 --template-file cftemplates/00-base.yaml --stack-name DockerMeetupBase2 --capabilities CAPABILITY_IAM --parameter-overrides DNSHostedZone=aws2.nkh.io ValidationDomain=nkh.io EnvironmentName=DockerMeetup2 KeyPayload="$(cat key.pub | tr -d '\n')" $AWS_PROFILE || true

echo 'Preparing build environment...'
aws cloudformation describe-stacks --region ap-southeast-2 --stack-name DockerMeetupBase $AWS_PROFILE > DockerMeetupBaseDescribe.json
aws cloudformation describe-stacks --region ap-southeast-1 --stack-name DockerMeetupBase2 $AWS_PROFILE > DockerMeetupBase2Describe.json
S3BUCKET=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("S3Bucket")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRALIEN=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRAlien")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRPSCORE=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRPscore")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRSCORES=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRScores")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRCREDITS=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRCredits")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRREDIRECT=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRRedirect")) | .OutputValue' DockerMeetupBaseDescribe.json)
S3BUCKET2=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("S3Bucket")) | .OutputValue' DockerMeetupBase2Describe.json)
ECRALIEN2=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRAlien")) | .OutputValue' DockerMeetupBase2Describe.json)
ECRPSCORE2=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRPscore")) | .OutputValue' DockerMeetupBase2Describe.json)
ECRSCORES2=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRScores")) | .OutputValue' DockerMeetupBase2Describe.json)
ECRCREDITS2=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRCredits")) | .OutputValue' DockerMeetupBase2Describe.json)
ECRREDIRECT2=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRRedirect")) | .OutputValue' DockerMeetupBase2Describe.json)
rm -f DockerMeetupBaseDescribe.json
rm -f DockerMeetupBase2Describe.json

echo 'Building containers...'
cp -f containers/AlienInvasion/game-sans-ajax.js containers/AlienInvasion/game.js
docker build containers/AlienInvasion -t ${ECRALIEN}:sans
docker tag ${ECRALIEN}:sans ${ECRALIEN2}:sans
cp -f containers/AlienInvasion/game-with-ajax.js containers/AlienInvasion/game.js
docker build containers/AlienInvasion -t ${ECRALIEN}:ajax
docker tag ${ECRALIEN}:ajax ${ECRALIEN2}:ajax
rm -f containers/AlienInvasion/game.js
docker build containers/postscore -t ${ECRPSCORE}:latest
docker tag ${ECRPSCORE}:latest ${ECRPSCORE2}:latest
docker build containers/redirect -t ${ECRREDIRECT}:latest
docker tag ${ECRREDIRECT}:latest ${ECRREDIRECT2}:latest
docker build containers/scoreboard -t ${ECRSCORES}:latest
docker tag ${ECRSCORES}:latest ${ECRSCORES2}:latest

echo 'Pushing Containers...'
$(aws ecr get-login --region ap-southeast-2 $AWS_PROFILE)
docker push ${ECRALIEN}:sans
docker push ${ECRALIEN}:ajax
docker push ${ECRPSCORE}:latest
docker push ${ECRREDIRECT}:latest
docker push ${ECRSCORES}:latest
$(aws ecr get-login --region ap-southeast-1 $AWS_PROFILE)
docker push ${ECRALIEN2}:sans
docker push ${ECRALIEN2}:ajax
docker push ${ECRPSCORE2}:latest
docker push ${ECRREDIRECT2}:latest
docker push ${ECRSCORES2}:latest

echo 'Pushing files to S3..'
aws s3 cp cftemplates/02-deployinfra.yaml s3://${S3BUCKET}/02-deployinfra.yaml --region ap-southeast-2 $AWS_PROFILE
aws s3 cp cftemplates/02-deployinfra.yaml s3://${S3BUCKET2}/02-deployinfra.yaml --region ap-southeast-1 $AWS_PROFILE
aws s3 cp cftemplates/03-addscores.yaml s3://${S3BUCKET}/03-addscores.yaml --region ap-southeast-2 $AWS_PROFILE
aws s3 cp cftemplates/03-addscores.yaml s3://${S3BUCKET2}/03-addscores.yaml --region ap-southeast-1 $AWS_PROFILE
aws s3 cp cftemplates/04-addboard.yaml s3://${S3BUCKET}/04-addboard.yaml --region ap-southeast-2 $AWS_PROFILE
aws s3 cp cftemplates/04-addboard.yaml s3://${S3BUCKET2}/04-addboard.yaml --region ap-southeast-1 $AWS_PROFILE
