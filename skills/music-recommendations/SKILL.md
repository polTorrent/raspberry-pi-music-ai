# Skill: Music Recommendations

## Description
Genera recomanacions musicals setmanals personalitzades combinant l'historial d'escolta de Navidrome amb cerques web de novetats. Categoritza propostes en: joies oblidades, àlbums no escoltats, novetats discogràfiques, artistes similars i joies desconegudes.

## When to Use
- L'usuari demana recomanacions musicals
- L'usuari vol saber què escoltar
- Recurrent: cada dilluns (automàtic via cron)
- L'usuari vol descobrir música nova basada en els seus gustos

## Prerequisites
- Navidrome funcionant (port 4533) amb base de dades SQLite
- Access a internet per cerques web de novetats
- Skill `soulseek-music` per descarregar recomanacions (opcional però recomanat)

## Architecture

```
analyze_listening.py  →  Analitza BD Navidrome (scrobbles, annotation, library)
        ↓
generate_recommendations.py  →  Combina anàlisi + perfil musical → JSON estructurat
        ↓
Agent (web_search)  →  Cerca novetats dels artistes top + gèneres
        ↓
Agent  →  Filtra els que ja estan a la biblioteca → Presenta recomanacions
```

## Scripts

### `analyze_listening.py` — Anàlisi d'Historial
Consulta la BD de Navidrome i extreu:
- Top artistes i àlbums (per reproduccions)
- Reproduccions recents (últimes 30)
- Joies oblidades (escoltats fa més de 90 dies, amb play_count alt)
- Distribució de gèneres
- Àlbums mai escoltats (a la biblioteca però 0 plays)
- Artistes similars (de Last.fm, creuat amb biblioteca)
- Àlbums afegits recentment
- Activitat mensual (últims 12 mesos)
- Items starred/rated

```bash
python3 scripts/analyze_listening.py
```

Output: `analysis_output.json` + human-readable summary to stdout.

### `generate_recommendations.py` — Generador de Recomanacions
Combina l'anàlisi de Navidrome amb el perfil musical de l'usuari per generar recomanacions categoritzades.

```bash
python3 scripts/generate_recommendations.py
```

Output: JSON with categories:
- `forgotten_gems` — Àlbums de la biblioteca que fa temps que no escoltes
- `never_played` — Àlbums a la biblioteca que encara no has escoltat
- `similar_artists` — Artistes similars als teus favorits que no tens a la biblioteca
- `recently_added` — Afegits recentment
- `search_queries` — Queries per cercar novetats web (agent ho fa)
- `listening_stats` — Estadístiques d'escolta

### `print_recs.py` — Resum llegible

```bash
python3 scripts/print_recs.py
```

Imprimeix les recomanacions en format llegible per l'usuari.

## Workflow de la Recomanació Setmanal

1. **Executar `generate_recommendations.py`** → obtenir base de dades local
2. **Cercar novetats web** amb `web_search`:
   - `"{artist} new album {year}"` per cada artista top
   - `"best new {genre} albums {year}"` per cada gènere clau
   - `"underrated {genre} albums"` per joies desconegudes
3. **Filtrar** els resultats que ja estan a la biblioteca (cross-reference amb l'anàlisi)
4. **Presentar** les recomanacions en categories clares:
   - 🔄 **Joies Oblidades** — Tens aquests àlbums, fa temps que no els sents
   - 🆕 **Novetats Discogràfiques** — Nous llançaments dels teus artistes
   - 💎 **Àlbums Per Descobrir** — A la teva biblioteca, encara no els has escoltat
   - 🎯 **Artistes Similars** — Descobriments basats en els teus gustos
   - 🔍 **Joies Desconegudes** — Recomanacions externes alineades amb el teu perfil
5. **Oferir descarregar** via Soulseek qualsevol recomanació

## Perfil Musical de l'Usuari
Definit a `USER_MUSIC_PROFILE` dins `generate_recommendations.py`:
- Gèneres: IDM, ambient, electrònica experimental, krautrock, post-punk, world music, art rock, psychedelic, jazz
- Artistes clau: Aphex Twin, FSOL, YMO, Air, Yello, Ariel Pink, King Gizzard, Mdou Moctar, Boards of Canada, Can, Neu!, The Cure, Kate Bush, Radiohead, Talking Heads, Ryuichi Sakamoto, Morphine

## Configuració
- `NAVIDROME_DB` — ruta a la BD (default: `~/navidrome/data/navidrome.db`)
- `NAVIDROME_USER_ID` — ID d'usuari de Navidrome

## Notes
- Els gèneres a la BD de Navidrome sovint estan buits (tags no importats). El script usa el perfil musical hardcoded com a fallback.
- Els `similar_artists` venen de Last.fm (Navidrome els emmagatzema a la taula `artist.similar_artists`).
- La cerca web de novetats la fa l'agent directament amb `web_search`, no és un script.