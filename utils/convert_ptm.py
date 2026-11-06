#!/usr/bin/env python3
"""Convert uncompressed PTM_1.2 RGB files to OpenLIME coefficient PNGs.

Install Pillow with: python3 -m pip install Pillow
Format specification: https://shiftleft.com/mirrors/www.hpl.hp.com/research/ptm/downloads/PtmFormat12.pdf
"""

import argparse
import json
import math
from pathlib import Path

from PIL import Image

# PTM: x*x, y*y, x*y, x, y, 1; OpenLIME: 1, x, y, x*x, x*y, y*y.
ORDER = (5, 3, 4, 0, 2, 1)


def read_ptm(path):
    path = Path(path)
    with Path(path).open('rb') as stream:
        if stream.readline().strip() != b'PTM_1.2':
            raise ValueError('Expected PTM_1.2')
        if stream.readline().strip() != b'PTM_FORMAT_RGB':
            raise ValueError('Only uncompressed PTM_FORMAT_RGB is supported')
        # Header fields can share lines or span multiple lines. Never strip the
        # binary payload: a coefficient byte may itself be ASCII whitespace.
        tokens = []
        while len(tokens) < 14:
            line = stream.readline(4096)
            if not line or not line.endswith(b'\n'):
                raise ValueError('Incomplete PTM header')
            tokens.extend(line.split())
        if len(tokens) != 14:
            raise ValueError('Expected dimensions, six scales and six biases')
        width, height = map(int, tokens[:2])
        scale = list(map(float, tokens[2:8]))
        bias = list(map(int, tokens[8:14]))
        if width <= 0 or height <= 0 or not all(map(math.isfinite, scale)):
            raise ValueError('Invalid dimensions or scales')
        expected = width * height * 18
        if path.stat().st_size - stream.tell() != expected:
            raise ValueError(f'Expected exactly {expected} coefficient bytes')
        data = stream.read(expected)
    return width, height, scale, bias, data


def convert(path, destination):
    path, destination = Path(path), Path(destination)
    width, height, scale, bias, data = read_ptm(path)
    if destination.exists():
        raise ValueError(f'Output already exists: {destination}')
    destination.mkdir(parents=True)
    pixels = width * height
    for plane, coefficient in enumerate(ORDER):
        channels = []
        for channel in range(3):
            start = channel * pixels * 6 + coefficient
            raw = data[start:(channel + 1) * pixels * 6:6]
            channels.append(Image.frombytes('L', (width, height), raw))
        image = Image.merge('RGB', channels).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        image.save(destination / f'plane_{plane}.png')
    # Textures and output colors use [0,1], whereas PTM uses byte intensities.
    # (byte/255 - bias/255)*scale == ((byte-bias)*scale)/255.
    info = {
        'width': width, 'height': height, 'format': 'png',
        'type': 'ptm', 'colorspace': 'rgb', 'nplanes': 18,
        'materials': [{
            'scale': [scale[i] for i in ORDER for _ in range(3)],
            'bias': [bias[i] / 255 for i in ORDER for _ in range(3)],
        }],
    }
    (destination / 'info.json').write_text(json.dumps(info, indent=2) + '\n')
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='A .ptm file or directory of .ptm files')
    parser.add_argument('output', type=Path, help='Parent directory for converted datasets')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip existing output directories when converting a batch')
    args = parser.parse_args()
    files = sorted(args.input.glob('*.ptm')) if args.input.is_dir() else [args.input]
    if not files:
        parser.error('No .ptm files found')
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
