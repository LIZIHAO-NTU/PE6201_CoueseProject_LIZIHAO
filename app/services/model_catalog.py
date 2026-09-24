from __future__ import annotations


MODEL_PROFILES = (
    {
        "id": "google/gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "tier": "Recommended default",
        "use_case": "Best everyday balance for repeated development and evaluation runs.",
        "input_cost_per_million": 0.30,
        "output_cost_per_million": 2.50,
    },
    {
        "id": "anthropic/claude-haiku-4.5",
        "name": "Claude Haiku 4.5",
        "tier": "Fast Claude comparison",
        "use_case": "Useful for comparing model families while keeping latency and cost controlled.",
        "input_cost_per_million": 1.00,
        "output_cost_per_million": 5.00,
    },
    {
        "id": "anthropic/claude-sonnet-4.6",
        "name": "Claude Sonnet 4.6",
        "tier": "High-quality review",
        "use_case": "Use selectively for difficult or ambiguous cases and final showcase comparisons.",
        "input_cost_per_million": 3.00,
        "output_cost_per_million": 15.00,
    },
)

MODEL_BY_ID = {profile["id"]: profile for profile in MODEL_PROFILES}
