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
        self.assertEqual(len(centers), 3, "Expected exactly 3 finder patterns to be detected")
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

    def test_identify_fp_corners(self):
        # Centres dans l'ordre TL, TR, BL
        fp_size = 70
        size = 350
        TL = (fp_size//2, fp_size//2)
        TR = (size-fp_size//2-1, fp_size//2)
        BL = (fp_size//2, size-fp_size//2-1)
        centers = [TL, TR, BL]
        corners = decoder.identify_fp_corners(centers)
        self.assertEqual(corners['TL'], TL)
        self.assertEqual(corners['TR'], TR)
        self.assertEqual(corners['BL'], BL)
        # Image tournée de 90° (TR devient TL, BL devient TR, TL devient BL)
        centers_rot = [TR, BL, TL]
        corners_rot = decoder.identify_fp_corners(centers_rot)
        self.assertEqual(set(corners_rot.values()), set([TL, TR, BL]))
        # TL doit être le plus proche des deux autres
        dists = [sum(np.linalg.norm(np.array(c)-np.array(o)) for o in centers_rot if o!=c) for c in centers_rot]
        min_idx = int(np.argmin(dists))
        self.assertEqual(corners_rot['TL'], centers_rot[min_idx])

    def test_compute_rotation_angle(self):
        # TL à gauche, TR à droite (horizontal)
        TL = (10, 10)
        TR = (110, 10)
        BL = (10, 110)
        corners = {'TL': TL, 'TR': TR, 'BL': BL}
        angle = decoder.compute_rotation_angle(corners)
        self.assertAlmostEqual(angle, 0, delta=1)
        # TL en haut, TR en bas (vertical)
        TL2 = (10, 10)
        TR2 = (10, 110)
        BL2 = (110, 10)
        corners2 = {'TL': TL2, 'TR': TR2, 'BL': BL2}
        angle2 = decoder.compute_rotation_angle(corners2)
        self.assertAlmostEqual(angle2, 90, delta=1)
        # TL à droite, TR à gauche (180°)
        TL3 = (110, 10)
        TR3 = (10, 10)
        BL3 = (110, 110)
        corners3 = {'TL': TL3, 'TR': TR3, 'BL': BL3}
        angle3 = decoder.compute_rotation_angle(corners3)
        self.assertAlmostEqual(abs(angle3), 180, delta=1)
        # TL en bas, TR en haut (270° ou -90°)
        TL4 = (10, 110)
        TR4 = (10, 10)
        BL4 = (110, 110)
        corners4 = {'TL': TL4, 'TR': TR4, 'BL': BL4}
        angle4 = decoder.compute_rotation_angle(corners4)
        self.assertAlmostEqual(abs(angle4), 90, delta=1)

    def test_rotate_image(self):
        # Image blanche avec carré noir en haut à gauche
        size = 100
        img = Image.new('RGB', (size, size), (255,255,255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0,0,29,29], fill=(0,0,0))
        # Tourner de 90°
        img_rot = decoder.rotate_image(img, 90)
        arr = np.array(img_rot)
        # Le carré noir doit être en haut à droite
        # Zone attendue : [0:30, 70:100]
        black_zone = arr[0:30, 70:100]
        white_zone = arr[0:30, 0:30]
        self.assertTrue(np.mean(black_zone) < 50)  # Noir
        self.assertTrue(np.mean(white_zone) > 200) # Blanc

    def test_estimate_cell_size_from_fp(self):
        # 7x7 cellules, donc 6 intervalles entre TL et TR/BL
        matrix_dim = 7
        TL = (10, 10)
        TR = (70, 10)
        BL = (10, 70)
        corners = {'TL': TL, 'TR': TR, 'BL': BL}
        cell_size = decoder.estimate_cell_size_from_fp(corners, matrix_dim)
        expected = 60/6  # (70-10)/6
        self.assertAlmostEqual(cell_size, expected, delta=0.5)
        # Cas non carré
        TR2 = (100, 10)
        BL2 = (10, 70)
        corners2 = {'TL': TL, 'TR': TR2, 'BL': BL2}
        cell_size2 = decoder.estimate_cell_size_from_fp(corners2, matrix_dim)
        expected2 = ((90)+(60))/2/6
        self.assertAlmostEqual(cell_size2, expected2, delta=0.5)

if __name__ == '__main__':
    unittest.main() 