import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

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

# Function to convert folder structure to plotly treemap data
def create_treemap_data(folder_structure, parent="", level=0, path=""):
    labels = []
    parents = []
    values = []
    ids = []
    
    # Process each folder in the current level
    for folder_name, subfolders in folder_structure.items():
        # Create a unique ID for this folder
        folder_id = f"{path}/{folder_name}" if path else folder_name
        
        # Add this folder to the data
        labels.append(folder_name)
        parents.append(parent)
        values.append(1)  # All nodes have equal weight
        ids.append(folder_id)
        
        # Process subfolders recursively
        if subfolders:
            sub_labels, sub_parents, sub_values, sub_ids = create_treemap_data(
                subfolders, folder_name, level + 1, folder_id
            )
            labels.extend(sub_labels)
            parents.extend(sub_parents)
            values.extend(sub_values)
            ids.extend(sub_ids)
    
    return labels, parents, values, ids

# Function to get direct children of a node
def get_direct_children(folder_structure, node_id):
    parts = node_id.split('/')
    current = folder_structure
    
    # Navigate to the correct node
    for part in parts:
        if part in current:
            current = current[part]
        else:
            return []
    
    # Return direct children
    return list(current.keys())

# Main application layout
st.title("Interactive Folder Tree Visualization")

# Sidebar for file upload and options
with st.sidebar:
    st.header("Upload")
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    
    st.header("Options")
    max_depth = st.slider("Max Display Depth", min_value=1, max_value=10, value=3,
                         help="Maximum depth of folders to display")
    
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
                # Create treemap data
                labels, parents, values, ids = create_treemap_data(folder_structure)
                
                # Add root node
                labels.insert(0, "Root")
                parents.insert(0, "")
                values.insert(0, 1)
                ids.insert(0, "root")
                
                # Create treemap figure
                fig = go.Figure(go.Treemap(
                    labels=labels,
                    parents=parents,
                    values=values,
                    ids=ids,
                    root_color="lightblue",
                    branchvalues="total",
                    maxdepth=max_depth,
                    marker=dict(
                        colors=['rgba(135, 206, 250, 0.8)'] * len(labels),
                        line=dict(width=2, color='white')
                    ),
                    textfont=dict(size=14),
                    hovertemplate='<b>%{label}</b><br>Path: %{id}<extra></extra>'
                ))
                
                # Update layout
                fig.update_layout(
                    margin=dict(t=30, l=10, r=10, b=10),
                    height=600,
                    width=800
                )
                
                # Display the treemap
                st.plotly_chart(fig, use_container_width=True)
                
                # Add click handler for node selection
                st.info("👆 Click on a node in the treemap to select it")
                
                # Allow node selection via selectbox
                selected_node = st.selectbox("Select a node:", 
                                           options=ids,
                                           format_func=lambda x: x.split('/')[-1] if '/' in x else x)
                
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
        node_label = node_id.split('/')[-1] if '/' in node_id else node_id
        
        st.markdown(f"### Selected Node: {node_label}")
        st.markdown(f"**Path:** {node_id}")
        
        # Display children if available
        if uploaded_file is not None:
            try:
                # Process the Excel file again to get the folder structure
                paths, _ = process_excel_data(uploaded_file)
                folder_structure, _ = build_folder_hierarchy(paths)
                
                # Get direct children
                children = get_direct_children(folder_structure, node_id)
                
                if children:
                    st.markdown("### Children:")
                    for child in children:
                        st.markdown(f"- {child}")
                else:
                    st.markdown("This node has no children.")
            except Exception as e:
                st.error(f"Error getting children: {str(e)}")
    else:
        st.info("Click on a node to view its details")
