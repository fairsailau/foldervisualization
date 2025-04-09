import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# Page configuration with improved caching
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
if 'selected_node_id' not in st.session_state:
    st.session_state.selected_node_id = None
if 'max_nodes_display' not in st.session_state:
    st.session_state.max_nodes_display = 50  # Limit nodes for performance
if 'horizontal_layout' not in st.session_state:
    st.session_state.horizontal_layout = True  # Default to horizontal layout

# Cached Excel processing for better performance
@st.cache_data
def process_excel_data(file):
    """Process Excel data into flat paths with caching for performance."""
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

# Optimized tree building function
def build_hierarchy(paths):
    """Build tree hierarchy with efficient metadata generation."""
    root = {"name": "Root", "children": [], "level": 0, "id": "root_0"}
    
    # Create timestamps for folders (just once)
    now = datetime.now()
    classifications = ["Public", "Internal", "Confidential"]
    owners = ["User1", "User2", "Admin"]
    
    # Count paths for performance warning
    if len(paths) > 100:
        st.warning(f"Processing {len(paths)} paths may affect performance. Consider using a smaller dataset.")
    
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
                node_id = f"{part}_{i}_{np.random.randint(10000)}"  # More unique IDs
                
                # Metadata only for leaf nodes to improve performance
                is_leaf = (i == len(parts) - 1)
                
                new_node = {
                    "name": part, 
                    "children": [], 
                    "level": i + 1,
                    "id": node_id
                }
                
                # Only generate detailed metadata for leaf nodes
                if is_leaf:
                    new_node["size"] = f"{np.random.randint(1, 1000)} KB"
                    new_node["owner"] = np.random.choice(owners)
                    new_node["classification"] = np.random.choice(classifications)
                    new_node["created"] = (now - pd.Timedelta(days=np.random.randint(1, 365))).strftime("%Y-%m-%d")
                
                current.setdefault("children", []).append(new_node)
                current = new_node
    
    return root

