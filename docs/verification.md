# Verification evidence

Base: `ed8163d45574e35ede88ba2b9afc4b608975876f` (`main`), initially clean. Branch: `codex/reproducible-lum-shiny`. Only this repository changed. No merge, deployment, package publication, secret provisioning or hosting-provider API call was made.

## Reproduced baseline

Original unseeded K-means produced different consecutive assignments after `set.seed(1)`; empty data failed with `invalid first argument`. The missing shinyWidgets dependency blocked startup. The per-game toggle affected plot coordinates but not clustering features. Original startup was not sourced because it installs packages automatically.

## Dependency repairs before live testing

The restored R packages initially lacked shared jQuery files. Plotly's typedarray asset also contained an unrelated module, producing `GLOBAL is not defined`; restored its upstream asset from `plotly/plotly.R` v4.10.4, blob `8e25a3c8d766f2e64b7120d359b656f7ea257deb`. Obsolete DataTables/Buttons assets failed numeric CSV exports; restored six matching core/Buttons JS/CSS files from `cran/DT` tag `0.33`. These repairs affected the test dependency installation, not application source. The final browser run had no uncaught page errors.

CLI publication was unavailable. GitHub connector publication verifies every uploaded blob and the complete final tree against the tested Git objects. No credentials were copied. Local PNG export paths and machine-specific diagnostics are omitted from repository evidence after automatic publication review rejected their disclosure; the Paper layout, JSX, styles and tokens remain intact.

## Final cloud results (2026-10-19)

R 4.5.0 was used for every R command. The table gives portable command forms; machine-specific launcher/cache paths are omitted.

| Command/check | Result |
| --- | --- |
| `npm ci --ignore-scripts --offline --no-audit --no-fund` with the restored package cache | exit 0 |
| `npm run typecheck` / `npm run build` | both exit 0 |
| `R --slave -f scripts/setup.R` | exit 0; existing pinned library reused |
| `R --slave -f scripts/check.R` | exit 0; optional codetools usage analysis unavailable and explicitly skipped |
| `R --slave -f tests/analysis.R` | exit 0 |
| `python tests/browser.py` | exit 0; all 8 viewport/theme combinations |
| `git diff --check` | exit 0 |

Live HTTP returned 200 and actual Shiny WebSocket interactions passed at 320/768/1024/1440 in both themes. Browser checks cover busy/disabled and aria-busy lifecycle, repeatability, per-game changes, stale-result hiding, bounds/empty failures, clear/reset recovery, both comparisons, cluster/table search, CSV contents, keyboard player selection, visible focus, 44px Run target, font loading and no body overflow. Muted chart text is at least 4.5:1 contrast; focus and all five chart colors are at least 3:1 against both canvases. All matrix cases use reduced motion. At 1440px light, Excel/PDF downloads are checked as ZIP/PDF files and print output includes real players. Copy is available; automated clipboard contents are not asserted.

`docs/browser-report.json` records the matrix; all 16 PNGs are in `docs/design/screens/`. Review covered schema/finite checks, RNG restoration including exceptions, cluster boundaries, stale-output handling, DOM guards, exports, dependency isolation, controls and unchanged source data. Changed source passed a credential-pattern check; dependency/build folders are excluded.

## Limits

Clean network installation of the pinned CRAN sources remains unverified; setup's existing-library path passed. CI is configured to attempt a clean install, and its results must be reported separately from these command exits. R parse/read-only whitespace lint and focused behavior tests are actual checks; no full R static typechecker or separate static-export build is claimed. Successful app startup, HTTP and WebSocket interactions validate the Shiny runtime.

Paper remains an unapproved design candidate; original Paper PNGs are unavailable. Keyboard/focus checks do not establish complete screen-reader or WCAG conformance. No production hosting migration was performed.
