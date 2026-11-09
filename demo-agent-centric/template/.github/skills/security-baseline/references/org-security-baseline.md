# Security baseline aziendale (esempio da personalizzare)

> Questo file rappresenta la conoscenza **specifica dell'organizzazione**.
> In un contesto reale va sostituito con la baseline del proprio team
> (CAF, Well-Architected, standard interni).

| ID | Area | Controllo |
|---|---|---|
| SEC-01 | Identità | Autenticazione utenti esclusivamente tramite Microsoft Entra ID; nessuna gestione locale delle password. |
| SEC-02 | Identità | I servizi si autenticano tra loro con **managed identity**; nessuna connection string con chiavi. |
| SEC-03 | Autorizzazione | Ruoli applicativi espliciti (es. `Employee`, `FacilityManager`) definiti nell'app registration. |
| SEC-04 | Segreti | Tutti i segreti residui (es. chiavi di terze parti) in **Azure Key Vault** con RBAC abilitato. |
| SEC-05 | Rete | Endpoint pubblici solo per il frontend e l'API; database e Key Vault non esposti pubblicamente dove il piano lo consente. |
| SEC-06 | Dati | Cifratura at-rest abilitata (default della piattaforma) e TLS 1.2+ in transito. |
| SEC-07 | Monitoraggio | Telemetria applicativa in **Application Insights** collegato a un Log Analytics workspace. |
| SEC-08 | GDPR | Data residency nell'Unione Europea (regioni `italynorth`, `westeurope` o `swedencentral`). |
| SEC-09 | GDPR | Dati personali minimizzati; politica di conservazione documentata (default 12 mesi per lo storico prenotazioni). |
| SEC-10 | AI | Se si usa Azure OpenAI: nessun dato personale nei prompt oltre allo stretto necessario; content filtering attivo. |
| SEC-11 | Naming | Nomi risorse `<tipo>-<workload>-<ambiente>-<regione>`, es. `ca-meetingrooms-dev-itn`. |
| SEC-12 | Tag | Tag obbligatori su ogni risorsa: `owner`, `costCenter`, `environment`, `dataClassification`. |
