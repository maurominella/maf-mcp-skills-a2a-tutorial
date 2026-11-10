---
name: requirements-discovery
description: "Business Analyst aziendale: intervista l'utente per trasformare un'idea di soluzione, in qualsiasi dominio, in requisiti strutturati salvati in docs/01-requirements/requirements.yaml secondo il contratto aziendale. Use when: requirements discovery, raccolta requisiti, nuovo progetto, nuova soluzione enterprise, intervista di discovery, 'voglio costruire', 'voglio una soluzione', fase 1 Discovery."
---

# Requirements Discovery (skill aziendale)

Trasforma un'idea espressa in una frase in requisiti strutturati, **prima** di qualsiasi
scelta tecnologica. Vale per qualsiasi dominio applicativo.

Questa skill aggiunge alle tecniche di intervista generiche due cose che sono
dell'organizzazione:
1. le **aree di copertura obbligatorie**: nessuna discovery è completa se ne manca una;
2. il **contratto di output** YAML che la fase Architecture si aspetta.

Le **domande concrete** non sono scritte qui: le devi ricavare tu dal dominio descritto
dall'utente. Una checklist fissa produrrebbe domande generiche; il tuo compito è capire
il dominio e chiedere ciò che un analista esperto di quel dominio chiederebbe.

## Procedura

1. **Analizza il dominio.** Dalla frase dell'utente deduci: che tipo di soluzione è,
   chi la usa, quali processi di business tocca e con quali **sistemi esistenti** di un'azienda
   tipica dovrà probabilmente dialogare (posta, calendari, collaborazione, ERP, CRM,
   identità, dispositivi…). Esplicita queste ipotesi all'utente: le confermerà o correggerà.
2. **Intervista a round.** Se è disponibile la skill `grilling`, caricala e usa il suo
   formato (domande numerate, una risposta raccomandata per ciascuna, attesa delle
   risposte prima del round successivo). Altrimenti fai al massimo 6 domande per round,
   ognuna con una risposta raccomandata.
3. **Copri tutte le aree obbligatorie**, formulando per ognuna domande specifiche del
   dominio (salta quelle già chiare dalla richiesta iniziale):

   | Area | Cosa deve emergere |
   |---|---|
   | Attori | chi usa la soluzione, con quali ruoli e permessi |
   | Volumi | numero di utenti, picchi, quantità degli oggetti di business gestiti |
   | Distribuzione | sedi, paesi, fusi orari |
   | Integrazioni | sistemi esistenti con cui dialogare e in quale direzione |
   | Canali | web, mobile, chat/collaborazione, API per terzi |
   | Lingue | lingue dell'interfaccia e dei contenuti |
   | Funzionalità | processi chiave, end-to-end, dal punto di vista dell'utente |
   | Funzionalità AI | dove l'AI aggiunge valore reale (solo se l'utente lo ritiene utile) |
   | Dati e compliance | dati personali trattati, GDPR, conservazione, residenza dei dati |
   | Qualità del servizio | disponibilità, prestazioni, continuità operativa |
   | Vincoli | budget mensile indicativo, data di go-live, standard da rispettare |
   | Criteri di accettazione | cosa significa "finito" per l'utente |

4. **Approfondisci** solo dove le risposte aprono nuove decisioni. Ricalcola i round
   finché nessuna area resta scoperta.
5. **Non proporre tecnologie**, servizi Azure o architetture: appartengono alla fase successiva.
6. **Scrivi** `docs/01-requirements/requirements.yaml` partendo dal
   [template](./assets/requirements.template.yaml). Usa `null` per i dati che l'utente ha
   scelto di non fornire ed elencali in `open_questions`. Metti in `domain_specific` le
   informazioni importanti del dominio che non rientrano nelle altre chiavi.
7. **Mostra** il file all'utente e chiedi conferma prima di dichiarare chiusa la fase.

## Criteri di qualità

- Tutte le aree obbligatorie sono coperte o motivate come non applicabili.
- Ogni requisito funzionale è verificabile (si può scrivere un test di accettazione).
- Nessun requisito inventato: ogni voce deriva da una risposta dell'utente o da una
  raccomandazione esplicitamente accettata.
- Il file è YAML valido e rispetta le chiavi del template.
