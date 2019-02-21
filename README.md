# Automatic Verification of Parameterized Population Protocols

This is the artifact for the PODC'19 submission "Automatic Verification of Parameterized Population Protocols".

## Dependencies

- [Python 3](https://www.python.org/).
- [Graph-tool](https://graph-tool.skewed.de/) library for Python 3.
- [Graphviz](https://www.graphviz.org/) with Python 3 bindings.
- [Z3](https://github.com/Z3Prover/z3/) with Python 3 bindings.
- TeX distribution with `pdflatex` command and `geometry`, `amsmath`, `booktabs`, `multirow` and `siunitx` packages for generating a PDF with the table of experimental results (optional).

On Ubuntu 18.04, all dependencies can be installed using the following commands:
```
echo 'echo "deb http://downloads.skewed.de/apt/bionic bionic universe" >> /etc/apt/sources.list' | sudo bash
echo 'echo "deb-src http://downloads.skewed.de/apt/bionic bionic universe" >> /etc/apt/sources.list' | sudo bash
sudo apt-key adv --keyserver pgp.skewed.de --recv-key 612DEFB798507F25
sudo apt update
sudo apt install python3 python3-graph-tool python3-gv python3-pip
pip3 install z3-solver
sudo apt install texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-science
```

## Overview of the artifact

- The folder `protocols` contains several parameterized protocols for flock-of-birds, remainder and threshold.
- The folder `src` contains the source code for constructing the abstraction, stage graph and checking the termination witness.
- The folder `benchmarks` contains scripts to reproduce the experimental results from the paper.

## Running the tool

The tool can be run on e.g. the basic basic parameterized flock-of-birds protocol as follows, with additional options for more verbose output and inspectable intermediate results:
```
python3 src/main.py protocols/flockofbirds_basic.ppp -v -o -t stages.pdf -p -a abstraction.pp
```
The tool will print information on the termination and termination time of the protocol. The file `stages.pdf` will contain the stage graph afterwards, and the file `abstraction.pp` the abstraction of the parameterized protocol.

## Reproducing the experimental results

The results table from the paper can be reproduced by running the following command from the main folder:
```
sh run_benchmarks.sh
```
Execution of this command should take at most 10 minutes. Afterwards, it will generate a file `results.pdf` which will resemble Table 1 in the paper.