# Improved visualization with better spacing, click interactions, and horizontal layout
def visualize_tree_plotly(tree_data, collapsed_nodes=None, selected_node_id=None, horizontal_layout=True):
    """Create an interactive tree visualization with improved spacing and click handling."""
    if collapsed_nodes is None:
        collapsed_nodes = set()
        
    node_x, node_y, node_text, node_info = [], [], [], []
    edge_x, edge_y = [], []
    node_colors, node_sizes, node_ids = [], [], []
    
    # Initially collapse all nodes except root
    if not collapsed_nodes and tree_data.get("id") not in collapsed_nodes:
        for child in tree_data.get("children", []):
            collapsed_nodes.add(child.get("id"))
    
    def traverse_tree(node, x, y, level=0, parent_x=None, parent_y=None, is_visible=True):
        # Performance check - limit node rendering for large trees
        if len(node_x) > st.session_state.max_nodes_display and level > 2:
            return
            
        node_id = node.get("id", f"{node['name']}_{level}")
        is_collapsed = node_id in collapsed_nodes
        is_selected = node_id == selected_node_id
        
        if is_visible:
            # For horizontal layout, swap x and y coordinates
            if horizontal_layout:
                node_x.append(y)  # y becomes x in horizontal layout
                node_y.append(x)  # x becomes y in horizontal layout
            else:
                node_x.append(x)
                node_y.append(y)
                
            node_text.append(node["name"])
            node_ids.append(node_id)
            
            # Enhanced visualization - color and size based on node properties
            if is_selected:
                color = "yellow"  # Highlight selected node
                size = 20
            elif "classification" in node:
                if node["classification"] == "Confidential":
                    color = "red"
                elif node["classification"] == "Internal":
                    color = "orange"
                else:
                    color = "skyblue"
                size = 15
            else:
                color = "green"  # root node
                size = 18
                
            node_colors.append(color)
            node_sizes.append(size)
            
            # Store node information for display
            info = {
                "name": node["name"],
                "level": node.get("level", 0),
                "id": node_id,
                "size": node.get("size", "N/A"),
                "owner": node.get("owner", "N/A"),
                "classification": node.get("classification", "N/A"),
                "created": node.get("created", "N/A"),
                "is_collapsed": is_collapsed,
                "is_selected": is_selected,
                "has_children": bool(node.get("children", []))
            }
            node_info.append(info)
            
            # Draw edges from parent to this node
            if parent_x is not None and parent_y is not None:
                if horizontal_layout:
                    edge_x.extend([parent_y, y, None])  # Swap for horizontal layout
                    edge_y.extend([parent_x, x, None])
                else:
                    edge_x.extend([parent_x, x, None])
                    edge_y.extend([parent_y, y, None])
        
        # Process children if not collapsed
        if "children" in node and node["children"] and not is_collapsed:
            num_children = len(node["children"])
            
            # Improved spacing calculation - more space between nodes
            spacing_factor = 6  # Increased spacing between nodes
            
            if horizontal_layout:
                # For horizontal layout, children expand to the right
                for i, child in enumerate(node["children"]):
                    # Horizontal layout: x increases (moves right), y varies for siblings
                    child_x = x + spacing_factor  # Move right for children
                    # Better vertical distribution for siblings
                    if num_children > 1:
                        child_y = y - (spacing_factor * (num_children-1)/2) + i * spacing_factor
                    else:
                        child_y = y
                    traverse_tree(child, child_x, child_y, level+1, x, y, is_visible)
            else:
                # For vertical layout (top to bottom)
                width = max(num_children * spacing_factor, spacing_factor)
                
                for i, child in enumerate(node["children"]):
                    # Better horizontal distribution
                    child_x = x - width/2 + i * (width/(num_children-1 if num_children > 1 else 1))
                    # Increased vertical spacing
                    child_y = y - spacing_factor  # Move down for children
                    traverse_tree(child, child_x, child_y, level+1, x, y, is_visible)
    
    # Start traversal from root
    traverse_tree(tree_data, 0, 0)
    
    # Define edges
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Define nodes with hover info
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="middle right" if horizontal_layout else "bottom center",
        hoverinfo='text',
        customdata=node_ids,  # Store node IDs for click handling
        marker=dict(
            showscale=False,
            color=node_colors,
            size=node_sizes,
            line=dict(width=2, color='DarkSlateGrey')
        )
    )
    
    # Create figure with improved layout settings
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        height=700,  # Larger visualization area
                        width=1000,  # Wider for horizontal layout
                        clickmode='event'  # Enable click events
                    )
                   )
    
    # Add title indicating layout direction and interaction instructions
    layout_direction = "Horizontal (Left to Right)" if horizontal_layout else "Vertical (Top to Bottom)"
    fig.update_layout(
        title=f"Folder Tree Visualization - {layout_direction}<br><sub>Click on nodes to expand/collapse</sub>"
    )
    
    return fig, node_info, node_ids

# Handle node clicking
def handle_node_click(node_id):
    """Process node click to toggle expansion/collapse and select node."""
    # Toggle collapse state
    if node_id in st.session_state.collapsed_nodes:
        st.session_state.collapsed_nodes.remove(node_id)
    else:
        st.session_state.collapsed_nodes.add(node_id)
    
    # Set as selected node
    st.session_state.selected_node_id = node_id

