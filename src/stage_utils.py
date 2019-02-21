import z3
from graph_tool import Graph
from graph_tool.topology import label_components
from formula import Formula
from stage import Stage
from unordered_pair import upair

def transformation_graph(protocol, stage):
    V = set(protocol.states)
    T = set()
    graph    = Graph(directed=True)
    vertices = {v: i for (i, v) in enumerate(V)}
    edges    = dict()

    def add_edge(p, q, t):
        graph.add_edge(vertices[p], vertices[q])

        if (p, q) in edges:
            edges[p, q].add(t)
        else:
            edges[p, q] = {t}

    graph.add_vertex(len(V))
    Phi = stage_formula(stage)

    for t in protocol.transitions:
        if ((not t.silent()) and
            (not Phi.implies_all_absent_tautology_check({t.pre}))):
            if len(t.preset & t.postset) == 0:
                A, B = t.pre
                C, D = t.post

                add_edge(A, C, t)
                add_edge(A, D, t)
                add_edge(B, C, t)
                add_edge(B, D, t)
            else:
                A = list(t.preset & t.postset)[0]
                B = t.pre.other(A)
                D = t.post.other(A)

                add_edge(B, D, t)

    return (graph, vertices, edges)

def compute_K(protocol, stage, mem):
    key = stage_key(stage)

    if key in mem["K"]:
       return mem["K"][key]

    graph, vertices, edges = transformation_graph(protocol, stage)
    components, _          = label_components(graph)

    K = set()
    T = set()

    for (p, q) in edges:
        if components[vertices[p]] != components[vertices[q]]:
            for t in edges[p, q]:
                K.add(t.pre)
                T.add(t)

    mem["K"][key] = (K, T)

    return K, T

def refine_K(protocol, stage, K, mem):

    # TODO: fix bug when refine_K is called both for transition invariants
    # and for implication graph on the same stage, but with different K
    # maybe use different mems for transition invariant and implication graph?
    #key = stage_key(stage)

    #if key in mem["K_"]:
    #    return mem["K_"][key]

    def f(X):
        to_remove = set()

        for EF in X:
            r = False

            for t in protocol.transitions:
                Phi = stage_formula(stage)
                Phi.assert_all_pairs_absent(X)

                # Case AB -> EF
                if t.post == EF:
                    r = not Phi.implies_all_absent_tautology_check({t.pre})
                # Case AB -> EG (and its symmetric case)
                elif len(t.postset & set(EF)) == 1:
                    E = list(t.postset & set(EF))[0]
                    F = EF.other(E)
                    G = t.post.other(E)

                    if E != F:
                        Phi.assert_all_states_absent({E})
                        Phi.assert_all_states_present({F})

                        r = not Phi.implies_all_absent_tautology_check({t.pre})
                    else:
                        Phi.assert_all_states_present({E}, unique=True)

                        r = not (E in t.pre or
                            Phi.implies_all_absent_tautology_check({t.pre}))

                if r:
                    break

            if r:
                to_remove.add(EF)

        return set(X) - to_remove

    # Compute greatest fixed-point of f
    M  = set(K)
    M_ = f(M)

    while M != M_:
        M  = M_
        M_ = f(M)

    # TODO readd (see above)
    #mem["K_"][key] = M

    return M

# Unique key associated with stage_formula
def stage_key(stage):
    return (frozenset(stage.present),
            frozenset(stage.present_unique),
            frozenset(stage.absent),
            frozenset(stage.disabled))

# Formula Phi_C
# Must remain consistent with info used in stage_key
def stage_formula(stage):
    Phi = Formula()

    Phi.assert_all_states_present(stage.present)
    Phi.assert_all_states_present(stage.present_unique, unique=True)
    Phi.assert_all_states_absent(stage.absent)
    Phi.assert_all_pairs_absent(stage.disabled)

    return Phi

