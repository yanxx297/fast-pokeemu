#!/bin/sh

TE=$HOME/TE

cat - | python $TE/TCGen/gen_uniq_shell_code.py | cut -f 2  | while read shellcode; do mkdir "$shellcode" ; done

# exit 0

# mov to/from cr/dr
for i in 0f2004 0f2286 0f2093 0f2291 0f209e 0f22df 0f20e2 0f2225 0f210f 0f234b 0f2115 0f23d7 0f215c 0f23de 0f2123 0f23a5 0f21ea 0f2328 0f21bf 0f23f9
do
    mkdir $i
done

