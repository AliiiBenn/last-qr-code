import unittest
import src.core.protocol_config as pc
import src.core.matrix_layout as ml
import src.core.encoder as en # 'en' pour encoder
import src.core.data_processing as dp # Ajouté pour utiliser les fonctions de data_processing dans les tests si besoin

class TestEncoder(unittest.TestCase):

    def setUp(self):
        # Réinitialiser les caches de matrix_layout si nécessaire
        ml._zone_coords_cache = {}
        ml._all_defined_zones_cache = None
        self.expected_matrix_dim = pc.MATRIX_DIM
        # S'assurer que la config des métadonnées est celle attendue pour les calculs de taille
        self.assertEqual(pc.METADATA_CONFIG['total_bits'], 104)
        self.assertEqual(pc.METADATA_CONFIG['protection_bits'], 52)
        self.assertEqual(pc.METADATA_CONFIG['key_bits'], 16)

    def test_initialize_bit_matrix(self):
        bit_matrix = en.initialize_bit_matrix()
        self.assertEqual(len(bit_matrix), self.expected_matrix_dim, "Matrix should have MATRIX_DIM rows.")
        for row in bit_matrix:
            self.assertEqual(len(row), self.expected_matrix_dim, "Each row should have MATRIX_DIM columns.")
            for cell in row:
                self.assertIsNone(cell, "Initial cell value should be None.")

    def test_populate_fixed_zones(self):
        bit_matrix = en.initialize_bit_matrix()
        populated_matrix = en.populate_fixed_zones(bit_matrix)
        self.assertIs(populated_matrix, bit_matrix, "populate_fixed_zones should modify the matrix in-place.")
        manual_fixed_zone_count = 0
        for r in range(self.expected_matrix_dim):
            for c in range(self.expected_matrix_dim):
                zone_type = ml.get_cell_zone_type(r, c)
                cell_value = populated_matrix[r][c]
                if zone_type == 'METADATA_AREA' or zone_type == 'DATA_ECC':
                    self.assertIsNone(cell_value, 
                                      f"Cell ({r},{c}) of type {zone_type} should be None after populate_fixed_zones.")
                else: 
                    self.assertIsNotNone(cell_value, 
                                         f"Cell ({r},{c}) of type {zone_type} should NOT be None.")
                    self.assertIsInstance(cell_value, str) 
                    self.assertEqual(len(cell_value), pc.BITS_PER_CELL)
                    manual_fixed_zone_count += 1
                    relative_r, relative_c = -1, -1
                    if zone_type.startswith('FP_TL'):
                        base_coords = ml.get_zone_coordinates('FP_TL')
                        if 'CORE' in zone_type: core_coords = ml.get_zone_coordinates('FP_TL_CORE'); relative_r, relative_c = r - core_coords[0], c - core_coords[2]
                        else: relative_r, relative_c = r - base_coords[0], c - base_coords[2]
                    elif zone_type.startswith('FP_TR'):
                        base_coords = ml.get_zone_coordinates('FP_TR')
                        if 'CORE' in zone_type: core_coords = ml.get_zone_coordinates('FP_TR_CORE'); relative_r, relative_c = r - core_coords[0], c - core_coords[2]
                        else: relative_r, relative_c = r - base_coords[0], c - base_coords[2]
                    elif zone_type.startswith('FP_BL'):
                        base_coords = ml.get_zone_coordinates('FP_BL')
                        if 'CORE' in zone_type: core_coords = ml.get_zone_coordinates('FP_BL_CORE'); relative_r, relative_c = r - core_coords[0], c - core_coords[2]
                        else: relative_r, relative_c = r - base_coords[0], c - base_coords[2]
                    elif zone_type == 'TP_H':
                        tp_h_coords = ml.get_zone_coordinates('TP_H'); relative_r, relative_c = r - tp_h_coords[0], c - tp_h_coords[2]
                    elif zone_type == 'TP_V':
                        tp_v_coords = ml.get_zone_coordinates('TP_V'); relative_r, relative_c = r - tp_v_coords[0], c - tp_v_coords[2]
                    elif zone_type.startswith('CCP_PATCH_'):
                        patch_coords = ml.get_zone_coordinates(zone_type); relative_r, relative_c = r - patch_coords[0], c - patch_coords[2]
                    expected_bits = ml.get_fixed_pattern_bits(zone_type, relative_r, relative_c)
                    self.assertEqual(cell_value, expected_bits,
                                     f"Cell ({r},{c}) of type {zone_type} has bits {cell_value}, expected {expected_bits}.")
        self.assertGreater(manual_fixed_zone_count, 0)

    def test_encode_message_to_matrix_simple(self):
        message = "Hello"
        ecc_percent = 20
        
        # Exécuter l'encodage
        bit_matrix = en.encode_message_to_matrix(message, ecc_percent)

        self.assertEqual(len(bit_matrix), self.expected_matrix_dim)
        self.assertEqual(len(bit_matrix[0]), self.expected_matrix_dim)

        # Vérifier que toutes les cellules sont remplies
        none_cells_count = 0
        for r in range(self.expected_matrix_dim):
            for c in range(self.expected_matrix_dim):
                zone_type = ml.get_cell_zone_type(r, c)
                if zone_type == 'METADATA_AREA':
                    continue  # Les cellules METADATA_AREA sont remplies séparément
                self.assertIsNotNone(bit_matrix[r][c], f"Cell ({r},{c}) should be filled.")
                self.assertIsInstance(bit_matrix[r][c], str)
                self.assertEqual(len(bit_matrix[r][c]), pc.BITS_PER_CELL)
                if bit_matrix[r][c] is None:
                    none_cells_count +=1
        self.assertEqual(none_cells_count,0, "No cells should be None after full encoding (hors METADATA_AREA).")

        # Des vérifications plus approfondies pourraient impliquer de décoder les métadonnées
        # et de vérifier le payload, mais cela anticipe les phases de décodage.
        # Pour l'instant, on s'assure que le processus se termine et remplit la matrice.

    def test_encode_message_to_matrix_custom_key(self):
        message = "TestKey"
        ecc_percent = 10
        custom_key = dp.generate_xor_key(pc.METADATA_CONFIG['key_bits']) # Utiliser la bonne longueur
        
        bit_matrix = en.encode_message_to_matrix(message, ecc_percent, custom_xor_key_str=custom_key)
        self.assertEqual(len(bit_matrix), self.expected_matrix_dim)
        # Ici aussi, on pourrait essayer de décoder la clé des métadonnées pour la vérifier
        # Pour l'instant, on s'assure juste que ça ne crashe pas.

    def test_encode_message_to_matrix_ecc_levels(self):
        message = "Data"
        # Test avec 0% ECC
        bit_matrix_0_ecc = en.encode_message_to_matrix(message, 0)
        self.assertIsNotNone(bit_matrix_0_ecc)

        # Test avec un ECC élevé (ex: 50%).
        # Il faut s'assurer que cela ne cause pas d'erreur si l'espace pour le message devient trop petit.
        # La logique dans encode_message_to_matrix ajuste num_ecc_bits pour laisser de la place.
        try:
            bit_matrix_high_ecc = en.encode_message_to_matrix(message, 50)
            self.assertIsNotNone(bit_matrix_high_ecc)
            bit_matrix_max_ecc = en.encode_message_to_matrix(message, 100) # Peut-être 0 bit de données
            self.assertIsNotNone(bit_matrix_max_ecc)
        except ValueError as e:
            # Si le message est trop long même après ajustement de l'ECC, une ValueError peut être levée
            # par text_to_padded_bits. C'est un comportement attendu dans certains cas extrêmes.
            self.assertIn("Encoded text", str(e), "ValueError for message too long expected in extreme ECC cases.")

    def test_encode_message_to_matrix_value_errors(self):
        # ECC percent hors limites
        with self.assertRaisesRegex(ValueError, "ecc_level_percent must be between 0 and 100"):
            en.encode_message_to_matrix("test", -10)
        with self.assertRaisesRegex(ValueError, "ecc_level_percent must be between 0 and 100"):
            en.encode_message_to_matrix("test", 110)

        # Clé custom de mauvaise longueur
        with self.assertRaisesRegex(ValueError, "Custom XOR key length must be"):
            en.encode_message_to_matrix("test", 10, custom_xor_key_str="10101") # Trop court/long

        # Message trop long pour l'espace disponible (même avec 0% ECC)
        # Calculons approximativement l'espace max
        data_ecc_fill_order = ml.get_data_ecc_fill_order()
        available_data_ecc_bits = len(data_ecc_fill_order) * pc.BITS_PER_CELL
        # Si num_ecc_bits est 0, target_message_bit_length = available_data_ecc_bits
        # Un caractère = 8 bits. Donc max_chars ~ available_data_ecc_bits / 8
        max_chars = available_data_ecc_bits // 8
        long_message = "a" * (max_chars + 5) # Définitivement trop long
        with self.assertRaisesRegex(ValueError, "Encoded text .* is longer than target bit length"):
            en.encode_message_to_matrix(long_message, 0)

if __name__ == '__main__':
    unittest.main() 