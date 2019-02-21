#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json
import re
from collections import deque
from z3 import *
from protocol import Protocol
from transition import Transition
from unordered_pair import upair

VERBOSE = False

def log(s):
    if VERBOSE:
        print(s)

def check_sat(p):
    s = Solver()
    s.add(p)
    result = s.check()
    if result == sat:
        return True
    elif result == unsat:
        return False
    else:
        raise Exception("Unknown sat result")

def non_empty(p, q, pred):
    predicate = Exists([Int(param) for param in p['parameters']] + [Int('x')], \
                    And(And(p['states'][q], p['constraints']), pred))
    return check_sat(predicate)

def print_table(p, q, states):
    imax=10
    cmax=10
    print("c\i", end=' ')
    print(' '.join(f"{i:3}" for i in range(0,imax)))
    for c in range(0,cmax):
        print(f"{c:3}", end=' ')
        for x in range(0,imax):
            empty = True
            for idx,a in enumerate(states):
                if a['state'] == q:
                    predicate = And([Int('x') == x, Int('c') == c, a['predicate']])
                    if non_empty(p, q, predicate):
                        empty = False
                        print(f" {q}{idx}", end=' ')
            if empty:
                print(" ", end=' ')
        print()

def apply_recursively(s, tactic):
    """
    Recursively apply tactic on boolean applications in term s
    """
    todo = deque() # to do queue
    todo.append(s)
    cache = AstMap(ctx=s.ctx)
    while todo:
        n = todo[-1]
        if is_var(n):
            todo.pop()
            cache[n] = n
        elif is_int(n):
            todo.pop()
            cache[n] = n
        elif is_app(n):
            visited  = True
            new_args = []
            for i in range(n.num_args()):
                arg = n.arg(i)
                if not arg in cache:
                    todo.append(arg)
                    visited = False
                else:
                    new_args.append(cache[arg])
            if visited:
                todo.pop()
                if is_and(n):
                    new_n = And(new_args)
                elif is_or(n):
                    new_n = Or(new_args)
                else:
                    new_n = n.decl()(new_args)
                if is_bool(new_n):
                    updated_n = tactic(new_n).as_expr()
                else:
                    updated_n = new_n
                cache[n] = updated_n
        else:
            raise Exception("Quantifiers not supported")
    return cache[s]

def simplify_term(s):
    simp = Tactic('simplify')
    qetactic = Tactic('qe')
    propvalues = Tactic('propagate-values')
    propineqs = Tactic('propagate-ineqs')
    t = Then(qetactic, Then(simp, Then(propvalues, simp)))

    return simp(apply_recursively(t(s).as_expr(), propineqs)).as_expr()

def simplify_by_equal_pred(protocol, q, pred, simp_level):
    ivars = ["x"] + protocol['parameters']
    test_pred_lists = \
        [ [(x == y), (x < y), (x <= y), (x >= y), (x > y), (x != y)] \
                for xv in ivars for x in [ Int(xv) ] \
                for y in [0,1,-1] + [ yvs for yv in ivars if xv != yv for yvs in (-Int(yv), Int(yv)) ] ]
    # for AVC protocol: add for y in [0,1,-1,3,-3] + ...
    test_preds =  [ pred for pred_list in test_pred_lists for pred in pred_list ]
    if simp_level >= 2:
        for test_pred in [ BoolVal(True), BoolVal(False) ] + test_preds:
            if not non_empty(protocol, q, (pred != test_pred)):
                return test_pred
    if simp_level >= 3:
        for i,test_pred1 in enumerate(test_preds):
            for j,test_pred2 in enumerate(test_preds[i+1:]):
                test_pred = And(test_pred1, test_pred2)
                if not non_empty(protocol, q, (pred != test_pred)):
                    return test_pred
    return pred

def abstract_state_name(q, i):
    pred = pretty_print_pred(q['predicate'])
    if pred == 'True':
        return q['state']
    elif len(pred) <= 10:
        return "{}_{{{}}}".format(q['state'], pred)
    else:
        return "{}{}".format(q['state'], i)

indices_decls = { 'x': Int('x') }
t_indices = ['i','j','k','l']
transition_decls = { i: Int(i) for i in t_indices }

def parse_predicate(predicate, decls):
    ast = parse_smt2_string(f"(assert {predicate})", decls=decls)
    if isinstance(ast, z3.z3.AstVector):
        return ast[0]
    else:
        return ast

def parse_protocol(protocol):
    parameter_decls = { param: Int(param) for param in protocol['parameters'] }

    indices_decls.update(parameter_decls)

    transition_decls.update(parameter_decls)

    protocol['constraints'] = parse_predicate(protocol['constraints'], parameter_decls)

    for q in protocol['states'].keys():
        for s in ['states','initialStates','falseStates','trueStates']:
            protocol[s][q] = parse_predicate(protocol[s][q], indices_decls)

    for t in protocol['transitions'].values():
        t['predicate'] = parse_predicate(t['predicate'], transition_decls)

