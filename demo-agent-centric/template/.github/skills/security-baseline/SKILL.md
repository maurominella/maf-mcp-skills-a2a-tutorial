---
name: security-baseline
description: "Security Architect aziendale: verifica un'architettura Azure contro la security baseline dell'organizzazione (identità Entra ID, segreti in Key Vault, monitoraggio Application Insights, GDPR, naming e tag) e produce docs/03-security/security-review.md. Use when: security review, security assessment, verifica sicurezza architettura, baseline di sicurezza, GDPR check, fase 3 Security."
---

# Security Baseline (skill aziendale)

Applica le regole di sicurezza **specifiche dell'organizzazione**, che nessuna skill
pubblica conosce, all'architettura proposta.

## Input

- `docs/01-requirements/requirements.yaml`
- `docs/02-architecture/architecture.md` e `docs/adr/`

## Procedura

1. Leggi la [baseline aziendale](./references/org-security-baseline.md).
2. Per ogni controllo della baseline valuta l'architettura: **Conforme**,
   **Non conforme** (con correzione proposta) o **Non applicabile** (con motivo).
3. Per l'autenticazione, se è disponibile la skill Microsoft `entra-app-registration`,
   usala per definire app registration, scope e ruoli applicativi necessari.
4. Collega i dati personali elencati in `compliance.personal_data` dei requisiti
   alle misure GDPR (minimizzazione, conservazione, diritto alla cancellazione).
5. Scrivi `docs/03-security/security-review.md` con questa struttura:
   - riepilogo (numero di controlli conformi / non conformi);
   - tabella dei controlli `ID | Controllo | Esito | Evidenza / Correzione`;
   - sezione finale con le chiavi minime attese dal cap. 6.3:
     ```yaml
     authentication: Entra ID
     secrets: Key Vault
     monitoring: Application Insights
     compliance: GDPR
     ```
   - rischi residui che richiedono l'accettazione esplicita dell'utente.
6. Se una correzione modifica l'architettura, aggiorna `architecture.md` e aggiungi un ADR.
7. Non dichiarare la fase chiusa se resta un controllo **Non conforme** senza
   correzione o senza accettazione esplicita del rischio da parte dell'utente.
