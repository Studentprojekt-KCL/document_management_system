*# Kravspecifikation Studentprojekt 2026

| Author: Martin Vesterlund<br>Approved by: Simon Andersson | Date<br>2026-01-26 |
| --- | --- |

## Inledning
### Syfte

Syftet med detta dokument är att beskriva krav på ett dokumenthanteringssystem som möjliggör integrerad sökning, metadatahantering och informationsanalys över flera befintliga informationskällor. Kravspecifikationen ska fungera som ett styrande underlag för design, utveckling och utvärdering av systemet.

### Bakgrund

Organisationer lagrar idag dokument och information i ett flertal separata system, exempelvis SharePoint, Confluence, GitHub, GitLab och nätverksbaserade filsystem. Denna fragmentering medför svårigheter att hitta relevant information, säkerställa korrekt metadata samt upprätthålla enhetlig informationsklassning och regelefterlevnad.

Det föreslagna systemet ska fungera som ett sammanhållande lager som förbättrar tillgänglighet, överblick och kontroll utan att ersätta befintliga källsystem.

### Omfattning

Systemet ska tillhandahålla funktioner för:

- Integration med flera dokument- och informationskällor
- Gemensam sökning över integrerade källor
- Hantering och visning av metadata
- Stöd för informationsklassning och efterlevnad av säkerhetskrav
- Identifiering av likartat innehåll i flera dokument

Systemet ska inte lagra primära originaldokument om detta inte uttryckligen krävs av integrationen, utan utgå från respektive källsystems innehåll och behörighetsmodell.

### Definitioner och förkortningar
- **Källsystem**: Externa system där dokument lagras (t.ex. SharePoint, Confluence).
- **Metadata**: Strukturerad information om dokument, exempelvis författare, version och klassning.
- **Informationsklassning**: Indelning av information utifrån känslighet, t.ex. Public, Internal, Sensitive, Confidential.
- **Dokument**: Logiskt avgränsad och sammanhållen informationsbehållare  

### System Context Diagram
```
@startuml ContextDiagram
' System Context: Document Management & Integration System (DMIS)
!include <C4/C4_Context>
!include <C4/C4_Container>

Person(User, "Knowledge Worker\n(Browser)")
Person(InfoMgr, "Information Manager\n(Admin UI)")
Person(Compliance, "Compliance Officer")
Person(IT, "IT / System Integrator")

System_Ext(IdP, "Organization Identity Provider", "(SSO / IdP / OAuth2)")
System_Ext(SP, "SharePoint")
System_Ext(Conf, "Confluence")
System_Ext(Git, "GitHub / GitLab")
System_Ext(NFS, "Network File Shares", "(NFS/SMB)")
System_Ext(Ext, "External Tools", "(e.g., Notion, Google Drive)")
System_Ext(Ext_LLM, "External ML/LLM\nservices")

System_Boundary(DMIS, "DMIS (Document Management & Integration System)") {
    Container(UI, "Web/Admin UI")
    Container(APIG, "Backend")
    Container(ConnMgr, "Connector Manager")
    Container(Ingest, "Ingestion\nServices", "Separate for each target service")
    ContainerDb(Index, "Search\nIndex")
    ContainerDb(MetaDB, "Database", "Metadata")
    Container(ACL, "Authentication, Authorization & ACL Engine")
    Container(ML, "ML Services", "Classify, summarize etc")
}

' Relationships
User --> UI
InfoMgr --> UI
Compliance --> UI
IT --> ConnMgr

UI --> APIG
APIG --> ACL
APIG --> Index
APIG --> MetaDB
APIG --> ML

Ingest --> SP
Ingest --> Conf
Ingest --> Git
Ingest --> NFS
Ingest --> Ext
Ingest --> APIG

ConnMgr --> Ingest

ACL --> Ingest

ML <-- MetaDB
ML <-- Index
ML -Left-> Ext_LLM

IdP --> APIG
IdP --> ACL
@enduml
```

## Övergripande krav
### Generella krav

- KR-01 Systemet ska utformas så att det kan användas av både tekniska och icke-tekniska användare.

- KR-02 Systemet ska följa organisationens gällande informationssäkerhets- och dataskyddspolicyer.

- KR-03 Systemet ska respektera och tillämpa behörighetsstyrning i samtliga integrerade källsystem.

## Funktionella krav
### Integration med källsystem

