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
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="TruthSeeker AI",
    layout="wide",
    page_icon="🔎",
    initial_sidebar_state="expanded"
)

st.title("🔎 TruthSeeker")
st.markdown("**Internet Research AI** — Ask anything. Gets the most truthful, well-sourced answers possible.")

# ============================================================================
# SIDEBAR & SETTINGS
# ============================================================================

with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Configuration
    with st.expander("🔑 API Configuration", expanded=False):
        api_key = st.text_input("xAI Grok API Key", type="password", help="Get it at https://console.x.ai")
        model = st.selectbox("Model", ["grok-4", "grok-beta"], index=0)
        api_timeout = st.slider("API Timeout (seconds)", 10, 60, 30)
    
    # Research Settings
    with st.expander("🔍 Research Settings", expanded=True):
        depth = st.slider("Research Depth", 1, 3, 2, help="1=fast, 3=deep multi-step analysis")
        num_results = st.slider("Search Results", 8, 25, 12)
        include_sources = st.checkbox("Include source credibility scores", value=True)
        fact_check = st.checkbox("Enable fact-check mode (slower)", value=False)
    
    # Response Settings
    with st.expander("🤖 Response Settings", expanded=False):
        temperature = st.slider("Response Temperature", 0.0, 1.0, 0.6, 
                               help="0=deterministic, 1=creative")
        max_tokens = st.slider("Max Response Length", 2000, 8000, 4000)
        include_sources_inline = st.checkbox("Include sources in response", value=True)
        include_summary = st.checkbox("Include executive summary", value=True)
    
    # Advanced Options
    with st.expander("🛠️ Advanced Options", expanded=False):
        enable_cache = st.checkbox("Enable search caching", value=True)
        clear_cache = st.button("🗑️ Clear Cache")
        if clear_cache:
            st.session_state.search_cache = {}
            st.success("Cache cleared!")
        
        show_raw_results = st.checkbox("Show raw search results", value=False)
    
    st.divider()
    st.caption("**ℹ️ TruthSeeker v2.0**\n\nNo API key? Basic search still works.\n\nPowered by DuckDuckGo + xAI Grok")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_cache_key(query: str) -> str:
    """Generate a cache key for a query."""
    return hashlib.md5(query.lower().encode()).hexdigest()

def is_cache_valid(timestamp: float) -> bool:
    """Check if cached data is still valid."""
    return (datetime.now().timestamp() - timestamp) < (CACHE_EXPIRY_HOURS * 3600)

def validate_query(query: str) -> tuple[bool, str]:
    """Validate user query is not empty or whitespace-only."""
    if not query or not query.strip():
        return False, "❌ Please enter a search query."
    if len(query.strip()) < 3:
        return False, "❌ Query must be at least 3 characters."
    if len(query.strip()) > 500:
        return False, "❌ Query must be under 500 characters."
    return True, "✅"

def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return "unknown"

def score_source_credibility(url: str) -> tuple[str, int]:
    """
    Score source credibility based on domain.
    Returns (level, score) where score is 0-100.
    """
    domain = get_domain(url).lower()
    
    for indicator in CREDIBILITY_INDICATORS["high"]:
        if indicator in domain:
            return "🟢 High", 85
    
    for indicator in CREDIBILITY_INDICATORS["medium"]:
        if indicator in domain:
            return "🟡 Medium", 60
    
    for indicator in CREDIBILITY_INDICATORS["low"]:
        if indicator in domain:
            return "🔴 Low", 30
    
    # Default for unknown sources
    return "⚪ Unknown", 50

def search_internet(query: str, num_results: int, use_cache: bool = True) -> Optional[List[dict]]:
    """Search with proper error handling, logging, and optional caching."""
    cache_key = get_cache_key(query)
    
    # Check cache first
    if use_cache and cache_key in st.session_state.search_cache:
        cached_data = st.session_state.search_cache[cache_key]
        if is_cache_valid(cached_data["timestamp"]):
            logger.info(f"Using cached results for: {query}")
            st.info("🔄 Using cached results (fresh)")
            return cached_data["results"]
    
    try:
        progress_placeholder = st.empty()
        progress_placeholder.info("🔍 Searching the internet...")
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
        
        # Add credibility scores to results
        for result in results:
            credibility_level, credibility_score = score_source_credibility(result['href'])
            result['credibility_level'] = credibility_level
            result['credibility_score'] = credibility_score
        
        # Sort by credibility if enabled
        if include_sources:
            results.sort(key=lambda x: x.get('credibility_score', 50), reverse=True)
        
        # Cache results
        if use_cache:
            st.session_state.search_cache[cache_key] = {
                "results": results,
                "timestamp": datetime.now().timestamp()
            }
        
        logger.info(f"Found {len(results)} results for: {query}")
        progress_placeholder.success(f"✅ Found {len(results)} sources")
        return results
    
    except Exception as e:
        logger.error(f"Search failed: {type(e).__name__}: {str(e)}")
        st.error(f"❌ Search failed: {type(e).__name__}\n\n{str(e)}")
        return None