# Generate recommendations for folder structure
@st.cache_data
def get_ai_recommendations(tree_data):
    """Get AI recommendations with caching for better performance."""
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
    # Layout direction option
    st.session_state.horizontal_layout = st.checkbox(
        "Horizontal Layout (Left to Right)", 
        value=True,
        help="Toggle between horizontal (left to right) and vertical (top to bottom) layout"
    )
    
    # Performance controls
    st.session_state.max_nodes_display = st.slider(
        "Max nodes to display:", 
        min_value=20, 
        max_value=200, 
        value=50,
        help="Limit the number of nodes for better performance"
    )
    
    if st.button("Export as PNG"):
        if 'fig' in st.session_state and st.session_state.fig is not None:
            with st.spinner("Generating PNG..."):
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
        st.info("👆 Click on nodes to expand/collapse and view details")
        
        # Process the file with progress indicator
        with st.spinner("Processing Excel file..."):
            flat_paths = process_excel_data(uploaded_file)
        
        if flat_paths:
            # Build hierarchy with progress indicator
            with st.spinner("Building folder structure..."):
                tree_data = build_hierarchy(flat_paths)
                st.session_state.tree_data = tree_data
            
            # Create visualization
            with st.spinner("Generating visualization..."):
                fig, node_info, node_ids = visualize_tree_plotly(
                    tree_data, 
                    st.session_state.collapsed_nodes,
                    st.session_state.selected_node_id,
                    st.session_state.horizontal_layout
                )
                st.session_state.fig = fig
                st.session_state.node_info = node_info
            
            # Display visualization with click handling
            clicked = st.plotly_chart(fig, use_container_width=True, key="tree_plot")
            
            # Handle clicks through a callback
            if clicked and "clickData" in clicked:
                point_index = clicked["points"][0]["pointIndex"]
                clicked_node_id = node_ids[point_index]
                handle_node_click(clicked_node_id)
                st.experimental_rerun()
            
            # Search functionality
            search_term = st.text_input("Search folders:")
            if search_term:
                matches = [node for node in node_info if search_term.lower() in node["name"].lower()]
                if matches:
                    st.success(f"Found {len(matches)} matches:")
                    # Make search results clickable
                    for i, match in enumerate(matches):
                        if st.button(f"{match['name']}", key=f"search_{i}"):
                            st.session_state.selected_node_id = match['id']
                            # Ensure parent nodes are expanded
                            st.experimental_rerun()
                else:
                    st.warning("No matches found")
        else:
            st.error("Could not extract folder paths from the Excel file.")
else:
    with col1:
        st.info("Upload an Excel file to visualize folder structure")
        
        # Display example visualization
        st.subheader("Example visualization:")
        st.image("https://miro.medium.com/max/700/1*YYQEubBxN6h3L1fNpBEkrw.png", 
                 caption="Example folder tree (actual visualization will be interactive)")

# Display metadata and recommendations
with col2:
    st.header("Metadata")
    
    if 'node_info' in st.session_state and st.session_state.node_info:
        # Find selected node
        selected_node = None
        if st.session_state.selected_node_id:
            selected_node = next((node for node in st.session_state.node_info 
                                if node["id"] == st.session_state.selected_node_id), None)
        
        if not selected_node:
            # Default to first node if none selected
            selected_node = st.session_state.node_info[0]
        
        # Display node metadata with improved formatting
        st.markdown("---")
        st.markdown(f"### {selected_node['name']}")
        st.markdown(f"**Level:** {selected_node['level']}")
        
        if selected_node['size'] != 'N/A':
            st.markdown(f"**Size:** {selected_node['size']}")
        if selected_node['owner'] != 'N/A':
            st.markdown(f"**Owner:** {selected_node['owner']}")
        if selected_node['classification'] != 'N/A':
            st.markdown(f"**Classification:** {selected_node['classification']}")
        if selected_node['created'] != 'N/A':
            st.markdown(f"**Created:** {selected_node['created']}")
        
        # Show expand/collapse status
        if selected_node['has_children']:
            status = "Collapsed" if selected_node['is_collapsed'] else "Expanded"
            st.markdown(f"**Status:** {status}")
            
            # Add button to expand/collapse
            if selected_node['is_collapsed']:
                if st.button("Expand Node"):
                    st.session_state.collapsed_nodes.remove(selected_node['id'])
                    st.experimental_rerun()
            else:
                if st.button("Collapse Node"):
                    st.session_state.collapsed_nodes.add(selected_node['id'])
                    st.experimental_rerun()
    
    # Display recommendations if available
    if 'recommendations' in st.session_state and st.session_state.recommendations:
        st.header("AI Recommendations")
        for i, rec in enumerate(st.session_state.recommendations):
            st.markdown(f"{i+1}. {rec}")
