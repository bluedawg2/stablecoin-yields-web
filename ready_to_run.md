# Ready to Run

## Prerequisites

- Python 3.14
- pip

## Install Dependencies

```bash
pip install streamlit pandas requests beautifulsoup4 aiohttp
```

For scrapers that use Selenium (optional, only needed for some sources):

```bash
pip install selenium webdriver-manager
```

## Run the App

```bash
streamlit run streamlit_app.py
```

Opens at `http://localhost:8501` by default.

## First Load

- On first load, all scrapers fetch live data from their APIs. This takes 30–90 seconds.
- Results are cached for 5 minutes. Subsequent loads are instant.
- Click **Refresh** in the sidebar to force a fresh fetch.

## Common Issues

| Problem | Fix |
|---|---|
| Blank table on first load | Wait for scrapers to finish; click Refresh |
| `ModuleNotFoundError: streamlit` | Run `pip install streamlit pandas` |
| A scraper returns no data | Check your internet connection; some APIs are geo-restricted |
| Very high APY numbers (>200%) | These may be Pendle YT tokens — use "Exclude Yield Tokens (YT)" filter |
| Cache is stale | Delete the `.cache/` directory and click Refresh |

## Environment Notes

- No `.env` file needed — all data is fetched from public APIs
- Cache is written to `.cache/` in the project root (auto-created)
- Hidden rows persist in `.hidden_items.json` in the project root
