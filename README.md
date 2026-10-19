# ALGS Split 2 player analysis

R/Shiny exploration of the existing ALGS Year 4 Split 2 Playoffs dataset from [Liquipedia](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Split_2/Playoffs). Cluster labels describe similarity, not player quality.

## Reproducible setup

Use R **4.5.0**, a C/C++ toolchain, and development libraries for curl, OpenSSL and XML. The runtime never installs packages or changes CRAN options. `scripts/package-versions.R` pins all 72 non-base dependencies in installation order; `scripts/dependencies.R` checks the four direct runtime versions. Base/recommended libraries come from R 4.5.0. `renv` was unavailable in the cloud runtime, so this slice uses an explicit manifest rather than an untested renv bootstrap.

```sh
export R_LIBS_USER="$PWD/.Rlibrary"
mkdir -p "$R_LIBS_USER"
Rscript scripts/setup.R
Rscript -e 'shiny::runApp(".", host="127.0.0.1", port=3838, launch.browser=FALSE)'
```

Setup downloads exact CRAN source tarballs, checking Archive first and then the current path with the same versioned filename. It fails on missing sources or version mismatches; it never upgrades to a different version. Installation requires network access and system build dependencies. The cloud verification reused the restored dependency installation; a clean Internet install remains to be verified by CI.

## Use

Choose either metric comparison, its original range filters, per-game mode and 1–15 clusters, then **Run analysis**. Per-game mode now changes both clustering and plotted kills/damage. The rate comparison already uses K+A/D and damage difference per game. Filters continue to use the original totals/rates. Settings changes invalidate displayed results until Run succeeds. **Reset example** restores the original defaults; **Clear filters** includes all players. Empty or invalid selections explain the constraint without leaving stale results visible.

Chart shapes and colors identify clusters. Use **Table** for search, sorting, cluster filtering and copy/CSV/Excel/PDF/print exports. **Inspect player** offers native keyboard access to details. Controls stack below 768px; the statistics region deliberately scrolls horizontally. Light/dark follows system settings, and reduced motion disables transitions. Geist and Geist Mono are self-hosted with their OFL license.

## Checks

Node is needed only to compile the small strict TypeScript accessibility/lifecycle helper. Application logic remains R; this is not a full-repository TypeScript migration.

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run typecheck
npm run build
Rscript scripts/check.R
Rscript tests/analysis.R
pip install playwright==1.55.0
# Start Shiny in another cloud terminal first; set CHROMIUM for your cloud browser.
CHROMIUM=/usr/bin/chromium python tests/browser.py
```

`check.R` parses all R sources and checks trailing whitespace; it also runs codetools usage analysis when available. It is not a full R typechecker. The browser test exercises the live WebSocket app at 320/768/1024/1440 in both themes with reduced motion, including repeatability, controls, errors, reset, CSV contents and keyboard detail selection. CI has a 20-minute bound and read-only repository permissions. Screenshots support the behavior checks; they are not the test oracle.

See [design provenance](docs/design/README.md) and [verification evidence](docs/verification.md).

## Hosting

Run this app on an R/Shiny-capable server such as Shiny Server, Posit Connect or shinyapps.io, with dependencies installed during setup and the CSV packaged alongside `app.R`. WebSockets and a persistent R process are required. Cloudflare Workers cannot execute this R app; no static export or adapter was verified and no Cloudflare deployment configuration is supplied. This change does not deploy to the existing shinyapps.io account or call its provider API.
