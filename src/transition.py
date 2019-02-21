# -*- coding: utf-8 -*-
from unordered_pair import upair

class Transition:
    def __init__(self, pre, post):
        self._pre     = upair(pre)
        self._post    = upair(post)
        self._preset  = frozenset(self._pre)
        self._postset = frozenset(self._post)

    @property
    def pre(self):
        return self._pre

    @property
    def post(self):
        return self._post

    @property
    def preset(self):
        return self._preset

    @property
    def postset(self):
        return self._postset

    def silent(self):
        return (self.pre == self.post)

    def increased(self, q):
        return (self.pre.count(q) < self.post.count(q))

    def decreased(self, q):
        return (self.pre.count(q) > self.post.count(q))

    def unchanged(self, q):
        return (self.pre.count(q) == self.post.count(q))
        
    def __eq__(self, other):
        return (self._pre == other._pre and self._post == other._post)

    def __ne__(self, other):
        return (self != other)

    def __hash__(self):
        return hash((self._pre, self._post))
    
    def __str__(self):
        return "{} →  {}".format(str(self._pre), str(self._post))

    def __repr__(self):
        return str(self)
