# LUM / Paper implementation candidate

[Exact Paper handoff](https://app.paper.design/file/01M5B2V51AQCVK1FV588NPVXZQ/p-1-0), 2026-10-19. Candidate only, not user-approved. The supplied layout, JSX, styles and tokens are preserved in `paper-readback.json`; local PNG export paths are omitted for privacy. Original desktop/mobile PNGs were not attached and are not claimed as committed. Files in `screens/` are new cloud browser captures of the implemented Shiny app.

The native Shiny layout uses the specified 288px desktop control rail, 24px sections, 32px results gutters, 24px mobile gutters, 44px actions, a named Edit analysis link, Chart/Table switch and readable selected-player details. All original filters survive, including both rate filters. Stacked controls keep every input directly available on mobile; no focus-trapping sheet is needed. Fictional names/numbers from Paper do not ship in the application.

LUM sources read through the GitHub connector:

- `src/styles/design-tokens.ts`, blob `e7e0c2362848c209914a5d9da2bcaa5657b663b8`
- `src/styles/fonts.ts`, blob `d32cace0ed25de3f8e164b9b2d906ca6e782c0e9`
- `src/dashboard-shell-css/primitives.ts`, blob `86324ebdaca47f0837b09c774e31a96f4d81b2d5`
- `src/dashboard-shell-css/shell-chrome.ts`, blob `9678f3e1bf6d00e4f2701b355b8612b2a488574b`

Canonical `--bg/--panel/--panel2/--sidebar/--line/--line2/--fg/--mut/--mut2/--acc/--on-acc`, typography and radius tokens match LUM. Dark mode uses its near-black canvas and gold accent with dark accent text. Spacing is the Paper candidate decision, not a canonical LUM claim. Plot colors remain data encoding; shapes and a searchable table provide alternatives. The plot uses the theme's text/grid colors, and the table has its own labeled horizontal scroller.

Self-hosted variable fonts from `vercel/geist-font`: Geist blob `71dab8bedba3bfef5dccd7875ed05cac44c7345d`, Geist Mono blob `0e746fc18223dfcb107a85502a0abe1b1a02d51a`. License: `www/fonts/OFL.txt`. No font requests to external providers are needed.

Intentional native adaptations: full controls stack instead of a compact sheet; plot legends wrap; the existing complete statistics table scrolls instead of showing fictional compact rows. Desktop and mobile use the same valid ALGS data and fixed seed. No animation is necessary to inspect results.