def enlarge_stage_components(protocol, stage, valuation, K_):
    def f(M, N, O):
        def assert_rho(formula):
            formula.assert_all_states_present(M)
            formula.assert_all_states_present(N, unique=True)
            formula.assert_all_states_absent(O)

            return formula

        Phi = stage_formula(stage)
        Phi.assert_all_pairs_absent(K_)
        assert_rho(Phi)

        # Find elements to remove from M
        remove_from_M = set()

        for X in M:
            heads = set()

            for t in protocol.transitions:
                # Case XY -> CD where C != X != D
                if (X in t.pre) and (X not in t.post):
                    heads.add(t.pre)

            if not Phi.implies_all_absent_tautology_check(heads):
                remove_from_M.add(X)

        # Find elements to remove from N
        remove_from_N = set()

        for X in N:
            heads = set()

            for t in protocol.transitions:
                # Case XY -> CD where X != Y and [C = D = X or C != X != D]
                if (X != t.pre.other(X)) and (t.postset == {X} or
                                              X not in t.post):
                    heads.add(t.pre)
                # Case CD -> XY where C != X != D
                elif (X in t.post) and (X not in t.pre):
                    heads.add(t.pre)

            if not Phi.implies_all_absent_tautology_check(heads):
                remove_from_N.add(X)

        # Find elements to remove from O
        remove_from_O = set()

        for X in O:
            heads = set()

            for t in protocol.transitions:
                # Case CD -> XY where C != X != D
                if (X in t.post) and (X not in t.pre):
                    heads.add(t.pre)

            if not Phi.implies_all_absent_tautology_check(heads):
                remove_from_O.add(X)

        return (M - remove_from_M,
                N - remove_from_N,
                O - remove_from_O)

    # Compute greatest fixed-point of f
    E  = {v.state for v in valuation if     valuation[v] and not v.unique}
    Eu = {v.state for v in valuation if     valuation[v] and     v.unique}
    D  = {v.state for v in valuation if not valuation[v] and not v.unique}
    E_, Eu_, D_ = f(E, Eu, D)

    while (E, Eu, D) != (E_, Eu_, D_):
        E,  Eu,  D  = E_, Eu_, D_
        E_, Eu_, D_ = f(E, Eu, D)

    return (E, Eu, D)

def compute_U(protocol, disabled, K_, refined):
    def less(A, B):
        others = {head.other(A) for head in K_ if A in head}

        return all(upair(B, C) in K_ for C in others)

    def less_upair(x, y):
        A, B = tuple(x)
        C, D = tuple(y)

        return (less(A, C) and less(B, D)) or (less(A, D) and less(B, C))

    return {t.post for t in protocol.transitions
            if ((t.pre not in disabled) and (t.post not in K_) and
                ((not refined) or (not less_upair(t.pre, t.post))))}

def compute_K_from_invariants(protocol, stage):
    T = set()
    Phi = stage_formula(stage)

    trans = []
    for t in protocol.transitions:
        if ((not t.silent()) and
            (not Phi.implies_all_absent_tautology_check({t.pre}))):
            trans.append(t)

    ctx = z3.Context()
    solver = z3.Solver(ctx=ctx)
    t_vars = [ z3.Int(f't{idx}', ctx=ctx) for idx in range(len(trans)) ]
    for t_var in t_vars:
        solver.add(t_var >= 0)

    for q in protocol.states:
        sum_terms = []
        for idx,t in enumerate(trans):
            val = t.post.count(q) - t.pre.count(q)
            if val == 1:
                sum_terms.append(t_vars[idx])
            elif val == -1:
                sum_terms.append(-t_vars[idx])
            elif val != 0:
                sum_terms.append(val * t_vars[idx])
        solver.add(z3.Sum(sum_terms) == 0)

    # print(solver.to_smt2())

    # print("Checking new stage...")
    for idx,t in enumerate(trans):
        solver.push()
        solver.add(t_vars[idx] >= 1)
        result = solver.check()
        solver.pop()
        if result == z3.sat:
            #print("Transition {} part of T-invariant".format(t))
            pass
        elif result == z3.unsat:
            #print("Transition {} not part of T-invariant".format(t))
            T.add(t)
        else:
            raise Exception("Unknown sat result")

    K = {t.pre for t in T}
    return K, T