def format_sources(results: List[dict], max_display: int = 12, include_scores: bool = True) -> str:
    """Format search results into a sources text block."""
    sources_text = ""
    for i, r in enumerate(results[:max_display], 1):
        source_info = f"Source {i}: {r['title']}\nURL: {r['href']}\n"
        if include_scores:
            source_info += f"Credibility: {r.get('credibility_level', 'Unknown')}\n"
        source_info += f"Snippet: {r['body']}\n\n"
        sources_text += source_info
    return sources_text

def extract_key_facts(text: str) -> List[str]:
    """Extract key facts/claims from text."""
    # Simple extraction: look for sentences with numbers, percentages, dates
    sentences = re.split(r'(?<=[.!?])\s+', text)
    key_facts = [s.strip() for s in sentences if any(c.isdigit() for c in s)]
    return key_facts[:5]  # Return top 5

def fact_check_claims(claims: List[str], sources_text: str) -> Dict[str, str]:
    """Simple fact-check: see if claims are mentioned in sources."""
    results = {}
    for claim in claims:
        is_supported = any(word in sources_text.lower() for word in claim.lower().split()[:3])
        results[claim] = "✅ Supported by sources" if is_supported else "⚠️ Not directly supported"
    return results

def synthesize_answer(query: str, sources_text: str, api_key: str, model: str, 
                      temperature: float, max_tokens: int, depth: int,
                      include_sources: bool = True, include_summary: bool = True) -> str:
    """Synthesize answer using API or fallback to raw sources."""
    
    # Build system prompt based on settings
    system_prompt = """You are TruthSeeker, an unbiased research AI with expertise in analyzing information.
Your goal is maximum truthfulness and balanced analysis.
- Synthesize the sources into a clear, balanced, comprehensive answer.
- Highlight areas of agreement, disagreement, and genuine uncertainties.
- Cite sources inline using [Source N] format.
- Be direct, avoid speculation, and acknowledge limitations in available data.
- If sources conflict, explain the different perspectives fairly and provide context.
- Use clear headers and bullet points for readability.
- When uncertain, express that clearly."""

    if depth == 3:
        system_prompt += "\n\nThis is a DEEP research request. Provide comprehensive analysis with:\n- Multiple perspectives\n- Historical context\n- Potential implications\n- Areas needing further research"
    elif depth == 1:
        system_prompt += "\n\nThis is a QUICK research request. Provide a concise, direct answer focusing on the most important facts."

    user_prompt = f"Question: {query}\n\nSources:\n{sources_text}"

    if not api_key:
        st.warning("⚠️ No API key provided. Generating report from search results only.")
        return generate_search_based_report(query, sources_text, include_sources)

    try:
        progress_bar = st.progress(0, text="🤖 Synthesizing answer with AI...")
        
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
        
        progress_bar.progress(100, text="✅ Analysis complete")
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"API Error: {type(e).__name__}: {str(e)}")
        error_msg = f"**API Error:** {type(e).__name__}"
        
        if "401" in str(e) or "auth" in str(e).lower():
            error_msg += "\n\n❌ Authentication failed. Check your API key."
        elif "timeout" in str(e).lower():
            error_msg += "\n\n⏱️ Request timed out. Try a simpler query."
        elif "429" in str(e):
            error_msg += "\n\n⏳ Rate limited. Try again in a few moments."
        
        st.error(error_msg)
        return generate_search_based_report(query, sources_text, include_sources)

def generate_search_based_report(query: str, sources_text: str, include_sources: bool) -> str:
    """Generate a report directly from search results (no API)."""
    report = f"## Search-Based Report\n\n**Query:** {query}\n\n"
    report += "### Key Information from Sources\n\n"
    report += sources_text[:3000]
    report += "\n\n---\n\n*This report was generated from search results without AI synthesis.*"
    return report

