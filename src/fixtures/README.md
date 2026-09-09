`fixture-italic.woff` is an original test font derived from the rectangle-glyph
ASCII fixture embedded in `render.test.ts`. Each outline point `(x, y)` becomes
`(x + round(0.2 * y), y)`. Its family stays `Fixture Sans`, its PostScript name
is `FixtureSans-Italic`, and its OS/2, head, post, and name tables identify an
italic face. It supports deterministic native-face browser tests without system
fonts or public network access.
