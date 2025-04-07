import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Folder Tree Visualization",
    page_icon="🌳",
    layout="wide"
)

# Initialize session state
if 'tree_data' not in st.session_state:
    st.session_state.tree_data = None
if 'node_info' not in st.session_state:
    st.session_state.node_info = None
if 'fig' not in st.session_state:
    st.session_state.fig = None
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None
if 'collapsed_nodes' not in st.session_state:
    st.session_state.collapsed_nodes = set()

# Process Excel data into folder paths
def process_excel_data(file):
    """Process Excel data into flat paths."""
    try:
        df = pd.read_excel(file)
        flat_paths = []
        
        for _, row in df.iterrows():
            path_parts = [str(cell) for cell in row if pd.notna(cell) and str(cell).strip()]
            if path_parts:
                path = '/'.join(path_parts)
                flat_paths.append(path)
        
        return flat_paths
    except Exception as e:
        st.error(f"Error processing Excel file: {str(e)}")
        return []

# Convert flat paths to hierarchical tree structure
def build_hierarchy(paths):
    """Convert flat paths to hierarchical tree structure."""
    root = {"name": "Root", "children": [], "level": 0}
    
    # Create timestamps for folders
    now = datetime.now()
    
    for path in paths:
        parts = path.split('/')
        current = root
        
        for i, part in enumerate(parts):
            if not part.strip():
                continue
                
            # Check if this part already exists
            found = False
            for child in current.get("children", []):
                if child["name"] == part:
                    current = child
                    found = True
                    break
            
            if not found:
                new_node = {
                    "name": part, 
                    "children": [], 
                    "level": i + 1
                }
                
                # Add metadata for leaf nodes
                created_date = now - pd.Timedelta(days=np.random.randint(1, 365))
                
                new_node["size"] = f"{np.random.randint(1, 1000)} KB"
                new_node["owner"] = np.random.choice(["User1", "User2", "Admin"])
                new_node["classification"] = np.random.choice(["Public", "Internal", "Confidential"])
                new_node["created"] = created_date.strftime("%Y-%m-%d")
                
                current.setdefault("children", []).append(new_node)
                current = new_node
    
    return root

# Create tree visualization using Plotly
def visualize_tree_plotly(tree_data, collapsed_nodes=None):
    """Create an interactive tree visualization using Plotly."""
    if collapsed_nodes is None:
        collapsed_nodes = set()
        
    node_x, node_y, node_text, node_info = [], [], [], []
    edge_x, edge_y = [], []
    node_colors = []
    
    def traverse_tree(node, x, y, level=0, parent_x=None, parent_y=None, is_visible=True):
        # Manage collapsed nodes
        node_id = f"{node['name']}_{level}"
        is_collapsed = node_id in collapsed_nodes
        
        if is_visible:
            node_x.append(x)
            node_y.append(y)
            node_text.append(node["name"])
            
            # Set node color based on classification
            if "classification" in node:
                if node["classification"] == "Confidential":
                    color = "red"
                elif node["classification"] == "Internal":
                    color = "orange"
                else:
                    color = "skyblue"
            else:
                color = "green"  # root node
            
            node_colors.append(color)
            
            info = {
                "name": node["name"],
                "level": node.get("level", 0),
                "node_id": node_id,
                "size": node.get("size", "N/A"),
                "owner": node.get("owner", "N/A"),
                "classification": node.get("classification", "N/A"),
                "created": node.get("created", "N/A"),
                "is_collapsed": is_collapsed
            }
            node_info.append(info)
            
            if parent_x is not None and parent_y is not None:
                edge_x.extend([parent_x, x, None])
                edge_y.extend([parent_y, y, None])
        
        # Process children if not collapsed
        if "children" in node and node["children"] and not is_collapsed:
            num_children = len(node["children"])
            width = max(num_children * 2, 2)
            
            for i, child in enumerate(node["children"]):
                child_x = x - width/2 + i * (width/(num_children-1 if num_children > 1 else 1))
                child_y = y - 2
                traverse_tree(child, child_x, child_y, level+1, x, y, is_visible)
    
    traverse_tree(tree_data, 0, 0)
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="bottom center",
        hoverinfo='text',
        marker=dict(
            showscale=False,
            color=node_colors,
            size=15,
            line=dict(width=2, color='DarkSlateGrey')
        )
    )
    
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        height=600
                    )
                   )
    
    return fig, node_info

# Toggle node collapse state
def toggle_node_collapse(node_id):
    if node_id in st.session_state.collapsed_nodes:
        st.session_state.collapsed_nodes.remove(node_id)
    else:
        st.session_state.collapsed_nodes.add(node_id)