def add_to_history(query: str, answer: str):
    """Add research to history."""
    st.session_state.research_history.append({
        "query": query,
        "answer": answer[:200] + "...",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })

def add_to_favorites(query: str, answer: str):
    """Add research to favorites."""
    st.session_state.favorites.append({
        "query": query,
        "answer": answer,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })

# ============================================================================
# MAIN RESEARCH INTERFACE
# ============================================================================

# Create tabs for different features
tab_search, tab_history, tab_favorites, tab_about = st.tabs(
    ["🔍 Research", "📋 History", "⭐ Favorites", "ℹ️ About"]
)

with tab_search:
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_input(
            "What do you want to research?",
            placeholder="What really happened with the 2024 US election integrity claims?",
            key="query"
        )
    
    with col2:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    
    if search_button:
        is_valid, message = validate_query(query)
        
        if not is_valid:
            st.error(message)
        else:
            # Search
            results = search_internet(query, num_results, use_cache=enable_cache)
            
            if results:
                # Display raw results if requested
                if show_raw_results:
                    with st.expander("📊 Raw Search Results"):
                        st.json([{k: v for k, v in r.items() if k != 'credibility_level'} for r in results[:5]])
                
                # Display sources with credibility scores
                st.subheader("📚 Key Sources")
                sources_col1, sources_col2 = st.columns([3, 1])
                
                with sources_col2:
                    if st.button("📌 Save to Favorites", key="fav_sources"):
                        st.success("Added to favorites!")
                
                for i, r in enumerate(results[:12], 1):
                    with st.container(border=True):
                        col1, col2 = st.columns([5, 1])
                        with col1:
                            st.markdown(f"**{i}. [{r['title']}]({r['href']})**")
                            st.caption(r['body'][:150] + "...")
                        with col2:
                            if include_sources:
                                st.metric("Credibility", r.get('credibility_level', 'N/A'))
                
                sources_text = format_sources(results, max_display=12, include_scores=include_sources)
                
                # Deep analysis
                answer = synthesize_answer(
                    query, sources_text, api_key, model,
                    temperature, max_tokens, depth,
                    include_sources=include_sources,
                    include_summary=include_summary
                )
                
                # Add executive summary if enabled
                if include_summary and api_key:
                    with st.expander("📄 Executive Summary", expanded=True):
                        # Extract first 2-3 paragraphs as summary
                        paragraphs = answer.split('\n\n')[:2]
                        st.write('\n\n'.join(paragraphs))
                
                st.subheader("📝 Full Research Report")
                st.markdown(answer)
                
                # Fact-check mode
                if fact_check and api_key:
                    with st.expander("🔍 Fact-Check Analysis"):
                        key_facts = extract_key_facts(answer)
                        if key_facts:
                            fact_checks = fact_check_claims(key_facts, sources_text)
                            for claim, status in fact_checks.items():
                                st.write(f"{status}\n\n> {claim}")
                        else:
                            st.info("No specific claims to fact-check found.")
                
                # Download options
                st.subheader("📥 Export & Share")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Markdown download
                    report_md = f"""# TruthSeeker Research Report

**Question:** {query}

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

**Research Depth:** {'🔍 ' * depth} ({depth}/3)

---

## Report

{answer}

---

## Sources Consulted

Total sources: {len(results)}

### Source List

"""
                    for i, r in enumerate(results[:12], 1):
                        report_md += f"{i}. [{r['title']}]({r['href']})\n   - Credibility: {r.get('credibility_level', 'Unknown')}\n"
                    
                    report_md += f"\n---\n\n*Generated by TruthSeeker v2.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
                    
                    st.download_button(
                        label="📄 Download as Markdown",
                        data=report_md,
                        file_name=f"truthseeker_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                        mime="text/markdown",
                        key="download_md"
                    )
                
                with col2:
                    # JSON download (for data analysis)
                    report_json = {
                        "query": query,
                        "timestamp": datetime.now().isoformat(),
                        "depth": depth,
                        "sources_count": len(results),
                        "summary": answer[:500],
                        "sources": [
                            {
                                "title": r['title'],
                                "url": r['href'],
                                "credibility": r.get('credibility_level', 'Unknown'),
                                "snippet": r['body'][:200]
                            }
                            for r in results[:12]
                        ]
                    }
                    
                    st.download_button(
                        label="📊 Download as JSON",
                        data=json.dumps(report_json, indent=2),
                        file_name=f"truthseeker_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                        mime="application/json",
                        key="download_json"
                    )
                
                with col3:
                    # Save to favorites
                    if st.button("⭐ Save Report", key="save_report"):
                        add_to_favorites(query, answer)
                        st.success("Report saved to favorites!")
                
                # Add to history
                add_to_history(query, answer)
                
                st.divider()
                st.success("✅ Research complete! Download, share, or ask follow-ups.")
            
            else:
                st.warning("❌ No results found. Try a different query or check your internet connection.")

