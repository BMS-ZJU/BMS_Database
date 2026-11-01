# Noto Sans SC web font

CSS family: BMS Noto Sans SC
Normal variable weights exposed by font.css: 100-900
Verified wght axis in every font binary: 100-900 (default 100)
Google Fonts asset version: v40
Files: 102 WOFF2 slices, total 4,527,952 bytes (4.32 MiB)

The 101 default Google Fonts unicode-range slices are retained. One extra slice from the same official family supplies supported characters in the public Unicode Greek/Coptic (U+0370-03FF) and Number Forms (U+2150-218F) blocks, including Greek letters and Roman numerals. Supplement request parameters are fixed public Unicode blocks, not website text.

All font binaries are unmodified official downloads. The original Google Fonts CSS request specified weights 400-600, but each delivered variable binary has a real wght axis of 100-900. font.css exposes that verified full range, including intermediate weights such as 450 and 650 and bold weight 700. Internal names such as Thin do not indicate the selected variable weight.

font.css declares a separate CSS family and uses relative WOFF2 URLs and unicode-range subsets. It does not apply the family to any element. Browsers fetch relevant slices only when page text uses this family; there is no local() source or runtime Google dependency. Only normal style is provided.

License: SIL Open Font License 1.1, included as OFL.txt. The Google Fonts metadata records (c) 2014-2021 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source', and source https://github.com/notofonts/noto-cjk at commit 523d033d6cb47f4a80c58a35753646f5c3608a78. The CSS alias does not modify the internal font names.

Official sources:
- https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400..600&display=swap
- https://github.com/google/fonts/tree/main/ofl/notosanssc
- https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/OFL.txt
- https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/METADATA.pb
- https://www.unicode.org/charts/PDF/U0370.pdf
- https://www.unicode.org/charts/PDF/U2150.pdf

SOURCE.json preserves the original CSS/font request URLs and font download checksums. SHA256SUMS.txt checks every delivered file except itself, including the license, CSS, provenance and .gitattributes. Text files use UTF-8 with LF line endings; the directory .gitattributes fixes LF on checkout so these byte-level checksums also work with Git core.autocrlf=true. WOFF2 files are binary.
