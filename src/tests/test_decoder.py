import unittest
from PIL import Image, ImageDraw
import numpy as np
import src.core.decoder as decoder

class TestFinderPatternDetection(unittest.TestCase):
    def test_detect_finder_patterns_synthetic(self):
        # Créer une image blanche
        size = 350
        cell = 10
        img = Image.new('RGB', (size, size), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        # FP : 7x7 cellules = 70x70 px
        fp_size = 7 * cell
        # TL
        draw.rectangle([0, 0, fp_size-1, fp_size-1], fill=(0,0,0))
        # TR
        draw.rectangle([size-fp_size, 0, size-1, fp_size-1], fill=(0,0,0))
        # BL
        draw.rectangle([0, size-fp_size, fp_size-1, size-1], fill=(0,0,0))
        # Appel détection
        centers = decoder.detect_finder_patterns(img)
        # Centres attendus
        expected = [
            (fp_size//2, fp_size//2), # TL
            (size-fp_size//2-1, fp_size//2), # TR
            (fp_size//2, size-fp_size//2-1)  # BL
        ]
        # Vérifier que chaque centre détecté est proche d'un attendu
        for ec in expected:
            found = any(np.linalg.norm(np.array(ec)-np.array(c)) < cell*2 for c in centers)
            self.assertTrue(found, f"FP attendu {ec} non détecté dans {centers}")

if __name__ == '__main__':
    unittest.main() 