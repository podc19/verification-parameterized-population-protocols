import z3
from variable import Var
from valuation import Valuation

class Formula:
    def __init__(self):
        self._domain = set()
        self._assertions = []

    @property
    def domain(self):
        return self._domain

    def __iter__(self):
        for v in self.domain:
            yield v

    @staticmethod
    def _id(var):
        return z3.Bool("{}{}".format(var.state,
                                     "!" if var.unique else ""))

    @staticmethod
    def _states_constraints_and(states, unique_states):
        conjuncts = []
        domain    = set()

        for q in states:
            var = Var(q, unique=unique_states)
            
            conjuncts.append(z3.Not(Formula._id(var)))
            domain.add(var)

        return (z3.And(conjuncts), domain)

    @staticmethod
    def _states_constraints_or(states, unique_states):
        conjuncts = []
        domain    = set()

        for q in states:
            var = Var(q, unique=unique_states)
            
            conjuncts.append(z3.Not(Formula._id(var)))
            domain.add(var)

        return (z3.Or(conjuncts), domain)
            
    def assert_some_states_present(self, states, unique=False):
        constraints, domain = Formula._states_constraints_and(states, unique)
            
        self._assertions.append(z3.Not(constraints))
        self._domain |= domain

    def assert_all_states_present(self, states, unique=False):
        constraints, domain = Formula._states_constraints_or(states, unique)

        self._assertions.append(z3.Not(constraints))
        self._domain |= domain
        
    def assert_some_states_absent(self, states, unique=False):
        constraints, domain = Formula._states_constraints_or(states, unique)

        self._assertions.append(constraints)
        self._domain |= domain

    def assert_all_states_absent(self, states, unique=False):
        constraints, domain = Formula._states_constraints_and(states, unique)

        self._assertions.append(constraints)
        self._domain |= domain

    @staticmethod
    def _pairs_constraints(pairs):
        conjuncts = []
        domain    = set()

        for pair in pairs:
            p, q = tuple(pair)

            if p != q:
                domain |= {Var(p), Var(q)}
                conjuncts.append(z3.Or(z3.Not(Formula._id(Var(p))),
                                       z3.Not(Formula._id(Var(q)))))
            else:
                domain |= {Var(p), Var(p, True)}
                conjuncts.append(z3.Or(z3.Not(Formula._id(Var(p))),
                                              Formula._id(Var(p, True))))
                      
        return (conjuncts, domain)

    def _consistency_constraints(self):
        conjuncts = []
        
        for v in self._domain:
            if (v.unique):
                expr = z3.Implies(Formula._id(v),
                                  Formula._id(v.opposite()))
            else:
                expr = z3.Implies(z3.Not(Formula._id(v)),
                                  z3.Not(Formula._id(v.opposite())))

            conjuncts.append(expr)

        return z3.And(conjuncts)

    def assert_all_pairs_absent(self, pairs):
        constraints, domain = Formula._pairs_constraints(pairs)

        self._assertions.append(z3.And(constraints))
        self._domain |= domain

    def assert_some_pair_present(self, pairs):
        constraints, domain = Formula._pairs_constraints(pairs)

        self._assertions.append(z3.Not(z3.And(constraints)))
        self._domain |= domain

    def assert_some_pair_absent(self, pairs):
        constraints, domain = Formula._pairs_constraints(pairs)

        self._assertions.append(z3.Or(constraints))
        self._domain |= domain

    def assert_all_pair_present(self, pairs):
        constraints, domain = Formula._pairs_constraints(pairs)

        self._assertions.append(z3.Not(z3.Or(constraints)))
        self._domain |= domain

    def implies_all_absent_tautology_check(self, pairs):
        solver = z3.Solver()
        constraints, _ = Formula._pairs_constraints(pairs)

        solver.add(self._consistency_constraints())
        solver.add(z3.Not(z3.Implies(z3.And(self._assertions),
                                     z3.And(constraints))))

        result = solver.check()
        
        return (result == z3.unsat)

    def implies_some_present_tautology_check(self, pairs):
        solver = z3.Solver()
        constraints, _ = Formula._pairs_constraints(pairs)

        solver.add(self._consistency_constraints())
        solver.add(self._assertions) # (assertions and constraints) equiv. to:
        solver.add(z3.And(constraints)) # not(assertions => not constraints)

        result = solver.check()
        
        return (result == z3.unsat)

    def implies_all_states_absent_tautology_check(self, states):
        solver = z3.Solver()
        constraints, _ = Formula._states_constraints_and(states, False)

        solver.add(self._consistency_constraints())
        solver.add(z3.Not(z3.Implies(z3.And(self._assertions),
                                     z3.And(constraints))))

        result = solver.check()
        
        return (result == z3.unsat)

    def solutions(self):
        solver = z3.Solver()
        solver.add(self._consistency_constraints())
        solver.add(self._assertions)
        
        sol = []

        while (solver.check() == z3.sat):
            model = solver.model()
            valuation = Valuation()

            for var in self:
                valuation[var] = z3.is_true(model[Formula._id(var)])

            sol.append(valuation)

            # Forbid solution in future checks
            solver.add(z3.Or([z3.Not(Formula._id(v)) if valuation[v]
                              else Formula._id(v) for v in valuation]))

        return sol

    def implies(self, formula):
        solver = z3.Solver()

        solver.add(self._consistency_constraints())
        solver.add(formula._consistency_constraints())
        solver.add(z3.Not(z3.Implies(z3.And(self._assertions),
                                     z3.And(formula._assertions))))

        result = solver.check()
        
        return (result == z3.unsat)

    def make_disjunctive(self):
        self._assertions = [z3.Or(self._assertions)]

    def assert_formula(self, formula):
        self._domain |= formula._domain
        self._assertions.extend(formula._assertions)
    
    def __str__(self):
        return str(self._assertions)
                      
    def __repr__(self):
        return str(self)
