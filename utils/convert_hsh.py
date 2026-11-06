#!/usr/bin/env python3
"""Convert HSH .rti files (RTIBuilder / RTIViewer format) to OpenLIME coefficient PNGs.

Install dependencies with: python3 -m pip install Pillow numpy
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def read_header_line(stream):
    """Read the next non-comment header line."""
    while True:
        line = stream.readline(4096)
        if not line:
            raise ValueError('Incomplete RTI header')
        if not line.startswith(b'#'):
            return line.split()


def read_hsh(path):
    path = Path(path)
    with path.open('rb') as stream:
        if not stream.readline(4096).startswith(b'#HSH'):
            raise ValueError('Expected an HSH .rti file (#HSH header)')
        if int(read_header_line(stream)[0]) != 3:
            raise ValueError('Only HSH (type 3) RTI files are supported')
        width, height, bands = map(int, read_header_line(stream)[:3])
        terms, _basis, elem_size = map(int, read_header_line(stream)[:3])
        if bands != 3 or elem_size != 1 or terms not in (4, 9):
            raise ValueError(f'Unsupported layout: bands={bands} terms={terms} element size={elem_size}')
        scale = np.frombuffer(stream.read(4 * terms), '<f4')
        bias = np.frombuffer(stream.read(4 * terms), '<f4')
        expected = width * height * bands * terms
        if path.stat().st_size - stream.tell() != expected:
            raise ValueError(f'Expected exactly {expected} coefficient bytes')
        # Per pixel: for each colour band, all terms. Rows are stored top-down.
        data = np.frombuffer(stream.read(expected), np.uint8).reshape(height, width, bands, terms)
    return width, height, terms, scale, bias, data


def convert(path, destination):
    path, destination = Path(path), Path(destination)
    width, height, terms, scale, bias, data = read_hsh(path)
    if destination.exists():
        raise ValueError(f'Output already exists: {destination}')
    destination.mkdir(parents=True)
    # One RGB plane per HSH term.
    for term in range(terms):
        Image.fromarray(np.ascontiguousarray(data[:, :, :, term]), 'RGB').save(destination / f'plane_{term}.png')
    # RTI: value = byte/255 * scale + bias. OpenLIME: (byte/255 - b) * s.
    info = {
        'width': width, 'height': height, 'format': 'png',
        'type': 'hsh', 'colorspace': 'rgb', 'nplanes': terms * 3,
        'materials': [{
            'scale': [float(scale[t]) for t in range(terms) for _ in range(3)],
            'bias': [float(-bias[t] / scale[t]) for t in range(terms) for _ in range(3)],
        }],
    }
    (destination / 'info.json').write_text(json.dumps(info, indent=2) + '\n')
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='An .rti file or directory of .rti files')
    parser.add_argument('output', type=Path, help='Parent directory for converted datasets')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip existing output directories when converting a batch')
    args = parser.parse_args()
    files = sorted(args.input.glob('*.rti')) if args.input.is_dir() else [args.input]
    if not files:
        parser.error('No .rti files found')
    for path in files:
        if args.skip_existing and (args.output / path.stem).exists():
            print(f'Skipping existing output: {path.stem}')
            continue
        try:
            info = convert(path, args.output / path.stem)
        except (ValueError, OSError) as error:
            parser.exit(1, f'{path}: {error}\n')
        print(f'{path.name}: {info["width"]} x {info["height"]} -> {args.output / path.stem}')


if __name__ == '__main__':
    main()
