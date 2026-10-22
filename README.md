# Vektprogrammet

Offentlig visning av dashbordet «Vektprogrammet», publisert med GitHub Pages.

- `data/*.csv` – tallene (vekt, mat, matkilder, aktivitet, livvidde, Strava). Blodsukker legges aldri her, hentet fra Claude-dashbordet.
- `fragment.html` – dashbordets side.
- `build.py` – bygger `index.html` av de to.

Oppdateres automatisk hver natt av en planlagt Claude-oppgave. Ikke rediger `index.html` for hånd.

`tools/strava_prosess.py` lager `data/strava_turer.csv` og `data/strava_splitter.csv` fra rå Strava-svar (se docstring).
