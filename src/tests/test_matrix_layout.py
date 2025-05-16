import unittest
import src.core.protocol_config as pc
import src.core.matrix_layout as ml

class TestMatrixLayout(unittest.TestCase):

    def setUp(self):
        # Réinitialiser le cache pour chaque test pour assurer l'indépendance des tests
        ml._zone_coords_cache = {}
        ml._all_defined_zones_cache = None
        # S'assurer que MATRIX_DIM est bien 35 comme attendu par les coordonnées codées en dur dans les tests
        self.assertEqual(pc.MATRIX_DIM, 35)
        self.assertEqual(pc.FP_CONFIG['size'], 7)
        self.assertEqual(pc.FP_CONFIG['margin'], 1)
        self.assertEqual(pc.METADATA_CONFIG['rows'], 6)
        self.assertEqual(pc.METADATA_CONFIG['cols'], 6)
        self.assertEqual(pc.CCP_CONFIG['patch_size'], 2)


    def test_get_zone_coordinates(self):
        # Finder Patterns (FP)
        self.assertEqual(ml.get_zone_coordinates('FP_TL'), (0, 6, 0, 6))
        self.assertEqual(ml.get_zone_coordinates('FP_TR'), (0, 6, 28, 34))
        self.assertEqual(ml.get_zone_coordinates('FP_BL'), (28, 34, 0, 6))

        # FP Cores
        self.assertEqual(ml.get_zone_coordinates('FP_TL_CORE'), (1, 5, 1, 5)) # 7-1-1 = 5, so 1 to 5
        self.assertEqual(ml.get_zone_coordinates('FP_TR_CORE'), (1, 5, 29, 33))
        self.assertEqual(ml.get_zone_coordinates('FP_BL_CORE'), (29, 33, 1, 5))

        # Timing Patterns (TP)
        # TP_H: row = 6, col = 7 to 34-1-7 = 27 (35 - 1 - 7 = 27)
        self.assertEqual(ml.get_zone_coordinates('TP_H'), (6, 6, 7, 27))
        # TP_V: row = 7 to 27, col = 6
        self.assertEqual(ml.get_zone_coordinates('TP_V'), (7, 27, 6, 6))

        # Metadata Area
        # rows=6, cols=6. c_start = 35 - 7 - 6 = 22.
        # (r_start, r_end, c_start, c_end) -> (0, 5, 22, 27)
        self.assertEqual(ml.get_zone_coordinates('METADATA_AREA'), (0, 5, 22, 27))

        # Calibration Color Patches (CCP)
        # patch_size = 2. r_start = 35-7 = 28.
        # Patch 0: c_start = 7 + (0*2) = 7. (28, 29, 7, 8)
        # Patch 1: c_start = 7 + (1*2) = 9. (28, 29, 9, 10)
        # Patch 2: c_start = 7 + (2*2) = 11. (28, 29, 11, 12)
        # Patch 3: c_start = 7 + (3*2) = 13. (28, 29, 13, 14)
        self.assertEqual(ml.get_zone_coordinates('CCP_PATCH_0'), (28, 29, 7, 8))
        self.assertEqual(ml.get_zone_coordinates('CCP_PATCH_1'), (28, 29, 9, 10))
        self.assertEqual(ml.get_zone_coordinates('CCP_PATCH_2'), (28, 29, 11, 12))
        self.assertEqual(ml.get_zone_coordinates('CCP_PATCH_3'), (28, 29, 13, 14))
        
        ccp_area_coords = ml.get_zone_coordinates('CCP_AREA')
        self.assertIsInstance(ccp_area_coords, list)
        self.assertEqual(len(ccp_area_coords), len(pc.CCP_CONFIG['colors']))
        self.assertEqual(ccp_area_coords[0], (28, 29, 7, 8))

        with self.assertRaises(ValueError):
            ml.get_zone_coordinates('UNKNOWN_ZONE')

    def test_get_cell_zone_type(self):
        # FP Cores
        self.assertEqual(ml.get_cell_zone_type(1, 1), 'FP_TL_CORE')      # TL Core
        self.assertEqual(ml.get_cell_zone_type(3, 3), 'FP_TL_CORE')      # Center of TL Core
        self.assertEqual(ml.get_cell_zone_type(1, 29), 'FP_TR_CORE')     # TR Core
        self.assertEqual(ml.get_cell_zone_type(29, 1), 'FP_BL_CORE')     # BL Core

        # FP Margins
        self.assertEqual(ml.get_cell_zone_type(0, 0), 'FP_TL_MARGIN')      # TL Margin
        self.assertEqual(ml.get_cell_zone_type(0, 34), 'FP_TR_MARGIN')     # TR Margin
        self.assertEqual(ml.get_cell_zone_type(34, 0), 'FP_BL_MARGIN')     # BL Margin
        self.assertEqual(ml.get_cell_zone_type(6, 0), 'FP_TL_MARGIN')

        # Timing Patterns
        self.assertEqual(ml.get_cell_zone_type(6, 7), 'TP_H')          # Start of TP_H
        self.assertEqual(ml.get_cell_zone_type(6, 27), 'TP_H')         # End of TP_H
        self.assertEqual(ml.get_cell_zone_type(7, 6), 'TP_V')          # Start of TP_V
        self.assertEqual(ml.get_cell_zone_type(27, 6), 'TP_V')         # End of TP_V

        # Metadata Area
        self.assertEqual(ml.get_cell_zone_type(0, 22), 'METADATA_AREA') # Start of Metadata
        self.assertEqual(ml.get_cell_zone_type(5, 27), 'METADATA_AREA') # End of Metadata
        self.assertEqual(ml.get_cell_zone_type(2, 25), 'METADATA_AREA') # Middle of Metadata

        # CCP Patches
        self.assertEqual(ml.get_cell_zone_type(28, 7), 'CCP_PATCH_0')
        self.assertEqual(ml.get_cell_zone_type(29, 8), 'CCP_PATCH_0')
        self.assertEqual(ml.get_cell_zone_type(28, 13), 'CCP_PATCH_3')
        self.assertEqual(ml.get_cell_zone_type(29, 14), 'CCP_PATCH_3')

        # Data/ECC Area (example points)
        self.assertEqual(ml.get_cell_zone_type(10, 10), 'DATA_ECC')
        self.assertEqual(ml.get_cell_zone_type(0, 7), 'DATA_ECC') # Between FP_TL and TP_H start, but not metadata
        self.assertEqual(ml.get_cell_zone_type(7,0), 'DATA_ECC') # Between FP_TL and TP_V start
        self.assertEqual(ml.get_cell_zone_type(7,7), 'DATA_ECC') # Center-ish area

    def test_get_fixed_pattern_bits(self):
        # FP_TL_CORE (centre doit être ROUGE)
        self.assertEqual(ml.get_fixed_pattern_bits('FP_TL_CORE', 2, 2), pc.COLOR_TO_BITS_MAP[pc.FP_CONFIG['center_colors']['TL']])
        # FP_TR_CORE (centre doit être BLEU)
        self.assertEqual(ml.get_fixed_pattern_bits('FP_TR_CORE', 2, 2), pc.COLOR_TO_BITS_MAP[pc.FP_CONFIG['center_colors']['TR']])
        # FP_BL_CORE (centre doit être NOIR)
        self.assertEqual(ml.get_fixed_pattern_bits('FP_BL_CORE', 2, 2), pc.COLOR_TO_BITS_MAP[pc.FP_CONFIG['center_colors']['BL']])
        # Anneaux restent inchangés (exemple pour TL)
        self.assertEqual(ml.get_fixed_pattern_bits('FP_TL_CORE', 1, 2), pc.COLOR_TO_BITS_MAP[pc.FP_CONFIG['pattern_colors'][1]])
        self.assertEqual(ml.get_fixed_pattern_bits('FP_TL_CORE', 0, 2), pc.COLOR_TO_BITS_MAP[pc.FP_CONFIG['pattern_colors'][2]])

        # FP_TL_MARGIN -> WHITE ('00')
        self.assertEqual(ml.get_fixed_pattern_bits('FP_TL_MARGIN', 0, 0), pc.COLOR_TO_BITS_MAP[pc.WHITE])

        # CCP_PATCH_0 -> colors[0] (WHITE '00')
        self.assertEqual(ml.get_fixed_pattern_bits('CCP_PATCH_0', 0, 0), pc.COLOR_TO_BITS_MAP[pc.CCP_CONFIG['colors'][0]])
        self.assertEqual(ml.get_fixed_pattern_bits('CCP_PATCH_1', 1, 1), pc.COLOR_TO_BITS_MAP[pc.CCP_CONFIG['colors'][1]])

        # TP_H (line_color1: BLACK '01', line_color2: WHITE '00')
        self.assertEqual(ml.get_fixed_pattern_bits('TP_H', 0, 0), pc.COLOR_TO_BITS_MAP[pc.TP_CONFIG['line_color1']]) # col 0 -> BLACK
        self.assertEqual(ml.get_fixed_pattern_bits('TP_H', 0, 1), pc.COLOR_TO_BITS_MAP[pc.TP_CONFIG['line_color2']]) # col 1 -> WHITE

        # TP_V
        self.assertEqual(ml.get_fixed_pattern_bits('TP_V', 0, 0), pc.COLOR_TO_BITS_MAP[pc.TP_CONFIG['line_color1']]) # row 0 -> BLACK
        self.assertEqual(ml.get_fixed_pattern_bits('TP_V', 1, 0), pc.COLOR_TO_BITS_MAP[pc.TP_CONFIG['line_color2']]) # row 1 -> WHITE

        with self.assertRaises(ValueError):
            ml.get_fixed_pattern_bits('UNKNOWN_ZONE_TYPE', 0, 0)
        with self.assertRaises(ValueError): # Out of bounds for FP core
            ml.get_fixed_pattern_bits('FP_TL_CORE', 5, 5)


    def test_get_data_ecc_fill_order(self):
        fill_order = ml.get_data_ecc_fill_order()
        self.assertIsInstance(fill_order, list)
        
        # Calculate expected number of DATA_ECC cells
        total_cells = pc.MATRIX_DIM * pc.MATRIX_DIM
        
        fp_cells = 3 * (pc.FP_CONFIG['size'] * pc.FP_CONFIG['size'])
        
        tp_h_coords = ml.get_zone_coordinates('TP_H')
        tp_v_coords = ml.get_zone_coordinates('TP_V')
        # TP_H length: (c_end - c_start + 1)
        tp_h_cells = (tp_h_coords[3] - tp_h_coords[2] + 1)
        # TP_V length: (r_end - r_start + 1)
        tp_v_cells = (tp_v_coords[1] - tp_v_coords[0] + 1)
        # Intersection of TP_H and TP_V (cell at (6,6) for FP_TL) is counted by get_cell_zone_type
        # However, TPs are defined to not overlap FPs in the current coordinate definition.
        # Cell (6,6) is FP_TL_MARGIN.
        # Let's verify that (6,6) is not TP_H or TP_V
        self.assertNotEqual(ml.get_cell_zone_type(6,6), 'TP_H')
        self.assertNotEqual(ml.get_cell_zone_type(6,6), 'TP_V')

        metadata_cells = pc.METADATA_CONFIG['rows'] * pc.METADATA_CONFIG['cols']
        
        ccp_cells = len(pc.CCP_CONFIG['colors']) * (pc.CCP_CONFIG['patch_size'] * pc.CCP_CONFIG['patch_size'])
        
        # Count non-DATA_ECC cells by iterating
        non_data_ecc_count = 0
        for r in range(pc.MATRIX_DIM):
            for c in range(pc.MATRIX_DIM):
                if ml.get_cell_zone_type(r,c) != 'DATA_ECC':
                    non_data_ecc_count +=1
        
        expected_data_ecc_cells = total_cells - non_data_ecc_count
        
        self.assertEqual(len(fill_order), expected_data_ecc_cells)

        # Check uniqueness
        self.assertEqual(len(fill_order), len(set(fill_order)))

        # Check that all cells in fill_order are indeed DATA_ECC
        for r_coord, c_coord in fill_order:
            self.assertEqual(ml.get_cell_zone_type(r_coord, c_coord), 'DATA_ECC',
                             f"Cell ({r_coord},{c_coord}) in fill_order is not DATA_ECC type.")

if __name__ == '__main__':
    unittest.main() 