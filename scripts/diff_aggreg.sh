#!/bin/bash
LOGDIR=$1
SDIR=$2
ADIR=$3

touch Mch
touch Mis
touch SepMis
touch AggMis

for dir in $LOGDIR/*;
do
	Sdiff=0;
	Adiff=0;
	CODE=$(basename $dir);
	if [[ ! -e $SDIR/$CODE ]] || [[ ! -e $ADIR/$CODE ]];
	then
		continue;
	fi;

	TMP=$(tr "," "\n" < $dir/log);
	echo $CODE;
	for line in $TMP;
	do
		ID=$(basename $(dirname $line));
		if [[ ! -s $SDIR/$(basename $dir)/$ID.diff ]];
		then
			continue;
		fi;
		if [[ $(cat $SDIR/$(basename $dir)/$ID.diff) != $(cat /tmp/00000000.diff) ]];
		then
			cat $SDIR/$(basename $dir)/$ID.diff
			Sdiff=1;
			break;
		fi;
	done;
	for file in $ADIR/$(basename $dir)/*.diff;
	do
		if [[ $(cat $file) != $(cat /tmp/00000000.diff) ]];
		then
			echo "Aggreg Not Match"
			Adiff=1;
			break;
		fi;
	done;
	echo $Adiff $Sdiff >> /tmp/res
	if [[ $Adiff == 0 ]] && [[ $Sdiff == 0 ]];
	then
		echo $dir >> Mch;
	fi;
	if [[ $Adiff == 1 ]] && [[ $Sdiff == 1 ]];
	then
		echo "Double Mis"
		echo $dir >> Mis;
	fi;
	if [[ $Adiff == 1 ]] && [[ $Sdiff == 0 ]];
	then
		echo $dir >> AggMis;
	fi;
	if [[ $Adiff == 0 ]] && [[ $Sdiff == 1 ]];
	then
		echo $dir >> SepMis;
	fi;
done;
	

