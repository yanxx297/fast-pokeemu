#! /bin/bash
dir=/tmp
in=../data/state-explr
out=$dir/out/
start=10
single=false

is_match () {
	if [ -e $1/mismatch ]; then
		return 1;
	elif [ -e $1/match ]; then
		return 0;
	else
		return 2;
	fi
}

while [ "$1" != "" ]; do
        case $1 in
                -n )
                        single=true
                        ;;
                -s | --start )
                        shift
                        start=$1
                        ;;                    
                -h | --help )
                        echo "Usage: ./pokeEMU-offline.sh [-s STARTING_POINT] [-n]
                        0       Run full test (single mode 3)
                        1       Generate aggregating list
                        2       Single mode 0
                        3       Aggregated mode 3
                        4       generate final results"
                        ;;
        esac
        shift
done

if (( $start >= 10 )); then
        exit 0
fi

if (( $start <= 0 )); then
        echo 'Run single mode 3 experiment'
	./run-testcase-offline.sh -m 3 -in $in -out $out
	./run-testcase-offline.sh -kvm -in $in -out $out
	mv $out $dir/single-m3-kvm/
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 1 )); then
        echo 'Generate the list of valid test cases for aggregating'
	mkdir -p aggreg_list
	for insn in $dir/single-m3-kvm/*; do
		mkdir aggreg_list/$(basename $insn)
		for file in $insn/*.diff; do
			echo $in/$(basename $insn)/$(basename $file .diff)/testcase >> aggreg_list/$(basename $insn)/log
		done
		var=$(tr "\n" "," < aggreg_list/$(basename $insn)/log)
		echo ${var::-1} > aggreg_list/$(basename $insn)/log
		python split_log.py aggreg_list/$(basename $insn)/log 600
		rm aggreg_list/$(basename $insn)/log
	done
        mv aggreg_list/ $dir/aggreg_list/
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 2 )); then
        echo 'Run single mode 0 experiment'
        ./run-testcase-offline.sh -m 0 -in $in -out $out
	./run-testcase-offline.sh -kvm -in $in -out $out
	mv $out $dir/single-m0-kvm/
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 3 )); then
        echo 'Run aggregate mode 3 experiment and compute performance results'
	./run-testcase-offline.sh -aggreg -m 3 -in $dir/aggreg_list/ -out $out
        for folder in $out*;
        do
                cat $folder/time >> $out/time-m3
                for dump in $folder/*.post;
                do
                        for log in $dir/aggreg_list/$(basename $folder)/*.log;
                        do
                                if grep -q $(basename $dump .post) $log; then
                                        cat $log >> $out/count-m3
                                fi;
                        done;
                done;
        done;
	./run-testcase-offline.sh -kvm -in $in -out $out
	mv $out $dir/aggreg-m3-kvm/
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 4 )); then
        echo 'generate effectiveness results'
	mkdir -p $out
	touch $out/000 $out/001 $out/010 $out/011 $out/100 $out/101 $out/110 $out/111
	for aggreg in $dir/aggreg-m3-kvm/*; do
		s0=$dir/single-m0-kvm/$(basename $aggreg)
		s3=$dir/single-m3-kvm/$(basename $aggreg)
		is_match $aggreg
		if [ $? == 2 ]; then
			echo skip $(basename $aggreg)
			continue
		fi
		if $(is_match $s0) && $(is_match $s3) && $(is_match $aggreg); then
			echo $(basename $aggreg) >> $out/000;
		elif $(is_match $s0) && $(is_match $s3) && ! $(is_match $aggreg); then
			echo $(basename $aggreg) >> $out/001;
		elif $(is_match $s0) && ! $(is_match $s3) && $(is_match $aggreg); then
			echo $(basename $aggreg) >> $out/010;
		elif $(is_match $s0) && ! $(is_match $s3) && ! $(is_match $aggreg); then
			echo $(basename $aggreg) >> $out/011;
		elif ! $(is_match $s0) && $(is_match $s3) && $(is_match $aggreg); then
			echo $(basename $aggreg) >> $out/100;
		elif ! $(is_match $s0) && $(is_match $s3) && ! $(is_match $aggreg); then
			echo $(basename $aggreg) >> $out/101;
		elif ! $(is_match $s0) && ! $(is_match $s3) && $(is_match $aggreg); then
			echo $(basename $aggreg) >> $out/110;
		elif ! $(is_match $s0) && ! $(is_match $s3) && ! $(is_match $aggreg); then
			echo $(basename $aggreg) >> $out/111;
		fi
	done
	echo "
	Match     & Match    	& Match		& $(cat $out/000| wc -l) \\\\
	Match     & Match	& Mismatch 	& $(cat $out/001| wc -l) \\\\
	Match     & Mismatch    & Match		& $(cat $out/010| wc -l) \\\\
	Match     & Mismatch	& Mismatch 	& $(cat $out/011| wc -l) \\\\
	Mismatch  & Match    	& Match		& $(cat $out/100| wc -l) \\\\
	Mismatch  & Match 	& Mismatch 	& $(cat $out/101| wc -l) \\\\
	Mismatch  & Mismatch    & Match		& $(cat $out/110| wc -l) \\\\
	Mismatch  & Mismatch 	& Mismatch 	& $(cat $out/111| wc -l) \\\\\\hline "> $out/output2
fi
