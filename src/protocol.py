# -*- coding: utf-8 -*-
class Protocol:
    def __init__(self, states, transitions,
                 alphabet, input_mapping, output_mapping,
                 problematic_heads = {}):
        self._states      = frozenset(states)
        self._transitions = frozenset(transitions)
        self._alphabet    = frozenset(alphabet)
        self._input       = dict(input_mapping)
        self._output      = dict(output_mapping)
        self._problematic_heads = frozenset(problematic_heads)

    @property
    def states(self):
        return self._states

    @property
    def transitions(self):
        return self._transitions

    @property
    def alphabet(self):
        return self._alphabet

    def input(self, state):
        return self._input.get(state, None)
    
    def output(self, state):
        return self._output.get(state, None)

    @property
    def initial_states(self):
        return {self._input[a] for a in self._input}

    @property
    def true_states(self):
        return {s for s in self.states if self.output(s) is 1}

    @property
    def false_states(self):
        return {s for s in self.states if self.output(s) is 0}

    @property
    def problematic_heads(self):
        return self._problematic_heads

    def __str__(self):
        return ("Q = {}\n"
                "T = {}\n"
                "Σ = {}\n"
                "I = {}\n"
                "O = {}\n"
                "H = {}\n").format(set(self._states),
                                 set(self._transitions),
                                 set(self._alphabet),
                                 self._input,
                                 self._output,
                                 set(self._problematic_heads))

    def __repr__(self):
        return str(self)
