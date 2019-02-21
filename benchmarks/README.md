## Reproducing benchmarks

The PODC'19 submission benchmarks can be reproduced by running:

```
> python3 main.py podc19.json | tee output.json
```

The results can be converted into a LaTeX table by running:

```
> python3 format.py output.json | tee table.tex
```

This table can be compiled to a PDF by running:
```
> pdflatex template.tex
```

## New benchmarks

New benchmarks can be obtained by writing a new JSON configuration
file; podc19.json can serve as a basis to write such a new file.
