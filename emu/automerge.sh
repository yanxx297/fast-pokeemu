#! /bin/bash
# Automatically merge official QEMU commits to PokeQEMU
# Usage: ./automerge.sh <path/to/PokeQEMU/>

for line in $(cat commit);
do
        echo "Merge "$line
        git -C $1 merge --no-edit $line
        if [ $? == 0 ]; then
                continue
        else
                break
        fi
done
