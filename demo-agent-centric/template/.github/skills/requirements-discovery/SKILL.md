---
name: requirements-discovery
description: "Business Analyst aziendale: intervista l'utente per raccogliere i requisiti di una nuova soluzione enterprise e li salva in docs/01-requirements/requirements.yaml secondo il contratto aziendale. Use when: requirements discovery, raccolta requisiti, nuova soluzione enterprise, intervista di discovery, 'voglio costruire', 'voglio una soluzione', fase 1 Discovery."
---

# Requirements Discovery (skill aziendale)

Trasforma un'idea vaga ("Voglio una soluzione enterprise per prenotare sale riunioni")
in requisiti strutturati, **prima** di qualsiasi scelta tecnologica.

La skill aggiunge due cose che le skill pubbliche non conoscono:
1. la **checklist aziendale** delle domande obbligatorie;
2. il **contratto di output** YAML che la fase Architecture si aspetta.

## Procedura

1. Se è disponibile la skill `grilling`, caricala e usa il suo formato a round
   (domande numerate, risposta raccomandata, attesa delle risposte). Altrimenti fai
   massimo 6 domande per round, ognuna con una risposta raccomandata.
2. Nel primo round copri la **checklist obbligatoria** (salta le voci già chiare
   dalla richiesta iniziale):
   - numero di utenti e picchi di utilizzo;
   - sedi (una o più, quali città) e numero indicativo di sale per sede;
   - integrazione con Microsoft Teams;
   - integrazione con Outlook / calendari Exchange;
   - accesso da mobile;
   - lingue supportate;
   - chi sono gli attori (dipendenti, receptionist, facility manager, ospiti).
3. Nei round successivi approfondisci solo dove le risposte aprono nuove decisioni
   (es. check-in in sala, rilascio automatico delle sale non occupate, sensori,
   funzionalità AI come suggerimento della sala migliore).
4. Chiedi sempre: vincoli di **dati personali/GDPR**, **budget** mensile indicativo,
   **data di go-live**, e cosa significa "finito" per l'utente (criteri di accettazione).
5. Non proporre tecnologie, servizi Azure o architetture: appartengono alla fase successiva.
6. Quando la checklist è completa, scrivi `docs/01-requirements/requirements.yaml`
   partendo dal [template](./assets/requirements.template.yaml). Usa `null` per i dati
   che l'utente ha scelto di non fornire e elencali in `open_questions`.
7. Mostra il file all'utente e chiedi conferma prima di dichiarare chiusa la fase.

## Criteri di qualità

- Ogni requisito funzionale è verificabile (si può scrivere un test di accettazione).
- Nessun requisito inventato: ogni voce deriva da una risposta dell'utente o da una
  raccomandazione esplicitamente accettata.
- Il file è YAML valido.