def new_stages(protocol, stage, mem, use_t_invariants):
    # No new stages if stable consensus
    if ((protocol.false_states <= stage.absent) or
        (protocol.true_states  <= stage.absent)):
        return [], True

    if use_t_invariants:
        # Compute K and T from transition invariants
        K, T = compute_K_from_invariants(protocol, stage)
    else:
        # Compute K from transformation graph
        K, T = compute_K(protocol, stage, mem)
    if len(K) == 0:
        return None, False

    refined = True
    # Refine K with greatest fixed-point computation
    K_ = refine_K(protocol, stage, K, mem)
    T_ = {t for t in T if t.pre in K_}

    if len(K_) == 0:
        K_ = K
        T_ = T
        refined = False

    # Add information about disabled heads and
    # transitions used to disable heads
    stage._K = K_
    stage._T = T_

    # To prevent an unnecessary blowup in the number of stage...
    pass # Not implemented

    # Compute new stages
    U = compute_U(protocol, stage.disabled, K_, refined)

    phi_ = Formula()
    phi_.assert_formula(stage.formula)
    phi_.assert_some_pair_present(U)
    phi_.make_disjunctive()

    Phi = stage_formula(stage)
    Phi.assert_all_pairs_absent(K_)
    Phi.assert_formula(phi_)

    stages = []

    for val in Phi.solutions():
        enlarged  = enlarge_stage_components(protocol, stage, val, K_)
        disabled_ = stage.disabled | K_

        stages.append(Stage(*enlarged, disabled_, phi_, parent=stage))

    return stages, refined

def check_termination_witness(protocol, stage, refined):
    if refined:
        T_C = stage._T
        K_C = stage._K
    else:
        # Currently just use all non-disabled transitions for set H
        # TODO: identify smaller set where some transition is always
        #       enabled in current stage
        T_C = {t for t in protocol.transitions if t not in stage.disabled}
        K_C = {t.pre for t in T_C}
    P_C = set()

    for head in K_C:
        if head in protocol.problematic_heads:
            # Head problematic due to missing head in concrete protocol
            # print(("Head {} potentially problematic due to "
            #        "missing concrete head").format(head))
            P_C.add(head)
        else:
            for t in protocol.transitions:
                if (t.pre == head) and (not t in T_C):
                    # Head problematic due to missing transition in T_C
                    # print(("Head {} potentially problematic due to "
                    #        "missing transition {}").format(head, t))
                    P_C.add(head)

    if not P_C:
        # strong witness
        return True
    else:
        # Quasi-tautology check
        formula = stage_formula(stage)
        formula.assert_all_pairs_absent(K_C - P_C)
        formula.assert_some_pair_present(P_C)

        O = [protocol.false_states, protocol.true_states]
        result = (formula.implies_all_states_absent_tautology_check(O[0]) or
                  formula.implies_all_states_absent_tautology_check(O[1]))
        if result:
            # weak witness
            return False
        else:
            return None

def is_good(protocol, stage, mem, use_t_invariants):
    graph, vertices, edges   = transformation_graph(protocol, stage)
    components, _, is_bottom = label_components(graph, attractors=True)

    if use_t_invariants:
        # Compute K and T for comparison from transformation graph
        K, T = compute_K(protocol, stage, mem)
        # Refine K with greatest fixed-point computation
        K_C = refine_K(protocol, stage, K, mem)
        T_C = {t for t in T if t.pre in K_C}
        if K_C != stage._K:
            return False
    else:
        K_C = stage._K
        T_C = stage._T

    A_C = {q for q in vertices if not is_bottom[components[vertices[q]]]}

    # Checks if SCC i is a predecessor of SCC j
    def pred_scc(i, j):
        for (p, q) in edges:
            if (components[vertices[p]] == i and components[vertices[q]] == j):
                return True

        return False

    # Checks if every AB -> CD in T_C generates an outgoing edge of A
    # in the transformation graph leading to an SCC different from the
    # one of A
    def all_generate_edge(AB, A):
        for t in T_C:
            if t.pre == AB:
                C = t.post.some()
                D = t.post.other(C)
                i = components[vertices[A]]
                j = components[vertices[C]]
                k = components[vertices[D]]

                if not ((t in edges.get((A, C), set()) and pred_scc(i, j)) or
                        (t in edges.get((A, D), set()) and pred_scc(i, k))):
                    return False

        return True

    # Stage is good?
    for A in A_C:
        K_A = {head for head in K_C if ((A in head) and
                                        all_generate_edge(head, A))}
        U_A = {B for B in A_C if pred_scc(components[vertices[B]],
                                          components[vertices[A]])}

        formula = stage_formula(stage)
        formula.assert_some_states_present({A})
        formula.assert_all_states_absent(U_A)
        formula.assert_some_pair_present(K_C)

        if not formula.implies_some_present_tautology_check(K_A):
            return False

    return True
