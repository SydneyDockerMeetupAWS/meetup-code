#!/bin/bash -xe
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ZIPNAME=lambda.zip
cd $DIR

# Update the Submodules
git submodule init
git submodule update
mkdir -p compile
rm -fdr compile/*
cp -r lambda.py compile/
cp -r modules/boto3/boto3 compile/
cp -r modules/botocore/botocore compile/
cp -r modules/ask-alexa-pykit/ask compile/
cd compile
python -m compileall -f .
zip -9r $ZIPNAME *
mv $ZIPNAME $DIR/
cd $DIR
rm -fdr compile/
