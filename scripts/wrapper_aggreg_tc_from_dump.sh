#!/bin/bash
TCDIR=$1
QDIR=$2
KDIR=$3
OUT=$4


for dir in $TCDIR/*;
do
	TC=$(basename $dir);
	OUTDIR=$OUT/$TC;
	mkdir $OUTDIR;
	./aggreg_tc_from_dump.sh $dir/ $QDIR/$TC/ $KDIR/$TC/ > $OUTDIR/log; 
done;
	

