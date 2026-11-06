"""Check byte preservation, orientation, and relighting against PTM's equation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

from PIL import Image

spec = importlib.util.spec_from_file_location(
    'convert_ptm', Path(__file__).resolve().parents[1] / 'utils/convert_ptm.py')
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class ConversionTest(unittest.TestCase):
    def test_relighting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'sample.ptm'
            scales = [0.4, 0.6, 0.8, 1.2, 1.4, 1.6]
            biases = [120, -12, 70, 80, 90, 100]
            # Includes whitespace-valued coefficients at the payload boundary.
            payload = bytes((10 + c * 61 + p * 17 + k * 7) % 256
                            for c in range(3) for p in range(4) for k in range(6))
            source.write_bytes(b'PTM_1.2\r\nPTM_FORMAT_RGB\r\n2 2\r\n'
                               b'0.4 0.6 0.8 1.2 1.4 1.6\r\n'
                               b'120 -12 70 80 90 100\r\n' + payload)
            info = converter.convert(source, root / 'result')
            planes = [Image.open(root / 'result' / f'plane_{i}.png')
                      for i in range(6)]
            material = info['materials'][0]
            for y in range(2):
                for x in range(2):
                    pixel = (1-y)*2+x
                    for channel in range(3):
                        raw = payload[channel*24+pixel*6:channel*24+pixel*6+6]
                        for lx, ly in [(0, 0), (0.3, -0.5), (-0.7, 0.2)]:
                            weights = [lx*lx, ly*ly, lx*ly, lx, ly, 1]
                            expected = sum((raw[k]-biases[k])*scales[k]*weights[k]
                                           for k in range(6))/255
                            weights_gl = [1, lx, ly, lx*lx, lx*ly, ly*ly]
                            actual = sum((planes[i].getpixel((x, y))[channel]/255
                                          - material['bias'][3*i+channel])
                                         * material['scale'][3*i+channel]*weights_gl[i]
                                         for i in range(6))
                            self.assertAlmostEqual(actual, expected, places=12)
            for plane in planes:
                plane.close()
            with self.assertRaises(ValueError):
                converter.convert(source, root / 'result')
            source.write_bytes(source.read_bytes()[:-1])
            with self.assertRaises(ValueError):
                converter.convert(source, root / 'truncated')


if __name__ == '__main__':
    unittest.main()
