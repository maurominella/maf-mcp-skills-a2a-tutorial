<a id="passaggio-2"></a>

# Passaggio 2 — Aggiungere tool funzione locali

Aggiungiamo tre funzioni deterministiche allo stesso file sorgente:

- `all_campaigns`;
- `campaign_metrics`;
- `compute_roi`.

In questo caso, i due metodi `all_campaigns` e `campaign_metrics` sono funzioni implementate nel file `asb_campaign.py` a puro scopo dimostrativo per consentire l'esecuzione dell'esercizio. In una situazione reale, queste funzioni dovrebbero attingere al dataset reale delle campagne.<br/>
Questo il codice da aggiungere all'inizio del modulo, subito dopo l'istruzione `load_dotenv()`:

```python
from typing import Annotated
from pydantic import Field
from asb_campaign import get_campaign, list_campaigns


def all_campaigns() -> list:
    """List the id, client, and sector of every campaign."""
    return list_campaigns()

def campaign_metrics(
    campaign_id: Annotated[
        str,
        Field(description="Campaign identifier, for example CMP-004"),
    ],
) -> dict:
    """Return the authoritative metrics for one campaign."""
    campaign = get_campaign(campaign_id)
    if campaign is None:
        return {"error": f"Campaign {campaign_id} was not found."}
    return campaign

def compute_roi(
    revenue_eur: Annotated[
        float,
        Field(description="Campaign revenue in EUR"),
    ],
    budget_eur: Annotated[
        float,
        Field(description="Campaign budget in EUR"),
    ],
) -> dict:
    """Calculate ROI as a percentage from revenue and budget."""
    if budget_eur <= 0:
        return {"error": "budget_eur must be greater than zero"}

    roi_pct = (revenue_eur - budget_eur) / budget_eur * 100
    return {"roi_pct": round(roi_pct, 1)}
```

L'Agent Framework può registrare i nomi di queste funzioni durante la creazione dell'agente, associandole attraverso un array al parametro `tools` della classe `agent`:

```python
maf_agent = Agent(
    client=openai_client,
    name="CampaignAnalyst",
    description="Analyzes advertising campaign performance.",
    instructions=(
        "You are an analyst at AdvertSphere Broadcasting. "
        "Always answer in English, concisely and professionally."
    ),
    tools=[all_campaigns, campaign_metrics, compute_roi],
)
```

L'LLM riceve ora gli schemi generati dalle funzioni, dalle annotazioni e dalle
docstring. Può richiedere una chiamata a un tool, mentre MAF esegue
effettivamente la funzione.

```text
Utente
  ↓
L'LLM richiede campaign_metrics
  ↓
MAF esegue la funzione Python
  ↓
MAF restituisce il risultato del tool all'LLM
  ↓
L'LLM produce la risposta
```

Questa progettazione è appropriata finché le funzionalità appartengono alla
stessa applicazione e non devono essere condivise.

---

