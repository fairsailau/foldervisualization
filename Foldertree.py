import streamlit as st
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config
import random

# Page configuration
st.set_page_config(
    page_title="Interactive Folder Tree Visualization",
    page_icon="🌳",
    layout="wide"
)

# Initialize session state for expanded nodes
if 'expanded_nodes' not in st.session_state:
    st.session_state.expanded_nodes = set()
if 'selected_node' not in st.session_state:
    st.session_state.selected_node = None
if 'node_colors' not in st.session_state:
    st.session_state.node_colors = {}

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

# Function to create nodes and edges from folder hierarchy
def create_graph_elements(folder_structure, parent_id=None, level=0):
    nodes = []
    edges = []
    
    # Root node handling
    if parent_id is None:
        root_id = "root"
        nodes.append(Node(
            id=root_id,
            label="Root",
            size=25,
            shape="circle",
            color="#FF4500"  # Root node color
        ))
        parent_id = root_id
    
    # Process each folder in the current level
    for folder_name, subfolders in folder_structure.items():
        # Create a unique ID for this folder
        folder_id = f"{parent_id}_{folder_name}" if parent_id != "root" else folder_name
        
        # Check if this node should be visible based on expanded state
        is_expanded = parent_id in st.session_state.expanded_nodes or parent_id == "root"
        
        if is_expanded:
            # Get or assign a color for this node
            if folder_id not in st.session_state.node_colors:
                # Generate a light blue color with slight variations
                hue = 210 + random.randint(-15, 15)  # Blue with variation
                saturation = 70 + random.randint(-10, 10)
                lightness = 70 + random.randint(-10, 10)
                st.session_state.node_colors[folder_id] = f"hsl({hue}, {saturation}%, {lightness}%)"
            
            # Create node for this folder
            nodes.append(Node(
                id=folder_id,
                label=folder_name,
                size=20,
                shape="circle",
                color=st.session_state.node_colors[folder_id]
            ))
            
            # Create edge from parent to this folder
            edges.append(Edge(
                source=parent_id,
                target=folder_id,
                type="STRAIGHT"
            ))
            
            # Process subfolders recursively if this node is expanded
            if folder_id in st.session_state.expanded_nodes:
                sub_nodes, sub_edges = create_graph_elements(subfolders, folder_id, level + 1)
                nodes.extend(sub_nodes)
                edges.extend(sub_edges)
    
    return nodes, edges

# Function to get all child nodes of a given node
def get_all_children(folder_structure, node_id, prefix=""):
    all_children = set()
    
    if node_id == "root":
        # For root, all top-level folders are direct children
        for folder_name in folder_structure.keys():
            child_id = folder_name
            all_children.add(child_id)
            # Add children of this child recursively
            for subfolder_name, subfolders in folder_structure[folder_name].items():
                child_children = get_all_children({subfolder_name: subfolders}, child_id)
                all_children.update(child_children)
    else:
        # Extract the folder name from the node_id
        parts = node_id.split('_')
        folder_name = parts[-1]
        
        # Navigate to the correct level in the folder structure
        current_level = folder_structure
        for part in parts[1:]:  # Skip the first part which is the parent
            if part in current_level:
                current_level = current_level[part]
            else:
                return all_children  # Return empty set if path not found
        
        # Add all direct children
        for subfolder_name in current_level.keys():
            child_id = f"{node_id}_{subfolder_name}"
            all_children.add(child_id)
            # Add children of this child recursively
            child_children = get_all_children(current_level, child_id, prefix=f"{node_id}_")
            all_children.update(child_children)
    
    return all_children

# Main application layout
st.title("Interactive Folder Tree Visualization")

