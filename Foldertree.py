import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import io
from PIL import Image
import os

# Page configuration
st.set_page_config(
    page_title="Interactive Folder Tree Visualization",
    page_icon="🌳",
    layout="wide"
)

# Initialize session state for expanded nodes
if 'expanded_nodes' not in st.session_state:
    st.session_state.expanded_nodes = set(["root"])
if 'selected_node' not in st.session_state:
    st.session_state.selected_node = None

# Function to process Excel data
def process_excel_data(file):
    try:
        df = pd.read_excel(file)
        flat_paths = []
        
        for _, row in df.iterrows():
            path_parts = [str(cell) for cell in row if pd.notna(cell) and str(cell).strip()]
            if path_parts:
                path = '/'.join(path_parts)
                flat_paths.append(path)
        
        return flat_paths, None
    except Exception as e:
        return [], f"Error processing Excel file: {str(e)}"

# Function to build folder hierarchy
def build_folder_hierarchy(paths):
    try:
        # Create a dictionary to represent the folder structure
        folder_structure = {}
        
        for path in paths:
            parts = path.split('/')
            current_level = folder_structure
            
            for i, part in enumerate(parts):
                if part not in current_level:
                    current_level[part] = {}
                
                current_level = current_level[part]
        
        return folder_structure, None
    except Exception as e:
        return {}, f"Error building folder hierarchy: {str(e)}"

# Function to create a NetworkX graph from folder hierarchy
def create_graph(folder_structure, parent_id=None, level=0, max_depth=None):
    G = nx.DiGraph()
    
    # Root node handling
    if parent_id is None:
        parent_id = "root"
        G.add_node(parent_id, label="Root")
    
    # Process each folder in the current level
    for folder_name, subfolders in folder_structure.items():
        # Create a unique ID for this folder
        folder_id = f"{parent_id}_{folder_name}" if parent_id != "root" else folder_name
        
        # Check if this node should be visible based on expanded state
        is_expanded = parent_id in st.session_state.expanded_nodes
        
        if is_expanded:
            # Add node and edge
            G.add_node(folder_id, label=folder_name)
            G.add_edge(parent_id, folder_id)
            
            # Process subfolders recursively if this node is expanded and we haven't reached max depth
            if folder_id in st.session_state.expanded_nodes and (max_depth is None or level < max_depth):
                subgraph = create_graph(subfolders, folder_id, level + 1, max_depth)
                G = nx.compose(G, subgraph)
    
    return G

# Function to get direct children of a node
def get_direct_children(folder_structure, node_id):
    direct_children = set()
    
    if node_id == "root":
        # For root, all top-level folders are direct children
        for folder_name in folder_structure.keys():
            child_id = folder_name
            direct_children.add(child_id)
    else:
        # Extract the folder name from the node_id
        parts = node_id.split('_')
        
        # Navigate to the correct level in the folder structure
        current_level = folder_structure
        for part in parts[1:]:  # Skip the first part which is the parent
            if part in current_level:
                current_level = current_level[part]
            else:
                return direct_children  # Return empty set if path not found
        
        # Add all direct children
        for subfolder_name in current_level.keys():
            child_id = f"{node_id}_{subfolder_name}"
            direct_children.add(child_id)
    
    return direct_children

# Function to draw the graph
def draw_graph(G, direction="LR"):
    # Create a figure
    plt.figure(figsize=(12, 8))
    
    # Use graphviz_layout for tree-like structure
    if direction == "LR":
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot", args="-Grankdir=LR")
    elif direction == "RL":
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot", args="-Grankdir=RL")
    elif direction == "UD":
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    else:  # DU
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot", args="-Grankdir=BT")
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_size=500, node_color='lightblue', alpha=0.8)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, arrows=True, arrowsize=15)
    
    # Draw labels
    labels = {node: G.nodes[node].get('label', node) for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=10)
    
    plt.axis('off')
    
    # Save figure to a buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    buf.seek(0)
    
    # Convert buffer to image
    img = Image.open(buf)
    return img

# Main application layout
st.title("Interactive Folder Tree Visualization")

# Sidebar for file upload and options
with st.sidebar:
    st.header("Upload")
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    
    st.header("Options")
    direction = st.selectbox("Layout Direction", 
                           options=["LR", "RL", "UD", "DU"],
                           index=0,
                           help="LR: Left to Right, RL: Right to Left, UD: Up to Down, DU: Down to Up")
    
    # Reset button
    if st.button("Reset View"):
        st.session_state.expanded_nodes = set(["root"])
        st.session_state.selected_node = None
        st.rerun()

# Main content area
col1, col2 = st.columns([3, 1])

with col1:
    if uploaded_file is not None:
        # Process the Excel file
        paths, error = process_excel_data(uploaded_file)
        
        if error:
            st.error(error)
        elif not paths:
            st.warning("No valid folder paths found in the Excel file.")
        else:
            # Build folder hierarchy
            folder_structure, error = build_folder_hierarchy(paths)
            
            if error:
                st.error(error)
            else:
                # Create graph
                G = create_graph(folder_structure)
                
                # Draw graph
                img = draw_graph(G, direction)
                
                # Display the graph
                st.info("👆 Click on a node in the metadata panel to expand/collapse it")
                st.image(img, use_column_width=True)
                
                # Create a list of all nodes for selection
                all_nodes = list(G.nodes())
                
                # Allow node selection via selectbox
                selected_node = st.selectbox("Select a node to expand/collapse:", 
                                           options=all_nodes,
                                           format_func=lambda x: G.nodes[x].get('label', x) if x != 'root' else 'Root')
                
                if selected_node:
                    st.session_state.selected_node = selected_node
    else:
        st.info("Upload an Excel file to visualize your folder structure")

# Metadata panel
with col2:
    st.header("Metadata")
    
    if st.session_state.selected_node:
        st.markdown("---")
        node_id = st.session_state.selected_node
        
        # Get node label
        if uploaded_file is not None:
            G = create_graph(folder_structure)
            node_label = G.nodes[node_id].get('label', node_id) if node_id != 'root' else 'Root'
        else:
            node_label = node_id.split('_')[-1] if '_' in node_id else node_id
        
        st.markdown(f"### Selected Node: {node_label}")
        
        # Display node status
        is_expanded = node_id in st.session_state.expanded_nodes
        status = "Expanded" if is_expanded else "Collapsed"
        st.markdown(f"**Status:** {status}")
        
        # Add buttons to expand/collapse
        col_a, col_b = st.columns(2)
        
        with col_a:
            if is_expanded:
                if st.button("Collapse Node"):
                    st.session_state.expanded_nodes.remove(node_id)
                    st.rerun()
            else:
                if st.button("Expand Node"):
                    st.session_state.expanded_nodes.add(node_id)
                    st.rerun()
        
        with col_b:
            # Add button to expand one level (direct children only)
            if st.button("Expand One Level"):
                if uploaded_file is not None:
                    try:
                        # Process the Excel file again to get the folder structure
                        paths, _ = process_excel_data(uploaded_file)
                        folder_structure, _ = build_folder_hierarchy(paths)
                        
                        # Get direct children of the selected node
                        direct_children = get_direct_children(folder_structure, node_id)
                        
                        # Add the selected node and its direct children to expanded_nodes
                        st.session_state.expanded_nodes.add(node_id)
                        st.session_state.expanded_nodes.update(direct_children)
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error expanding children: {str(e)}")
    else:
        st.info("Select a node to view its details")
