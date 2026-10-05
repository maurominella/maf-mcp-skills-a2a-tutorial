# Da un agente MAF a una soluzione completa basata sulle skill

Gli AI skill sono stati [annunciati da Antrhopic](https://claude.com/blog/skills) a ottobre 2025 e si sono diffusi molto rapidamente. Ora il punto chiave -e per nulla scontato- è capire dove ha senso posizionarli, perché le funzionalità che si portano dietro in realtà esistevano anche prima, senza gli skill. Quindi si potrebbero considerare un'alternativa al system prompt, o ai tool, e in certe casi addirittura ha senso valutarli come un modo per ottimizzare sistemi multiagentici costruiti intorno ad A2A.
Quindi, per comprendere come gestire queste possibili sovrapposizioni, e imparare però anche come utilizzarli nel concreto, ho predisposto questo tutorial, rivolto a sviluppatori e solution architect, che parte da un agente minimale basato su Microsoft Agent Framework (MAF) e arriva a una soluzione completa basata sugli skill, passando attraverso Function Calling, Tools, server MCP e A2A.

Lo scenario segue un analista di AdvertSphere Broadcasting, un'azienda fittizia che vende spazi pubblicitari per un network televisivo.

Attraverso sette passaggi incrementali, che troviamo descritti e implementati in questo repo pubblico su GitHub, costruiremo una soluzione completa, partendo da scratch, e che fornirà all'analista di questa azienda
- l'accesso a dati autorevoli sulle campagne, 
- la revisione uniforme del portafoglio, 
- e un servizio di creazione preventivi.

Nell'ultima parte del tutorial faremo prima l'implementazione seguendo un approccio multiagentico basato su [A2A, annunciato da Google sei mesi prima degli skill](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/); questo approccio resta validissimo anche oggi, ma grazie agli skill abbiamo ora l'opportunità di valutare in certi casi una possibile ottimizzazione, di fatto "trasportando" le capacità dell'agente A2A all'interno di uno skill, e sfruttando come LLM quello dell'agente orchestratore. 

Relativamente al tutorial, potete procedere nell'ordine dei punti se volete arrivare ad implementare la soluzione E2E. Oppure se lo usate come un riferimento architetturale, utilizzate il sommario per raggiungere direttamente il pattern o il confronto che vi interessa.

Quindi adesso partiamo direttamente con l'implementazione del primo punto, ovvero la creazione di un agente minimale con Agent Framework.

## Sommario

- [Prerequisiti](#prerequisiti)
- [Passaggio 1 — Creare un agente MAF minimale](<./Step 01 - Create a Minimal MAF Agent.md>)
- [Passaggio 2 — Aggiungere tool funzione locali](<./Step 02 - Add Local Function Tools.md>)
- [Passaggio 3 — Spostare i tool in un server MCP](<./Step 03 - Move Tools to an MCP Server.md>)
- [Passaggio 4 — Osservare un'orchestrazione incoerente](<./Step 04 - Observe Inconsistent Orchestration.md>)
- [Passaggio 5 — Aggiungere la skill `campaign-performance-review`](<./Step 05 - Add the Campaign Performance Review Skill.md>)
- [Passaggio 6 — Aggiungere un agente A2A di pricing basato su LLM](<./Step 06 - Add an LLM-Based A2A Pricing Agent.md>)
- [Passaggio 7 — Sostituire l'agente A2A di pricing con una skill](<./Step 07 - Replace the A2A Pricing Agent with a Skill.md>)
- [Confrontare le versioni A2A e basata sulle skill](<./Comparison and Conclusions.md#confronto>)
- [Conclusioni](<./Comparison and Conclusions.md#conclusioni>)

<a id="prerequisiti"></a>

## Prerequisiti

Questo tutorial presuppone:

- Python 3.13 o versione successiva;
- `agent-framework==1.19.0`;
- `fastmcp==3.4.7`;
- `a2a-sdk==1.1.5`;
- `uvicorn==0.54.0`;
- una distribuzione Azure OpenAI configurata tramite le variabili di ambiente
  esistenti;
- una sessione Azure CLI autenticata.

Gli esempi utilizzano le variabili seguenti:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
```

La struttura di progetto suggerita è:

```text
labs/solutions/
├── agent_campaign_mcp.py
├── campaign_data.py
├── campaign_agent.py
├── pricing_a2a_agent.py
└── skills/
    ├── campaign-performance-review/
    │   └── SKILL.md
    └── campaign-quotation-policy/
        └── SKILL.md
```

I nomi esatti dei file non sono importanti. Ciò che conta è il modo in cui le
responsabilità si spostano nel corso dei sette passaggi.

---

