
# Bad Roses

## Uploading website updates to GitHub

This folder is connected to `https://github.com/badr0ses/badr0ses.github.io.git` on branch `main`. Keep `index.html`, the JavaScript/CSS files, `assets/`, and `data/` at the repository root.

Run these commands in PowerShell from this folder after editing the website:

```powershell
git status
git add .
git commit -m "Update website"
git push origin main
```

Git uploads the changes together, so GitHub's browser limit of 100 files per upload does not apply. The existing `.gitignore` keeps local `tmp/`, `backups/`, and Python cache folders out of commits. Sign in to GitHub if Git Credential Manager prompts you. If Git reports that the remote has newer commits, run `git pull --rebase origin main` before pushing again. If a conflict appears, resolve it before continuing; do not force-push.

You can also add this folder as an existing repository in GitHub Desktop, then use **Commit to main** and **Push origin**.

This is a buildless website. Preview it through a web server so the catalogue can load its JSON:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/#database`.

The public catalogue contains 6,450 items and 247 horses from the supplied Nalya Legacy installation (6,697 entries). The database page includes search, collections, type, location, event, level and currency filters, price sorting, and full entry details. Internal coats, manes, character bodies, eyes and faces, service/test assets, unlisted entries and ambassador items are excluded from the generated database. There is no unlisted-items toggle. `scripts/catalogue_visibility.py` applies this policy on every import; metadata retains the original source totals and exclusion counts.

To regenerate from an installed client:

```powershell
python scripts/import-nalya.py --game "C:\path\to\game"
python scripts/check-catalogue.py --game "C:\path\to\game"
```

The importer only reads the client. It does not launch the game or execute any game scripts. The original website database is backed up to `backups/database-before-nalya.json` on the first import. Existing item reference images are retained by exact game item ID in `data/catalogue-image-references.json`. All other metadata is rebuilt from the client.

Most icon conversion uses Python's standard library. Ten Crunch icons additionally need `texture2ddecoder`:

```powershell
python -m pip install --target tmp/nalya-tools texture2ddecoder==1.0.6
python scripts/import-nalya.py --game "C:\path\to\game" --decoder-path tmp/nalya-tools
```

Generated files are `data/database.json`, `data/catalogue-meta.json`, `data/catalogue-shops.json`, and `assets/catalogue/icons/`. The website itself has no Python or package dependency. Metadata includes conversion errors and source coverage. The archived client lists content for its legacy build; it does not prove current live availability. Zero cash prices are displayed as **No price listed**, because some records require tokens or belong to quests.

Item locations use explicit place names in local shop records where available, otherwise shop faction regions. These are not independently verified shop coordinates. Horse locations come from sale placements and their named parent objects. Missing locations remain unlisted. Event badges come from explicit seasonal codes, event shop names, and event names in local item names; missing tags do not prove year-round availability.

The polished catalogue groups horse coats by legacy model and hairstyles by style. Opening an entry shows its local colour/coat choices; switching a choice switches its picture, price, requirements and recorded location. Makeup entries keep the original preview images extracted from the local game files. Missing event tags display as **Unknown**.

Photographs do **not** add entries to the database. `data/catalogue-visuals.json` is an overlay keyed by existing client IDs; `data/catalogue-variants.json` contains only those IDs. Horse photo pools are restricted by the explicit legacy model-generation crosswalk in `scripts/import-catalogue-photos.py`. Coats are assigned using decoded local textures, colour/pattern features and source metadata, and remain labelled as photo references. A few unmatched prototypes retain the actual game coat texture. Hairstyles use the supplied `assets/HAIRSTYLES` portraits matched by model and colour material; full-screen captures are framed around the hair in CSS. The previous JoJo Siwa portraits are retained. Entries without a matching portrait retain their game icon. `data/hairstyle-assets.json` records image matches and display frames, and `data/hairstyle-colours.json` records reviewed type and colour labels. `scripts/hairstyle_assets.py` applies these on every import without adding records. Models sharing a texture are kept in separate galleries. Modern source-only haircuts, makeup looks and horse models are never appended.

To refresh the photo pipeline (authoring tools only):

```powershell
python -m pip install --target tmp/nalya-tools Pillow==13.0.0 texture2ddecoder==1.0.6
python scripts/import-catalogue-photos.py --game "C:\path\to\game"
python scripts/match-catalogue-coats.py --game "C:\path\to\game"
python scripts/import-nalya.py --game "C:\path\to\game" --decoder-path tmp/nalya-tools
python scripts/check-catalogue.py --game "C:\path\to\game"
```

The matching step needs local coat textures; it creates that cache from the client on first run. Contact sheets in `tmp/coat-matching/` pair the local texture and proposed source photo for visual review. Explicit manual corrections can be stored in `data/catalogue-coat-corrections.json`. `data/catalogue-photo-report.json` records the photo coverage and the zero-added-record guarantee.

Reference item images credit InstanceID, Velau, Newcarnatiøn and Anuhi: https://velausc.github.io/sso-items-list/. Horse references are from https://ssodb.bplaced.net/db/en/. The read-only localization reader was informed by the format documentation at https://github.com/RealIndrit/sso-format; the supplied legacy variant uses a different metadata layout. Game assets belong to their respective owners.

The account-free wishlist saves exact item, hair-colour and horse-coat choices in browser local storage (`wishlist.js`). Hearts on cards and detail views toggle favourites; **My wishlist** shows saved variants individually and keeps the existing filters. Storage stays on that browser/device and does not sync. If storage is blocked or full, the UI explains that changes last for the current page visit only. Run `node scripts/check-wishlist.cjs` to check persistence and fallback behavior.

To refresh the supplied hairstyle assets without reimporting other entries, run `python scripts/hairstyle_assets.py --game "C:\path\to\game"`. The catalogue About/import disclosure block has been removed from the page.

Hairstyle colours appear as separate cards (duplicate records for the same model/material share a preview), with the full style gallery still available in details. Supplied images at different salons are labelled by location; selecting a location filter uses that salon's matching portrait. Cards show a location badge when there is no known event, without repeating the location underneath. The legacy price/availability sentence has been removed from detail views.

The long braided ponytail (`Hair_23`) and its seven colours are excluded from the public catalogue by request. The visibility policy preserves this exclusion during rebuilds.

Reviewed horse screenshots are recorded in `data/horse-photo-corrections.json` and take priority over automatic photo matching in every import. The bay Morgan (`horse-142`, body `6124`) uses the supplied Crescent Moon Village screenshot; its client location remains Crescent Moon Village. Other Morgan coats retain their own recorded locations.
