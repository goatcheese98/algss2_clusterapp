# R/Shiny runtime candidate

This packages the existing ALGS app for an R-capable Linux container host. It does not deploy, publish an image, configure a domain, or provide a Cloudflare Workers adapter. Dataset, math, controls, LUM tokens and Paper candidate status are unchanged.

## Before / after debt inventory

| Area | Before this slice | After this slice |
| --- | --- | --- |
| Browser bridge | Already strict `client/busy.ts`; committed JS is generated | Revalidated with typecheck/build and zero generated-JS diff; no untyped application JS found |
| R dependency installation | 72 exact package versions; hosted clean installs already passed | Same manifest is installed from an empty library in a clean container build |
| Runtime identity/start | Framework start expression documented; no container user/entrypoint | Digest-pinned R 4.5.0 base, UID/GID 10001, an init that forwards stop signals to R, strict port and all-package version checks |
| Readiness | No packaged probe | Bounded loopback HTTP probe checks the real ALGS Shiny page; rejects error/wrong-service/closed-port responses |
| Isolation/start verification | No repeatable runtime contract | CI runs read-only with dropped capabilities, no-new-privileges and temporary writable caches; tests R and actual browser behavior against the container |

## Build and run in cloud

Build on a Linux Docker host with HTTPS access to Docker Hub, Ubuntu package repositories and CRAN. The base is pinned to immutable multi-platform index `sha256:f97b4944221bdc309583dfbc37dc0bf2654cfbd1f330cded047aeec4ae5df7e3`. Verified target is **linux/amd64**; arm64 is not claimed as tested. Dependencies are installed only at image build time. The final image copies the compiled R library from the dependency stage, plus an allowlist of production source/data/assets. Git metadata, deployment-account configuration, tests, node_modules and local credentials are outside the build context.

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run typecheck && npm run build
# Image stays in this cloud Docker daemon; no registry push is required.
docker build --pull --build-arg "VCS_REF=$(git rev-parse HEAD)" -t algss2-runtime:review .
docker run --rm --name algss2-review \
  --read-only --cap-drop=ALL --security-opt=no-new-privileges \
  --pids-limit=128 --memory=512m --cpus=1 \
  --tmpfs /tmp:rw,noexec,nosuid,size=67108864 \
  --tmpfs /home/shiny:rw,noexec,nosuid,uid=10001,gid=10001,size=16777216 \
  -p 127.0.0.1:3838:3838 algss2-runtime:review
```

If a cloud proxy requires an additional CA, pass its **public trust bundle** through BuildKit's `proxy_ca` secret. Networked build steps mount it only for that step; it is not copied into image layers. Preserve platform proxy settings and TLS verification. Registry credentials, browser cookies and local desktop certificates are not part of the runtime handoff. No environment-specific proxy hostname is embedded.

`PORT` defaults to 3838 and must be an integer from 1024 through 65535. The server binds all container interfaces; publish it on loopback as shown until an explicitly configured front proxy is ready. For a different port, pass `-e PORT=3840` and map that container port. The health command reads the same value. The entrypoint first checks R 4.5.0 and every pinned R package version, then Shiny loads the application and validates the CSV before serving.

```sh
docker exec algss2-review Rscript --vanilla scripts/health.R
docker stop --time=10 algss2-review
```

The health check runs on loopback with base R sockets, so it needs no curl executable or proxy access. It verifies HTTP 200 plus ALGS/Shiny markers; it does not prove every reactive computation or a WebSocket session. The browser gate supplies that separate evidence. The packaged init forwards stop signals to R and reaps child processes; the smoke test rejects a forced-kill exit. Bare R as PID 1 required a forced kill in the cloud base-image check. Existing sessions are not promised a drain period.

## Repeated verification

The 30-minute `runtime` CI job performs `docker build --pull --no-cache`, then runs `python tests/container.py algss2-runtime:ci`. That contract checks UID, read-only data/root filesystem, dropped capabilities, no-new-privileges, a custom port, Docker health status, rejected invalid/unbound ports, in-container runtime/analysis/RNG/reference tests, all eight actual browser cases and stop behavior. It removes only its own temporary test container. Reports/screenshots are uploaded as `non-root-runtime-evidence`; the image is never pushed to a registry. The existing source quality gate remains enabled and now also exercises start/health configuration.

For a non-container Shiny-capable service, install the pinned manifest in a writable build library, then run `Rscript --vanilla scripts/start.R` from the app root. Keep the installed library and production source read-only for the service user. A host must provide a persistent R process and forward WebSocket upgrade traffic. Shiny Server, Posit Connect or a container-capable VM can host R; choosing/provisioning that destination, TLS, authentication, routing and any account/cost approval remains human work. No provider API or production account is used here.

## Exact limits

- Base image digest, R version and all 72 R package versions are fixed. All 72 CRAN release archive SHA-256 values are locked and checked before clean installation. Ubuntu apt patch versions are refreshed within 24.04 but are not separately frozen; byte-identical builds or signed attestations are not claimed. See [security coverage and evidence](../security/README.md). Security refreshes require a reviewed rebuild and the same tests.
- The R base itself includes build utilities; this is not a minimal OS image. Extra dependency-build headers are isolated to their build stage. Runtime UID/capabilities/read-only policy constrain writes, but do not establish complete host security.
- One R process serves sessions. TLS/authentication, orchestration, restart policy, resource sizing under concurrent load, rolling session drain and production monitoring are not implemented or claimed.
- Original Paper exports and human design approval remain unavailable. This runtime-only slice makes no visual design changes; container browser captures verify the existing LUM candidate with real data.
