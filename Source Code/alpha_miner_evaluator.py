import networkx as nx
from typing import List, Tuple

class ProcessModelEvaluator:
    def __init__(self, event_log, petri_net):
        self.event_log = event_log
        self.petri_net = petri_net
        self.evaluation_metrics = {}

    def calculate_fitness(self, traces: List[List[str]]) -> float:
        """Calculate fitness score for actual traces"""
        total_score = 0
        total_traces = len(traces)
        
        for trace in traces:
            if not trace:
                continue
            
            # Initialize marking with start place
            current_marking = {'start'}
            moves_possible = 0
            total_moves = len(trace)
            
            # Replay the trace
            for event in trace:
                # Get enabled transitions from current marking
                enabled = set()
                for place in current_marking:
                    enabled.update(self.petri_net.successors(place))
                    
                if event in enabled:
                    moves_possible += 1
                    # Update marking - get output places of the fired transition
                    current_marking = set(self.petri_net.successors(event))
            
            # Check if trace reached end
            if 'end' in current_marking:
                moves_possible += 1
                
            trace_fitness = moves_possible / (total_moves + 1)  # +1 for reaching end
            total_score += trace_fitness
        
        return total_score / total_traces if total_traces > 0 else 0.0

    def _replay_trace(self, trace: List[str]) -> float:
        """Replay a single trace and compute fitness"""
        if not trace:
            return 0
            
        # Find initial and final transitions
        initial_transitions = {node for node, in_degree 
                             in self.petri_net.in_degree() 
                             if in_degree == 1 and 
                             list(self.petri_net.predecessors(node))[0] == 'start'}
        
        final_transitions = {node for node, out_degree 
                            in self.petri_net.out_degree() 
                            if out_degree == 1 and 
                            list(self.petri_net.successors(node))[0] == 'end'}

        if trace[0] not in initial_transitions or trace[-1] not in final_transitions:
            return 0.0
            
        valid_moves = 0
        total_moves = len(trace) - 1
        
        for i in range(total_moves):
            current = trace[i]
            next_event = trace[i + 1]
            if self._is_valid_transition(current, next_event):
                valid_moves += 1
                
        return valid_moves / total_moves if total_moves > 0 else 1

    def _is_valid_transition(self, current: str, next_event: str) -> bool:
        """Check if transition between events is valid"""
        try:
            relation = self.petri_net.footprint_matrix.loc[current, next_event]
            return relation == '→'
        except:
            return False

    def calculate_precision(self, test_traces: List[List[str]]) -> float:
        """Calculate precision based on allowed vs observed behavior."""
        # Collect all observed transitions from test traces
        observed_transitions = set()
        for trace in test_traces:
            for i in range(len(trace) - 1):
                observed_transitions.add((trace[i], trace[i + 1]))
        
        # Collect all possible transitions from the model
        allowed_transitions = set()
        for state in self.petri_net.nodes():
            if state not in ['start', 'end'] and not str(state).startswith('p'):
                for place in self.petri_net.successors(state):
                    for transition in self.petri_net.successors(place):
                        if transition not in ['start', 'end'] and not str(transition).startswith('p'):
                            allowed_transitions.add((state, transition))
        
        # Count qualified traces (those that can be replayed)
        qualified_traces = sum(
            1 for trace in test_traces if all((trace[i], trace[i + 1]) in allowed_transitions for i in range(len(trace) - 1))
        )
        
        total_traces = len(test_traces)

        # Calculate precision
        if total_traces == 0:  # Avoid division by zero
            return 0.0
        
        precision = qualified_traces / total_traces
        
        return precision
