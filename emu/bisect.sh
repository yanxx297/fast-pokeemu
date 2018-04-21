#! /bin/bash
git bisect start HEAD afc6ffd005af42b7f411e660f493ef91fcaefa39
git bisect run ./check-qemu.sh -c -t -r
git bisect log > $1
git checkout .
git bisect reset

