# 🔎 TruthSeeker AI

An AI-powered internet research assistant that combines real-time web search with advanced language models to provide well-sourced, truthful answers.

## Features

✅ **Real-time Web Search** — Uses DuckDuckGo for privacy-preserving search  
✅ **Source Credibility Scoring** — Automatically rates source reliability (🟢 High, 🟡 Medium, 🔴 Low)  
✅ **Depth Modes** — Fast summaries (1) or deep multi-step analysis (3)  
✅ **Search Caching** — Reuses recent searches for speed and cost savings  
✅ **Fact-Check Mode** — Verifies claims against source material  
✅ **Research History** — Track all your research queries  
✅ **Favorites** — Save important reports for later  
✅ **Multiple Export Formats** — Download as Markdown or JSON  
✅ **Customizable Settings** — Adjust temperature, token length, depth, and more  

## Installation

### Prerequisites
- Python 3.8+
- An xAI Grok API key (optional, but recommended) from [console.x.ai](https://console.x.ai)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/TroysReviews/truthseeker.git
cd truthseeker
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the app:
```bash
streamlit run truthseeker.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### Quick Start

1. **Enter a query** — Type what you want to research
2. **Adjust settings** (optional):
   - Research Depth (1=fast, 3=deep)
   - Number of sources (8-25)
   - Temperature (0=deterministic, 1=creative)
   - Enable fact-checking
3. **Click Search** — The app will:
   - Search DuckDuckGo for sources
   - Score each source's credibility
   - Synthesize findings using xAI Grok
   - Generate a comprehensive report
4. **Export or Save**:
   - Download as Markdown or JSON
   - Save to Favorites for later
   - View Research History

### Settings Explained

#### Research Settings
- **Depth**: 1=quick facts, 2=balanced (default), 3=comprehensive analysis
- **Search Results**: How many sources to retrieve (8-25)
- **Credibility Scores**: Show/hide source reliability ratings
- **Fact-Check Mode**: Verify claims against source material (slower)

#### Response Settings
- **Temperature**: 0=precise, 0.6=balanced (default), 1=creative
- **Max Length**: Token count for response (2000-8000, default 4000)
- **Executive Summary**: Auto-generate concise summary

#### Advanced Options
- **Search Caching**: Reuse recent searches (24-hour expiry)
- **Raw Results**: Debug view of search data
- **Clear Cache**: Manually clear cached searches

## API Configuration

### Using xAI Grok (Optional)

For AI-powered synthesis:

1. Get an API key from [console.x.ai](https://console.x.ai)
2. Paste it in Settings → API Configuration → xAI Grok API Key
3. Select your model (grok-4 or grok-beta)

**Without an API key**, the app works fine — just displays search results without AI synthesis.

## Examples

### Example 1: Quick Fact Check
- Depth: 1 (fast)
- Temperature: 0.2 (deterministic)
- Query: "What's the capital of Brazil?"
- Result: Direct answer with top sources

### Example 2: Deep Research
- Depth: 3 (comprehensive)
- Temperature: 0.6 (balanced)
- Fact-Check: Enabled
- Query: "What are the latest developments in renewable energy?"
- Result: Multi-perspective analysis with historical context

### Example 3: Controversy Analysis
- Depth: 2 (balanced)
- Temperature: 0.7 (creative)
- Credibility Scores: Enabled
- Fact-Check: Enabled
- Query: "Different perspectives on cryptocurrency regulation"
- Result: Fair comparison of viewpoints with source credibility

## Privacy

- Your queries are sent to DuckDuckGo (privacy-focused search engine)
- If you provide an xAI API key, responses are sent to xAI servers
- Session data (history, favorites) is stored **locally in your browser**
- No data is stored on our servers
- No tracking or analytics

## Troubleshooting

### No search results?
- Try a different query (more specific is better)
- Check your internet connection
- Avoid overly broad or specific terms

### API authentication errors?
- Verify your xAI API key is correct
- Check your API usage at [console.x.ai](https://console.x.ai)
- Ensure you have API credits remaining

### Slow responses?
- Reduce max_tokens in settings
- Use depth=1 instead of depth=3
- Try a simpler query
- Check your internet connection

### Cache not working?
- Click "🗑️ Clear Cache" in Advanced Options
- Check "Enable search caching" is checked
- Note: Cache expires after 24 hours

## Architecture

```
User Query
    ↓
[Validation] → Check query length/format
    ↓
[Cache Check] → Reuse if recent query exists
    ↓
[DuckDuckGo Search] → Retrieve sources
    ↓
[Credibility Scoring] → Rate each source
    ↓
[AI Synthesis] → xAI Grok analyzes & cites sources
    ↓
[Fact-Check] (optional) → Verify claims
    ↓
[Export] → Download as MD/JSON or save to favorites
```

## Performance Tips

1. **Enable caching** — Reuse searches saves API calls and money
2. **Use appropriate depth** — 1 for quick facts, 3 for research papers
3. **Adjust temperature** — 0.2-0.4 for factual queries, 0.6-0.8 for creative
4. **Reduce token limit** — Shorter responses are faster
5. **Batch searches** — Research multiple topics in one session to warm cache

## Contributing

Feel free to submit issues, fork the repository, or create pull requests!

## License

MIT License — see LICENSE file for details

## Credits

- Built with [Streamlit](https://streamlit.io/)
- Search powered by [DuckDuckGo](https://duckduckgo.com/)
- AI synthesis by [xAI Grok](https://grok.x.ai/)

## Support

Have questions or feedback? 
- Open an issue on GitHub
- Check the "About" tab in the app for FAQs
- Email: support@truthseeker.ai (placeholder)

---

**TruthSeeker v2.0** — Built with ❤️ for truthful, well-sourced research
