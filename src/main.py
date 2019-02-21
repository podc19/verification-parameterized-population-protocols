# -*- coding: utf-8 -*-
import argparse
import importlib.util
import json
import time

from abstract import load_abstract_protocol
from speed import Speed
from stage_tree import StageTree
from stage_tree_utils import export

DESCRIPTION = ("Automatic analysis of expected termination time "
               "of population protocols.")

verbose = False

def log(message):
    if verbose:
        print(message)

def load_protocol(filename, args, simp_level = 0, output_file=None):
    log("Loading protocol from {}...".format(filename))
    fmt = filename.split(".")[-1]

    if fmt == "ppp":
        protocol = load_abstract_protocol(filename, simp_level, output_file)
    else:
        spec = importlib.util.spec_from_file_location("", filename)
        gen  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        protocol = gen.generate(*args)

    log(("Protocol loaded "
         "({} states, {} transitions).").format(len(protocol.states),
                                                len(protocol.transitions)))

    return protocol

def generate_tree(protocol, depth=None, check_termination_witness=False,
                  use_t_invariants=False):
    log("Generating stage tree...")

    tree = StageTree(protocol, max_depth=depth,
                     check_termination_witness=check_termination_witness,
                     use_t_invariants=use_t_invariants)

    log("Stage tree generated. ")
    log(("Generated {} stages "
         "and {} terminal stages.").format(len(tree.stages),
                                           len(tree.terminal_stages)))

    return tree

def export_tree(tree, filename, struct_only):
    log("Exporting stage tree...")
    export(tree, filename=filename, struct_only=struct_only)
    log("Stage tree exported to {}.".format(filename))

def execute(args):
    global verbose
    verbose = args.verbose

    simp_level = 3 if args.simp_predicates else 1
    start     = time.process_time()
    prot_args = json.loads(args.protocol[1]) if len(args.protocol) > 1 else []
    protocol  = load_protocol(args.protocol[0], prot_args,
                    simp_level, None if args.abstract is None else args.abstract[0])
    end       = time.process_time()
    load_time = end - start

    log("Loading took {:.4f} seconds.".format(load_time))

    depth     = None if args.depth is None else args.depth[0]
    start     = time.process_time()
    tree      = generate_tree(protocol, depth, args.nowitness is not True,
                              args.implication is not True)
    end       = time.process_time()
    tree_time = end - start

    log("Generation took {:.4f} seconds.".format(tree_time))

    # Termination?
    if (args.nowitness is not True):
        termination = "verified" if tree.terminates() else \
                      "could not be verified"
        witness = "verified (fast)" if tree.witness() is True else \
                      "verified (safe)" if tree.witness() is False else \
                        "could not be verified"
        log("Protocol termination: {}.".format(termination))
        log("Protocol termination witness: {}.".format(witness))

    # Interaction complexity
    if (args.nowitness is not True):
        speed = "n³"        if tree.speed() == Speed.CUBIC         else \
                "n²·log(n)" if tree.speed() == Speed.QUADRATIC_LOG else \
                "unknown"
        log("Expected termination time: {}.".format(speed))

    # Create outputs
    speed = str(tree.speed()) if tree.speed() is not None else None
    
    output = {}
    output["elapsed"]  = {"loading": load_time, "tree": tree_time}
    output["tree"] = {"stages":      len(tree.stages),
                      "terminal":    len(tree.terminal_stages),
                      "max-depth":   tree.max_depth(),
                      "termination": tree.terminates(),
                      "witness":     tree.witness(),
                      "speed":       speed}

    if args.tree is not None:
        export_tree(tree, args.tree[0], args.struct)

    return json.dumps(output) if args.out else None

if __name__ == "__main__":
    # Create parser and parse arguments
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    
    parser.add_argument("protocol", metavar="protocol", nargs="+", type=str,
                        help=("protocol filename and "
                               "optional arguments as JSON list"))
    parser.add_argument("-t", "--tree", metavar="filename", nargs=1, type=str,
                        help="export stage tree to filename")
    parser.add_argument("-o", "--out",
                        help="output results", action="store_true")
    parser.add_argument("-v", "--verbose",
                        help="enable verbosity", action="store_true")
    parser.add_argument("-s", "--struct",
                        help="generate only stage tree structure (no labels)",
                        action="store_true")
    parser.add_argument("-d", "--depth", metavar="depth", nargs=1, type=int,
                        help="maximum depth of the stage tree")
    parser.add_argument("-w", "--nowitness",
                        help="do not check termination witness",
                        action="store_true")
    parser.add_argument("-i", "--implication",
                        help="use implication graph instead of transition invariants",
                        action="store_true")
    parser.add_argument("-p", "--simp-predicates",
                        help="simplify predicates for better readability (may increase time for computation)",
                        action="store_true")
    parser.add_argument("-a", "--abstract", metavar="filename", nargs=1, type=str,
                        help="export abstract protocol to filename")

    args = parser.parse_args()
    out  = execute(args)

    if out is not None:
        print(out)
