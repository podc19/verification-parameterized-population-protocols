from variable import Var

class Valuation:
    def __init__(self):
        self._vars = dict()

    def __setitem__(self, var, value):
        if value:
            self._vars[var] = True

            if var.unique:
                self._vars[var.opposite()] = True
        else:
           self._vars[var] = False

           if not var.unique:
                self._vars[var.opposite()] = False

    def __getitem__(self, var):
        return self._vars.get(var, None)

    def domain(self):
        return set(self._vars.keys())

    def __iter__(self):
        for var in self._vars:
            yield var

    def __eq__(self, other):
        return self._vars == other._vars

    def __hash__(self):
        return hash(frozenset([(var, self[var]) for var in self]))

    def __ne__(self, other):
        return (self != other)

    def present_states(self):
        return {v.state for v in self if self[v]}

    def absent_states(self):
        return {v.state for v in self if not self[v] and not v.unique}

    def unique_states(self):
        return {v.state for v in self if self[v] and v.unique}

    def non_unique_states(self):
        return {v.state for v in self if not self[v] and v.unique}    

    def __str__(self):
        expr = ["{} = {}".format(var, "tt" if self[var]
                                 else "ff") for var in self]

        return "({})".format(", ".join(expr))

    def __repr__(self):
        return str(self)
