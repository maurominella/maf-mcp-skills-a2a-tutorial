<a id="confronto"></a>

# Confrontare le versioni A2A e basata sulle skill

Usa lo stesso input per entrambe le versioni:

```text
Crea un preventivo per una campagna Travel con 9.200.000 impression.
```

I volumi previsti per gli scenari sono:

| Scenario | Impression |
|---|---:|
| Ridotto | 7.360.000 |
| Richiesto | 9.200.000 |
| Esteso | 11.040.000 |

Per il settore Travel con un CPM di 16 EUR, il tool deterministico dovrebbe
restituire:

| Scenario | Impression | CPM | Totale |
|---|---:|---:|---:|
| Ridotto | 7.360.000 | 16 EUR | 117.760 EUR |
| Richiesto | 9.200.000 | 16 EUR | 147.200 EUR |
| Esteso | 11.040.000 | 16 EUR | 176.640 EUR |

Strumenta entrambe le versioni e raccogli:

- latenza end-to-end;
- numero di chiamate LLM dell'agente principale;
- numero di chiamate LLM dell'agente di pricing;
- numero di richieste A2A;
- numero di chiamate ai tool MCP;
- token di input e output;
- rispetto di tutti i requisiti dei criteri.

Un confronto indicativo è:

| Dimensione | Agente A2A di pricing | Skill + tool MCP diretto |
|---|---:|---:|
| LLM principale | Necessario | Necessario |
| Secondo LLM | Necessario | Non necessario |
| Richiesta HTTP A2A | Necessaria | Non necessaria |
| Chiamate MCP | Tre | Tre |
| Posizione dei criteri | Istruzioni dell'agente di pricing | `SKILL.md` |
| Servizio di pricing separato | Necessario | Non necessario |
| Caricamento progressivo della skill | No | Sì |

Il numero esatto di chiamate LLM dipende dal modello e dal comportamento del
runtime. Un tipico flusso basato sulle skill aggiunge un turno LLM per
`load_skill`, ma evita l'intero ciclo di ragionamento dell'agente remoto di
pricing.

Il miglioramento di latenza previsto deriva dall'eliminazione di:

1. chiamate di inferenza LLM dell'agente remoto;
2. round trip A2A HTTP/JSON-RPC;
3. serializzazione e deserializzazione A2A;
4. ciclo di vita del servizio aggiuntivo.

L'inferenza LLM risparmiata nel secondo agente è normalmente più significativa
delle sole operazioni HTTP locali e di serializzazione JSON.

---

<a id="conclusioni"></a>

# Cosa dimostra questo tutorial

## Un tool è sufficiente per un'operazione atomica

`campaign_quote(sector, impressions)` è autoesplicativo e deterministico. Il
modello può spesso richiamarlo correttamente senza una skill.

## Una skill è utile quando aggiunge criteri

La skill di preventivazione è utile perché aggiunge un comportamento che non è
presente nello schema del tool:

- tre scenari;
- la regola ±20%;
- la gestione degli input necessari;
- gli avvisi sulla tariffa predefinita;
- i requisiti di output;
- le restrizioni sulla modifica dei prezzi autorevoli.

Se la skill dicesse soltanto "estrai due parametri e chiama `campaign_quote`",
aggiungerebbe poco valore e potrebbe introdurre soltanto un ulteriore turno
LLM.

## MCP e skill risolvono problemi diversi

MCP espone le operazioni. Le skill definiscono come orchestrare tali operazioni.

```text
Tool MCP:
Che cosa può fare il sistema?

Skill:
Quando e secondo quale procedura deve farlo?
```

## A2A rimane appropriato per una vera autonomia

Non sostituire un agente A2A con una skill quando l'agente remoto ha una
responsabilità indipendente significativa, ad esempio:

- negoziazione con stato;
- proprietà o confini di sicurezza separati;
- approvazioni indipendenti;
- attività di lunga durata;
- avanzamento asincrono;
- accesso a sistemi privati non disponibili all'agente principale;
- coordinamento autonomo con altri agenti.

In questi casi, i costi aggiuntivi di rete e LLM sono il prezzo di un vero
confine architetturale.

## Regola decisionale finale

Usa:

- un **tool** per una funzionalità atomica;
- **MCP** quando tale funzionalità deve essere condivisa in remoto;
- una **skill** per flussi di lavoro e criteri riutilizzabili;
- **A2A** per delegare a un agente realmente autonomo.