# Sidebar for file upload and options
with st.sidebar:
    st.header("Upload")
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    
    st.header("Options")
    physics_enabled = st.checkbox("Enable Physics", value=True, 
                                help="Enable physics simulation for automatic layout")
    
    hierarchical_layout = st.checkbox("Hierarchical Layout", value=True,
                                    help="Organize nodes in a hierarchical structure")
    
    direction = st.selectbox("Layout Direction", 
                           options=["LR", "RL", "UD", "DU"],
                           index=0,
                           help="LR: Left to Right, RL: Right to Left, UD: Up to Down, DU: Down to Up")
    
    node_spacing = st.slider("Node Spacing", min_value=50, max_value=200, value=100,
                           help="Control spacing between nodes")
    
    level_separation = st.slider("Level Separation", min_value=100, max_value=500, value=200,
                               help="Control separation between hierarchical levels")
    
    # Reset button
    if st.button("Reset View"):
        st.session_state.expanded_nodes = set()
        st.session_state.selected_node = None
        st.experimental_rerun()

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
                # Create graph elements
                nodes, edges = create_graph_elements(folder_structure)
                
                # Configure the graph
                config = Config(
                    width=800,
                    height=600,
                    directed=True,
                    physics=physics_enabled,
                    hierarchical=hierarchical_layout,
                    nodeHighlightBehavior=True,
                    highlightColor="#F7A7A6",
                    collapsible=True,
                    node={'labelProperty': 'label'},
                    link={'labelProperty': 'label', 'renderLabel': False},
                    # Hierarchical layout configuration
                    **{
                        "hierarchy": {
                            "enabled": hierarchical_layout,
                            "direction": direction,
                            "sortMethod": "directed",
                            "nodeSpacing": node_spacing,
                            "levelSeparation": level_separation
                        }
                    }
                )
                
                # Render the graph
                st.info("👆 Click on nodes to expand/collapse branches")
                
                clicked_node = agraph(nodes=nodes, 
                                     edges=edges, 
                                     config=config)
                
                # Handle node clicks for expand/collapse
                if clicked_node:
                    if clicked_node in st.session_state.expanded_nodes:
                        st.session_state.expanded_nodes.remove(clicked_node)
                    else:
                        st.session_state.expanded_nodes.add(clicked_node)
                    
                    st.session_state.selected_node = clicked_node
                    st.experimental_rerun()
    else:
        st.info("Upload an Excel file to visualize your folder structure")
        
        # Example image
        st.image("https://miro.medium.com/max/700/1*YYQEubBxN6h3L1fNpBEkrw.png", 
                 caption="Example folder tree (actual visualization will be interactive) ")

# Metadata panel
with col2:
    st.header("Metadata")
    
    if st.session_state.selected_node:
        st.markdown("---")
        st.markdown(f"### Selected Node: {st.session_state.selected_node.split('_')[-1] if '_' in st.session_state.selected_node else st.session_state.selected_node}")
        
        # Display node status
        is_expanded = st.session_state.selected_node in st.session_state.expanded_nodes
        status = "Expanded" if is_expanded else "Collapsed"
        st.markdown(f"**Status:** {status}")
        
        # Add buttons to expand/collapse
        col_a, col_b = st.columns(2)
        
        with col_a:
            if is_expanded:
                if st.button("Collapse Node"):
                    st.session_state.expanded_nodes.remove(st.session_state.selected_node)
                    st.experimental_rerun()
            else:
                if st.button("Expand Node"):
                    st.session_state.expanded_nodes.add(st.session_state.selected_node)
                    st.experimental_rerun()
        
        with col_b:
            # Add button to expand all children
            if st.button("Expand All Children"):
                if uploaded_file is not None:
                    # Process the Excel file again to get the folder structure
                    paths, _ = process_excel_data(uploaded_file)
                    folder_structure, _ = build_folder_hierarchy(paths)
                    
                    # Get all children of the selected node
                    all_children = get_all_children(folder_structure, st.session_state.selected_node)
                    
                    # Add the selected node and all its children to expanded_nodes
                    st.session_state.expanded_nodes.add(st.session_state.selected_node)
                    st.session_state.expanded_nodes.update(all_children)
                    
                    st.experimental_rerun()
    else:
        st.info("Click on a node to view its details")
