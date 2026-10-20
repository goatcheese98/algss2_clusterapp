# Runtime verification record

Baseline was the clean, reviewed draft head `4b5d2ec3d38174899bfeaa1099d639262e9d96c4`. The remote head matched, no additional repository instructions were found, and the original Hartigan-Wong/RNG/reference tests passed again. `client/busy.ts` was already strict TypeScript; typecheck/build produced no change to `www/busy.js`. There was no Dockerfile or packaged start/readiness command.

Cloud checks before publication:

| Check | Result |
| --- | --- |
| Existing analysis/RNG/reference suite | exit 0; mathematical implementation and dataset unchanged |
| Runtime port/version checks | exit 0 |
| Readiness against HTTP 200/503, wrong service and closed port | exit 0 |
| Real startup on configured port, followed by readiness command | exit 0; actual ALGS Shiny page served |
| Existing browser suite through the new startup entrypoint | exit 0; all eight width/theme cases, reduced motion and existing downloads/filters |
| TypeScript typecheck/build and generated-JS equality | exit 0 |
| R parse/read-only whitespace lint | exit 0; optional cloud codetools analysis unavailable |
| Docker build checks | exit 0, no warnings |
| Digest-pinned base pull and clean system-stage build | exit 0; R 4.5.0 confirmed and no Shiny preinstalled |
| Bare R PID-1 shutdown | forced-kill exit 137 reproduced |
| Non-root init/R shutdown on read-only filesystem | exit 143, no forced kill; build-only CA absent |
| Workflow YAML structure / Python compilation / Git whitespace | passed |

The workspace cloud proxy denied CRAN access with HTTP 403. No attempt was made to bypass it. The complete clean application-container build is verified by the existing cloud-hosted CI, which already supports clean CRAN installation. The new `runtime` job builds without a reused R library, runs non-root/read-only, checks health and invalid configuration, runs R/RNG/reference tests inside the image, and executes the actual browser suite against the container. Final exact-head job outcomes and cloud artifact links are reported in the draft PR; predecessor evidence is not substituted for them.

No visual behavior or LUM tokens changed. The saved Paper handoff remains an unapproved candidate; original canvas PNGs were not supplied. Runtime browser captures are CI evidence, not new design approval. No image registry publication, production deployment, infrastructure purchase, domain change, credentials or local desktop/browser handoff occurred.
