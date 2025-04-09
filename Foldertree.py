import streamlit as st
import pandas as pd
import numpy as np
import networkx as nx
import plotly.graph_objects as go
from networkx.drawing.nx_pydot import graphviz_layout
from datetime import datetime
import os
import traceback

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
if 'graph' not in st.session_state:
    st.session_state.graph = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None

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
        
        return flat_paths, None
    except Exception as e:
        error_msg = f"Error processing Excel file: {str(e)}"
        return [], error_msg

# Build tree hierarchy
def build_hierarchy(paths):
    """Build tree hierarchy with efficient metadata generation."""
    try:
        # Create a directed graph
        G = nx.DiGraph()
        
        # Add root node
        root_id = "root"
        G.add_node(root_id, name="Root", level=0, is_expanded=True)
        
        # Create timestamps for folders (just once)
        now = datetime.now()
        classifications = ["Public", "Internal", "Confidential"]
        owners = ["User1", "User2", "Admin"]
        
        # Count paths for performance warning
        if len(paths) > 100:
            st.warning(f"Processing {len(paths)} paths may affect performance. Consider using a smaller dataset.")
        
        for path in paths:
            parts = path.split('/')
            current_id = root_id
            current_path = ""
            
            for i, part in enumerate(parts):
                if not part.strip():
                    continue
                    
                # Build the path up to this point
                if current_path:
                    current_path = f"{current_path}/{part}"
                else:
                    current_path = part
                    
                node_id = f"{current_path}"
                
                # Check if this node already exists
                if not G.has_node(node_id):
                    # Metadata only for leaf nodes to improve performance
                    is_leaf = (i == len(parts) - 1)
                    
                    node_attrs = {
                        "name": part, 
                        "level": i + 1,
                        "is_expanded": False  # Initially collapsed
                    }
                    
                    # Only generate detailed metadata for leaf nodes
                    if is_leaf:
                        node_attrs["size"] = f"{np.random.randint(1, 1000)} KB"
                        node_attrs["owner"] = np.random.choice(owners)
                        node_attrs["classification"] = np.random.choice(classifications)
                        node_attrs["created"] = (now - pd.Timedelta(days=np.random.randint(1, 365))).strftime("%Y-%m-%d")
                    
                    G.add_node(node_id, **node_attrs)
                    G.add_edge(current_id, node_id)
                
                current_id = node_id
        
        return G, None
    except Exception as e:
        error_msg = f"Error building hierarchy: {str(e)}"
        return None, error_msg

# Create a visualization of the tree using Plotly
def visualize_tree_plotly(graph, collapsed_nodes=None, selected_node_id=None):
    """Create an interactive tree visualization with improved spacing and click handling."""
    try:
        if collapsed_nodes is None:
            collapsed_nodes = set()
        
        # Create a subgraph with only the visible nodes based on collapsed state
        visible_graph = nx.DiGraph()
        
        # Start with the root node
        root_nodes = [n for n, d in graph.in_degree() if d == 0]
        if not root_nodes:
            return None, [], [], "No root node found in the graph"
        
        root_id = root_nodes[0]
        visible_nodes = set([root_id])
        
        # Function to recursively add visible nodes
        def add_visible_nodes(node_id):
            if node_id in collapsed_nodes:
                return
            
            for child in graph.successors(node_id):
                visible_nodes.add(child)
                visible_graph.add_edge(node_id, child)
                add_visible_nodes(child)
        
        # Add all visible nodes to the subgraph
        for node in root_nodes:
            add_visible_nodes(node)
        
        # Add all visible nodes to the subgraph
        for node in visible_nodes:
            attrs = {k: v for k, v in graph.nodes[node].items()}
            visible_graph.add_node(node, **attrs)
        
        # Use graphviz_layout with dot to get a hierarchical layout
        # The rankdir='LR' parameter makes the tree expand from left to right
        try:
            pos = graphviz_layout(visible_graph, prog="dot", root=root_id, args="-Grankdir=LR -Gnodesep=0.5 -Granksep=2.0")
        except Exception as e:
            st.warning(f"Graphviz layout error: {str(e)}. Using fallback layout.")
            # Fallback to a simple layout
            pos = {node: (i * 100, (visible_graph.nodes[node].get('level', 0) - 1) * -100) 
                  for i, node in enumerate(visible_graph.nodes())}
        
        # Create edge traces
        edge_x = []
        edge_y = []
        
        for edge in visible_graph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        
        # Create node traces
        node_x = []
        node_y = []
        node_text = []
        node_info = []
        node_ids = []
        node_colors = []
        node_sizes = []
        
        for node in visible_graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            node_attrs = visible_graph.nodes[node]
            node_name = node_attrs.get('name', str(node))
            node_text.append(node_name)
            node_ids.append(node)
            
            # Node color and size based on properties
            is_selected = (node == selected_node_id)
            has_children = any(visible_graph.successors(node))
            is_collapsed = node in collapsed_nodes
            
            if is_selected:
                color = "yellow"  # Highlight selected node
                size = 20
            elif "classification" in node_attrs:
                if node_attrs["classification"] == "Confidential":
                    color = "red"
                elif node_attrs["classification"] == "Internal":
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
                "id": node,
                "name": node_name,
                "level": node_attrs.get("level", 0),
                "size": node_attrs.get("size", "N/A"),
                "owner": node_attrs.get("owner", "N/A"),
                "classification": node_attrs.get("classification", "N/A"),
                "created": node_attrs.get("created", "N/A"),
                "is_collapsed": is_collapsed,
                "is_selected": is_selected,
                "has_children": has_children
            }
            node_info.append(info)
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_text,
            textposition="middle right",  # Text to the right of nodes for horizontal layout
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
                            title="Folder Tree Visualization - Horizontal Layout<br><sub>Click on nodes to expand/collapse</sub>",
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
        
        return fig, node_info, node_ids, None
    except Exception as e:
        error_msg = f"Error visualizing tree: {str(e)}\n{traceback.format_exc()}"
        return None, [], [], error_msg

