# KOHA Manuell Översättare

En Python-applikation för att översätta KOHA-manualen från engelska till svenska med hjälp av DeepL API. Detta verktyg arbetar direkt med RST-källfilerna från den officiella KOHA-manualens repository och bevarar all formatering, direktiv och teknisk terminologi samtidigt som det skapar en parallell katalogstruktur för det översatta innehållet.

<img src="https://koha.se/wp-content/uploads/2016/12/cropped-koha-logga-green-only-logo-768x461.jpg" alt="KOHA Logo" width="300">

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
- Implementerar ett översättningscachesystem för att spara DeepL API-krediter

## Krav

- Python 3.7 eller högre
- DeepL API-nyckel (Pro-konto rekommenderas för stora volymer)
- Git
- Internetanslutning för API-åtkomst
- SQLite (ingår i Pythons standardbibliotek)

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

**Översättningsskript:**
```bash
python translator.py [ALTERNATIV]
```

Översättningsalternativ:
- `--translate`: Kör översättningsprocessen
- `--lang KOD`: Språkkod (standard: sv)
- `--file FILNAMN`: Bearbeta specifik fil (utan .rst-tillägg)
- `--all`: Bearbeta alla filer (krävs för massöversättning)
- `--phrases SÖKVÄG`: Sökväg till phrases.csv-fil (standard: phrases.csv)
- `--ref-phrases SÖKVÄG`: Sökväg till referensfras-CSV-fil (standard: ref_phrases.csv)
- `--translate-all`: Översätt alla strängar, även om de redan finns i PO-filen
- `--debug`: Aktivera felsökningsläge med fullständig textutdata
- `--log-file SÖKVÄG`: Ange anpassad loggfilssökväg

**Statusskript:**
```bash
python status.py [ALTERNATIV]
```

Statusalternativ:
- `--lang KOD`: Språkkod (standard: sv)
- `--file FILNAMN`: Kontrollera specifik fil (utan .rst-tillägg)
- `--source-dir SÖKVÄG`: Sökväg till RST-källfiler
- `--po-dir SÖKVÄG`: Sökväg till PO-filskatalog

### Exempel

Kontrollera översättningsstatus:
```bash
python status.py
```

Kontrollera status för en specifik fil:
```bash
python status.py --file enhancedcontentpreferences
```

Översätt en specifik fil:
```bash
python translator.py --translate --file enhancedcontentpreferences
```

Översätt alla filer, inklusive redan översatta strängar:
```bash
python translator.py --translate --all --translate-all
```

Bygg den svenska manualen (från koha-manual-katalogen):
```bash
make -e SPHINXOPTS="-q -D language='sv' -d build/doctrees" BUILDDIR="build/sv" singlehtml
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
├── TRANSLATION_PROCESS.md # Dokumentation för icke-tekniska användare
├── phrases.csv           # Ordlistetermer för översättning
├── auto_phrases.csv      # Automatiskt genererade fraser för översättning
├── requirements.txt      # Python-beroenden
├── setup_repos.py        # Skript för repositorieinställning
├── translator.py         # Huvudöversättningsskript
├── status.py             # Skript för rapportering av översättningsstatus
├── build_sv_manual.py    # Skript för att bygga den svenska manualen
├── find_auto_phrases.py  # Skript för att hitta och extrahera fraser för automatisk översättning
├── clean_translation_cache.py # Verktyg för att rensa översättningscachen
├── log/                  # Katalog för loggfiler
├── cache/                # Katalog för översättningscache
│   └── translation_cache.db # SQLite-databas för cachade översättningar
└── repos/                # Innehåller klonade repositorier
    └── koha-manual/      # Käll-RST-filer
        ├── source/       # Ursprungliga RST-filer
        └── locales/      # Lokaliseringsfiler (koha-manual-l10n)
```

### Översättningsprocess

1. Skriptet skannar käll-RST-filerna i KOHA-manualens repository
2. För varje fil extraherar det översättningsbart innehåll samtidigt som formateringen bevaras
3. Det kontrollerar om översättningar redan finns i PO-filerna
4. Nytt eller modifierat innehåll skickas till DeepL för översättning
5. Ordlistan säkerställer konsekvent terminologi
6. Översatt innehåll skrivs tillbaka till PO-filer i lokaliseringsrepositoriet
7. Statusskriptet kan användas för att kontrollera översättningsframsteg och identifiera saknade översättningar

Översättningsprocessen hanterar specialfall som escapade tecken i RST-filer (t.ex. `\_\_\_`) och säkerställer att allt innehåll extraheras och översätts korrekt.

## Översättningscachesystem

Översättaren implementerar ett cachesystem för att undvika att översätta innehåll som redan har översatts, vilket hjälper till att spara DeepL API-krediter och påskyndar översättningsprocessen:

- **Automatisk cachning**: Alla översättningar cachas automatiskt i en SQLite-databas (`cache/translation_cache.db`)
- **Cache-sökning**: Innan text skickas till DeepL kontrollerar systemet om exakt samma källtext har översatts tidigare
- **Cache-träffar**: Systemet spårar och rapporterar hur många API-anrop som sparades genom att använda cachade översättningar
- **Cache-rensning**: Verktyget `clean_translation_cache.py` gör det möjligt att ta bort specifika översättningar från cachen:
  ```bash
  # Ta bort översättningar som innehåller platshållarmönster
  python clean_translation_cache.py --pattern '%\w+%'
  
  # Förhandsgranska vad som skulle tas bort utan att faktiskt ta bort
  python clean_translation_cache.py --pattern 'specifik text' --dry-run --verbose
  ```
- **Cache-lagring**: Cachen lagras i en lokal SQLite-databas och är exkluderad från Git-versionskontroll

Detta cachesystem minskar avsevärt antalet API-anrop till DeepL, särskilt när man kör om översättningar eller uppdaterar manualen med mindre ändringar.

## Ordliste- och Referensfiler

### phrases.csv

Filen `phrases.csv` innehåller en ordlista med Koha-specifika termer och deras översättningar. Detta säkerställer konsekvent terminologi genom hela manualen. Filen har ett enkelt format:

```
Engelsk term,Svensk översättning
```

Till exempel:
```
patron,låntagare
checkout,utlån
hold,reservation
```

Översättaren använder denna fil som en ordlista med DeepL API för att säkerställa konsekventa översättningar av tekniska termer oavsett sammanhang.

### ref_phrases.csv

Filen `ref_phrases.csv` hanterar specifikt referenser inom RST-dokumentationen. I RST-filer ser referenser ut som `:ref:`etikett`` och används för interna länkar. Denna fil hjälper till att översätta dessa referenser korrekt.

Du kanske inte vill överskriva `ref_phrases.csv` när:
1. Du har noggrant kurerat referensöversättningar som bör bevaras
2. Du arbetar med en specifik version av manualen där referens-ID:n är stabila
3. Du vill behålla konsekvens i hur referenser översätts över uppdateringar

Verktygsskriptet `extract_ref_display_text_from_rst.py` kan hjälpa till att generera denna fil genom att extrahera referensetiketter och deras visningstexts från RST-filer.

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
