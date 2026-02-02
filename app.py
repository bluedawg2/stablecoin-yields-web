"""Flask web application for Stablecoin Yield Summarizer.

Provides REST API endpoints and a web UI for browsing stablecoin yield opportunities.
"""

import os
from datetime import datetime
from typing import List, Optional

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from models.opportunity import YieldOpportunity
from main import (
    fetch_opportunities,
    filter_opportunities,
    sort_opportunities,
    SCRAPERS,
    CATEGORY_ALIASES,
)
from config import SUPPORTED_CHAINS

app = Flask(__name__)
CORS(app)

# Suppress console output during web requests
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def get_all_categories() -> List[str]:
    """Get list of all available categories."""
    return list(SCRAPERS.keys())


def get_all_chains() -> List[str]:
    """Get list of all supported chains."""
    return SUPPORTED_CHAINS


def opportunities_to_json(opportunities: List[YieldOpportunity]) -> List[dict]:
    """Convert opportunities to JSON-serializable list."""
    return [opp.to_dict() for opp in opportunities]


# =============================================================================
# API Routes
# =============================================================================

@app.route("/api/opportunities", methods=["GET"])
def api_opportunities():
    """Get yield opportunities with optional filtering.

    Query Parameters:
        category: Filter by category (can repeat for multiple)
        min_apy: Minimum APY (float)
        max_risk: Maximum risk level (Low/Medium/High/Very High)
        chain: Filter by blockchain
        stablecoin: Filter by stablecoin symbol
        protocol: Filter by protocol name
        max_leverage: Maximum leverage (float)
        min_tvl: Minimum TVL in USD (float)
        sort_by: Sort field (apy/tvl/risk/chain/protocol)
        ascending: Sort direction (true/false)
        refresh: Force cache refresh (true/false)

    Returns:
        JSON with opportunities array, count, and timestamp
    """
    try:
        # Parse query parameters
        categories = request.args.getlist("category")
        min_apy = request.args.get("min_apy", type=float)
        max_risk = request.args.get("max_risk")
        chain = request.args.get("chain")
        stablecoin = request.args.get("stablecoin")
        protocol = request.args.get("protocol")
        max_leverage = request.args.get("max_leverage", type=float)
        min_tvl = request.args.get("min_tvl", type=float)
        sort_by = request.args.get("sort_by", "apy")
        ascending = request.args.get("ascending", "false").lower() == "true"
        refresh = request.args.get("refresh", "false").lower() == "true"

        # Fetch opportunities
        use_cache = not refresh
        opportunities = fetch_opportunities(
            categories=categories if categories else None,
            use_cache=use_cache,
        )

        # Apply filters
        opportunities = filter_opportunities(
            opportunities,
            min_apy=min_apy,
            max_risk=max_risk,
            chain=chain,
            stablecoin=stablecoin,
            protocol=protocol,
            max_leverage=max_leverage,
            min_tvl=min_tvl,
        )

        # Sort results
        opportunities = sort_opportunities(
            opportunities,
            sort_by=sort_by,
            ascending=ascending,
        )

        return jsonify({
            "opportunities": opportunities_to_json(opportunities),
            "count": len(opportunities),
            "timestamp": datetime.utcnow().isoformat(),
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "opportunities": [],
            "count": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }), 500


@app.route("/api/categories", methods=["GET"])
def api_categories():
    """Get list of available categories.

    Returns:
        JSON with categories array and aliases mapping
    """
    return jsonify({
        "categories": get_all_categories(),
        "aliases": CATEGORY_ALIASES,
    })


@app.route("/api/chains", methods=["GET"])
def api_chains():
    """Get list of supported chains.

    Returns:
        JSON with chains array
    """
    return jsonify({
        "chains": get_all_chains(),
    })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Force refresh all cached data.

    Returns:
        JSON with success status and count of opportunities fetched
    """
    try:
        opportunities = fetch_opportunities(use_cache=False)
        return jsonify({
            "success": True,
            "count": len(opportunities),
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }), 500


# =============================================================================
# Web Routes
# =============================================================================

@app.route("/")
def index():
    """Main dashboard page."""
    return render_template(
        "index.html",
        categories=get_all_categories(),
        chains=get_all_chains(),
    )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Stablecoin Yield Summarizer - Web Application")
    print("=" * 60)
    print("\nStarting Flask server...")
    print("  - Web UI:  http://localhost:5000")
    print("  - API:     http://localhost:5000/api/opportunities")
    print("\nPress Ctrl+C to stop the server.\n")

    app.run(debug=True, host="0.0.0.0", port=5000)
