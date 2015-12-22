#!/bin/bash
#./print_testcase.sh <root dir>
cd $1
for FILENAME in *
do
	cd $FILENAME        
	EXEC="testcase"
	PATH=$(pwd)"/"$EXEC
	#echo "testcase-"$FILENAME
	#echo "zcat "$PATH
	zcat $PATH
	cd ..
done
