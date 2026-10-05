---
name: campaign-quotation-policy
description: >-
  Use for campaign prices, quotations, cost estimates, budget scenarios, or
  advertising briefs that specify a sector and a target number of impressions.
---

# Campaign quotation policy

Create a policy-compliant campaign quotation from authoritative pricing data.

## Required tool

Use `campaign_quote` for every scenario and every monetary value. Never
calculate, infer, or modify CPM rates or campaign prices directly.

## Required inputs

- Advertising sector
- Requested number of impressions

If either input is missing, ask the user for it before requesting a quote.
Reject zero or negative impression volumes.

## Procedure

1. Extract the sector and requested impressions from the user's request.
2. Calculate only the impression volumes for these scenarios:
   - lean: 20% fewer impressions than requested;
   - requested: the original number of impressions;
   - extended: 20% more impressions than requested.
3. Round scenario impressions to whole numbers.
4. Call `campaign_quote` once for each scenario.
5. Use the CPM and total price returned by the tool without alteration.
6. If the tool reports `used_default_rate=true`, state clearly that the sector
   was priced with the default CPM.
7. Do not describe the result as an approved commercial offer.

## Output format

Return:

1. A one-sentence summary
2. A table with scenario, impressions, CPM, and total price
3. Any default-rate warning
4. A note that the figures are indicative quotations