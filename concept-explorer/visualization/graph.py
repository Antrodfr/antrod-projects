"""Build interactive pyvis network graphs from ConceptGraph data."""

from __future__ import annotations

from ai.models import ConceptGraph

# Color palette for relationship types and categories
RELATION_COLORS: dict[str, str] = {
    "prerequisite": "#ff6b6b",
    "related": "#4ecdc4",
    "part-of": "#45b7d1",
}

CATEGORY_COLORS: list[str] = [
    "#6c5ce7", "#fd79a8", "#00b894", "#e17055",
    "#0984e3", "#fdcb6e", "#e84393", "#00cec9",
    "#2d3436", "#636e72",
]


def build_pyvis_graph(
    graph: ConceptGraph,
    height: str = "600px",
    width: str = "100%",
    filter_category: str | None = None,
) -> str:
    """Build a pyvis HTML graph from a ConceptGraph. Returns HTML string."""
    try:
        from pyvis.network import Network
    except ImportError as exc:
        raise ImportError("pyvis is required: pip install pyvis") from exc

    net = Network(
        height=height,
        width=width,
        bgcolor="#1a1a2e",
        font_color="#ffffff",
        directed=True,
        select_menu=False,
        filter_menu=False,
    )

    net.barnes_hut(
        gravity=-3000,
        central_gravity=0.3,
        spring_length=200,
        spring_strength=0.05,
    )

    # Map categories to colors
    categories = graph.categories
    cat_color_map: dict[str, str] = {}
    for i, cat in enumerate(categories):
        cat_color_map[cat] = CATEGORY_COLORS[i % len(CATEGORY_COLORS)]

    # Filter concepts by category if specified
    concepts = graph.concepts
    if filter_category:
        concept_ids = {c.id for c in concepts if c.category == filter_category}
        concepts = [c for c in concepts if c.category == filter_category]
    else:
        concept_ids = {c.id for c in concepts}

    # Add nodes
    for concept in concepts:
        color = cat_color_map.get(concept.category, "#6c5ce7")
        net.add_node(
            concept.id,
            label=concept.name,
            title=concept.get_explanation("beginner"),
            color=color,
            size=25,
            font={"size": 14, "color": "#ffffff"},
            borderWidth=2,
            borderWidthSelected=4,
        )

    # Add edges
    for rel in graph.relationships:
        if rel.source in concept_ids and rel.target in concept_ids:
            edge_color = RELATION_COLORS.get(rel.relation_type, "#4ecdc4")
            net.add_edge(
                rel.source,
                rel.target,
                title=rel.label or rel.relation_type,
                color=edge_color,
                width=2,
                arrows="to",
                smooth={"type": "curvedCW", "roundness": 0.2},
            )

    # Generate HTML
    html = net.generate_html()

    # Inject click-event handler for Streamlit integration
    click_script = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Make node IDs available to parent for Streamlit
        if (typeof network !== 'undefined') {
            network.on("click", function(params) {
                if (params.nodes.length > 0) {
                    var nodeId = params.nodes[0];
                    window.parent.postMessage({type: 'node_click', nodeId: nodeId}, '*');
                }
            });
        }
    });
    </script>
    """
    html = html.replace("</body>", click_script + "</body>")

    return html
