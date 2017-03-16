#!/bin/bash -xe
if ! test -z $1
then
    AWS_PROFILE="--profile $1"
fi
wget https://s3-ap-southeast-2.amazonaws.com/vpc-ipv6-cfn-code-ap-southeast-2/template.yml
aws cloudformation deploy --region ap-southeast-2 --template-file template.yml --stack-name vpc-ipv6-cfn --capabilities CAPABILITY_IAM $AWS_PROFILE || true
aws cloudformation deploy --region ap-southeast-1 --template-file template.yml --stack-name vpc-ipv6-cfn --capabilities CAPABILITY_IAM $AWS_PROFILE || true
rm -f template.yml
aws cloudformation deploy --region ap-southeast-2 --template-file cftemplates/00-base.yaml --stack-name DockerMeetupBase --capabilities CAPABILITY_IAM --parameter-overrides  DNSHostedZone=aws.nkh.io ValidationDomain=nkh.io KeyPayload="$(cat key.pub | tr -d '\n')" $AWS_PROFILE || true
aws cloudformation deploy --region ap-southeast-1 --template-file cftemplates/00-base.yaml --stack-name DockerMeetupBase2 --capabilities CAPABILITY_IAM --parameter-overrides DNSHostedZone=aws2.nkh.io ValidationDomain=nkh.io EnvironmentName=DockerMeetup2 KeyPayload="$(cat key.pub | tr -d '\n')" $AWS_PROFILE || true
aws cloudformation describe-stacks --region ap-southeast-2 --stack-name DockerMeetupBase $AWS_PROFILE > DockerMeetupBaseDescribe.json
aws cloudformation describe-stacks --region ap-southeast-1 --stack-name DockerMeetupBase2 $AWS_PROFILE > DockerMeetupBase2Describe.json
S3BUCKET=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("S3Bucket")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRALIEN=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRAlien")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRPSCORE=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRPscore")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRSCORES=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRScores")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRCREDITS=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRCredits")) | .OutputValue' DockerMeetupBaseDescribe.json)
S3BUCKET2=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("S3Bucket")) | .OutputValue' DockerMeetupBase2Describe.json)
ECRALIEN2=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRAlien")) | .OutputValue' DockerMeetupBase2Describe.json)
ECRPSCORE2=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRPscore")) | .OutputValue' DockerMeetupBase2Describe.json)
ECRSCORES2=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRScores")) | .OutputValue' DockerMeetupBase2Describe.json)
ECRCREDITS2=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRCredits")) | .OutputValue' DockerMeetupBase2Describe.json)
rm -f DockerMeetupBaseDescribe.json
rm -f DockerMeetupBase2Describe.json
cp -f containers/AlienInvasion/game-sans-ajax.js containers/AlienInvasion/game.js
docker build containers/AlienInvasion -t ${ECRALIEN}:sans
docker tag ${ECRALIEN}:sans ${ECRALIEN2}:sans
cp -f containers/AlienInvasion/game-with-ajax.js containers/AlienInvasion/game.js
docker build containers/AlienInvasion -t ${ECRALIEN}:ajax
docker tag ${ECRALIEN}:ajax ${ECRALIEN2}:ajax
rm -f containers/AlienInvasion/game.js
docker build containers/postscore -t ${ECRPSCORE}:latest
docker tag ${ECRPSCORE}:latest ${ECRPSCORE2}:latest
$(aws ecr get-login --region ap-southeast-2 $AWS_PROFILE)
docker push ${ECRALIEN}:sans
docker push ${ECRALIEN}:ajax
docker push ${ECRPSCORE}:latest
$(aws ecr get-login --region ap-southeast-1 $AWS_PROFILE)
docker push ${ECRALIEN2}:sans
docker push ${ECRALIEN2}:ajax
docker push ${ECRPSCORE2}:latest

aws s3 cp cftemplates/02-deployinfra.yaml s3://${S3BUCKET}/02-deployinfra.yaml --region ap-southeast-2 $AWS_PROFILE
aws s3 cp cftemplates/02-deployinfra.yaml s3://${S3BUCKET2}/02-deployinfra.yaml --region ap-southeast-1 $AWS_PROFILE