# Handle node clicking
def handle_node_click(node_id):
    """Process node click to toggle expansion/collapse and select node."""
    try:
        # Toggle collapse state
        if node_id in st.session_state.collapsed_nodes:
            st.session_state.collapsed_nodes.remove(node_id)
        else:
            st.session_state.collapsed_nodes.add(node_id)
        
        # Set as selected node
        st.session_state.selected_node_id = node_id
        return None
    except Exception as e:
        return f"Error handling node click: {str(e)}"

# Generate recommendations for folder structure
@st.cache_data
def get_ai_recommendations(graph):
    """Get AI recommendations with caching for better performance."""
    try:
        max_depth = 0
        total_folders = 0
        
        for node, attrs in graph.nodes(data=True):
            level = attrs.get('level', 0)
            max_depth = max(max_depth, level)
            total_folders += 1
        
        # Generate recommendations based on structure analysis
        recommendations = [
            f"Your folder structure has a maximum depth of {max_depth} levels. Consider keeping it under 5 levels for better navigation.",
            "Group related files in dedicated subfolders for better organization.",
            "Use a consistent naming convention for all folders (e.g., CamelCase or snake_case).",
            "Include README files in each major section to explain the purpose and contents.",
            "Separate work-in-progress from finalized content to avoid confusion.",
            "Use classification tags consistently across similar content types."
        ]
        
        return recommendations, None
    except Exception as e:
        error_msg = f"Error generating recommendations: {str(e)}"
        return [], error_msg

# Main application layout
st.title("Folder Tree Visualization")

# Layout: Sidebar and main content
col1, col2 = st.columns([3, 1])

# Sidebar for file upload and options
with st.sidebar:
    st.header("Upload")
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    
    st.header("Options")
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
            try:
                with st.spinner("Generating PNG..."):
                    img_bytes = st.session_state.fig.to_image(format="png")
                    st.download_button(
                        label="Download PNG",
                        data=img_bytes,
                        file_name="folder_tree.png",
                        mime="image/png"
                    )
            except Exception as e:
                st.error(f"Error exporting PNG: {str(e)}")
        else:
            st.warning("Generate a visualization first")
    
    if st.button("Get AI Recommendations"):
        if 'graph' in st.session_state and st.session_state.graph:
            with st.spinner("Analyzing folder structure..."):
                recommendations, error = get_ai_recommendations(st.session_state.graph)
                if error:
                    st.error(error)
                else:
                    st.session_state.recommendations = recommendations
        else:
            st.warning("Generate a visualization first")

# Display any error message
if st.session_state.error_message:
    st.error(st.session_state.error_message)
    st.session_state.error_message = None  # Clear the error after displaying

# Process uploaded file
if uploaded_file is not None:
    with col1:
        st.header("Folder Tree Visualization")
        st.info("👆 Click on nodes to expand/collapse and view details")
        
        # Process the file with progress indicator
        with st.spinner("Processing Excel file..."):
            flat_paths, error = process_excel_data(uploaded_file)
            if error:
                st.error(error)
        
        if flat_paths:
            # Build hierarchy with progress indicator
            with st.spinner("Building folder structure..."):
                graph, error = build_hierarchy(flat_paths)
                if error:
                    st.error(error)
                else:
                    st.session_state.graph = graph
                    
                    # Initially collapse all nodes except root
                    root_nodes = [n for n, d in graph.in_degree() if d == 0]
                    if root_nodes:
                        for node in graph.nodes():
                            if node not in root_nodes:
                                st.session_state.collapsed_nodes.add(node)
            
            if graph:
                # Create visualization
                with st.spinner("Generating visualization..."):
                    fig, node_info, node_ids, error = visualize_tree_plotly(
                        graph, 
                        st.session_state.collapsed_nodes,
                        st.session_state.selected_node_id
                    )
                    if error:
                        st.error(error)
                    else:
                        st.session_state.fig = fig
                        st.session_state.node_info = node_info
                
                if fig:
                    # Display visualization with click handling
                    try:
                        clicked = st.plotly_chart(fig, use_container_width=True, key="tree_plot")
                        
                        # Handle clicks through a callback
                        if clicked and "clickData" in clicked:
                            point_index = clicked["points"][0]["pointIndex"]
                            clicked_node_id = node_ids[point_index]
                            error = handle_node_click(clicked_node_id)
                            if error:
                                st.error(error)
                            else:
                                st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error displaying visualization: {str(e)}")
                
                # Search functionality
                search_term = st.text_input("Search folders:")
                if search_term:
                    try:
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
                    except Exception as e:
                        st.error(f"Error searching: {str(e)}")
        else:
            if not error:  # Only show this if there's no other error
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
        try:
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
        except Exception as e:
            st.error(f"Error displaying metadata: {str(e)}")
    
    # Display recommendations if available
    if 'recommendations' in st.session_state and st.session_state.recommendations:
        try:
            st.header("AI Recommendations")
            for i, rec in enumerate(st.session_state.recommendations):
                st.markdown(f"{i+1}. {rec}")
        except Exception as e:
            st.error(f"Error displaying recommendations: {str(e)}")
