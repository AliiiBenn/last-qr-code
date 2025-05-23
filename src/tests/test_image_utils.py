import unittest
import os
import tempfile
from PIL import Image, UnidentifiedImageError

import src.core.protocol_config as pc
import src.core.image_utils as iu

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

if __name__ == '__main__':
    unittest.main() 