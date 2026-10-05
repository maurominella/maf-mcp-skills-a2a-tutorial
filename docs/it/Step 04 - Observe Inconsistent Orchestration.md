<a id="passaggio-4"></a>

# Passaggio 4 — Osservare un'orchestrazione incoerente

Le domande atomiche vengono in genere gestite bene perché gli schemi dei tool
rendono evidente l'operazione richiesta:

```text
Qual è il ROI di CMP-004?
```

Il percorso previsto è semplice:

```text
campaign_metrics("CMP-004")
→ compute_roi(revenue_eur, budget_eur)
→ risposta
```

Usa ora una domanda più ampia:

```text
Esamina l'intero portafoglio di campagne e consiglia quale campagna dovrebbe
ricevere un budget aggiuntivo nel prossimo trimestre.
```

L'agente dispone delle funzionalità necessarie per rispondere, ma non gli è
stata fornita una procedura di revisione standard. Tra esecuzioni ripetute o
modelli diversi, potrebbe:

- classificare le campagne soltanto in base al ROI;
- considerare i ricavi ma ignorare le conversioni;
- esaminare soltanto un sottoinsieme delle campagne;
- calcolare autonomamente alcuni valori di ROI anziché usare `compute_roi`;
- omettere i limiti relativi alla qualità dei dati;
- produrre una tabella in un'esecuzione e testo discorsivo in un'altra;
- consigliare una campagna senza spiegare il compromesso tra redditività e
  scala.

Questo non è un problema di MCP. MCP espone correttamente le funzionalità.
L'elemento mancante è una procedura di dominio riutilizzabile.

Esegui più volte lo stesso prompt ed esamina `response.messages`:

```python
prompt = (
    "Review the entire campaign portfolio and recommend which campaign "
    "should receive additional budget next quarter."
)

async with agent:
    for run_number in range(1, 4):
        response = await agent.run(prompt)
        print(f"\n--- Run {run_number} ---")
        print(response.text)

        for message in response.messages:
            print(message)
```

Non affermare che il comportamento debba necessariamente essere incoerente a
ogni esecuzione. Misura invece se la risposta soddisfa con regolarità criteri
espliciti:

| Criterio | Risultato previsto senza una skill? |
|---|---|
| Viene esaminata ogni campagna | Non garantito |
| Ogni ROI usa `compute_roi` | Non garantito |
| Vengono considerate sia la redditività sia la scala | Non garantito |
| Vengono dichiarati i limiti dei dati | Non garantito |
| Viene usata la stessa struttura di output | Non garantito |

---

