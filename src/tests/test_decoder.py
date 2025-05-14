import unittest
from PIL import Image, ImageDraw
import numpy as np
import src.core.decoder as decoder
import os

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

    def test_integration_encode_rotate90_decode(self):
        import src.core.encoder as encoder
        import src.core.image_utils as image_utils
        import src.core.protocol_config as pc
        # Compatibilité V1/V2
        if hasattr(pc, 'DEFAULT_CELL_PIXEL_SIZE'):
            cell_size = pc.DEFAULT_CELL_PIXEL_SIZE
        else:
            cell_size = pc.get_protocol_config('V2_S')['DEFAULT_CELL_PIXEL_SIZE']
        if hasattr(pc, 'MATRIX_DIM'):
            matrix_dim = pc.MATRIX_DIM
        else:
            matrix_dim = pc.get_protocol_config('V2_S')['MATRIX_DIM']
        message = "ROTATION"
        # 1. Encoder le message
        bit_matrix = encoder.encode_message_to_matrix(message, pc.DEFAULT_ECC_LEVEL_PERCENT)
        # 2. Générer l'image
        tmp_path = 'test_rotation_tmp.png'
        image_utils.create_protocol_image(bit_matrix, cell_size, tmp_path)
        from PIL import Image
        img = Image.open(tmp_path)
        # 3. Tourner l'image de 90°
        img_rot = img.rotate(90, expand=False)
        # 4. Détection FP
        centers = decoder.detect_finder_patterns(img_rot)
        corners = decoder.identify_fp_corners(centers)
        angle = decoder.compute_rotation_angle(corners)
        # 5. Rotation inverse pour redresser
        img_redress = decoder.rotate_image(img_rot, -angle)
        # DEBUG: Sauvegarder l'image redressée pour inspection
        img_redress.save('debug_img_redress.png')
        # 6. Redétecter FP sur l'image redressée
        centers2 = decoder.detect_finder_patterns(img_redress)
        corners2 = decoder.identify_fp_corners(centers2)
        # 7. Estimer la taille de cellule
        cell_size_est = cell_size  # Utiliser la valeur d'origine pour garantir la cohérence
        # 8. Calibration couleurs
        calibration_map = decoder.perform_color_calibration(img_redress, int(round(cell_size_est)))
        # 9. Extraction de la grille
        bit_matrix2 = decoder.extract_bit_matrix_from_rotated_image(
            img_redress, corners2, cell_size_est, matrix_dim, calibration_map)
        # 10. Décodage (pipeline normal)
        metadata_stream = decoder.extract_metadata_stream(bit_matrix2)
        payload_stream = decoder.extract_payload_stream(bit_matrix2)
        parsed_metadata = decoder.dp.parse_metadata_bits(metadata_stream)
        encrypted_message_bits = payload_stream[:parsed_metadata['message_encrypted_len']]
        received_ecc_bits = payload_stream[parsed_metadata['message_encrypted_len']:]
        is_ecc_valid = decoder.dp.verify_simple_ecc(encrypted_message_bits, received_ecc_bits)
        self.assertTrue(is_ecc_valid)
        padded_message_bits = decoder.dp.apply_xor_cipher(encrypted_message_bits, parsed_metadata['xor_key'])
        decoded_message = decoder.dp.padded_bits_to_text(padded_message_bits)
        self.assertEqual(decoded_message, message)
        # Nettoyer le fichier temporaire
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    def test_get_tp_line_coords(self):
        # Grille 7x7, FP TL à (0,0), TR à (60,0), BL à (0,60), cell_size=10
        fp_corners = {'TL': (0,0), 'TR': (60,0), 'BL': (0,60)}
        cell_size = 10
        matrix_dim = 7
        fp_size = 7
        coords = decoder.get_tp_line_coords(fp_corners, cell_size, matrix_dim, fp_size)
        # TP_H doit commencer à (0,60) et finir à (60,60)
        self.assertAlmostEqual(coords['TP_H'][0][0], 0)
        self.assertAlmostEqual(coords['TP_H'][0][1], 60)
        self.assertAlmostEqual(coords['TP_H'][1][0], 60)
        self.assertAlmostEqual(coords['TP_H'][1][1], 60)
        # TP_V doit commencer à (60,0) et finir à (60,60)
        self.assertAlmostEqual(coords['TP_V'][0][0], 60)
        self.assertAlmostEqual(coords['TP_V'][0][1], 0)
        self.assertAlmostEqual(coords['TP_V'][1][0], 60)
        self.assertAlmostEqual(coords['TP_V'][1][1], 60)

    def test_sample_tp_profile(self):
        from src.core.decoder import sample_tp_profile
        from src.core.image_utils import sample_line_profile
        # Créer une image 21x7 avec une TP horizontale alternant noir/blanc sur la ligne 3
        width, height = 21, 7
        img = Image.new('RGB', (width, height), (255,255,255))
        y_tp = 3
        for x in range(width):
            color = (0,0,0) if (x//3)%2 == 0 else (255,255,255)
            img.putpixel((x, y_tp), color)
        # Coords de la TP : de (0,3) à (20,3)
        tp_coords = ((0, y_tp), (width-1, y_tp))
        num_samples = width
        profile = sample_tp_profile(img, tp_coords, num_samples)
        expected = [(0,0,0) if (x//3)%2 == 0 else (255,255,255) for x in range(width)]
        self.assertEqual(profile, expected)

    def test_detect_tp_transitions(self):
        from src.core.decoder import detect_tp_transitions
        # Profil alternant 3 noirs, 3 blancs, 3 noirs, 3 blancs...
        profile = []
        for i in range(24):
            if (i//3)%2 == 0:
                profile.append((0,0,0))
            else:
                profile.append((255,255,255))
        transitions = detect_tp_transitions(profile, threshold=10)
        # On s'attend à une transition tous les 3 pixels
        expected = [3,6,9,12,15,18,21]
        self.assertEqual(transitions, expected)

    def test_interpolate_grid_positions(self):
        from src.core.decoder import interpolate_grid_positions
        # Transitions régulières tous les 10 pixels pour 5 cellules : [0,10,20,30,40,50]
        transitions = [0,10,20,30,40,50]
        num_cells = 5
        positions = interpolate_grid_positions(transitions, num_cells)
        expected = [5,15,25,35,45]
        for p, e in zip(positions, expected):
            self.assertAlmostEqual(p, e)
        # Cas transitions manquantes (extrapolation)
        transitions = [0,50]
        positions = interpolate_grid_positions(transitions, num_cells)
        expected = [5,15,25,35,45]
        for p, e in zip(positions, expected):
            self.assertAlmostEqual(p, e)

    def test_extract_bit_matrix_with_tp(self):
        from src.core.decoder import extract_bit_matrix_with_tp
        from src.core.image_utils import bits_to_rgb
        # Créer une image 24x24 avec une grille 4x4, cellules irrégulières
        img = Image.new('RGB', (24, 24), (255,255,255))
        # Définir les positions des centres de colonnes et lignes
        x_positions = [4, 8, 15, 19]
        y_positions = [5, 10, 16, 20]
        # Remplir chaque cellule avec une couleur différente
        bit_matrix_ref = [['00','01','10','11'], ['01','10','11','00'], ['10','11','00','01'], ['11','00','01','10']]
        for i, y in enumerate(y_positions):
            for j, x in enumerate(x_positions):
                color = bits_to_rgb(bit_matrix_ref[i][j])
                for dx in range(-2,3):
                    for dy in range(-2,3):
                        xx = int(round(x))+dx
                        yy = int(round(y))+dy
                        if 0 <= xx < 24 and 0 <= yy < 24:
                            img.putpixel((xx,yy), color)
        calibration_map = {
            '00': (255,255,255),
            '01': (0,0,0),
            '10': (255,0,0),
            '11': (0,0,255)
        }
        bit_matrix = extract_bit_matrix_with_tp(img, x_positions, y_positions, calibration_map)
        self.assertEqual(bit_matrix, bit_matrix_ref)

if __name__ == '__main__':
    unittest.main() 