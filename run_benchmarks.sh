#!/bin/bash

cd benchmarks
python3 main.py podc19.json | tee output.json
python3 format.py output.json | tee table.tex
if ! [ -x "$(command -v pdflatex)" ]; then
    echo "pdflatex not installed, not generating PDF table"
else
    pdflatex template.tex
fi
cp template.tex ../results.pdf
