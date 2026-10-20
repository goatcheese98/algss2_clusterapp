# Runtime security and provenance

This is a reviewable preparation step, not a production security certification or deployment. Native Shiny, R 4.5.0, the dataset, filtered row order, scale(), normal-case Hartigan-Wong defaults and RNG restoration remain unchanged. The only R dependency change is **plotly 4.10.4 → 4.12.0**; the other 71 pins remain fixed.

## Findings and bounded remediation

| Reviewed checkpoint debt | Change and evidence |
| --- | --- |
| Pinned versions but no source integrity gate | All 72 CRAN source archives have observed SHA-256 values in `scripts/source-lock.tsv`; setup verifies bytes before install. Corruption/version/coverage/origin rejection tests are required. |
| No actual-image dependency inventory | `scripts/security/inventory.py` emits sorted OS/R inventory and CycloneDX 1.6, including actual image ID/revision, installed versions, and source archive hashes. CI generates twice and compares bytes, then validates against the official tagged schema. |
| Inherited GPG/TIFF high findings | Same Ubuntu 24.04 release patch upgrades during clean build address CVE-2025-68973 (gpgv) and CVE-2025-9900 (TIFF). No distribution or R major migration. |
| Plotly bundled prototype pollution | R Consortium RSEC-2025-1 / CVE-2023-46308 flags 4.10.4; 4.12.0 upgrades plotly.js 2.11.1 → 2.25.2 and documents the fix. The browser suite requires the actually served Plotly bundle to report 2.25.2; no exploit path from the fixed CSV/validated controls has been demonstrated. |

The cloud OS-stage comparison is in [os-baseline-comparison.json](os-baseline-comparison.json). With the same Trivy database, non-kernel-header HIGH/CRITICAL matches fell from six package/advisory pairs to zero. Raw totals still include medium/low and kernel-source findings. The 902 → 309 remaining HIGH/CRITICAL header/source matches are **not hidden or called zero findings**: Ubuntu attributes kernel CVEs to `linux-libc-dev`, which provides headers, not an executing kernel. The deployment host's kernel is outside an image scan and requires its own assessment. See the complete final-image raw scan in CI artifacts; the local comparison only covers the system stages.

The R Consortium snapshot contains 14 advisory files at commit `60e8405cfd95ac555e462073877220265b197d3d`. Against the old installed plotly version it matches RSEC-2025-1; after 4.12.0 the snapshot has no matches for the pinned packages. This is a **sparse curated database**, not comprehensive R vulnerability coverage. The evaluator supports explicit versions and numeric R ecosystem intervals, tests boundary semantics, fails on unsupported schema/ranges, and records database revision/content digest. CI also records current upstream HEAD so snapshot freshness can be reviewed.

Official references:

