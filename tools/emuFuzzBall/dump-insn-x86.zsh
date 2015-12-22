#!/bin/zsh
objdump -b binary -m i386 -EL -D \
  =(perl -e 'print pack "C*", map(hex($_), @ARGV)' $*) | tail -n +8
