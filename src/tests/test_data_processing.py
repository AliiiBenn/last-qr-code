import unittest
from unittest import mock
import src.core.data_processing as dp
import src.core.protocol_config as pc
from importlib.util import find_spec

class TestDataProcessing(unittest.TestCase):

    def test_text_to_padded_bits(self):
        # Cas simple: 'Hi' (H=01001000, i=01101001) -> 0100100001101001
        self.assertEqual(dp.text_to_padded_bits("Hi", 16), "0100100001101001")
        # Avec padding
        self.assertEqual(dp.text_to_padded_bits("Hi", 20), "01001000011010010000")
        # Texte vide
        self.assertEqual(dp.text_to_padded_bits("", 8), "00000000")
        # Cas limite: longueur exacte
        self.assertEqual(dp.text_to_padded_bits("A", 8), "01000001")
        # Erreur si trop long
        with self.assertRaises(ValueError):
            dp.text_to_padded_bits("Hello", 16) # Hello = 5*8 = 40 bits
        # Caractères UTF-8 plus complexes (ex: é -> c3a9 -> 1100001110101001)
        self.assertEqual(dp.text_to_padded_bits("é", 16), "1100001110101001")
        self.assertEqual(dp.text_to_padded_bits("é", 20), "11000011101010010000")

    def test_generate_xor_key(self):
        key8 = dp.generate_xor_key(8)
        self.assertEqual(len(key8), 8)
        self.assertTrue(all(c in '01' for c in key8))

        key16 = dp.generate_xor_key(16)
        self.assertEqual(len(key16), 16)
        self.assertTrue(all(c in '01' for c in key16))

        with self.assertRaises(ValueError): # Longueur non positive
            dp.generate_xor_key(0)
        with self.assertRaises(ValueError):
            dp.generate_xor_key(-5)

    def test_apply_xor_cipher(self):
        data = "10101010"
        key = "01010101"
        expected = "11111111"
        self.assertEqual(dp.apply_xor_cipher(data, key), expected)
        # Test décryptage (XOR deux fois redonne l'original)
        self.assertEqual(dp.apply_xor_cipher(expected, key), data)

        # Clé plus courte que les données
        data2 = "1100110011001100"
        key2 = "1010"
        # 1100 ^ 1010 = 0110
        # 1100 ^ 1010 = 0110
        # 1100 ^ 1010 = 0110
        # 1100 ^ 1010 = 0110
        expected2 = "0110011001100110"
        self.assertEqual(dp.apply_xor_cipher(data2, key2), expected2)
        self.assertEqual(dp.apply_xor_cipher(expected2, key2), data2)
        
        # Clé vide
        with self.assertRaises(ValueError):
            dp.apply_xor_cipher(data, "")

    def test_calculate_simple_ecc(self):
        # Checksum 8 bits
        # "00000001" (1) + "00000010" (2) = 3 -> "00000011"
        data1 = "0000000100000010"
        self.assertEqual(dp.calculate_simple_ecc(data1, 8), "00000011")
        # Checksum 16 bits
        # (1 + 2) % 2^16 = 3 -> "0000000000000011"
        self.assertEqual(dp.calculate_simple_ecc(data1, 16), "0000000000000011")

        # Données plus longues
        # "11111111" (255) + "00000001" (1) = 256. Pour 8 bits ECC, 256 % 256 = 0 -> "00000000"
        data2 = "1111111100000001"
        self.assertEqual(dp.calculate_simple_ecc(data2, 8), "00000000")
        # Pour 16 bits ECC, 256 % 65536 = 256 -> "0000000100000000"
        self.assertEqual(dp.calculate_simple_ecc(data2, 16), "0000000100000000")

        # Données non multiples de 8 bits (padding interne)
        # "101" -> "10100000" (160)
        data3 = "101"
        self.assertEqual(dp.calculate_simple_ecc(data3, 8), format(160, '08b')) # "10100000"
        
        # Test num_ecc_bits invalide
        with self.assertRaises(ValueError):
            dp.calculate_simple_ecc(data1, 0)
        with self.assertRaises(ValueError):
            dp.calculate_simple_ecc(data1, 7)
        with self.assertRaises(ValueError):
            dp.calculate_simple_ecc(data1, 15)

    def test_format_metadata_bits(self):
        # Utiliser les valeurs de pc.METADATA_CONFIG pour la cohérence
        cfg = pc.METADATA_CONFIG
        self.assertEqual(cfg['total_bits'], 72) # Assurer que la config est comme attendu par le test
        self.assertEqual(cfg['protection_bits'], 36)
        expected_info_len = cfg['total_bits'] - cfg['protection_bits'] # Devrait être 36
        self.assertEqual(cfg['version_bits'] + cfg['ecc_level_bits'] + cfg['msg_len_bits'] + cfg['key_bits'], expected_info_len)

        # Cas de test 1: valeurs simples
        version = 1     # 0001 (4b)
        ecc_level = 2   # 0010 (4b)
        msg_len = 1024  # 010000000000 (12b)
        xor_key = "1010101010101010" # (16b)
        # Total info bits: 4+4+12+16 = 36 bits
        
        version_b = format(version, f'0{cfg["version_bits"]}b')
        ecc_level_b = format(ecc_level, f'0{cfg["ecc_level_bits"]}b')
        msg_len_b = format(msg_len, f'0{cfg["msg_len_bits"]}b')
        
        info_bits_str = version_b + ecc_level_b + msg_len_b + xor_key
        self.assertEqual(len(info_bits_str), expected_info_len)
        
        # Protection par répétition
        expected_metadata = info_bits_str + info_bits_str 
        self.assertEqual(len(expected_metadata), cfg['total_bits'])
        
        self.assertEqual(dp.format_metadata_bits(version, ecc_level, msg_len, xor_key), expected_metadata)

        # Cas où la clé XOR a une mauvaise longueur
        with self.assertRaises(ValueError):
            dp.format_metadata_bits(version, ecc_level, msg_len, "101") # Clé trop courte

        # Test avec une configuration où protection_bits = 0 (si on la changeait temporairement)
        original_protection_bits = cfg['protection_bits']
        original_total_bits = cfg['total_bits']
        cfg['protection_bits'] = 0
        cfg['total_bits'] = expected_info_len # total_bits est maintenant égal à la longueur des infos pures
        try:
            expected_no_protection_metadata = info_bits_str
            self.assertEqual(len(expected_no_protection_metadata), cfg['total_bits'])
            self.assertEqual(dp.format_metadata_bits(version, ecc_level, msg_len, xor_key), expected_no_protection_metadata)
        finally:
            # Restaurer la config originale pour ne pas affecter d'autres tests
            cfg['protection_bits'] = original_protection_bits
            cfg['total_bits'] = original_total_bits

        # Test avec une configuration qui mènerait à NotImplementedError
        # (protection_bits non nul et ne correspondant pas au scénario de répétition simple)
        cfg['protection_bits'] = 10 # Une valeur arbitraire qui ne correspond pas à la répétition
        cfg['total_bits'] = expected_info_len + 10
        try:
            with self.assertRaises(NotImplementedError):
                dp.format_metadata_bits(version, ecc_level, msg_len, xor_key)
        finally:
            cfg['protection_bits'] = original_protection_bits
            cfg['total_bits'] = original_total_bits

