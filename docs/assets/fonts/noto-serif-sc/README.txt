# Noto Serif SC web font

Noto Serif SC, served through the CSS family alias `BMS Noto Serif SC`

- Source: Google Fonts CSS API, versioned Google Fonts asset URLs at `v35`
- Requested normal variable weight range: 300-700 (including 650)
- Contents: 101 official default unicode-range WOFF2 slices plus official Greek/Greek Extended and Roman numeral text subsets (103 files)
- WOFF2 total: 6,041,532 bytes (5.76 MiB)
- License: SIL Open Font License 1.1, provided unmodified in `OFL.txt`
- No local font files were copied; WOFF2 binaries are unmodified downloads
- `font.css` uses relative URLs, unicode-range and font-display: swap; there is no local() source
- The CSS alias isolates this site font from installed fonts and existing print font stacks; it does not rename the font binary

Official sources:

- https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@300..700&display=swap
- https://github.com/google/fonts/tree/main/ofl/notoserifsc
- https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifsc/OFL.txt
- https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifsc/METADATA.pb
- https://developers.google.com/fonts/docs/css2
- https://fonts.googleapis.com/css2?family=Noto+Serif+SC%3Awght%40300..700&display=swap&text=%E2%85%A0%E2%85%A1%E2%85%A2%E2%85%A3%E2%85%A4

The Google Fonts metadata identifies source repository https://github.com/notofonts/noto-cjk at commit `985fa52c81c1d6692ccdd82bc3656e8fb932fd89`, source path `google-fonts/NotoSerifSC[wght].ttf`, and records copyright `(c) 2017-2024 Adobe (http://www.adobe.com/)`. The accompanying Google Fonts OFL file starts with `Copyright 2012 Google Inc. All Rights Reserved.`; it is retained verbatim.

The browser downloads only slices needed for text using this family. Loading this stylesheet alone while using the original sans font did not request any WOFF2 files. Before the Roman numeral supplement, a four-line sample containing Chinese, English, digits and beta loaded 13 of the original 102 files (896,268 bytes). Browser font inspection confirmed downloaded font rendering at weights 300, 400, 650 and 700. Page size varies with its characters; this is not a universal download-size estimate.

The public request URLs above identify the font sources. `SHA256SUMS.txt` lists the checksums for the delivered font binaries, stylesheet and license.

Roman numeral coverage: U+2160-2164 (ⅠⅡⅢⅣⅤ), used in course names and ordinary prose. The original 102 WOFF2 cmap tables have no glyph mapping for these characters. The additional unmodified Google Fonts v35 text subset is 1,772 bytes and contains all five mappings and a wght variable axis (200-900 internally, exposed as 300-700 in font.css). It uses the same Noto Serif SC family and accompanying OFL license.
