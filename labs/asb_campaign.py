"""
Synthetic advertising-campaign data — AdvertSphere Broadcasting (training only).
No real data: this is just a shared base used by all Day 2 exercises.
Import this module from exercises 1, 3 and 4.

Per-campaign metrics:
- budget_eur   : money spent
- impressions  : delivered impressions
- clicks       : total clicks
- conversions  : attributed conversions
- revenue_eur  : revenue attributed to the campaign
"""

CAMPAIGNS = [
    {"id": "CMP-001", "client": "AutoMilano", "sector": "Automotive",
     "budget_eur": 120000, "impressions": 8_400_000, "clicks": 42_000,
     "conversions": 1_260, "revenue_eur": 210000, "channel": "TV+Digital",
     "start": "2026-01-07", "end": "2026-02-04"},
    {"id": "CMP-002", "client": "BancaVerde", "sector": "Finance",
     "budget_eur": 90000, "impressions": 5_100_000, "clicks": 20_400,
     "conversions": 612, "revenue_eur": 132000, "channel": "Digital",
     "start": "2026-01-14", "end": "2026-02-11"},
    {"id": "CMP-003", "client": "FreschErba", "sector": "FMCG",
     "budget_eur": 60000, "impressions": 6_800_000, "clicks": 34_000,
     "conversions": 1_700, "revenue_eur": 96000, "channel": "TV",
     "start": "2026-02-01", "end": "2026-02-28"},
    {"id": "CMP-004", "client": "VoloBlu", "sector": "Travel",
     "budget_eur": 150000, "impressions": 9_200_000, "clicks": 55_200,
     "conversions": 2_208, "revenue_eur": 351000, "channel": "TV+Digital",
     "start": "2026-02-10", "end": "2026-03-10"},
    {"id": "CMP-005", "client": "TeleCasa", "sector": "Telco",
     "budget_eur": 80000, "impressions": 4_300_000, "clicks": 12_900,
     "conversions": 387, "revenue_eur": 72000, "channel": "Digital",
     "start": "2026-02-18", "end": "2026-03-18"},
]

# Synthetic average ROI benchmark per sector, used by some exercises
SECTOR_AVG_ROI = {
    "Automotive": 55.0, "Finance": 40.0, "FMCG": 50.0, "Travel": 90.0, "Telco": 20.0
}


def list_campaigns():
    """Short list (id, client, sector) of all campaigns."""
    return [{"id": c["id"], "client": c["client"], "sector": c["sector"]}
            for c in CAMPAIGNS]


def get_campaign(campaign_id: str):
    """Full dict of the campaign with the given id, or None."""
    for c in CAMPAIGNS:
        if c["id"].lower() == campaign_id.lower():
            return c
    return None


def roi(campaign_id: str):
    """ROI percent = (revenue - budget) / budget * 100, rounded to 1 decimal."""
    c = get_campaign(campaign_id)
    if not c:
        return None
    return round((c["revenue_eur"] - c["budget_eur"]) / c["budget_eur"] * 100, 1)


def cpm(campaign_id: str):
    """CPM in euro = budget / impressions * 1000. Cost per thousand impressions."""
    c = get_campaign(campaign_id)
    if not c:
        return None
    return round(c["budget_eur"] / c["impressions"] * 1000, 2)


if __name__ == "__main__":
    # Sanity check: print a ROI/CPM summary
    for c in CAMPAIGNS:
        print(f"{c['id']} {c['client']:<12} ROI {roi(c['id']):>6.1f}%  CPM {cpm(c['id']):>6.2f} EUR")
