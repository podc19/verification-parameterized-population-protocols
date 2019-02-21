class Var:
    def __init__(self, state, unique=False):
        self._state  = state
        self._unique = unique

    @property
    def state(self):
        return self._state
    
    @property
    def unique(self):
        return self._unique

    def opposite(self):
        return Var(self.state, not self.unique)

    def __eq__(self, other):
        return (self._state == other._state and self._unique == other._unique)

    def __ne__(self, other):
        return (self != other)

    def __hash__(self):
        return hash((self._state, self._unique))

    def __str__(self):
        return "{}{}".format(self._state, "!" if self._unique else "")

    def __repr__(self):
        return str(self)
