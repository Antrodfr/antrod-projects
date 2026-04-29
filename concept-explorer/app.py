"""Concept Explorer — AI-powered interactive learning tool.

Streamlit entry point. Run with: streamlit run app.py
"""

from __future__ import annotations

import os
import json
import streamlit as st
import streamlit.components.v1 as components

from ai.models import Concept, ConceptGraph
from demo.loader import load_demo_graph
from visualization.graph import build_pyvis_graph


# ---------------------------------------------------------------------------
# Page config & styling
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Concept Explorer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

DARK_CSS = """
<style>
    .stApp { background-color: #0e1117; }
    .concept-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        border: 1px solid #16213e;
    }
    .concept-title { color: #e94560; font-size: 1.5rem; font-weight: bold; }
    .level-tab { padding: 1rem; border-radius: 8px; margin: 0.5rem 0; }
    .beginner { background: #1b4332; border-left: 4px solid #2d6a4f; }
    .intermediate { background: #3d2c00; border-left: 4px solid #e6a817; }
    .expert { background: #3c1518; border-left: 4px solid #e94560; }
    .quiz-card {
        background: #16213e;
        border-radius: 10px;
        padding: 1.2rem;
        margin: 1rem 0;
    }
    .source-excerpt {
        background: #16213e;
        border-left: 3px solid #4ecdc4;
        padding: 0.8rem;
        border-radius: 0 8px 8px 0;
        font-style: italic;
        color: #a8a8b3;
    }
</style>
"""
st.markdown(DARK_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _init_state() -> None:
    defaults: dict = {
        "graph": None,
        "selected_concept": None,
        "page": "upload",
        "quiz_answers": {},
        "quiz_submitted": False,
        "demo_mode": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()

HAS_API_KEY = bool(os.getenv("MISTRAL_API_KEY", ""))


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🧠 Concept Explorer")
    st.caption("Transform documents into interactive concept maps")
    st.divider()

    pages = {
        "upload": "📤 Upload / Load",
        "explorer": "🗺️ Explorer",
        "quiz": "❓ Quiz",
    }
    for key, label in pages.items():
        if st.button(label, use_container_width=True, key=f"nav_{key}"):
            st.session_state.page = key

    st.divider()
    if st.session_state.graph:
        graph: ConceptGraph = st.session_state.graph
        st.success(f"✅ {len(graph.concepts)} concepts loaded")
        if st.session_state.demo_mode:
            st.info("🎮 Demo mode (no API key)")
    else:
        st.warning("No document loaded")

    st.divider()
    st.caption("Built with Streamlit + Mistral AI")


# ---------------------------------------------------------------------------
# Upload / Load page
# ---------------------------------------------------------------------------

def page_upload() -> None:
    st.markdown("# 📤 Upload Document")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📁 Upload a File")
        uploaded = st.file_uploader(
            "Drag and drop a file",
            type=["pdf", "docx", "pptx", "png", "jpg", "jpeg", "md"],
            help="Supported: PDF, DOCX, PPTX, PNG, JPG, Markdown",
        )

        if uploaded is not None:
            if not HAS_API_KEY:
                st.warning(
                    "⚠️ No MISTRAL_API_KEY found. Set it in your environment or .env file "
                    "to process custom documents. Loading demo data instead."
                )
                _load_demo()
                return

            with st.spinner("Processing document..."):
                try:
                    _process_upload(uploaded)
                    st.success("✅ Document processed! Go to Explorer.")
                    st.session_state.page = "explorer"
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error processing file: {exc}")

    with col2:
        st.markdown("### 🎮 Demo Mode")
        st.markdown(
            "Explore a pre-built concept map about **Zero Trust Architecture** — "
            "no API key required."
        )
        if st.button("🚀 Load Demo", use_container_width=True, type="primary"):
            _load_demo()


def _load_demo() -> None:
    """Load the demo concept graph."""
    with st.spinner("Loading demo data..."):
        st.session_state.graph = load_demo_graph()
        st.session_state.demo_mode = True
        st.session_state.selected_concept = None
        st.session_state.quiz_answers = {}
        st.session_state.quiz_submitted = False
    st.session_state.page = "explorer"
    st.rerun()


def _process_upload(uploaded_file) -> None:  # type: ignore[no-untyped-def]
    """Process an uploaded file through ingestion and AI extraction."""
    import tempfile
    from pathlib import Path
    from ingestion import get_ingestor
    from ai.extractor import ConceptExtractor

    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        ingestor = get_ingestor(tmp_path)
        doc = ingestor.ingest(tmp_path)
        extractor = ConceptExtractor()
        graph = extractor.extract_concepts(doc.full_text)
        st.session_state.graph = graph
        st.session_state.demo_mode = False
        st.session_state.selected_concept = None
        st.session_state.quiz_answers = {}
        st.session_state.quiz_submitted = False
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Explorer page
# ---------------------------------------------------------------------------

def page_explorer() -> None:
    if not st.session_state.graph:
        st.info("📤 Please upload a document or load the demo first.")
        return

    graph: ConceptGraph = st.session_state.graph
    st.markdown("# 🗺️ Concept Explorer")

    # Controls row
    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("🔍 Search concepts", placeholder="Type to search...")
    with col_filter:
        categories = ["All"] + graph.categories
        selected_cat = st.selectbox("📂 Filter by category", categories)

    filter_cat = None if selected_cat == "All" else selected_cat

    # Build and render graph
    graph_col, detail_col = st.columns([3, 2])

    with graph_col:
        html = build_pyvis_graph(graph, height="550px", filter_category=filter_cat)
        components.html(html, height=570, scrolling=False)

        # Concept selector (since iframe click events are tricky)
        concept_names = [c.name for c in graph.concepts]
        if filter_cat:
            concept_names = [c.name for c in graph.concepts if c.category == filter_cat]
        if search_query:
            concept_names = [
                n for n in concept_names if search_query.lower() in n.lower()
            ]

        selected_name = st.selectbox(
            "Select a concept to explore:",
            ["(click a node or select here)"] + concept_names,
            key="concept_selector",
        )
        if selected_name and selected_name != "(click a node or select here)":
            for c in graph.concepts:
                if c.name == selected_name:
                    st.session_state.selected_concept = c.id
                    break

    with detail_col:
        _render_concept_detail(graph)


def _render_concept_detail(graph: ConceptGraph) -> None:
    """Render the detail panel for a selected concept."""
    concept_id = st.session_state.selected_concept
    if not concept_id:
        st.markdown(
            '<div class="concept-card">'
            "<p>👈 Select a concept from the graph or dropdown to see details.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    concept = graph.get_concept(concept_id)
    if not concept:
        st.warning("Concept not found.")
        return

    st.markdown(f'<div class="concept-title">📌 {concept.name}</div>', unsafe_allow_html=True)
    if concept.category:
        st.caption(f"Category: {concept.category}")

    # Difficulty tabs
    tab_b, tab_i, tab_e = st.tabs(["🟢 Beginner", "🟡 Intermediate", "🔴 Expert"])

    with tab_b:
        st.markdown(
            f'<div class="level-tab beginner">{concept.get_explanation("beginner")}</div>',
            unsafe_allow_html=True,
        )
    with tab_i:
        st.markdown(
            f'<div class="level-tab intermediate">{concept.get_explanation("intermediate")}</div>',
            unsafe_allow_html=True,
        )
    with tab_e:
        st.markdown(
            f'<div class="level-tab expert">{concept.get_explanation("expert")}</div>',
            unsafe_allow_html=True,
        )

    # Source excerpt
    if concept.source_excerpt:
        st.markdown("**📄 Source Excerpt**")
        st.markdown(
            f'<div class="source-excerpt">{concept.source_excerpt}</div>',
            unsafe_allow_html=True,
        )

    # Related concepts
    related = graph.get_related(concept_id)
    if related:
        st.markdown("**🔗 Related Concepts**")
        for rel_concept, rel_type in related:
            emoji = {"prerequisite": "⬅️", "related": "↔️", "part-of": "🧩"}.get(rel_type, "🔗")
            if st.button(
                f"{emoji} {rel_concept.name} ({rel_type})",
                key=f"rel_{concept_id}_{rel_concept.id}",
            ):
                st.session_state.selected_concept = rel_concept.id
                st.rerun()


# ---------------------------------------------------------------------------
# Quiz page
# ---------------------------------------------------------------------------

def page_quiz() -> None:
    if not st.session_state.graph:
        st.info("📤 Please upload a document or load the demo first.")
        return

    graph: ConceptGraph = st.session_state.graph
    st.markdown("# ❓ Concept Quiz")
    st.markdown("Test your understanding of the concepts!")

    # Collect all questions
    all_questions: list[tuple[Concept, int, dict]] = []
    for concept in graph.concepts:
        for qi, q in enumerate(concept.quiz_questions):
            all_questions.append((concept, qi, {
                "question": q.question,
                "choices": q.choices,
                "correct_index": q.correct_index,
                "explanation": q.explanation,
            }))

    if not all_questions:
        st.warning("No quiz questions available.")
        return

    st.markdown(f"**{len(all_questions)} questions** across {len(graph.concepts)} concepts")
    st.divider()

    for idx, (concept, qi, q_data) in enumerate(all_questions):
        key = f"q_{concept.id}_{qi}"
        st.markdown(f'<div class="quiz-card">', unsafe_allow_html=True)
        st.markdown(f"**Q{idx + 1}.** ({concept.name}) {q_data['question']}")

        answer = st.radio(
            "Select your answer:",
            q_data["choices"],
            key=key,
            index=None,
            label_visibility="collapsed",
        )
        if answer is not None:
            st.session_state.quiz_answers[key] = q_data["choices"].index(answer)

        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Submit Quiz", type="primary", use_container_width=True):
            st.session_state.quiz_submitted = True
            st.rerun()
    with col2:
        if st.button("🔄 Reset Quiz", use_container_width=True):
            st.session_state.quiz_answers = {}
            st.session_state.quiz_submitted = False
            st.rerun()

    if st.session_state.quiz_submitted:
        _show_quiz_results(all_questions)


def _show_quiz_results(
    all_questions: list[tuple[Concept, int, dict]],
) -> None:
    """Display quiz results with score."""
    correct = 0
    total = len(all_questions)

    st.markdown("---")
    st.markdown("## 📊 Results")

    for idx, (concept, qi, q_data) in enumerate(all_questions):
        key = f"q_{concept.id}_{qi}"
        user_answer = st.session_state.quiz_answers.get(key)
        is_correct = user_answer == q_data["correct_index"]
        if is_correct:
            correct += 1

        icon = "✅" if is_correct else "❌" if user_answer is not None else "⏭️"
        st.markdown(f"{icon} **Q{idx + 1}** ({concept.name}): {q_data['question']}")
        if not is_correct and user_answer is not None:
            correct_text = q_data["choices"][q_data["correct_index"]]
            st.caption(f"Correct answer: {correct_text} — {q_data.get('explanation', '')}")

    pct = (correct / total * 100) if total > 0 else 0
    st.divider()

    if pct >= 80:
        st.success(f"🎉 Excellent! {correct}/{total} correct ({pct:.0f}%)")
    elif pct >= 50:
        st.warning(f"👍 Good effort! {correct}/{total} correct ({pct:.0f}%)")
    else:
        st.error(f"📚 Keep studying! {correct}/{total} correct ({pct:.0f}%)")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

page_map = {
    "upload": page_upload,
    "explorer": page_explorer,
    "quiz": page_quiz,
}

current_page = st.session_state.get("page", "upload")
page_fn = page_map.get(current_page, page_upload)
page_fn()