def make_states(protocol):

    # TODO: compute separate set of abstract states for each parameterized state
    worklist = deque()

    # Compute states from output predicate
    for q in protocol['states'].keys():
        for predicate in (protocol['trueStates'][q], protocol['falseStates'][q]):
            if non_empty(protocol, q, predicate):
                worklist.append( { 'state': q, 'predicate': predicate } )

    # Compute states from transitions
    for t in protocol['transitions'].values():
        for idx,q in enumerate(t['pre'] + t['post']):
            predicate = Exists([Int(i) for i in t_indices], \
                    And( Int('x') == transition_decls[t_indices[idx]], t['predicate'] ))
            if non_empty(protocol, q, predicate):
                worklist.append( { 'state': q, 'predicate': predicate } )

    # Compute partition of states
    abstract_states = []
    while worklist:
        a = worklist.popleft()
        q = a['state']
        add_state_a = True
        for idx,b in enumerate(abstract_states):
            del_state_b = False
            if q == b['state']:
                intersection = And(a['predicate'], b['predicate'])
                diff1 = And(a['predicate'], Not(b['predicate']))
                diff2 = And(Not(a['predicate']), b['predicate'])

                if non_empty(protocol, q, intersection):
                    d1 = non_empty(protocol, q, diff1)
                    d2 = non_empty(protocol, q, diff2)

                    if not d1 and not d2:
                        # [a] and [b] are the same sets, keep one with smaller predicate
                        if len(str(a['predicate'])) <= len(str(b['predicate'])):
                            del_state_b = True
                        else:
                            add_state_a = False
                    elif d1 and not d2:
                        # [b] included in [a], keep b and a\b
                        add_state_a = False
                        worklist.append({ 'state': q, 'predicate': diff1 })
                    elif not d1 and d2:
                        # [a] included in [b], keep a and b\a
                        del_state_b = True
                        worklist.append({ 'state': q, 'predicate': diff2 })
                    else:
                        # keep all intersections and differences
                        add_state_a = False
                        del_state_b = True
                        worklist.append({ 'state': q, 'predicate': intersection })
                        worklist.append({ 'state': q, 'predicate': diff1 })
                        worklist.append({ 'state': q, 'predicate': diff2 })

            if del_state_b:
                del abstract_states[idx]
            if not add_state_a or del_state_b:
                break

        if add_state_a:
            abstract_states.append(a)

    # Add missing valid states
    for q,pred in protocol['states'].items():
        predicate = And([pred] + [Not(a['predicate']) for a in abstract_states if q == a['state']])
        if non_empty(protocol, q, predicate):
            abstract_states.append( { "state": q, "predicate": predicate } )

    return abstract_states

def simplify_states(protocol, states, simp_level):
    # Simplify predicates
    for a in states:
        if simp_level >= 1:
            a['predicate'] = simplify_term(a['predicate'])
        if simp_level >= 2:
            a['predicate'] = simplify_by_equal_pred(protocol, a['state'], a['predicate'], simp_level)

    # Print states
    for idx,a in enumerate(states):
        log("State {} with predicate: {}".format(abstract_state_name(a, idx), pretty_print_pred(a['predicate'])))

def rename_t_var(predicate, index):
    return substitute(predicate, [(Int('x'), transition_decls[t_indices[index]])])

def make_transitions(protocol, states):
    transitions = set()

    for i,a in enumerate(states):
        for j,b in enumerate(states):
            for k,c in enumerate(states):
                for l,d in enumerate(states):
                    #if not ((i == k and j == l) or (i == l and j == k)):
                        for t in protocol['transitions'].values():
                            if (t['pre'][0] == a['state'] and t['pre'][1] == b['state'] and \
                                t['post'][0] == c['state'] and t['post'][1] == d['state']):
                                predicate = Exists([Int(param) for param in protocol['parameters']] + [Int(i) for i in t_indices], \
                                    And([protocol['constraints'], \
                                            rename_t_var(protocol['states'][a['state']], 0), \
                                            rename_t_var(protocol['states'][b['state']], 1), \
                                            rename_t_var(protocol['states'][c['state']], 2), \
                                            rename_t_var(protocol['states'][d['state']], 3), \
                                            rename_t_var(a['predicate'], 0), \
                                            rename_t_var(b['predicate'], 1), \
                                            rename_t_var(c['predicate'], 2), \
                                            rename_t_var(d['predicate'], 3), \
                                            t['predicate']]))
                                if check_sat(predicate):
                                    ip = i if i < j else j
                                    jp = j if i < j else i
                                    kp = k if k < l else l
                                    lp = l if k < l else k
                                    transitions.add((ip,jp,kp,lp))
                                    break

    for i,j,k,l in transitions:
        a = states[i]
        b = states[j]
        c = states[k]
        d = states[l]
        log("Transition {} {} -> {} {}".format( \
                abstract_state_name(a, i), abstract_state_name(b, j), abstract_state_name(c, k), abstract_state_name(d, l)))

    return transitions

