from collections import Counter
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from itertools import combinations
from alpha_miner_evaluator import ProcessModelEvaluator

def print_pairs(pairs, label: str):
    """
    Print pairs in a cleaner format without the 'frozenset' text.
    
    Args:
        pairs: Set of pairs to print
        label: Label to print before the pairs
    """
    # Convert pairs to string and clean up the format
    pairs_str = str(pairs)
    # Remove 'frozenset' text
    pairs_str = pairs_str.replace('frozenset', '')
    print(f"\n{label}: {pairs_str}")

def alpha_miner(event_log):
    """
    Implements the Alpha Algorithm for Process Mining.
    
    Args:
        event_log (list): List of traces, where each trace is a list of activities
    
    Returns:
        tuple: (NetworkX DiGraph object representing the Petri net, DataFrame of footprint matrix)
    """
    # Step 1: Extract unique events and initial/final events
    unique_events = {event for trace in event_log for event in trace}
    initial_events = {trace[0] for trace in event_log}  # TI
    final_events = {trace[-1] for trace in event_log}   # TO

    # Step 2: Construct direct succession relations
    def get_direct_succession(traces):
        direct_succession = set()
        for trace in traces:
            for i in range(len(trace) - 1):
                direct_succession.add((trace[i], trace[i + 1]))
        return direct_succession

    direct_succession = get_direct_succession(event_log)
    
    def get_relations():
        """Calculate causality, parallel, and choice relations between activities."""
        causality = set()
        parallel = set()
        choice = set()
        
        for a in unique_events:
            for b in unique_events:
                if a != b:
                    follows_ab = (a, b) in direct_succession
                    follows_ba = (b, a) in direct_succession
                    
                    if follows_ab and not follows_ba:
                        causality.add((a, b))
                    elif follows_ba and not follows_ab:
                        causality.add((b, a))
                    elif follows_ab and follows_ba:
                        parallel.add((a, b))
                        parallel.add((b, a))
                    else:
                        choice.add((a, b))
                        choice.add((b, a))
        
        return causality, parallel, choice

    causality_rel, parallel_rel, choice_rel = get_relations()

    def create_footprint_matrix():
        """Create the footprint matrix showing relations between activities."""
        matrix = {a: {b: '#' for b in unique_events} for a in unique_events}
        for a, b in causality_rel:
            matrix[a][b] = '→'
            matrix[b][a] = '→'
        for a, b in parallel_rel:
            matrix[a][b] = '||'
            matrix[b][a] = '||'
        for a in unique_events:
            matrix[a][a] = '#'
        return matrix

    footprint_matrix = create_footprint_matrix()
    footprint_df = pd.DataFrame(footprint_matrix)
    print("\nFootprint Matrix:")
    print(footprint_df)
    print("\nDirect Succession Relations:", direct_succession)
    print("\nCausality Relations:", causality_rel)
    print("\nParallel Relations:", parallel_rel)
    print("\nChoice Relations:", choice_rel)

    # Step 3: Find pairs of sets (XL)
    def find_pairs():
        """Find valid pairs of sets for place creation."""
        XL = set()
        for a_set in [set(combo) for n in range(1, len(unique_events) + 1) 
                     for combo in combinations(unique_events, n)]:
            for b_set in [set(combo) for n in range(1, len(unique_events) + 1) 
                         for combo in combinations(unique_events, n)]:
                
                if all((x, y) in choice_rel or x == y 
                       for x in a_set for y in a_set):
                    if all((x, y) in choice_rel or x == y 
                           for x in b_set for y in b_set):
                        if all((a, b) in causality_rel 
                               for a in a_set for b in b_set):
                            XL.add((frozenset(a_set), frozenset(b_set)))
        return XL

    XL = find_pairs()
    print_pairs(XL, "XL (Valid Pairs)")

    # Step 4: Find maximal pairs (YL)
    YL = set()
    for pair in XL:
        if not any(pair != other and 
                  pair[0].issubset(other[0]) and 
                  pair[1].issubset(other[1]) 
                  for other in XL):
            YL.add(pair)
    
    print_pairs(YL, "YL (Maximal Pairs)")

    # Step 5: Create places
    places = set()
    place_mapping = {}  # To keep track of place names

    # Start numbering from p1
    place_counter = 1

    for idx, (a_set, b_set) in enumerate(YL):
        place_name = f"p{place_counter}"
        places.add(place_name)
        place_mapping[(a_set, b_set)] = place_name
        place_counter += 1

    places.add('start')
    places.add('end')

    # Step 6: Create flow relations
    flow_relations = set()
    
    # Add flows between transitions and places
    for (a_set, b_set), place in place_mapping.items():
        for a in a_set:
            flow_relations.add((a, place))
        for b in b_set:
            flow_relations.add((place, b))
    
    # Add flows from start place and to end place
    for t in initial_events:
        flow_relations.add(('start', t))
    for t in final_events:
        flow_relations.add((t, 'end'))

    print("\nPlaces:", places)
    print("\nFlow Relations:", flow_relations)

    # Step 7: Create and visualize Petri net
    petri_net = nx.DiGraph()
    
    # Add nodes
    for event in unique_events:
        petri_net.add_node(event, node_type='transition')
    for place in places:
        petri_net.add_node(place, node_type='place')
    
    # Add edges
    petri_net.add_edges_from(flow_relations)
    
    # Visualization
    plt.figure(figsize=(15, 8))
    
    # First, create a layered structure based on the flow of the Petri net
    def create_layers(petri_net):
        layers = {}
        # Start with the initial node
        current_layer = 0
        nodes_to_process = ['start']
        processed_nodes = set()
        
        while nodes_to_process:
            current_nodes = []
            next_nodes = set()
            
            for node in nodes_to_process:
                if node not in processed_nodes:
                    current_nodes.append(node)
                    processed_nodes.add(node)
                    # Add successors to next layer
                    next_nodes.update(list(petri_net.successors(node)))
            
            if current_nodes:
                layers[current_layer] = current_nodes
            
            nodes_to_process = list(next_nodes - processed_nodes)
            current_layer += 1
            
        return layers

    # Create dynamic layout
    layers = create_layers(petri_net)
    pos = {}
    
    # Assign x coordinates based on layer
    max_layers = len(layers)
    for layer_idx, nodes in layers.items():
        x_coord = layer_idx / (max_layers - 1)
        
        # Sort nodes within layer (places before transitions for consistent ordering)
        nodes.sort(key=lambda n: ('1' if n.startswith('p') or n in ['start', 'end'] else '2') + n)
        
        # Assign y coordinates within layer
        num_nodes = len(nodes)
        for node_idx, node in enumerate(nodes):
            if num_nodes == 1:
                y_coord = 0.5
            else:
                # Spread nodes evenly in the vertical space
                y_coord = node_idx / (num_nodes - 1) if num_nodes > 1 else 0.5
            pos[node] = (x_coord, y_coord)
    
    # Adjust positions to prevent arrows from entering nodes
    pos = {node: (x * 1.2, y * 1.2) for node, (x, y) in pos.items()}  # Spread out nodes more
    
    # Draw places (circles) with light blue color
    place_nodes = [node for node, attr in petri_net.nodes(data=True) 
                   if attr.get('node_type') == 'place']
    nx.draw_networkx_nodes(petri_net, pos, nodelist=place_nodes, 
                          node_color='lightblue', node_shape='o', 
                          node_size=700, edgecolors='black')
    
    # Draw transitions (squares) with light green color
    trans_nodes = [node for node, attr in petri_net.nodes(data=True) 
                   if attr.get('node_type') == 'transition']
    nx.draw_networkx_nodes(petri_net, pos, nodelist=trans_nodes, 
                          node_color='lightgreen', node_shape='s', 
                          node_size=700, edgecolors='black')
    
    # Draw edges with adjusted arrow positions
    edge_list = list(petri_net.edges())
    nx.draw_networkx_edges(petri_net, pos,
                          edgelist=edge_list,
                          edge_color='black',
                          width=1.5,
                          arrows=True,
                          arrowsize=20,
                          arrowstyle='-|>',
                          connectionstyle='arc3,rad=0.1',
                          node_size=700,  # Match node size to prevent overlap
                          min_source_margin=15,  # Space from source node
                          min_target_margin=12)  # Space from target node
    
    # Draw labels
    nx.draw_networkx_labels(petri_net, pos, font_size=8, font_weight='bold')
    
    plt.title("Alpha Algorithm Petri Net", pad=20, fontsize=16)
    plt.axis('off')
    plt.margins(0.2)
    plt.tight_layout()
    
    return petri_net, footprint_df

