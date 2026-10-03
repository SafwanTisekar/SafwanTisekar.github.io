# SafwanTisekar.github.io

Personal site of Safwan Tisekar: analytics, BI, AI and automation. Live at https://safwantisekar.github.io/.

## What's here

| Path | What it is |
|---|---|
| `index.html` | Home page: what I do, about, experience, skills, projects, education |
| `projects/dubai-property/` | Dubai Property Market & Mortgage Risk: live Power BI report, findings, how it's built ([code](https://github.com/SafwanTisekar/dubai-property-analytics)) |
| `styles.css`, `main.js`, `config.js` | Shared by every page. `config.js` holds the links (report embed, GitHub, CV) |
| `data/projects.json` | The project cards on the home page, one entry per project |
| `data/site.json` | The numbers shown on the pages, each with its label and source |
| `assets/` | Font (Manrope, SIL OFL), photo, favicon |
| `tests/` | Checks run before every deploy |

Static HTML, CSS and a little JavaScript: no framework and no build step here.

## Where the numbers come from

Nothing on the pages is typed by hand. `make site` in the [dubai-property-analytics](https://github.com/SafwanTisekar/dubai-property-analytics) repository reads that project's database and writes every number into its `<span data-kpi="...">` on the pages, plus `data/site.json`, and renders the project cards from `data/projects.json`. It writes into a local clone of this repository (`SITE_REPO_DIR` in that project's `.env`). Commit and push here to publish.

## Preview and test

```bash
python3 -m http.server 8000      # then open http://localhost:8000
pip install -r requirements-dev.txt && pytest
```

Links are root-relative (`/styles.css`), so preview from this folder with a local server, not by opening the file.

The tests check that the numbers match `data/site.json`, every link and image resolves, images have alt text, text contrast meets WCAG AA, and the pages carry no personal contact details or documents.

## Deploy

`.github/workflows/pages.yml` runs the tests and publishes the site on every push to `main` (Settings > Pages > Source: GitHub Actions). The repository files that are not part of the site (`tests/`, `README.md`, `.github/`) are left out of the published copy.

## Credits

Dubai project data: Dubai Land Department, CC BY 4.0. Area locations © OpenStreetMap contributors (ODbL). Independent work, not affiliated with DLD. Not investment or lending advice.