def pretty_print_pred(pred):
    if is_var(pred):
        return str(pred)
    elif is_int(pred):
        return str(pred)
    elif is_app(pred):
        args = []
        n = pred.num_args()
        if is_not(pred):
            assert n == 1
            return ("¬({})".format(pretty_print_pred(pred.arg(0))))
        if is_and(pred):
            return ("{}".format('∧'.join(pretty_print_pred(pred.arg(i)) for i in range(n))))
        elif is_or(pred):
            return ("({})".format('∨'.join(pretty_print_pred(pred.arg(i)) for i in range(n))))
        elif is_le(pred):
            assert n == 2
            return ("{}≤{}".format(pred.arg(0), pred.arg(1)))
        elif is_lt(pred):
            assert n == 2
            return ("{}<{}".format(pred.arg(0), pred.arg(1)))
        elif is_eq(pred):
            assert n == 2
            return ("{}={}".format(pred.arg(0), pred.arg(1)))
        elif is_distinct(pred):
            assert n == 2
            return ("{}≠{}".format(pred.arg(0), pred.arg(1)))
        elif is_gt(pred):
            assert n == 2
            return ("{}>{}".format(pred.arg(0), pred.arg(1)))
        elif is_ge(pred):
            assert n == 2
            return ("{}≥{}".format(pred.arg(0), pred.arg(1)))
        elif is_mod(pred):
            assert n == 2
            return ("{}%{}".format(pred.arg(0), pred.arg(1)))
        else:
            return str(pred)
    else:
        # pretty quantifiers not supported
        return str(pred)

def make_initial_output_states(protocol, states):
    initial_states = set()
    true_states = set()
    false_states = set()

    for i,a in enumerate(states):
        q = a['state']
        if non_empty(protocol, q, And(a['predicate'], protocol['initialStates'][q])):
            initial_states.add(i)
        if non_empty(protocol, q, And(a['predicate'], protocol['trueStates'][q])):
            true_states.add(i)
        if non_empty(protocol, q, And(a['predicate'], protocol['falseStates'][q])):
            false_states.add(i)
    for i in initial_states:
        log("Initial state {}".format(abstract_state_name(states[i], i)))
    for i in true_states:
        log("True state {}".format(abstract_state_name(states[i], i)))
    for i in false_states:
        log("False state {}".format(abstract_state_name(states[i], i)))

    return (initial_states, true_states, false_states)

def print_abstract_protocol(out, name, param, states, transitions, initial_states, true_states, false_states, problematic_heads):
    out.write('{\n')
    out.write('  "states": [ "{}" ],\n'.format('", "'.join(sorted(abstract_state_name(states[i], i) for i,q in enumerate(states)))))
    out.write('  "transitions": [\n')
    t_string = []
    for i,j,k,l in transitions:
        a = abstract_state_name(states[i], i)
        b = abstract_state_name(states[j], j)
        c = abstract_state_name(states[k], k)
        d = abstract_state_name(states[l], l)
        a,b = sorted((a,b))
        c,d = sorted((c,d))
        t_string.append('    {{ "name": "{} {} -> {} {}", "pre": ["{}", "{}"], "post": ["{}", "{}"] }}'.format(a, b, c, d, a, b, c, d))
    out.write(',\n'.join(sorted(t_string)))
    out.write('\n  ],\n')
    out.write('  "initialStates": [ {} ],\n'.format(', '.join(sorted(
        '"{}"'.format(abstract_state_name(states[i], i)) for i in initial_states))))
    out.write('  "trueStates":    [ {} ],\n'.format(', '.join(sorted(
        '"{}"'.format(abstract_state_name(states[i], i)) for i in true_states))))
    out.write('  "falseStates":   [ {} ],\n'.format(', '.join(sorted(
        '"{}"'.format(abstract_state_name(states[i], i)) for i in false_states))))
    if problematic_heads:
        out.write('  "problematicHeads":   [ {} ],\n'.format(', '.join(sorted(
            '["{}", "{}"]'.format(abstract_state_name(states[i], i), abstract_state_name(states[j], j)) for i,j in problematic_heads))))
    out.write('  "title": "{}"\n'.format(name))
    out.write('}\n')