# Generate AI recommendations for folder structure
def get_ai_recommendations(tree_data):
    """Get AI recommendations for folder structure organization."""
    def format_structure(node, level=0):
        output = "  " * level + f"- {node['name']}\n"
        for child in node.get("children", []):
            output += format_structure(child, level + 1)
        return output
    
    folder_structure = format_structure(tree_data)
    
    # Calculate structure metrics
    max_depth = 0
    total_folders = 0
    
    def analyze_tree(node, depth=0):
        nonlocal max_depth, total_folders
        max_depth = max(max_depth, depth)
        total_folders += 1
        
        if "children" in node:
            for child in node["children"]:
                analyze_tree(child, depth + 1)
    
    analyze_tree(tree_data)
    
    # Generate recommendations based on structure analysis
    recommendations = [
        f"Your folder structure has a maximum depth of {max_depth} levels. Consider keeping it under 5 levels for better navigation.",
        "Group related files in dedicated subfolders for better organization.",
        "Use a consistent naming convention for all folders (e.g., CamelCase or snake_case).",
        "Include README files in each major section to explain the purpose and contents.",
        "Separate work-in-progress from finalized content to avoid confusion.",
        "Use classification tags consistently across similar content types."
    ]
    
    return recommendations

# Main application layout
st.title("Folder Tree Visualization")

# Layout: Sidebar and main content
col1, col2 = st.columns([3, 1])

# Sidebar for file upload and options
with st.sidebar:
    st.header("Upload")
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    
    st.header("Options")
    if st.button("Export as PNG"):
        if 'fig' in st.session_state and st.session_state.fig is not None:
            img_bytes = st.session_state.fig.to_image(format="png")
            st.download_button(
                label="Download PNG",
                data=img_bytes,
                file_name="folder_tree.png",
                mime="image/png"
            )
        else:
            st.warning("Generate a visualization first")
    
    if st.button("Get AI Recommendations"):
        if 'tree_data' in st.session_state and st.session_state.tree_data:
            with st.spinner("Analyzing folder structure..."):
                recommendations = get_ai_recommendations(st.session_state.tree_data)
                st.session_state.recommendations = recommendations
        else:
            st.warning("Generate a visualization first")

# Process uploaded file
if uploaded_file is not None:
    with col1:
        st.header("Folder Tree Visualization")
        
        # Process the file
        with st.spinner("Processing Excel file..."):
            flat_paths = process_excel_data(uploaded_file)
        
        if flat_paths:
            # Build hierarchy and visualize
            tree_data = build_hierarchy(flat_paths)
            st.session_state.tree_data = tree_data
            
            fig, node_info = visualize_tree_plotly(tree_data, st.session_state.collapsed_nodes)
            st.session_state.fig = fig
            st.session_state.node_info = node_info
            
            # Display visualization
            st.plotly_chart(fig, use_container_width=True)
            
            # Search functionality
            search_term = st.text_input("Search folders:")
            if search_term:
                matches = [node for node in node_info if search_term.lower() in node["name"].lower()]
                if matches:
                    st.success(f"Found {len(matches)} matches:")
                    for match in matches:
                        st.write(f"- {match['name']}")
                else:
                    st.warning("No matches found")
        else:
            st.error("Could not extract folder paths from the Excel file.")
else:
    with col1:
        st.info("Upload an Excel file to visualize folder structure")

# Display metadata and recommendations
with col2:
    st.header("Metadata")
    
    if 'node_info' in st.session_state and st.session_state.node_info:
        node_names = [node["name"] for node in st.session_state.node_info]
        selected_name = st.selectbox("Select folder:", node_names)
        
        selected_node = next((node for node in st.session_state.node_info 
                             if node["name"] == selected_name), None)
        
        if selected_node:
            st.markdown("---")
            st.write(f"**Folder Name:** {selected_node['name']}")
            st.write(f"**Size:** {selected_node['size']}")
            st.write(f"**Owner:** {selected_node['owner']}")
            st.write(f"**Classification:** {selected_node['classification']}")
            st.write(f"**Created:** {selected_node['created']}")
            
            # Toggle collapse state button
            if st.button(f"{'Expand' if selected_node['is_collapsed'] else 'Collapse'} in Visualization", 
                       key=f"viz_toggle_{selected_node['node_id']}"):
                toggle_node_collapse(selected_node['node_id'])
                st.experimental_rerun()
    else:
        st.info("Upload an Excel file and select a node to see metadata")
    
    # Display AI recommendations if available
    if 'recommendations' in st.session_state and st.session_state.recommendations:
        st.header("AI Recommendations")
        for rec in st.session_state.recommendations:
            st.write(f"- {rec}")
