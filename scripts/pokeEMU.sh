#! /bin/bash
dir=/tmp
in=
out=$dir/out/
remote_dir=/export/scratch/tmp 
remote_in=$remote_dir/state-explr/
remote_out=$remote_dir/out/

is_match () {
	if [ -e $1/mismatch ]; then
		return 1;
	elif [ -e $1/match ]; then
		return 0;
	else
		return 2;
	fi
}

echo 'Run single mode 0 experiment'
if ! [ -e $dir/single-m0-kvm/ ]; then
	ssh yan@logan.cs.umn.edu $(echo "cd ~/Project/pokemu-oras/scripts; ./run-testcase.sh -m 0 -in $remote_in -out $remote_out")
	./run-testcase.sh -kvm -in $remote_out -out $out
	mv $out $dir/single-m0-kvm/
	ssh yan@logan.cs.umn.edu $(echo "mv $remote_out $remote_dir/single-m0-qemu/")
fi

echo 'Run single mode 3 experiment'
if ! [ -e $dir/single-m3-kvm/ ]; then
	ssh yan@logan.cs.umn.edu $(echo "cd ~/Project/pokemu-oras/scripts; ./run-testcase.sh -m 3 -in $remote_in -out $remote_out")
	./run-testcase.sh -kvm -in $remote_out -out $out
	mv $out $dir/single-m3-kvm/
	ssh yan@logan.cs.umn.edu $(echo "mv $remote_out $remote_dir/single-m3-qemu/")
fi

# Generate the list of valid test cases for aggregating
if ! [ -e aggreg_list ] && ! [ -e $dir/aggreg-m3-kvm/ ]; then
	mkdir -p aggreg_list
	for insn in $dir/single-m3-kvm/*; do
		mkdir aggreg_list/$(basename $insn)
		for file in $insn/*.diff; do
			echo $remote_in/$(basename $insn)/$(basename $file .diff)/testcase >> aggreg_list/$(basename $insn)/log
		done
		var=$(tr "\n" "," < aggreg_list/$(basename $insn)/log)
		echo ${var::-1} > aggreg_list/$(basename $insn)/log
		python split_log.py aggreg_list/$(basename $insn)/log 800
		rm aggreg_list/$(basename $insn)/log
	done
	scp -r aggreg_list/ yan@logan.cs.umn.edu:$remote_dir/aggreg_list/
fi

echo 'Run aggregate mode 3 experiment'
if ! [ -e $dir/aggreg-m3-kvm/ ]; then
	ssh yan@logan.cs.umn.edu $(echo "cd ~/Project/pokemu-oras/scripts; ./run-testcase.sh -aggreg -m 3 -in $remote_dir/aggreg_list/ -out $remote_out")
	./run-testcase.sh -kvm -in $remote_out -out $out
	mv $out $dir/aggreg-m3-kvm/
	ssh yan@logan.cs.umn.edu $(echo "mv $remote_out $remote_dir/aggreg-m3-qemu/")
	rm -r aggreg_list/
fi

echo 'generate effectiveness results'
if ! [ -e $out/000 ]; then
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
