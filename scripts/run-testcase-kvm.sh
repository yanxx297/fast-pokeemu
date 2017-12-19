#! /bin/bash

remote_dir=/export/scratch/tmp/out
dirnames=$(ssh yan@logan.cs.umn.edu $(echo ls $remote_dir))
for dir in $dirnames; 
do
	echo $remote_dir/$dir
	tcnames=$(ssh yan@logan.cs.umn.edu $(echo ls $remote_dir/$dir))
done;
