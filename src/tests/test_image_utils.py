import unittest
import os
import tempfile
from PIL import Image, UnidentifiedImageError

import src.core.protocol_config as pc
import src.core.image_utils as iu
from src.core.matrix_layout import get_cell_zone_type, get_fixed_pattern_bits

class TestImageUtils(unittest.TestCase):

    def test_bits_to_rgb(self):
        self.assertEqual(iu.bits_to_rgb('00'), pc.BITS_TO_COLOR_MAP['00'])
        self.assertEqual(iu.bits_to_rgb('01'), pc.BITS_TO_COLOR_MAP['01'])
        self.assertEqual(iu.bits_to_rgb('10'), pc.BITS_TO_COLOR_MAP['10'])
        self.assertEqual(iu.bits_to_rgb('11'), pc.BITS_TO_COLOR_MAP['11'])
        
        # Test cas non trouvé: la fonction actuelle retourne pc.BLACK
        # (et imprime un avertissement, qui ne sera pas capturé ici)
        self.assertEqual(iu.bits_to_rgb('99'), pc.BLACK)
        self.assertEqual(iu.bits_to_rgb(None), pc.BLACK) # Si None est passé accidentellement

    def test_create_protocol_image(self):
        # Créer une bit_matrix exemple simple (3x2)
        # '00' -> WHITE, '01' -> BLACK, '10' -> RED, '11' -> BLUE
        sample_bit_matrix = [
            ['00', '01'],  # White, Black
            ['10', '11'],  # Red,   Blue
            [None, '00']   # White (par défaut pour None), White
        ]
        matrix_height = len(sample_bit_matrix)
        matrix_width = len(sample_bit_matrix[0])
        cell_pixel_size = 10
        expected_image_width = matrix_width * cell_pixel_size
        expected_image_height = matrix_height * cell_pixel_size

        # Créer un fichier temporaire pour l'image
        # tempfile.NamedTemporaryFile crée un fichier qui est supprimé à la fermeture.
        # Sur Windows, il ne peut pas être rouvert par son nom tant qu'il est ouvert.
        # Donc, nous allons générer un nom, le fermer, puis l'utiliser.
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_filename = temp_file.name
        temp_file.close() # Fermer pour que Pillow puisse écrire dedans

        try:
            iu.create_protocol_image(sample_bit_matrix, cell_pixel_size, temp_filename)
            
            self.assertTrue(os.path.exists(temp_filename), "L'image n'a pas été créée.")
            
            with Image.open(temp_filename) as img:
                self.assertEqual(img.width, expected_image_width, "Largeur de l'image incorrecte.")
                self.assertEqual(img.height, expected_image_height, "Hauteur de l'image incorrecte.")
                self.assertEqual(img.mode, "RGB", "Mode de l'image incorrect.")
                
                # Vérifier les couleurs de quelques pixels (au centre de chaque cellule)
                pixel_offset = cell_pixel_size // 2
                
                # (0,0) -> bits '00' -> WHITE
                self.assertEqual(img.getpixel((pixel_offset, pixel_offset)), pc.WHITE)
                # (0,1) -> bits '01' -> BLACK
                self.assertEqual(img.getpixel((1 * cell_pixel_size + pixel_offset, pixel_offset)), pc.BLACK)
                # (1,0) -> bits '10' -> RED
                self.assertEqual(img.getpixel((pixel_offset, 1 * cell_pixel_size + pixel_offset)), pc.RED)
                # (1,1) -> bits '11' -> BLUE
                self.assertEqual(img.getpixel((1 * cell_pixel_size + pixel_offset, 1 * cell_pixel_size + pixel_offset)), pc.BLUE)
                # (2,0) -> bits None -> WHITE (selon la logique actuelle dans create_protocol_image)
                self.assertEqual(img.getpixel((pixel_offset, 2 * cell_pixel_size + pixel_offset)), pc.WHITE)
                # (2,1) -> bits '00' -> WHITE
                self.assertEqual(img.getpixel((1 * cell_pixel_size + pixel_offset, 2 * cell_pixel_size + pixel_offset)), pc.WHITE)

        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename) # Nettoyer le fichier temporaire

    def test_create_protocol_image_empty_matrix(self):
        with self.assertRaises(ValueError):
            iu.create_protocol_image([], 10, "test_empty.png")
        with self.assertRaises(ValueError):
            iu.create_protocol_image([[]], 10, "test_empty_row.png")

    # Nouveaux tests pour la Phase 4
    def test_load_image_from_file(self):
        # Ce test suppose que l'image test_output_from_main.png existe
        # Il serait préférable de créer une image de test dédiée et plus petite ici
        # ou de la rendre optionnelle si le fichier n'existe pas.
        test_image_path = "images_generes/test_output_from_main.png"
        if not os.path.exists(test_image_path):
            self.skipTest(f"Image de test {test_image_path} non trouvée, test sauté.")
        
        image = iu.load_image_from_file(test_image_path)
        self.assertIsNotNone(image)
        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.mode, "RGB") # Vérifier la conversion en RGB

    def test_load_image_from_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            iu.load_image_from_file("chemin/vers/image_inexistante.png")

    def test_load_image_from_file_corrupted(self):
        # Créer un fichier temporaire non image
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_filename = temp_file.name
        temp_file.write(b"ceci n'est pas une image")
        temp_file.close()
        try:
            # Pillow < 9.0.0 lève UnidentifiedImageError qui hérite de IOError/OSError.
            # Pillow >= 9.0.0 peut toujours lever UnidentifiedImageError, mais Exception est plus large.
            with self.assertRaises(Exception): # Attendre une erreur générique de chargement
                iu.load_image_from_file(temp_filename)
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    def test_rgb_to_bits_exact_match(self):
        calibration_map = {
            '00': (255, 255, 255), # WHITE
            '01': (0, 0, 0),       # BLACK
            '10': (255, 0, 0),     # RED
            '11': (0, 0, 255)      # BLUE
        }
        self.assertEqual(iu.rgb_to_bits((255, 255, 255), calibration_map), '00')
        self.assertEqual(iu.rgb_to_bits((0, 0, 0), calibration_map), '01')
        self.assertEqual(iu.rgb_to_bits((255, 0, 0), calibration_map), '10')
        self.assertEqual(iu.rgb_to_bits((0, 0, 255), calibration_map), '11')

    def test_rgb_to_bits_closest_match(self):
        calibration_map = {
            '00': (250, 250, 250), # Presque blanc
            '01': (10, 10, 10),     # Presque noir
            '10': (240, 5, 5)       # Presque rouge
        }
        self.assertEqual(iu.rgb_to_bits((255, 255, 255), calibration_map), '00') # Plus proche de '00'
        self.assertEqual(iu.rgb_to_bits((0, 0, 0), calibration_map), '01')       # Plus proche de '01'
        self.assertEqual(iu.rgb_to_bits((250, 0, 0), calibration_map), '10')     # Plus proche de '10'
        # Un cas un peu plus ambigu
        self.assertEqual(iu.rgb_to_bits((100, 100, 100), calibration_map), '01') # Devrait être plus proche de (10,10,10) que de (250,250,250)

    def test_rgb_to_bits_empty_map(self):
        with self.assertRaises(ValueError):
            iu.rgb_to_bits((100, 100, 100), {})

    def test_sample_line_profile(self):
        # Créer une image 20x5 avec une ligne horizontale alternant noir/blanc
        width, height = 20, 5
        img = Image.new('RGB', (width, height), (255,255,255))
        for x in range(width):
            color = (0,0,0) if (x//2)%2 == 0 else (255,255,255)
            for y in range(height):
                img.putpixel((x, y), color)
        # Profil le long de la ligne centrale
        start_px = (0, height//2)
        end_px = (width-1, height//2)
        num_samples = width
        profile = iu.sample_line_profile(img, start_px, end_px, num_samples)
        # On s'attend à une alternance tous les 2 pixels
        expected = []
        for x in range(width):
            expected.append((0,0,0) if (x//2)%2 == 0 else (255,255,255))
        self.assertEqual(profile, expected)

    def test_fp_center_colors(self):
        # Générer une image 35x35 cellules, chaque cellule = 10px
        cell_px_size = 10
        matrix_dim = 35
        img_size = matrix_dim * cell_px_size
        img = Image.new('RGB', (img_size, img_size), pc.WHITE)
        # Remplir uniquement les FP
        for r in range(matrix_dim):
            for c in range(matrix_dim):
                zone = get_cell_zone_type(r, c)
                if 'FP_' in zone:
                    bits = get_fixed_pattern_bits(zone.replace('_MARGIN',''), r%7 if 'FP_' in zone else 0, c%7 if 'FP_' in zone else 0)
                    color = iu.bits_to_rgb(bits)
                    for dr in range(cell_px_size):
                        for dc in range(cell_px_size):
                            img.putpixel((c*cell_px_size+dc, r*cell_px_size+dr), color)
        # Vérifier la couleur centrale de chaque FP
        fp_coords = {
            'TL': (3, 3),
            'TR': (3, matrix_dim-4),
            'BL': (matrix_dim-4, 3)
        }
        expected = pc.FP_CONFIG['center_colors']
        for label, (r, c) in fp_coords.items():
            px = c*cell_px_size + cell_px_size//2
            py = r*cell_px_size + cell_px_size//2
            rgb = img.getpixel((px, py))
            self.assertEqual(rgb, expected[label], f"FP {label} centre: attendu {expected[label]}, obtenu {rgb}")

if __name__ == '__main__':
    unittest.main() 