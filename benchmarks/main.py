# -*- coding: utf-8 -*-
import argparse
import json
import multiprocessing
import sys
import time
import os

sys.path.append("..")
sys.path.append("../src/")
from src.main import execute

DESCRIPTION = "Benchmarking utility."
verbose = False

class Timeout(Exception): pass

def log(message):
    if verbose:
        print(message)

# timeout is in seconds
def benchmark_single(protocol, timeout=None):
    args = argparse.Namespace()

    if len(protocol) > 1:
        protocol[1] = str(protocol[1])
    
    args.protocol    = protocol
    args.out         = True
    args.verbose     = False
    args.tree        = None
    args.struct      = False
    args.depth       = None
    args.nowitness   = False
    args.implication = False
    args.simp_predicates = False
    args.abstract    = [os.path.join("/tmp", os.path.basename(protocol[0]))]

    result = {}
    
    def run(queue):
        result = queue.get()
        result = json.loads(execute(args))
        queue.put(result)

    queue = multiprocessing.Queue()
    queue.put(result)
    process = multiprocessing.Process(target=run, args=(queue,))

    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join()
        result["elapsed"] = {"tree": "timeout"}
    else:
        result = queue.get()
    
    result["protocol"] = protocol

    return result

def benchmark_all(config):
    protocols = config["protocols"]
    timeout   = config["timeout"]

    print("[")
    
    for i, p in enumerate(protocols):
        sep = "," if i + 1 < len(protocols) else ""
        
        print(json.dumps(benchmark_single(p, timeout)) + sep)

    print("]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()    

    parser.add_argument("config", metavar="config", type=str,
                        help=("benchmarks JSON configuration file"))
    parser.add_argument("-v", "--verbose",
                        help="enable verbosity", action="store_true")

    args  = parser.parse_args()
    start = time.process_time()

    verbose = args.verbose 

    log("Loading benchmarks configuration from {}...".format(args.config))

    with open(args.config) as config_file:
        config = json.load(config_file)

    log("Configuration file loaded.")

    results = benchmark_all(config)
    end     = time.process_time()
    elapsed = end - start

    log("Benchmarking took {:.4f} seconds.".format(elapsed))
