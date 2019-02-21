from graph_tool import Graph
from graph_tool.topology import shortest_distance
from formula import Formula
from speed import Speed
from stage import Stage
from stage_utils import new_stages, check_termination_witness, is_good

class StageTree:
    def __init__(self, protocol, max_depth=None,
                 check_termination_witness=False,
                 use_t_invariants=False):
        self._protocol  = protocol
        self._graph     = Graph(directed=True)
        self._vertices  = {}
        self._max_depth = max_depth
        self._check_termination_witness = check_termination_witness
        self._use_t_invariants = use_t_invariants

        self._terminal_stages = set()
        self._true_stages     = set()
        self._false_stages    = set()
        self._failed_stages   = set()
        self._all_good        = check_termination_witness
        self._strong_witness  = check_termination_witness
        self._failed_witness_stages = set()
        self._construct_tree()

    def _construct_tree(self):
        def add_vertex(stage):
            vertex = self._graph.add_vertex()
            index  = self._graph.vertex_index[vertex]

            self._vertices[index] = stage

            return index

        def add_edge(i, j):
            self._graph.add_edge(i, j)

        phi = Formula()
        phi.assert_some_states_present(self.protocol.initial_states)
        
        root_stage  = Stage(set(), set(), set(), set(), phi)
        root_index  = add_vertex(root_stage)
        unprocessed = [(root_index, root_stage)]
        mem         = {"K": {}, "K_": {}} # For memoization
        
        while len(unprocessed) > 0:
            index, stage = unprocessed.pop(0)
            children, refined = new_stages(self.protocol, stage, mem, self._use_t_invariants)

            if not refined:
                # TODO find criterion to continue if refinement fails
                self._failed_stages.add(index)
                continue
                #self._strong_witness = False
                #self._all_good = False

            # If node failed to be expanded,
            # then flag as failure and skip to next iteration
            if children is None:
                self._failed_stages.add(index)
                continue

            # Check termination witness
            if self._check_termination_witness:
                witness = check_termination_witness(self.protocol, stage, refined)
                if witness is None:
                    self._failed_witness_stages.add(index)
                elif witness is False:
                    self._strong_witness = False
                    self._all_good = False
                elif self._all_good:
                    self._all_good = is_good(self.protocol, stage, mem, self._use_t_invariants)

            # If stage in stable consensus, then flag its consensus
            if self.protocol.false_states <= stage.absent:
                self._true_stages.add(index)
            elif self.protocol.true_states <= stage.absent:
                self._false_stages.add(index)

            # Construct stage successors
            is_terminal = True

            for child_stage in children:
                is_terminal = False

                # Add child if depth does not exceed max depth
                if ((self._max_depth is None) or
                    (child_stage.depth() <= self._max_depth)):
                    child_index = add_vertex(child_stage)
                    add_edge(index, child_index)

                    unprocessed.append((child_index, child_stage))

            # If stage is terminal, then flag as terminal
            if is_terminal:
                self._terminal_stages.add(index)

    @property
    def protocol(self):
        return self._protocol

    @property
    def graph(self):
        return self._graph

    @property
    def stages(self):
        return self._vertices

    @property
    def terminal_stages(self):
        return self._terminal_stages

    @property
    def true_stages(self):
        return self._true_stages

    @property
    def false_stages(self):
        return self._false_stages

    @property
    def failed_stages(self):
        return self._failed_stages

    @property
    def failed_witness_stages(self):
        return self._failed_witness_stages

    def max_depth(self):
        return max(shortest_distance(self._graph,
                                     source=self._graph.vertex(0)))

    def terminates(self):
        if self._check_termination_witness and len(self.failed_stages) == 0:
            return True
        else:
            return None

    def witness(self):
        if self.terminates() is True and len(self.failed_witness_stages) == 0:
            return self._strong_witness
        else:
            return None

    def speed(self):
        if self.witness() is True:
            if self._all_good:
                return Speed.QUADRATIC_LOG
            else:
                return Speed.CUBIC
        else:
            return None
