# Viewing your PTM files

`convert_ptm.py` supports the uncompressed `PTM_1.2` / `PTM_FORMAT_RGB`
files in `RTI Test`. It preserves the coefficient bytes in six lossless PNGs,
flips the bottom-up rows, and translates coefficient ordering and scale/bias
metadata for OpenLIME. Other PTM encodings are rejected.

From the repository root:

```sh
python3 -m pip install Pillow
python3 utils/convert_ptm.py "RTI Test/sccoin00301B-PTM18.ptm" dist/assets/rti/converted
npm install
npm run rollup
python3 -m http.server 8080 --directory dist
```

Open http://localhost:8080/examples/rti-viewer/ to view the sample coin.
Drag the light control to change illumination; use the toolbar to zoom.
The example enables automatic light rotation after inactivity.

To convert all 50 files instead, use:

```sh
python3 utils/convert_ptm.py "RTI Test" dist/assets/rti/converted --skip-existing
```

Each file gets a directory named after its filename without `.ptm`. Existing
output directories are protected against overwriting; `--skip-existing` leaves
them untouched (it does not check their contents). Batch conversion stops on the first error;
previously completed datasets remain available. PNG datasets can be large.

To open a dataset, add `?dataset=<folder name>` to the viewer URL, e.g.
http://localhost:8080/examples/rti-viewer/?dataset=sccoin00302A-PTM18. The source files have no
physical pixel size metadata, so the converter does not invent a scale in mm.

Run converter checks with:

```sh
python3 -m unittest discover -s tests -p 'test_convert_ptm.py'
```

Format reference: [HP's PTM 1.2 specification](https://shiftleft.com/mirrors/www.hpl.hp.com/research/ptm/downloads/PtmFormat12.pdf).
