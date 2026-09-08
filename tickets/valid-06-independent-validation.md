# valid-06-independent-validation: Check images and font binaries independently

- **Status**: In Progress
- **Branch**: `valid-01-benchmark-audit`
- **Base**: `14e792f`
- **Machine**: `eob-dev2`
- **Harness**: codex
- **Session ID**: `01a082ae-164d-73f2-a49e-a3d6e48adfaf` / evaluation_validity
- **Assignee**: Edward Benson

## Goal

Independently verify every claimed rendered line has visible pixels and every claimed font identity/weight agrees with the actual frozen binary. Harden malformed metadata reporting.

## Observed failures

Independent review of the first validator implementation found these reproducible results on its otherwise-valid fixture:

```text
missing_second_line valid= True errors= []
non_font_binary valid= True errors= []
catalog_null AttributeError 'NoneType' object has no attribute 'get'
transparent_LA valid= True errors= []
```

The first two are important validation omissions: hashing bytes pins their identity but does not prove that pixels or font metadata represent the claimed content.

## Plan

1. Record regression Red evidence for erased lines, invisible PNGs, malformed catalog shapes, invalid font bytes, and forged internal names/weights.
2. Decode each unique font once with fontTools; compare actual metadata to frozen claims and target families, supporting explicit catalog binary-family variants.
3. Require ink inside every measured line at the recorded pixel scale and reject transparency in every PNG mode.
4. Freeze the common prompt in `baseline/prompt.txt`; verify focused/full offline gates and a reversion against the pre-review validator.

## Decisions and durable findings

- Use fontTools independently from renderer fontkit, reducing shared implementation assumptions.
- The original generated WOFF fixture from renderer tests is copied to `tests/fixtures/fixture.woff`; no network font downloads are needed by unit tests.
- Pixel checks establish visible line presence and geometry consistency; they are not OCR and do not independently identify rendered glyph strings.