def read_event_log(filename):
    event_logs = []
    with open(filename, 'r') as file:
        for line in file:
            # Stop reading when we hit the Key section
            if line.strip().startswith('**Test Traces**') or line.strip().startswith('#Test Traces') or line.strip().startswith('Test Traces'):

                break
            # Skip empty lines
            if not line.strip():
                continue
            # Convert string representation of list to actual list
            try:
                events = eval(line.strip())
                event_logs.append(events)
            except:
                continue
    return event_logs

def read_test_traces(filename):
    test_traces = []
    is_test_section = False  # Flag to track if we are in the Test Traces section

    phrases = ["**Test Traces**", "#Test Traces", "Test Traces"]
    found = False  
    with open(filename, 'r') as file:
        for line in file:
            stripped_line = line.strip()
            if any(phrase in stripped_line for phrase in phrases):
                found = False  
                is_test_section = True
                continue  # Skip the header line

   
            # Stop reading when we hit another section
            if is_test_section and stripped_line.startswith("#"):
                break

            # If in the Test Traces section, read the traces
            if is_test_section and stripped_line:
                try:
                    # Convert string representation of list to actual list
                    events = eval(stripped_line)
                    test_traces.append(events)
                except (SyntaxError, NameError):
                    continue

    return test_traces


# MAIN FUNCTION FOR ALL.
def main():
    # Read event log from file
    file_path = "event_log.txt"
    event_log = read_event_log(file_path)
    
    if not event_log:
        print("Failed to read event log from file.")
        return
    
    print("Event Log:", event_log)
    petri_net, footprint_matrix = alpha_miner(event_log)

      # Create the evaluator
    evaluator =  ProcessModelEvaluator(event_log, petri_net)

    # Load test traces from a file
    filename = "event_log.txt"  # Replace with your actual file path
    test_traces = read_test_traces(filename)
    print("-------------------------------------Test Traces:", test_traces)

    if not test_traces:
        print("No test traces found. Exiting...")
    else:
        # Calculate metrics
        fitness_score = evaluator.calculate_fitness(event_log)
        precision_score = evaluator.calculate_precision(test_traces)

        # Print metrics
        print(f"\nFitness Score: {fitness_score:.3f}")
        print(f"Precision Score: {precision_score:.3f}")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()