# -*- coding: utf-8 -*-
class upair:
    # If y != None, constructs the unordered pair (x, y)
    # If y == None, constructs an unordered pair from iterable x, e.g. a tuple
    def __init__(self, x, y=None):
        if y is not None:
            self._x = x
            self._y = y
        else:
            self._x, self._y = tuple(x)

    def some(self):
        return self._x

    def other(self, x):
        if (self._x == x):
            return self._y
        else:
            return self._x

    def count(self, x):
        if x not in self:
            return 0
        elif self.other(x) != x:
            return 1
        else:
            return 2

    def __eq__(self, other):
        return ((self._x == other._x and self._y == other._y) or
                (self._x == other._y and self._y == other._x))

    def __ne__(self, other):
        return not (self == other)

    def __len__(self):
        return 2

    def __contains__(self, elem):
        return (self._x == elem or self._y == elem)

    def __iter__(self):
        yield self._x
        yield self._y

    def __hash__(self):
        return hash(hash((self._x, self._y)) + hash((self._y, self._x)))
    
    def __str__(self):
        return "⟅{}, {}⟆".format(self._x, self._y)

    def __repr__(self):
        return str(self)
