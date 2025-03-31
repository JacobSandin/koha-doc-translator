# KOHA Manuell Översättare

En Python-applikation för att översätta KOHA-manualen från engelska till svenska med hjälp av DeepL API. Detta verktyg arbetar direkt med RST-källfilerna från den officiella KOHA-manualens repository och bevarar all formatering, direktiv och teknisk terminologi samtidigt som det skapar en parallell katalogstruktur för det översatta innehållet.

![KOHA Logo](https://koha.se/wp-content/uploads/2016/12/cropped-koha-logga-green-only-logo-768x461.jpg)

## Innehållsförteckning

- [Översikt](#översikt)
- [Funktioner](#funktioner)
- [Krav](#krav)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Användning](#användning)
- [Utdata](#utdata)
- [Tekniska detaljer](#tekniska-detaljer)
- [Felsökning](#felsökning)
- [Bidra](#bidra)
- [Licens](#licens)

## Översikt

KOHA Manuell Översättare är utformad för att underlätta översättningen av KOHA Integrated Library System-dokumentationen från engelska till svenska. Den använder DeepLs professionella översättnings-API för att producera högkvalitativa översättningar samtidigt som den bevarar dokumentationens tekniska integritet.

## Funktioner

- Använder DeepLs professionella översättnings-API för högkvalitativa översättningar
- Arbetar direkt med RST (reStructuredText) källfiler från den officiella KOHA-manualen
- Bevarar all RST-formatering och direktiv under översättningen
- Upprätthåller tekniska termer och KOHA-specifik terminologi genom en anpassad ordlista
- Skapar en parallell katalogstruktur för översatta filer
- Översätter allt manualinnehåll samtidigt som dokumentstrukturen bevaras
- Stöder inkrementell översättning (översätter endast nytt eller modifierat innehåll)
- Integrerar med det officiella KOHA-manualens lokaliseringsarbetsflöde

## Krav

- Python 3.7 eller högre
- DeepL API-nyckel (Pro-konto rekommenderas för stora volymer)
- Git
- Internetanslutning för API-åtkomst

## Installation

1. Klona detta repository:
   ```bash
   git clone https://github.com/JacobSandin/koha-doc-translator.git
   cd koha-doc-translator
   ```

2. Installera beroenden:
   ```bash
   pip install -r requirements.txt
   ```

3. Konfigurera de nödvändiga repositorierna:
   ```bash
   python setup_repos.py
   ```
   Detta kommer att klona de nödvändiga KOHA-repositorierna till `repos`-katalogen:
   - koha-manual (käll-RST-filer)
   - koha-manual-l10n (lokaliseringsfiler)

4. Kopiera exempel-miljöfilen och lägg till din DeepL API-nyckel:
   ```bash
   cp .env_example .env
   # Redigera .env-filen för att lägga till din DeepL API-nyckel
   ```

## Konfiguration

### Miljövariabler

Skapa en `.env`-fil i rotkatalogen med följande variabler:

```
DEEPL_API_KEY=din_api_nyckel_här
```

### Anpassad Terminologi

Översättaren använder en ordlista för att upprätthålla konsekventa översättningar av tekniska termer. Du kan redigera `phrases.csv`-filen för att lägga till eller ändra termer:

```csv
EN,SV
"KOHA","KOHA"
"circulation","cirkulation"
```

## Användning

### Grundläggande användning

För att köra översättaren med standardinställningar:

```bash
python translator.py --translate --all
```

### Kommandoradsalternativ

```bash
python translator.py [ALTERNATIV]
```

Alternativ:
- `--status`: Visa översättningsstatus
- `--translate`: Kör översättningsprocessen
- `--lang KOD`: Språkkod (standard: sv)
- `--file FILNAMN`: Bearbeta specifik fil (utan .rst-tillägg)
- `--all`: Bearbeta alla filer (krävs för massöversättning)
- `--phrases SÖKVÄG`: Sökväg till phrases.csv-fil (standard: phrases.csv)
- `--translate-all`: Översätt alla strängar, även om de redan finns i PO-filen

### Exempel

Kontrollera översättningsstatus:
```bash
python translator.py --status
```

Översätt en specifik fil:
```bash
python translator.py --translate --file 01_introduction
```

Översätt alla filer, inklusive redan översatta strängar:
```bash
python translator.py --translate --all --translate-all
```

## Utdata

De översatta filerna kommer att skapas i KOHA-manualens lokaliseringsrepositoriestruktur under `repos/koha-manual-l10n`. Översättningsprocessen genererar och uppdaterar PO-filer som kan användas med det officiella KOHA-manualens byggsystem.

## Tekniska detaljer

### Projektstruktur

```
koha-doc-translator/
├── .env                  # Miljövariabler (inte i repo)
├── .env_example          # Exempel på miljöfil
├── .gitignore            # Git-ignorera fil
├── README.md             # Engelsk dokumentation
├── README-SV.md          # Svensk dokumentation
├── phrases.csv           # Ordlistetermer
├── requirements.txt      # Python-beroenden
├── setup_repos.py        # Skript för repositorieinställning
├── translator.py         # Huvudöversättningsskript
└── repos/                # Innehåller klonade repositorier
    ├── koha-manual/      # Käll-RST-filer
    └── koha-manual-l10n/ # Lokaliseringsfiler
```

### Översättningsprocess

1. Skriptet skannar käll-RST-filerna i KOHA-manualens repository
2. För varje fil extraherar det översättningsbart innehåll samtidigt som formateringen bevaras
3. Det kontrollerar om översättningar redan finns i PO-filerna
4. Nytt eller modifierat innehåll skickas till DeepL för översättning
5. Ordlistan säkerställer konsekvent terminologi
6. Översatt innehåll skrivs tillbaka till PO-filer i lokaliseringsrepositoriet

## Felsökning

### Vanliga problem

- **API-nyckelsproblem**: Säkerställ att din DeepL API-nyckel är korrekt inställd i `.env`-filen
- **Repositorieåtkomst**: Om du inte kan komma åt repositorierna, kontrollera din nätverksanslutning och GitLab/GitHub-åtkomst
- **Översättningsfel**: För specifika översättningsfel, kontrollera konsolens utdata för detaljer

### Loggar

Översättaren skriver detaljerade loggar till konsolen under drift. För permanenta loggar, omdirigera utdata till en fil:

```bash
python translator.py --translate --all > translation_log.txt 2>&1
```

## Bidra

Bidrag är välkomna! För att bidra till detta projekt:

1. Forka repositoriet
2. Skapa en funktionsgren (`git checkout -b funktion/fantastisk-funktion`)
3. Commit dina ändringar (`git commit -m 'Lägg till någon fantastisk funktion'`)
4. Push till grenen (`git push origin funktion/fantastisk-funktion`)
5. Öppna en Pull Request

Se till att din kod följer projektets stilriktlinjer och inkluderar lämpliga tester.

## Licens

Detta projekt är licensierat under MIT-licensen - se LICENSE-filen för detaljer.
