#! /bin/bash
git bisect start HEAD $(git rev-list HEAD | tail -n 1)
git bisect run ./check-qemu.sh -c -t -r
git bisect log > $1
git checkout .
git bisect reset

