# -*- coding: utf-8 -*-
import pprint

class Stage:
    def __init__(self, present, present_unique, absent, disabled,
                 formula, parent=None):
        self._present        = present
        self._present_unique = present_unique
        self._absent         = absent
        self._disabled       = disabled
        self._parent         = parent
        self._formula        = formula
        self._K              = set()
        self._T              = set()

    @property
    def present(self):
        return self._present

    @property
    def present_unique(self):
        return self._present_unique

    @property
    def absent(self):
        return self._absent

    @property
    def disabled(self):
        return self._disabled

    @property
    def formula(self):
        return self._formula

    @property
    def parent(self):
        return self._parent

    def depth(self):
        d = 0
        p = self

        while p.parent is not None:
            p  = p.parent
            d += 1

        return d

    def __str__(self):
        def pretty_set(S):
            return pprint.pformat(S).replace("'", "") if len(S) > 0 else "{}"
            # return ", ".join(map(str, S))

        if self._K or self._T:
            fmt = ("E = {}\n E! = {}\n D = {}\n T = {}\n "
                   "K_C = {}\n T_C = {}")

            return fmt.format(pretty_set(self._present),
                              pretty_set(self._present_unique),
                              pretty_set(self._absent),
                              pretty_set(self._disabled),
                              pretty_set(self._K),
                              pretty_set(self._T))
        else:
            fmt = "E = {}\n E! = {}\n D = {}\n T = {}"

            return fmt.format(pretty_set(self._present),
                              pretty_set(self._present_unique),
                              pretty_set(self._absent),
                              pretty_set(self._disabled))

    # def __eq__(self, other):
    #     return ((self._present        == other._present)        and
    #             (self._present_unique == other._present_unique) and
    #             (self._absent         == other._absent)         and
    #             (self._disabled       == other._disabled))

    # def __ne__(self, other):
    #     return not (self == other)

    def __repr__(self):
        return str(self)
