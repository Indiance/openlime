# Viewing local PTM and RTI files in OpenLIME

OpenLIME cannot open `.ptm` or `.rti` files directly. It expects a folder with
one image per coefficient plane and an `info.json` describing how to decode
them. This change adds converters for both formats and makes the RTI viewer
example open any converted dataset.

## Summary of changes

| File | Change |
| --- | --- |
| `utils/convert_ptm.py` | New. Converts uncompressed `PTM_1.2` / `PTM_FORMAT_RGB` files (see [PTM.md](PTM.md)). |
| `tests/test_convert_ptm.py` | New. Unit tests for the PTM converter. |
| `utils/convert_hsh.py` | New. Converts HSH `.rti` files (RTIBuilder / RTIViewer format). |
| `utils/PTM.md` | New. PTM conversion guide. |
| `utils/RTI-CONVERSION.md` | New. This document. |
| `src/Layout.js`, `src/LayoutTiles.js`, `src/LayerRTI.js` | The `image` layout now uses the dataset's `format` (from `info.json`) as the file extension instead of always `.jpg`, so lossless PNG planes load. |
| `dist/examples/rti-viewer/index.html` | Shows one converted dataset, chosen with `?dataset=<name>` (default `missal_2500`). Replaces the four bundled coin samples. |
| `README.md` | Links to the PTM conversion guide. |
| `.gitignore` | Ignores `*.ptm`, `*.rti`, `RTI Test/`, `dist/assets/rti/converted/` and `.DS_Store`. |

## Usage

From the repository root:

```sh
python3 -m pip install Pillow numpy
python3 utils/convert_ptm.py "RTI Test" dist/assets/rti/converted --skip-existing
python3 utils/convert_hsh.py missal_2500.rti dist/assets/rti/converted
npm install && npm run rollup
python3 -m http.server 8080 --directory dist
```

Then open http://localhost:8080/examples/rti-viewer/?dataset=missal_2500
(or `?dataset=sccoin00301B-PTM18`, etc. — the name is the converted folder).

The viewer starts with dragging controlling the light. Press **L** (or the
light button) to switch to panning, and zoom in first. RTI is a single fixed
viewpoint with movable lighting, so the object cannot be rotated in 3D.

## HSH `.rti` format notes

`convert_hsh.py` reads the text header

```
#HSH1.2
3                      # RTI type (3 = HSH)
<width> <height> 3     # 3 colour bands
<terms> <basis> 1      # 4 or 9 terms, 1 byte per coefficient
```

followed by `terms` float32 scales, `terms` float32 biases, and one byte per
pixel × band × term (terms innermost). A coefficient is
`byte / 255 * scale + bias`; OpenLIME computes `(byte / 255 - b) * s`, so the
converter writes `s = scale` and `b = -bias / scale`.

Each term becomes one RGB PNG (`plane_<term>.png`), and `info.json` uses
`type: 'hsh'`, `colorspace: 'rgb'` and `nplanes = terms × 3`. OpenLIME's HSH
basis uses the same term order as RTIViewer.

Rows are written as stored, without the vertical flip the PTM converter
applies. This was checked on `missal_2500.rti` using a calibration sphere:
the y-gradient coefficient is positive on the sphere's top edge in file
order, matching OpenLIME's "+y is up" light direction.

## Limitations

- Only HSH `.rti` files with 3 bands and 1-byte coefficients are supported;
  other RTI types (PTM-in-RTI, SH, compressed) are rejected.
- 4-term (first-order) HSH files produce soft shading; specular highlights
  cannot be represented.
- Converted datasets are uncompressed PNGs and are large (about 1.4 GB for
  the 50 test coins plus the missal), so they are git-ignored.
- The viewer example now depends on locally converted data. A fresh clone
  needs to run the converters before the example shows anything.
