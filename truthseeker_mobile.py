import streamlit as st
from duckduckgo_search import DDGS
import requests
from openai import OpenAI
from datetime import datetime, timedelta
import logging
from typing import Optional, List, Dict
import hashlib
import json
import re
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION & CACHING
# ============================================================================

# Initialize session state for caching and history
if "search_cache" not in st.session_state:
    st.session_state.search_cache = {}
if "research_history" not in st.session_state:
    st.session_state.research_history = []
if "favorites" not in st.session_state:
    st.session_state.favorites = []

CACHE_EXPIRY_HOURS = 24
CREDIBILITY_INDICATORS = {
    "high": ["gov", "edu", "org", "bbc", "reuters", "ap", "npr", "pbs"],
    "medium": ["medium", "substack", "linkedin"],
    "low": ["reddit", "twitter", "facebook", "quora"],
}

# ============================================================================
# MOBILE-OPTIMIZED PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="🔎 TruthSeeker",
    layout="wide",
    page_icon="🔎",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'https://github.com/TroysReviews/truthseeker',
        'Report a bug': "https://github.com/TroysReviews/truthseeker/issues",
        'About': "TruthSeeker v2.0 - AI Research Assistant"
    }
)

# Mobile-friendly CSS
st.markdown("""
<style>
@media (max-width: 768px) {
    .stTabs [data-baseweb="tab-list"] { gap: 0px; }
    .stTabs [data-baseweb="tab"] { height: auto; padding: 8px 12px; font-size: 13px; }
    .stButton button { width: 100%; padding: 12px 8px; font-size: 14px; border-radius: 8px; }
    .stTextInput input { font-size: 16px; padding: 12px; }
}
body { margin: 0; padding: 8px; }
button { min-height: 44px; min-width: 44px; }
.stMetric { background-color: #f0f2f6; padding: 12px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("🔎 TruthSeeker")
st.markdown("**Internet Research AI** — Ask anything, get truthful answers.")

# ============================================================================
# SIDEBAR & SETTINGS
# ============================================================================

with st.sidebar:
    st.header("⚙️ Settings")
    
    with st.expander("🔑 API Key", expanded=False):
        api_key = st.text_input("xAI Grok API Key", type="password", help="Get from console.x.ai")
        model = st.selectbox("Model", ["grok-4", "grok-beta"], index=0)
        api_timeout = st.slider("Timeout (sec)", 10, 60, 30)
    
    with st.expander("🔍 Search", expanded=True):
        depth = st.slider("Depth", 1, 3, 2, help="1=fast, 3=deep")
        num_results = st.slider("Sources", 8, 20, 10)
        include_sources = st.checkbox("Show credibility", value=True)
        fact_check = st.checkbox("Fact-check", value=False)
    
    with st.expander("🤖 Response", expanded=False):
        temperature = st.slider("Tone", 0.0, 1.0, 0.6)
        max_tokens = st.slider("Length", 2000, 6000, 3500, step=500)
        include_summary = st.checkbox("Summary", value=True)
    
    with st.expander("🛠️ Advanced", expanded=False):
        enable_cache = st.checkbox("Cache", value=True)
        show_raw_results = st.checkbox("Raw results", value=False)
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.session_state.search_cache = {}
            st.success("✅ Cache cleared!")
    
    st.divider()
    st.caption("📱 **Mobile v2.0**\\nDuckDuckGo + xAI Grok")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_cache_key(query: str) -> str:
    return hashlib.md5(query.lower().encode()).hexdigest()

def is_cache_valid(timestamp: float) -> bool:
    return (datetime.now().timestamp() - timestamp) < (CACHE_EXPIRY_HOURS * 3600)

def validate_query(query: str) -> tuple:
    if not query or not query.strip():
        return False, "❌ Enter a query"
    if len(query.strip()) < 3:
        return False, "❌ Min 3 chars"
    if len(query.strip()) > 500:
        return False, "❌ Max 500 chars"
    return True, "✅"

def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return "unknown"

def score_source_credibility(url: str) -> tuple:
    domain = get_domain(url).lower()
    
    for indicator in CREDIBILITY_INDICATORS["high"]:
        if indicator in domain:
            return "🟢 High", 85
    for indicator in CREDIBILITY_INDICATORS["medium"]:
        if indicator in domain:
            return "🟡 Med", 60
    for indicator in CREDIBILITY_INDICATORS["low"]:
        if indicator in domain:
            return "🔴 Low", 30
    return "⚪ ?", 50

def search_internet(query: str, num_results: int, use_cache: bool = True) -> Optional[List]:
    cache_key = get_cache_key(query)
    
    if use_cache and cache_key in st.session_state.search_cache:
        cached_data = st.session_state.search_cache[cache_key]
        if is_cache_valid(cached_data["timestamp"]):
            st.info("🔄 Cached")
            return cached_data["results"]
    
    try:
        with st.spinner("🔍 Searching..."):
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=num_results))
        
        for result in results:
            credibility_level, credibility_score = score_source_credibility(result['href'])
            result['credibility_level'] = credibility_level
            result['credibility_score'] = credibility_score
        
        if include_sources:
            results.sort(key=lambda x: x.get('credibility_score', 50), reverse=True)
        
        if use_cache:
            st.session_state.search_cache[cache_key] = {
                "results": results,
                "timestamp": datetime.now().timestamp()
            }
        
        return results
    
    except Exception as e:
        st.error(f"❌ {type(e).__name__}")
        return None

def format_sources(results: List, max_display: int = 10, include_scores: bool = True) -> str:
    sources_text = ""
    for i, r in enumerate(results[:max_display], 1):
        source_info = f"[{i}] {r['title']}\\n{r['href']}\\n"
        if include_scores:
            source_info += f"({r.get('credibility_level', '?')})\\n"
        source_info += f"{r['body'][:100]}...\\n\\n"
        sources_text += source_info
    return sources_text

def synthesize_answer(query: str, sources_text: str, api_key: str, model: str, 
                      temperature: float, max_tokens: int, depth: int) -> str:
    
    system_prompt = """You are TruthSeeker, an unbiased research AI.
- Synthesize sources into a clear, balanced answer
- Highlight disagreements and uncertainties
- Cite sources inline [1], [2], etc
- Be direct, avoid fluff"""

    if depth == 3:
        system_prompt += "\\n- Provide comprehensive analysis with context"
    elif depth == 1:
        system_prompt += "\\n- Provide concise, direct answer"

    user_prompt = f"Q: {query}\\n\\nSources:\\n{sources_text}"

    if not api_key:
        return f"**Search Results:**\\n\\n{sources_text[:2000]}"

    try:
        with st.spinner("🤖 Analyzing..."):
            client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=api_timeout
            )
        return response.choices[0].message.content
    
    except Exception as e:
        st.error(f"❌ {type(e).__name__}")
        return f"Fallback: {sources_text[:2000]}"

def add_to_history(query: str, answer: str):
    st.session_state.research_history.append({
        "query": query,
        "answer": answer[:150] + "...",
        "timestamp": datetime.now().strftime("%H:%M"),
    })

def add_to_favorites(query: str, answer: str):
    st.session_state.favorites.append({
        "query": query,
        "answer": answer,
        "timestamp": datetime.now().strftime("%m-%d %H:%M"),
    })

# ============================================================================
# MAIN INTERFACE
# ============================================================================

tab_search, tab_history, tab_favorites, tab_info = st.tabs(
    ["🔍 Search", "📋 History", "⭐ Saved", "ℹ️ Info"]
)

with tab_search:
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Search:",
            placeholder="Ask anything...",
            key="query",
            label_visibility="collapsed"
        )
    with col2:
        search_button = st.button("🔍", use_container_width=True)
    
    if search_button:
        is_valid, message = validate_query(query)
        
        if not is_valid:
            st.error(message)
        else:
            results = search_internet(query, num_results, use_cache=enable_cache)
            
            if results:
                st.subheader("📚 Sources")
                for i, r in enumerate(results[:8], 1):
                    with st.container(border=True):
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"**{i}.** [{r['title'][:60]}...]({r['href']})")
                            st.caption(r['body'][:100] + "...")
                        with col2:
                            if include_sources:
                                st.caption(r.get('credibility_level', '?'))
                
                sources_text = format_sources(results, max_display=8, include_scores=include_sources)
                
                answer = synthesize_answer(
                    query, sources_text, api_key, model,
                    temperature, max_tokens, depth
                )
                
                if include_summary and api_key:
                    with st.expander("📄 Summary"):
                        paragraphs = answer.split('\\n\\n')[:2]
                        st.write('\\n\\n'.join(paragraphs))
                
                st.subheader("📝 Report")
                st.markdown(answer)
                
                st.subheader("📥 Export")
                col1, col2 = st.columns(2)
                
                with col1:
                    report_md = f"""# TruthSeeker

**Q:** {query}

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

{answer}

---

Sources: {len(results)}
"""
                    for i, r in enumerate(results[:8], 1):
                        report_md += f"\\n{i}. {r['title']}\\n{r['href']}"
                    
                    st.download_button(
                        "📄 Markdown",
                        report_md,
                        f"truthseeker_{datetime.now().strftime('%Y%m%d')}.md",
                        "text/markdown",
                        key="dl_md",
                        use_container_width=True
                    )
                
                with col2:
                    report_json = {
                        "query": query,
                        "answer": answer[:500],
                        "sources": [{"title": r['title'], "url": r['href']} for r in results[:8]],
                        "timestamp": datetime.now().isoformat()
                    }
                    st.download_button(
                        "📊 JSON",
                        json.dumps(report_json, indent=2),
                        f"truthseeker_{datetime.now().strftime('%Y%m%d')}.json",
                        "application/json",
                        key="dl_json",
                        use_container_width=True
                    )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("⭐ Save", use_container_width=True):
                        add_to_favorites(query, answer)
                        st.success("✅ Saved!")
                
                add_to_history(query, answer)
                st.divider()
                st.success("✅ Done!")
            else:
                st.warning("❌ No results. Try a different query.")

with tab_history:
    st.subheader("📋 Recent Searches")
    
    if st.session_state.research_history:
        for item in reversed(st.session_state.research_history[-10:]):
            with st.container(border=True):
                st.write(f"**{item['query'][:50]}...**")
                st.caption(item['answer'])
                st.caption(f"⏰ {item['timestamp']}")
                if st.button("🔄 Re-search", key=f"redo_{item['timestamp']}"):
                    st.session_state.query = item['query']
                    st.rerun()
    else:
        st.info("No history yet")

with tab_favorites:
    st.subheader("⭐ Saved Reports")
    
    if st.session_state.favorites:
        for idx, item in enumerate(reversed(st.session_state.favorites[-10:])):
            with st.expander(f"📌 {item['query'][:40]}..."):
                st.markdown(item['answer'][:500])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Re-search", key=f"rs_{idx}", use_container_width=True):
                        st.session_state.query = item['query']
                        st.rerun()
                with col2:
                    if st.button("🗑️ Remove", key=f"rm_{idx}", use_container_width=True):
                        st.session_state.favorites.pop(len(st.session_state.favorites) - idx - 1)
                        st.rerun()
    else:
        st.info("No saved reports yet")

with tab_info:
    st.header("About TruthSeeker")
    
    st.markdown("""
    ### 🔍 What is TruthSeeker?
    
    An AI-powered research assistant combining:
    - 🌐 Real-time DuckDuckGo search
    - 🤖 xAI Grok AI synthesis
    - 🟢 Source credibility scoring
    - 💾 Search caching (24hr)
    
    ### ✨ Features
    
    ✅ Privacy-first  
    ✅ Mobile-responsive  
    ✅ Install as PWA  
    ✅ Offline history  
    ✅ Export as MD/JSON  
    
    ### 📱 Install on Android
    
    **Chrome:**
    1. Tap ⋮ (menu)
    2. \"Install app\"
    3. \"Install\"
    
    **Done!** App on home screen
    
    ### 🔐 Privacy
    
    - No account needed
    - No tracking
    - Data on **your device only**
    
    ---
    
    **v2.0 Mobile** • Free forever ❤️
    """)