#!/bin/bash
DIR="/tmp/"
cd $DIR
ls | grep ".*\.dot$" | while read -r line ; do
#       echo $line
        dot -Tpdf $line > $line.pdf
done
pdfunite $(ls | grep ".*\.pdf$") out.pdf