- KR-10 Systemet ska kunna integrera med följande källsystem: GitHub, GitLab, Nätverksbaserade filsystem

- KR-11 Systemet bör kunna integrera med följande källsystem: SharePoint, Confluence

- KR-12 Integrationer ska baseras på officiella och stödda API:er eller åtkomstmekanismer i respektive källsystem.

- KR-13 Systemets integrationsarkitektur ska vara modulär för att möjliggöra framtida tillägg av nya källsystem.

### Sökfunktionalitet

- KR-20 Systemet ska tillhandahålla en gemensam sökfunktion över samtliga integrerade källsystem.

- KR-21 Sökresultat ska kunna filtreras baserat på tillgänglig metadata, såsom källsystem, dokumenttyp och informationsklassning.

- KR-22 Systemet ska endast presentera sökresultat som användaren har behörighet att ta del av i respektive källsystem.

### Metadatahantering

- KR-30 Systemet ska visa relevant metadata för dokument, inklusive men inte begränsat till: - Författare - Versionsinformation - Informationsklassning

- KR-31 Behöriga användare ska kunna uppdatera och korrigera metadata i de fall detta stöds av underliggande källsystem.

- KR-32 Alla dokument ska ges en unik identifierare som inte kommer ändras under dokumentets livscykel.

### Automatisk informationsklassning

- KR-40 Systemet ska analysera dokumentinnehåll och föreslå informationsklassning baserat på innehållets karaktär.

- KR-41 Föreslagen informationsklassning ska kunna granskas och justeras av behörig användare.

### Sammanfattning av information

- KR-50 Systemet ska kunna generera sammanfattningar av innehåll från ett eller flera dokument.

- KR-51 Sammanfattningar ska kunna baseras på dokument från olika källsystem.

- KR-52 Systemet ska kunna identifiera och markera när information upprepas i flera källssystem

- KR-53 Systemet bör kunna identifiera upprepad information som inte är bokstavlig

- KR-54 Systemet bör kunna identifiera dokument som säger emot varandra informationsmässigt

- KR-54 Sammanfattningar skall inte innehålla information från dokument användaren inte har behörighet till

### Åtkomstkontroll

- KR-60 Systemet ska vid varje åtkomstförsök verifiera användarens behörighet till informationen.

- KR-61 Behörighet bör kontrolleras mot källsystemets behörighetsstyrning

- KR-61 Systemet får inte exponera dokument, metadata eller innehåll som användaren saknar behörighet till.

## Icke-funktionella krav
### Säkerhet

- NFR-10 Systemet ska säkerställa konfidentialitet, riktighet och tillgänglighet för information i enlighet med organisationens säkerhetskrav.

- NFR-11 Systemet ska inte kringgå behörighetsmodeller i källsystemen.

- NFR-12 Systemet ska klara verifikation mot OWASP ASVS 5.0 level 1

- NFR-13 Systemet bör klara verifikation mot OWASP ASVS 5.0 level 2

### Prestanda

- NFR-20 Systemet ska kunna hantera stora mängder dokument och metadata utan oacceptabla svarstider.

- NFR-21 Indexering och synkronisering ska ske på ett sätt som minimerar belastning på källsystemen.

### Användbarhet

- NFR-30 Systemets användargränssnitt ska vara konsekvent, intuitivt och lätt att förstå.

### Skalbarhet

- NFR-40 Systemet ska kunna skalas för ökande antal dokument, användare och källsystem.

### Tillförlitlighet

- NFR-50 Systemet ska säkerställa korrekt och konsekvent synkronisering av metadata och sökindex mellan integrerade källsystem.

## Användarroller
### Identifierade användarroller

- **Kunskapsarbetare**: Söker och konsumerar information.
- **Administratörer**: Ansvarar för metadata, klassning och struktur.
- **Compliance-ansvariga**: Följer upp regelefterlevnad och informationsklassning.
- **IT- och systemintegratörer**: Ansvarar för drift och teknisk integration.

## Användningsfall (översikt)
### UC-01 Söka och hitta dokument över flera källsystem.
### UC-02 Granska och hantera metadata för dokument.
### UC-03 Ta emot och hantera förslag på informationsklassning.
### UC-04 Skapa sammanfattningar baserat på ett eller flera dokument.
### UC-05 Säkerställa korrekt åtkomst och efterlevnad av säkerhetskrav.