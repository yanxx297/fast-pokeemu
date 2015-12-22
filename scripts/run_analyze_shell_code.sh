#!/bin/bash
#Usage: ./run_analyze_shell_code.sh <root folder of the output of running fuzzball-whitedisasm under emu_fuzzball, must be abosolute dir>
TCGEN=$(pwd)
WBOCHS=$TCGEN/../tools/WhiteBochs-old
TMP=$TCGEN/instructions.csv
IN=input
> $TMP
touch $IN
cd $1
for FILENAME in *
do	
	DIR=$1$FILENAME
	echo $DIR
	$TCGEN/analyze_shell_code.sh $DIR > $IN
	cat $IN
	echo $WBOCHS/concrete-whitedisasm $(cat $IN)
	$WBOCHS/concrete-whitedisasm $(cat $IN) >> $TMP 
done
rm $IN
cd $TCGEN
rm $IN