- [R Consortium advisory](https://github.com/RConsortium/r-advisory-database/blob/60e8405cfd95ac555e462073877220265b197d3d/vulns/plotly/RSEC-2025-1.yaml)
- [Plotly release notes](https://github.com/plotly/plotly.R/blob/v4.12.0/NEWS.md)
- [Trivy v0.76.0 release and checksums](https://github.com/aquasecurity/trivy/releases/tag/v0.76.0)
- [Ubuntu GnuPG advisory record](https://ubuntu.com/security/CVE-2025-68973)
- [Ubuntu TIFF advisory record](https://ubuntu.com/security/CVE-2025-9900)

## Source trust and reproducibility

The collection workflow `Source provenance collection` run [39384731299](https://github.com/goatcheese98/algss2_clusterapp/actions/runs/39384731299), at `3a469f747d9bff483991e857d367ea31b1663144`, downloaded the exact 72 release tarballs directly from CRAN over certificate-verified HTTPS and checked each DESCRIPTION package/version. The collector uses CRAN Archive, with current-contrib fallback for a missing archive. Those observed SHA-256 values were reviewed and committed separately; setup cannot refresh the trusted lock. Independent source-collection CI fetches again and compares to the committed hashes. No hashes are inferred from version strings, Git mirrors or installed package files.

This establishes byte integrity against a reviewed **trust-on-first-observation** snapshot. It is not an independent upstream signature, a signed builder attestation or proof that the first archive was safe. Version-matched packages already in a developer library are skipped, so this does not authenticate an existing library's historical installation. The required clean image build starts without that library and verifies all 72 archives. Linux setup requires coreutils `sha256sum`; digest checking adds no bootstrap R dependency. SHA mismatches abort before install and are never accepted by a fallback.

To propose a refresh, change only justified versions, run `python scripts/security/source_lock.py --output source-lock.candidate.json` on a cloud worker with CRAN access, review archive origins/identity and hashes, then update the TSV in a separate reviewed change. Do not make setup auto-update hashes. Run source-integrity, analysis/reference/RNG, runtime and browser tests before accepting any dependency change.

The base image is digest-pinned. Ubuntu apt patch versions and repositories remain time-dependent; the same source can build a different patched image later. Inventory is deterministic **for the same built image and source lock**, not byte-identical across rebuilds. OS scans use current Ubuntu advisories in Trivy's database; artifacts record scanner version, database metadata/digest and scan date. The mutable upstream database itself is not frozen or bundled. R advisory inputs and the official CycloneDX schema are commit-pinned. The SBOM is a flat inventory with direct container containment edges, not a complete transitive dependency graph. CRAN component hashes identify source archives, not compiled binaries.

## Reproduce and inspect evidence

After a clean image build using the hosting instructions:

```sh
python scripts/security/inventory.py algss2-runtime:review security-evidence
python scripts/security/install_trivy.py
pip install PyYAML==6.0.3 jsonschema==4.25.1
python tests/security.py
python scripts/security/validate_sbom.py security-evidence/sbom.cdx.json
.security-tools/trivy image --image-src docker --db-repository ghcr.io/aquasecurity/trivy-db:2 --scanners vuln --pkg-types os --format json --output security-evidence/os-trivy.json algss2-runtime:review
python scripts/security/os_report.py security-evidence/os-trivy.json security-evidence/os-summary.json
git clone https://github.com/RConsortium/r-advisory-database.git .security-tools/r-advisories
git -C .security-tools/r-advisories checkout --detach 60e8405cfd95ac555e462073877220265b197d3d
python scripts/security/r_advisories.py security-evidence/inventory.json .security-tools/r-advisories security-evidence/r-advisories.json
```

Run these in cloud. The complete-image CI job retains `runtime-security-evidence` for 14 days: inventory, CycloneDX SBOM, raw OS findings, triage summary, scanner/database metadata and R advisory report. Browser/runtime evidence is a separate artifact. PR description links the exact successful runs and tested head, so results are not silently carried to later commits.

## Remaining coverage and minimal options

- Trivy's Ubuntu scan covers dpkg packages. It does **not** establish advisory coverage for the manually compiled R 4.5.0 interpreter; R core security review and a compatible 4.5.x patch upgrade remain a separate bounded task if warranted by official advisories.
- CRAN/Bioconductor advisory matching does not comprehensively scan vendored C/C++/JavaScript, static links, every browser asset or packages with no published advisory. Unsupported ecosystems are unscanned, not zero findings. Application code analysis, penetration testing and secrets scanning are not claimed by this slice.
- Kernel/header matches remain in raw reports. An optional smaller runtime without development tools/headers needs its own package/removal and smoke review; simply hiding these packages in a scanner ignore file would not secure the host kernel. No ignore file or severity downgrade is added.
- Remaining medium/low/unfixed OS findings are visible. The new gate rejects all non-header HIGH/CRITICAL OS matches and any matching R snapshot advisory, and fails on scanner/database errors. It makes no zero-vulnerability promise.
- Hosted production TLS/authentication, WebSocket proxy, host kernel, resource/concurrency sizing, session draining and deployment identity are still unprovisioned. Paper remains a candidate without original PNGs or human approval. No image, package, live host or production release is published by these workflows.
