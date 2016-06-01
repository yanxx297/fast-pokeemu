#!/bin/bash
#Usage: ./aggreg_test_case.sh <path/to/testcase/dir/>
TCLIST=""
PATH=$1
cd $PATH
for dir in */ ;
do
	#echo $dir
	TCPATH=$PATH$dir"testcase"
	if [[ $TCLIST == "" ]]; then 
		TCLIST=$TCPATH
	else 
		TCLIST=$TCLIST","$TCPATH
	fi
done
echo $TCLIST