def test_heads(protocol, states, transitions):
    heads = set()
    problematic_heads = set()
    for i,j,k,l in transitions:
        heads.add((i,j))
    for i,j in heads:
        a = states[i]
        b = states[j]
        trans = []
        for t in protocol['transitions'].values():
            if t['pre'][0] == a['state'] and t['pre'][1] == b['state']:
                trans.append( And([ t['predicate'], \
                                    rename_t_var(protocol['states'][t['post'][0]], 2), \
                                    rename_t_var(protocol['states'][t['post'][1]], 3) ]))
            if t['pre'][1] == a['state'] and t['pre'][0] == b['state']:
                trans.append( And([ substitute(t['predicate'], [ \
                                        (transition_decls[t_indices[0]], transition_decls[t_indices[1]]), \
                                        (transition_decls[t_indices[1]], transition_decls[t_indices[0]]) \
                                    ]),
                                    rename_t_var(protocol['states'][t['post'][0]], 2), \
                                    rename_t_var(protocol['states'][t['post'][1]], 3) ]))
        predicate = Exists([Int(param) for param in protocol['parameters']] + [Int(i) for i in t_indices[0:2]], \
                        And([protocol['constraints'], \
                            rename_t_var(protocol['states'][a['state']], 0), \
                            rename_t_var(protocol['states'][b['state']], 1), \
                            rename_t_var(a['predicate'], 0), \
                            rename_t_var(b['predicate'], 1), \
                            ForAll([Int(i) for i in t_indices[2:4]], Not(Or(trans))) \
                        ]))
        if check_sat(predicate):
            log("Potentially problematic head ({},{})".format(abstract_state_name(a, i), abstract_state_name(b, j)))
            problematic_heads.add((i,j))
    return problematic_heads

def sn(s):
    s = re.sub(r'∧','&', s)
    s = re.sub(r'∨','|', s)
    s = re.sub(r'¬','!', s)
    s = re.sub(r'≠','!=', s)
    s = re.sub(r'≥','>=', s)
    s = re.sub(r'≤','<=', s)
    
    return re.sub(r'[^\x00-\x7F]+','_', s)

def load_abstract_protocol(filename, simp_level = 1, output_file=None):
    # Load protocol
    with open(filename) as in_file:
        protocol = json.load(in_file)

    parse_protocol(protocol)

    states = make_states(protocol)
    simplify_states(protocol, states, simp_level)

    transitions = make_transitions(protocol, states)
    io_states   = make_initial_output_states(protocol, states)
    initial_states, true_states, false_states = io_states

    problematic_heads = test_heads(protocol, states, transitions)

    if output_file is not None:
        with open(output_file, 'w') as out_file:
            print_abstract_protocol(out_file, protocol['title'],
                                    protocol['constraints'], states,
                                    transitions, initial_states,
                                    true_states, false_states,
                                    problematic_heads)

    # Construct Protocol(...)
    Q = {sn(abstract_state_name(states[i], i)) for i, q in enumerate(states)}
    T = set()
    
    for i, j, k, l in transitions:
        a = sn(abstract_state_name(states[i], i))
        b = sn(abstract_state_name(states[j], j))
        c = sn(abstract_state_name(states[k], k))
        d = sn(abstract_state_name(states[l], l))

        T.add(Transition((a, b), (c, d)))

    S  = {sn(abstract_state_name(states[i], i)) for i in initial_states}
    I  = {q: q for q in S}

    Q1 = {sn(abstract_state_name(states[i], i)) for i in true_states}
    Q0 = {sn(abstract_state_name(states[i], i)) for i in false_states}
    O  = {**{q: 1 for q in Q1}, **{q: 0 for q in Q0}}

    H  = {upair(sn(abstract_state_name(states[i], i)),
                sn(abstract_state_name(states[j], j)))
          for i, j in problematic_heads}

    P = Protocol(Q, T, S, I, O, H)
    P.name = lambda: name

    return P

if __name__ == "__main__":
    n = len(sys.argv)

    if n < 3:
        print("Usage:   {} [input] [output] [options]".format(sys.argv[0]))
        print("Options: -sL   Simplification stage L = 0,1,2,3")
    else:
        input_file  = sys.argv[1]
        output_file = sys.argv[2]
        simp_level  = 0
        
        for option in sys.argv[3:]:
            if option == "-s1":
                simp_level = 1
            if option == "-s2":
                simp_level = 2
            if option == "-s3":
                simp_level = 3

        with open(input_file) as in_file:
            protocol = json.load(in_file)
            parse_protocol(protocol)
            print(protocol)
            print()
            
            states = make_states(protocol)
            simplify_states(protocol, states, simp_level)
            print()

            transitions = make_transitions(protocol, states)
            print()

            io_states = make_initial_output_states(protocol, states)
            initial_states, true_states, false_states = io_states
            print()

            problematic_heads = test_heads(protocol, states, transitions)
            
            with open(output_file, 'w') as out_file:
                print_abstract_protocol(out_file, protocol['title'],
                                        protocol['constraints'], states,
                                        transitions, initial_states,
                                        true_states, false_states,
                                        problematic_heads)
