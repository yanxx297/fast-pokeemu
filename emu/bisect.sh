#! /bin/bash
git bisect start HEAD 80c58fdf0e93f79fce323677a5b96769e99feb6e
git bisect run ./check-qemu.sh -c -t -r
git bisect log > $1
git checkout .
git bisect reset

