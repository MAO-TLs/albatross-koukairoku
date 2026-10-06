# v1.0.0 executable and installer sources

These are the executable-hook, UI-label and installer sources used for the v1.0.0
patch and its 2026-10-07 UI and story-text crash hotfixes. Original game files are not included. The published ZIP is a delta patch
and requires the exact 2010-07-23 Japanese DVD retail files.

`install_patch.py` is standalone and accompanies `patch.json`, `patch.dat.gz`
and the licensed font in the release ZIP. The other sources are an engineering
snapshot: their default paths refer to the local MAO workspace, including the
hash-verified original executable and intermediate converter output. They are
not a standalone game build or a replacement for the installer.

The executable changes lock horizontal IBM Plex Mono, load the bundled font
privately through the Unicode executable-directory path, use unsigned CP1252
decoding, wrap at word boundaries while preserving hard breaks, reflow the
three text sizes in a 720×530 story area, and expand the glyph pool to 8,192
with constructor-specific stable registration. Font/direction controls are
inert. Japanese ruby annotations are absent from the English text, so ruby
display controls have no English annotations to show. Script voice/control
bytecode is preserved.

The story formatter treats the English archive as single-byte regardless of
the Windows system code page and uses an 8,192-byte temporary buffer. This
prevents CP1252 punctuation from being consumed as Shift-JIS and accommodates
the longest translated records without changing other engine string paths.

## Verification scope

- 20 x86/layout regression tests, 11 installer tests, 3 script-control tests,
  and 4 source-bound UI-label/scope tests.
- Stop Voice correctly shows On (left) / Off (right), matching あり / なし.
  Only its six normal/hover/selected sprite payloads changed; native positions,
  callbacks and every other archive entry are unchanged. The installer accepts
  the initial v1.0.0 UI archive only with its verified original-file backup.
- 13,098 native text calls audited in linear bytecode order; 11,265 modeled
  page groups across all three sizes, maximum candidate 3,429 glyphs and zero
  modeled fit failures. Native auto-clear-and-retry is modeled; this is not
  a path-sensitive VM playthrough.
- Opening-scene Wine checks, English settings/save/load, bundled-only font
  loading, and the reported truncation regression verified in the game window.
- Native Windows, full-game playthrough and every voice's audible timing are
  not verified. A standalone Mac app is not included.

Release archive SHA-256:
`8dbc045d0a50815c7a9054f5b6da167400e15eaf59003672e598c68347f93d5f`

Patched executable SHA-256:
`1fce23eca6f6b4292b86496cc1937836ee33611156daf76a672cd4ef06bd7f9f`