# --- Tests for Phase 6 Functions (parse_metadata, verify_ecc, bits_to_text) ---
class TestDecoderDataProcessing(unittest.TestCase):
    def setUp(self):
        self.cfg = pc.METADATA_CONFIG
        self.version = 1
        self.ecc_level_code = 3
        self.msg_len = 128
        self.xor_key = '1100110011001100' # 16 bits as per default config

        self.info_block = (
            format(self.version, f"0{self.cfg['version_bits']}b") +
            format(self.ecc_level_code, f"0{self.cfg['ecc_level_bits']}b") +
            format(self.msg_len, f"0{self.cfg['msg_len_bits']}b") +
            self.xor_key
        )
        # Assuming simple repetition protection as per default METADATA_CONFIG
        self.valid_metadata_stream = self.info_block + self.info_block
        self.assertEqual(len(self.info_block), self.cfg['total_bits'] - self.cfg['protection_bits'])
        self.assertEqual(len(self.valid_metadata_stream), self.cfg['total_bits'])

    def test_parse_metadata_bits_valid(self):
        parsed = dp.parse_metadata_bits(self.valid_metadata_stream)
        self.assertEqual(parsed['protocol_version'], self.version)
        self.assertEqual(parsed['ecc_level_code'], self.ecc_level_code)
        self.assertEqual(parsed['message_encrypted_len'], self.msg_len)
        self.assertEqual(parsed['xor_key'], self.xor_key)

    def test_parse_metadata_bits_invalid_length(self):
        with self.assertRaisesRegex(ValueError, "Metadata stream length is incorrect"):
            dp.parse_metadata_bits(self.valid_metadata_stream[:-1]) # Too short
        with self.assertRaisesRegex(ValueError, "Metadata stream length is incorrect"):
            dp.parse_metadata_bits(self.valid_metadata_stream + "0") # Too long

    def test_parse_metadata_bits_protection_failed(self):
        info_len = self.cfg['total_bits'] - self.cfg['protection_bits']
        bad_protection_block = '0' * self.cfg['protection_bits']
        if self.info_block[:self.cfg['protection_bits']] == bad_protection_block: # Ensure it's different
            bad_protection_block = '1' * self.cfg['protection_bits']
            
        invalid_stream = self.info_block + bad_protection_block
        # Ensure it's still the correct total length
        self.assertEqual(len(invalid_stream), self.cfg['total_bits'])
        
        with self.assertRaisesRegex(ValueError, "Metadata protection check failed: repeated blocks do not match"):
            dp.parse_metadata_bits(invalid_stream)

    def test_parse_metadata_bits_config_mismatch_for_repetition(self):
        # Config where protection_bits > 0 but not equal to info_block_len for simple repetition
        # or total_bits is not 2 * info_block_len
        # Example: info_block_len = 36, protection_bits = 10, total_bits = 72
        # This means expected_total_bits (72) != 2 * info_block_len (2 * (72-10=62)=124) is false
        # AND protection_bits (10) != info_block_len (62) is true
        # So (True or False) -> True for the first condition in parse_metadata_bits
        # and the second part (protection_bits == 0) is False. So it raises ValueError.
        
        mismatch_config = self.cfg.copy()
        mismatch_config['protection_bits'] = 10 
        # total_bits is still 72. info_block_len becomes 72-10 = 62.
        # The condition (cfg['protection_bits'] != info_block_len or expected_total_bits != 2 * info_block_len)
        # (10 != 62 or 72 != 2 * 62) -> (True or True) -> True.
        # The nested if (cfg['protection_bits'] == 0 ...) is False. So ValueError.
        
        dummy_stream_72bits = '0' * self.cfg['total_bits']

        with unittest.mock.patch.dict(pc.METADATA_CONFIG, mismatch_config, clear=True):
            with self.assertRaisesRegex(ValueError, "Metadata protection scheme mismatch or config inconsistency"):
                dp.parse_metadata_bits(dummy_stream_72bits)
        
        # Another mismatch: info_block_len=36, protection_bits=36, but total_bits=70 (not 2*36)
        mismatch_config_2 = self.cfg.copy() # protection_bits is 36, info_block_len will be total_bits - 36
        mismatch_config_2['total_bits'] = 70 # info_block_len = 70-36 = 34
        # (cfg['protection_bits'] != info_block_len or expected_total_bits != 2 * info_block_len)
        # (36 != 34 or 70 != 2 * 34) -> (True or 70 != 68 -> True) -> True
        dummy_stream_70bits = '0' * 70
        with unittest.mock.patch.dict(pc.METADATA_CONFIG, mismatch_config_2, clear=True):
            with self.assertRaisesRegex(ValueError, "Metadata protection scheme mismatch or config inconsistency"):
                dp.parse_metadata_bits(dummy_stream_70bits)


    def test_parse_metadata_bits_no_protection_config(self):
        cfg_no_protection = {
            'version_bits': 6, 'ecc_level_bits': 4, 'msg_len_bits': 10, 'key_bits': 16,
            'protection_bits': 0,
            'total_bits': 6 + 4 + 10 + 16 # 36
        }
        
        v, e, m, k = 1, 2, 50, '01'*8
        stream_no_protection = (
            format(v, f"0{cfg_no_protection['version_bits']}b") +
            format(e, f"0{cfg_no_protection['ecc_level_bits']}b") +
            format(m, f"0{cfg_no_protection['msg_len_bits']}b") +
            k
        )
        self.assertEqual(len(stream_no_protection), cfg_no_protection['total_bits'])

        with unittest.mock.patch.dict(pc.METADATA_CONFIG, cfg_no_protection, clear=True):
            parsed = dp.parse_metadata_bits(stream_no_protection)
            self.assertEqual(parsed['protocol_version'], v)
            self.assertEqual(parsed['ecc_level_code'], e)
            self.assertEqual(parsed['message_encrypted_len'], m)
            self.assertEqual(parsed['xor_key'], k)
            
    def test_parse_metadata_bits_info_block_len_zero_or_negative(self):
        bad_cfg = self.cfg.copy()
        bad_cfg['total_bits'] = 10
        bad_cfg['protection_bits'] = 10 # info_block_len = 0
        dummy_stream_10bits = '0'*10
        with unittest.mock.patch.dict(pc.METADATA_CONFIG, bad_cfg, clear=True):
            with self.assertRaisesRegex(ValueError, "Calculated info_block_len is not positive"):
                dp.parse_metadata_bits(dummy_stream_10bits)

        bad_cfg_2 = self.cfg.copy()
        bad_cfg_2['total_bits'] = 10
        bad_cfg_2['protection_bits'] = 12 # info_block_len = -2
        dummy_stream_10bits_v2 = '0'*10
        with unittest.mock.patch.dict(pc.METADATA_CONFIG, bad_cfg_2, clear=True):
            with self.assertRaisesRegex(ValueError, "Calculated info_block_len is not positive"):
                dp.parse_metadata_bits(dummy_stream_10bits_v2)


    def test_verify_simple_ecc_correct(self):
        data = "0101010110101010" # 16 bits
        ecc8 = dp.calculate_simple_ecc(data, 8)
        self.assertTrue(dp.verify_simple_ecc(data, ecc8))
        
        ecc16 = dp.calculate_simple_ecc(data, 16)
        self.assertTrue(dp.verify_simple_ecc(data, ecc16))

    def test_verify_simple_ecc_incorrect(self):
        data = "0101010110101010"
        ecc8 = dp.calculate_simple_ecc(data, 8)
        bad_ecc8 = '0' * 8 if ecc8 != '0' * 8 else '1' * 8
        self.assertFalse(dp.verify_simple_ecc(data, bad_ecc8))

        ecc16 = dp.calculate_simple_ecc(data, 16)
        bad_ecc16 = list(ecc16)
        bad_ecc16[0] = '1' if bad_ecc16[0] == '0' else '0' # Flip first bit
        self.assertFalse(dp.verify_simple_ecc(data, "".join(bad_ecc16)))

    def test_verify_simple_ecc_no_ecc_bits(self):
        data = "01010101"
        self.assertTrue(dp.verify_simple_ecc(data, ""))

    def test_verify_simple_ecc_invalid_ecc_len_for_calc(self):
        data = "01010101"
        # calculate_simple_ecc inside verify_simple_ecc will raise ValueError for non-multiple-of-8 ECC bits,
        # which verify_simple_ecc catches and returns False.
        self.assertFalse(dp.verify_simple_ecc(data, "01010")) # Length 5
        self.assertFalse(dp.verify_simple_ecc(data, "0101010")) # Length 7
        self.assertFalse(dp.verify_simple_ecc(data, "0"*9)) # Length 9

    def test_padded_bits_to_text_basic(self):
        text = "Hello World!"
        padded_bits = dp.text_to_padded_bits(text, len(text.encode('utf-8')) * 8 + 16) # Add 16 bits of '0' padding
        self.assertEqual(dp.padded_bits_to_text(padded_bits, original_bit_length=len(text.encode('utf-8'))*8), text)

    def test_padded_bits_to_text_exact_length_no_padding_needed(self):
        text = "Test"
        text_bits = "".join(format(b, '08b') for b in text.encode('utf-8'))
        # Pass bits that are an exact multiple of 8 and represent the text
        self.assertEqual(dp.padded_bits_to_text(text_bits, original_bit_length=len(text.encode('utf-8'))*8), text)

    def test_padded_bits_to_text_with_actual_null_chars_in_padding(self):
        text = "Bonjour"
        text_bits = "".join(format(b, '08b') for b in text.encode('utf-8'))
        # Pad with bits that happen to form null characters
        padded_with_nulls = text_bits + "00000000" + "00000000" # Two null bytes
        self.assertEqual(dp.padded_bits_to_text(padded_with_nulls, original_bit_length=len(text.encode('utf-8'))*8), text)

    def test_padded_bits_to_text_with_internal_null_chars(self):
        text_with_internal_null = "Hello\x00World"
        # text_to_padded_bits will preserve internal nulls
        padded_bits = dp.text_to_padded_bits(text_with_internal_null, 128) 
        self.assertEqual(dp.padded_bits_to_text(padded_bits, original_bit_length=len(text_with_internal_null.encode('utf-8'))*8), text_with_internal_null)

    def test_padded_bits_to_text_empty_string(self):
        self.assertEqual(dp.padded_bits_to_text("", original_bit_length=0), "")
        # Test with padding
        padded_empty = dp.text_to_padded_bits("", 16) # Should be "0"*16
        self.assertEqual(dp.padded_bits_to_text(padded_empty, original_bit_length=0), "")

    def test_padded_bits_to_text_invalid_utf8(self):
        # 0xC0 0x80 is an overlong encoding of U+0000, invalid.
        # 0xF_ indicates a 4-byte sequence. 0xF0 needs 3 continuation bytes.
        # 0xF0 0x80 0x80 (missing one continuation byte) - incomplete sequence
        invalid_bits_incomplete_seq = "11110000" + "10000000" + "10000000" # F0 80 80
        with self.assertRaisesRegex(ValueError, "Failed to decode bits to UTF-8 text"):
            dp.padded_bits_to_text(invalid_bits_incomplete_seq, original_bit_length=24)

        # 0xFF is not a valid start byte in UTF-8
        invalid_bits_bad_start = "11111111"
        with self.assertRaisesRegex(ValueError, "Failed to decode bits to UTF-8 text"):
            dp.padded_bits_to_text(invalid_bits_bad_start, original_bit_length=8)
            
        # Valid start of 2-byte seq (e.g. C2), but invalid continuation byte (e.g. not 10xxxxxx)
        invalid_bits_bad_continuation = "11000010" + "01000000" # C2 40
        with self.assertRaisesRegex(ValueError, "Failed to decode bits to UTF-8 text"):
            dp.padded_bits_to_text(invalid_bits_bad_continuation, original_bit_length=16)

    def test_padded_bits_to_text_multibyte_chars(self):
        text = "Résumé Test 😊" # Includes accented char and emoji
        padded_bits = dp.text_to_padded_bits(text, len(text.encode('utf-8')) * 8 + 24)
        self.assertEqual(dp.padded_bits_to_text(padded_bits, original_bit_length=len(text.encode('utf-8'))*8), text)
        
    def test_padded_bits_to_text_trailing_incomplete_byte(self):
        text = "Hi"
        text_bits = "".join(format(b, '08b') for b in text.encode('utf-8')) # "0100100001101001"
        # Add some bits that don't form a full byte at the end
        bits_with_trailing = text_bits + "0101"
        # padded_bits_to_text should ignore the trailing incomplete byte
        self.assertEqual(dp.padded_bits_to_text(bits_with_trailing, original_bit_length=len(text.encode('utf-8'))*8), text)
        
        # Test with only an incomplete byte
        self.assertEqual(dp.padded_bits_to_text("10101", original_bit_length=0), "")


