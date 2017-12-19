#! /bin/bash
git bisect start HEAD afc6ffd005af42b7f411e660f493ef91fcaefa39
git bisect run ./checkfix-rev.sh
git bisect log > $1
git checkout .
git bisect reset

