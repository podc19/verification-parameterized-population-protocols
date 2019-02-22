# -*- coding: utf-8 -*-
import argparse
import importlib.util
import json
import sys
import os
import re

sys.path.append("../src/")

def pretty_termination(terminates):
    out = "success" if terminates is True  else \
          "failure"  if terminates is False else \
          "unknown"

    return "\\emph{{{}}}".format(out)

def pretty_witness(witness):
    out = "yes" if witness is True  else \
          "yes"  if witness is False else \
          "unknown"

    return "\\emph{{{}}}".format(out)

def pretty_speed(speed):
    labels = {None: "---",
              "Speed.QUADRATIC_LOG": "$n^2 \\log n$",
              "Speed.CUBIC": "$n^3$"}

    return labels[speed]

def load_protocol(protocol):
    filename = os.path.join("/tmp", os.path.basename(protocol[0]))
    with open(filename) as in_file:
        spec = json.load(in_file)
    return spec["title"], spec

def table(data):
    TEMPLATE = "  {:28} & {:3} & {:3} & {:6} & & {:3} & {:6} & & {:14} & {:12} \\\\"
    print("\\begin{tabular}{lrrrc@{\\hspace{1pt}}rrc@{\\hspace{1pt}}cc}")
    print("\\toprule")
    print("& \\multicolumn{3}{c}{Abstraction $(\\calP, h)$} &")
    print("& \\multicolumn{2}{c}{Stage graph $G$} &")
    print("& \\multicolumn{2}{c}{Termination of $\\calQ$} \\\\")
    print("\\cmidrule{2-4}")
    print("\\cmidrule{6-7}")
    print("\\cmidrule{9-10}")
    print("Protocol $\\calQ$ & $|Q|$ & $|T|$ & Time (\\si{s}) & & Stages & Time (\\si{s}) & & Termination? & Bound \\\\")
    print("\\midrule")
    
    for d in data:
        if d["elapsed"]["tree"] != "timeout":
            name, protocol = load_protocol(d["protocol"])
            states     = len(protocol["states"])
            transitions = len(protocol["transitions"])
            stages     = d["tree"]["stages"]
            terminal   = d["tree"]["terminal"]
            depth      = d["tree"]["max-depth"]
            terminates = pretty_termination(d["tree"]["termination"])
            witness    = pretty_witness(d["tree"]["witness"])
            speed      = pretty_speed(d["tree"]["speed"])
            duration   = "{:.2f}".format(d["elapsed"]["tree"])
            loading    = "{:.2f}".format(d["elapsed"]["loading"])
        else:
            name       = re.sub('_', '\\_', os.path.basename(d["protocol"][0]))
            states     = "---"
            transitions = "---"
            stages     = "---"
            terminal   = "---"
            depth      = "---"
            terminates = "---"
            witness    = "---"
            speed      = "---"
            duration   = "timeout"
            loading    = "---"

        print(TEMPLATE.format(name,
                              states, transitions, loading,
                              stages, duration, witness, speed))


    print("\\bottomrule")
    print("\\end{tabular}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()    

    parser.add_argument("data", metavar="data", type=str,
                        help=("benchmarks data filename"))

    args = parser.parse_args()

    with open(args.data) as data_file:
        data = json.load(data_file)
 
    table(data)
