# Lessons Learned

This document tracks bugs, their root causes, and patterns to avoid in the future.

---

## 2026-02-03: Pendle Looping Borrow Rate Mismatch

### What Broke
The Pendle Looping scraper displayed borrow rates that didn't match what users see on Morpho.org. Users reported seeing ~7.43% in our app vs ~8.14% on Morpho.

### Why It Broke
The code used `avgNetBorrowApy` (historical average borrow rate) instead of `borrowApy` (current instantaneous rate). The Morpho API provides multiple rate fields:

- `borrowApy` - Current instantaneous borrow rate (what Morpho.org displays)
- `netBorrowApy` - Net borrow rate accounting for rewards
- `avgNetBorrowApy` - Historical average of the net borrow rate

A misleading comment in the code stated "Use avgNetBorrowApy (matches Morpho UI)" which was incorrect.

### Files Affected
- `streamlit_app.py:1170-1172` - `PendleLoopScraper._fetch_morpho_markets()`
- `scrapers/pendle_loop.py:212-216` - `PendleLoopScraper._find_best_borrow_markets()`

### The Fix
Changed both files to use `borrowApy` instead of `avgNetBorrowApy`:

```python
# Before (WRONG)
avg_borrow = state.get("avgNetBorrowApy") or state.get("borrowApy") or 0
borrow_apy = avg_borrow * 100

# After (CORRECT)
borrow_apy = (state.get("borrowApy") or 0) * 100
```

### Pattern to Avoid
**Don't assume API field names describe what the UI displays.** When integrating with external protocols:

1. Verify which API field matches the UI by testing against the live website
2. Don't trust comments that claim a field "matches the UI" without verification
3. Document which API field corresponds to which UI element

### Rule to Prevent Recurrence
**When fetching rates from external DeFi protocols:**

1. Always verify the displayed rate against the protocol's live UI before deployment
2. Add inline comments explaining WHY a specific field was chosen (not just which one)
3. If multiple rate fields exist (e.g., `borrowApy`, `avgBorrowApy`, `netBorrowApy`), document the difference between them
4. Consider adding a verification test that compares scraped rates against known UI values

### Cross-Reference
Note that other Morpho scrapers in the codebase (`MorphoLoopScraper`, `MorphoLendScraper`) correctly use `borrowApy`. Only the Pendle Loop scrapers had this bug because they were written separately with an incorrect assumption.
