# Albatross Koukairoku

The complete, unabridged MAO English script of raiL-soft’s *Albatross Koukairoku*, browsable alongside the Japanese source.

[Read online](https://mao-tls.github.io/albatross-koukairoku/script/) · [Title page](https://mao-tls.github.io/albatross-koukairoku/)

The reader contains all 13,128 passages across 84 scripts, with scene navigation, full-script search, and direct passage links.

[English patch v1.0.0](https://github.com/MAO-TLs/albatross-koukairoku/releases/tag/v1.0.0) requires the installed Japanese DVD retail edition (July 23, 2010) and Python 3. The patch-only ZIP includes a reversible, exact-hash installer and IBM Plex Mono; it does not include the original game or a standalone Mac app. See [installation instructions](public/patch-installation.txt).

Local Wine opening-scene, settings, save/load, wrapping and truncation regression checks are distinct from native Windows testing or a full-game playthrough, which have not been verified.

## Development

Use Node.js 24. Run `npm ci`, `npm test`, and `npm run build`. `npm run preview` serves the static export locally at http://127.0.0.1:4328/albatross-koukairoku/.

GitHub Actions verifies the script and MAO commit identity, builds the site, and publishes `dist/client` to GitHub Pages.

## Credits

- Project Lead: MAO
- Translator: GPT-6 Astra
- Special Thanks: gambs

This is an unofficial, noncommercial fan translation. Original works and trademarks belong to their respective owners.
