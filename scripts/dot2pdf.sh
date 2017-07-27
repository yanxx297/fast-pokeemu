#!/bin/bash
for file in $1/*.dot; do
        echo $file
        dot -Tpdf $file > $file.pdf
done
pdfunite $1/*.pdf $1/out.pdf
rm $1/*.dot
