#! /bin/bash
dir=/tmp
in=
out=$dir/out/
remote_dir=/export/scratch/tmp 
remote_in=$remote_dir/sample/
remote_out=$remote_dir/out/

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

# Copy list of valid test cases for aggregating
if ! [ -e aggreg_list ]; then
	mkdir -p aggreg_list
	for insn in $dir/single-m3-kvm/*; do
		mkdir aggreg_list/$(basename $insn)
		for file in $insn/*.diff; do
			echo $remote_in/$(basename $file .diff)/testcase >> aggreg_list/$(basename $insn)/log
		done
		var=$(tr "\n" "," < aggreg_list/$(basename $insn)/log)
		echo ${var::-1} > aggreg_list/$(basename $insn)/log
		python split_log.py aggreg_list/$(basename $insn)/log 800
		rm aggreg_list/$(basename $insn)/log
	done
	scp -r aggreg_list/ yan@logan.cs.umn.edu:$remote_dir/aggreg_list/
fi