class TestReedSolomonECC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.reedsolo_available = find_spec("reedsolo") is not None
        except ImportError:
            cls.reedsolo_available = False

    def setUp(self):
        if not self.reedsolo_available:
            self.skipTest("reedsolo n'est pas installé")

    def test_calculate_reed_solomon_ecc_length(self):
        data_bits = '10101010' * 4  # 32 bits (4 octets)
        num_ecc_symbols = 4
        ecc_bits = dp.calculate_reed_solomon_ecc(data_bits, num_ecc_symbols)
        self.assertEqual(len(ecc_bits), num_ecc_symbols * 8)

    def test_rs_encode_decode_no_error(self):
        data_bits = '11001100' * 8  # 64 bits (8 octets)
        num_ecc_symbols = 8
        ecc_bits = dp.calculate_reed_solomon_ecc(data_bits, num_ecc_symbols)
        message_plus_ecc = data_bits + ecc_bits
        is_valid, corrected = dp.verify_and_correct_reed_solomon_ecc(message_plus_ecc, num_ecc_symbols)
        self.assertTrue(is_valid)
        # Les bits de data peuvent être paddés à la fin, donc on compare le début
        self.assertTrue(corrected.startswith(data_bits))

    def test_rs_correct_single_error(self):
        data_bits = '11110000' * 8  # 64 bits
        num_ecc_symbols = 8
        ecc_bits = dp.calculate_reed_solomon_ecc(data_bits, num_ecc_symbols)
        message_plus_ecc = list(data_bits + ecc_bits)
        # Introduire une erreur sur un bit dans le premier octet
        message_plus_ecc[3] = '1' if message_plus_ecc[3] == '0' else '0'
        corrupted = ''.join(message_plus_ecc)
        is_valid, corrected = dp.verify_and_correct_reed_solomon_ecc(corrupted, num_ecc_symbols)
        self.assertTrue(is_valid)
        self.assertTrue(corrected.startswith(data_bits))

    def test_rs_too_many_errors(self):
        data_bits = '10101010' * 8  # 64 bits
        num_ecc_symbols = 8
        ecc_bits = dp.calculate_reed_solomon_ecc(data_bits, num_ecc_symbols)
        message_plus_ecc = list(data_bits + ecc_bits)
        # Injecter des erreurs sur 5 octets entiers (soit 5*8=40 bits), ce qui dépasse la capacité de correction (t=4)
        for octet in range(5):
            start = octet * 8
            for i in range(start, start + 8):
                message_plus_ecc[i] = '1' if message_plus_ecc[i] == '0' else '0'
        corrupted = ''.join(message_plus_ecc)
        is_valid, corrected = dp.verify_and_correct_reed_solomon_ecc(corrupted, num_ecc_symbols)
        self.assertFalse(is_valid)
        self.assertIsNone(corrected)


if __name__ == '__main__':
    unittest.main() 