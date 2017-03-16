#!/bin/bash -xe
if ! test -z $1
then
    AWS_PROFILE="--profile $1"
fi

aws cloudformation create-change-set --region ap-southeast-2 --stack-name vpc-ipv6-cfn --template-url https://s3-ap-southeast-2.amazonaws.com/vpc-ipv6-cfn-code-ap-southeast-2/template.yml --change-set-name deploy-ipv6-helper $AWS_PROFILE
aws cloudformation execute-change-set --region ap-southeast-2 --stack-name vpc-ipv6-cfn --change-set-name deploy-ipv6-helper $AWS_PROFILE || aws cloudformation --region ap-southeast-2 delete-change-set --stack-name vpc-ipv6-cfn --change-set-name deploy-ipv6-helper $AWS_PROFILE
aws cloudformation deploy --region ap-southeast-2  --template-file cftemplates/00-base.yaml --stack-name DockerMeetupBase --capabilities CAPABILITY_IAM --parameter-overrides  DNSHostedZone=aws.nkh.io $AWS_PROFILE || true
aws cloudformation describe-stacks --region ap-southeast-2 --stack-name DockerMeetupBase $AWS_PROFILE > DockerMeetupBaseDescribe.json
S3BUCKET=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("S3Bucket")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRALIEN=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRAlien")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRPSCORE=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRPscore")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRSCORES=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRScores")) | .OutputValue' DockerMeetupBaseDescribe.json)
ECRCREDITS=$(jq -r '.Stacks[] | .Outputs[] | select( .OutputKey | contains("ECRCredits")) | .OutputValue' DockerMeetupBaseDescribe.json)
rm -f DockerMeetupBaseDescribe.json
$(aws ecr get-login --region ap-southeast-2 $AWS_PROFILE)
cp -f containers/AlienInvasion/game-sans-ajax.js containers/AlienInvasion/game.js
docker build containers/AlienInvasion -t ${ECRALIEN}:sans
cp -f containers/AlienInvasion/game-with-ajax.js containers/AlienInvasion/game.js
docker build containers/AlienInvasion -t ${ECRALIEN}:ajax
rm -f containers/AlienInvasion/game.js
docker build containers/postscore -t ${ECRPSCORE}:latest
docker push ${ECRALIEN}:sans
docker push ${ECRALIEN}:ajax
docker push ${ECRPSCORE}:latest


