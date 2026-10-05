---
name: campaign-performance-review
description: >-
  Use for campaign reviews, portfolio analyses, rankings, investment
  recommendations, and comparisons involving profitability, scale, efficiency,
  or data quality.
---

# Campaign performance review

Apply a consistent, evidence-based method to assess campaign performance.
Base every conclusion on retrieved campaign data and make trade-offs explicit.

## Required tools

- Use `all_campaigns` to identify the campaigns in the portfolio.
- Use `campaign_metrics` to retrieve budget, impressions, conversions, and
  revenue for a campaign.
- Use `compute_roi` to calculate ROI from retrieved revenue and budget values.

Do not invent missing tool results or replace `compute_roi` with a manual ROI
calculation. If a required tool is unavailable or fails, identify the missing
information and limit the analysis accordingly.

## Procedure

1. For a portfolio-wide analysis, call `all_campaigns`; for a focused review,
   start with the campaign identifiers supplied by the user.
2. Call `campaign_metrics` for every campaign included in the analysis.
3. Call `compute_roi` for every campaign whose revenue and budget are valid.
4. Evaluate each campaign on:
   - profitability: ROI;
   - scale: revenue and conversions;
   - efficiency: conversions relative to budget;
   - data quality: missing or invalid values.
5. Do not declare a campaign "best" using ROI alone unless the user explicitly
   requests an ROI-only comparison.
6. If ROI and scale suggest different winners, explain the trade-off.
7. If required data is missing or invalid, identify the affected metrics and
   do not rank the campaign on those metrics.

## Output format

For a portfolio review or investment recommendation, return:

1. Executive summary
2. Metrics table
3. Trade-offs
4. Recommendation
5. Data limitations

For a focused comparison, provide a concise metrics table, explain the relevant
trade-offs, and answer the user's question directly.