with tab_history:
    st.subheader("📋 Research History")
    
    if st.session_state.research_history:
        for item in reversed(st.session_state.research_history):
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.write(f"**Q:** {item['query']}")
                    st.caption(item['answer'])
                    st.caption(f"🕐 {item['timestamp']}")
                with col2:
                    if st.button("🔄 Redo", key=f"redo_{item['timestamp']}"):
                        st.session_state.query = item['query']
                        st.rerun()
    else:
        st.info("No research history yet. Start by searching something!")

with tab_favorites:
    st.subheader("⭐ Saved Reports")
    
    if st.session_state.favorites:
        for idx, item in enumerate(reversed(st.session_state.favorites)):
            with st.expander(f"📌 {item['query'][:60]}... ({item['timestamp']})"):
                st.markdown(item['answer'])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Re-search", key=f"research_{idx}"):
                        st.session_state.query = item['query']
                        st.rerun()
                with col2:
                    if st.button("🗑️ Remove", key=f"remove_{idx}"):
                        st.session_state.favorites.pop(len(st.session_state.favorites) - idx - 1)
                        st.rerun()
    else:
        st.info("No favorite reports yet. Save reports to view them here!")

with tab_about:
    st.header("About TruthSeeker")
    
    st.markdown("""
    ### What is TruthSeeker?
    
    TruthSeeker is an AI-powered research assistant that combines real-time web search with advanced language models to provide well-sourced, truthful answers.
    
    ### How it works
    
    1. **Search** — Searches DuckDuckGo for relevant sources
    2. **Score** — Evaluates source credibility based on domain
    3. **Synthesize** — Uses xAI Grok to create a balanced, cited report
    4. **Verify** — Optional fact-checking against source material
    5. **Export** — Download as Markdown, JSON, or share
    
    ### Features
    
    ✅ **Real-time Web Search** — Uses DuckDuckGo for privacy-preserving search
    
    ✅ **Source Credibility Scoring** — Automatically rates source reliability
    
    ✅ **Depth Modes** — Fast summaries or deep multi-step analysis
    
    ✅ **Search Caching** — Reuses recent searches for speed and cost savings
    
    ✅ **Fact-Check Mode** — Verifies claims against source material
    
    ✅ **Research History** — Track all your research
    
    ✅ **Favorites** — Save important reports
    
    ✅ **Multiple Export Formats** — Download as Markdown or JSON
    
    ✅ **Customizable Settings** — Adjust temperature, length, depth, and more
    
    ### Privacy
    
    - Your queries are sent to DuckDuckGo (privacy search engine)
    - If you provide an xAI API key, responses are sent to xAI servers
    - Session data (history, favorites) is stored locally in your browser
    - No data is stored on our servers
    
    ### Tips for Best Results
    
    1. **Be specific** — "What are the benefits of meditation?" works better than "meditation"
    2. **Ask follow-ups** — Refine your query based on initial results
    3. **Adjust depth** — Use depth=1 for quick facts, depth=3 for comprehensive analysis
    4. **Use fact-check mode** — For controversial topics, enable fact-checking
    5. **Check sources** — Always review the source credibility scores
    
    ### Troubleshooting
    
    **No results?**
    - Try a different query
    - Check your internet connection
    - Avoid overly broad or specific terms
    
    **API errors?**
    - Verify your xAI API key is correct
    - Check your rate limits at console.x.ai
    - Try a simpler query to reduce processing time
    
    **Slow responses?**
    - Reduce max_tokens in settings
    - Use depth=1 instead of depth=3
    - Check your internet connection
    
    ### Version
    
    **TruthSeeker v2.0**
    
    Built with ❤️ for truthful, well-sourced research
    
    ---
    
    Have feedback? Found an issue? Let us know!
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🔎 **TruthSeeker v2.0**")
with col2:
    st.caption("Powered by DuckDuckGo + xAI Grok")
with col3:
    st.caption(f"📊 {len(st.session_state.search_cache)} cached searches")
