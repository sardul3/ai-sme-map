#!/usr/bin/env python3
"""Print arXiv category watchlist for quarterly Skim intake. Does not fetch."""

from __future__ import annotations

WATCH = [
    ("cs.LG", "machine learning"),
    ("cs.AI", "artificial intelligence"),
    ("cs.CL", "computation and language"),
    ("cs.CV", "computer vision"),
    ("stat.ML", "stat ML"),
    ("cs.RO", "robotics"),
]

print("Quarterly Skim-first. Do not auto-promote to Do.")
print("Search: https://arxiv.org/list/{cat}/recent")
for cat, name in WATCH:
    print(f"  {cat:8} {name}")
