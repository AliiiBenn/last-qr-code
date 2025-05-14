import random
import src.core.protocol_config as pc
from typing import Tuple, Optional

# --- ECC Reed-Solomon (V2) ---
try:
    import reedsolo
except ImportError:
    reedsolo = None

def text_to_padded_bits(text: str, target_bit_length: int) -> str:
    """
    Convertit un texte en une chaîne de bits (UTF-8) et ajoute un padding de '0'
    pour atteindre target_bit_length.
    Lève une ValueError si le texte encodé est déjà plus long que target_bit_length.
    """
    byte_array = text.encode('utf-8')
    bits_list = []
    for byte in byte_array:
        bits_list.append(format(byte, '08b'))
    
    data_bits = "".join(bits_list)
    
    if len(data_bits) > target_bit_length:
        raise ValueError(f"Encoded text ({len(data_bits)} bits) is longer than target bit length ({target_bit_length} bits).")
        
    padding_length = target_bit_length - len(data_bits)
    padded_bits = data_bits + '0' * padding_length
    return padded_bits

def generate_xor_key(bit_length: int) -> str:
    """Génère une clé XOR aléatoire de la longueur spécifiée (chaîne de bits)."""
    if bit_length <= 0:
        raise ValueError("Bit length must be positive.")
    return ''.join(random.choice('01') for _ in range(bit_length))

def apply_xor_cipher(data_bits: str, key_bits: str) -> str:
    """
    Applique un chiffrement XOR entre data_bits et key_bits.
    La clé est répétée si elle est plus courte que les données.
    """
    if not key_bits:
        raise ValueError("XOR key cannot be empty.")
    
    key_len = len(key_bits)
    encrypted_bits_list = []
    
    for i, bit in enumerate(data_bits):
        key_char = key_bits[i % key_len]
        encrypted_bit = str(int(bit) ^ int(key_char))
        encrypted_bits_list.append(encrypted_bit)
        
    return "".join(encrypted_bits_list)

def calculate_simple_ecc(data_bits: str, num_ecc_bits: int) -> str:
    """
    Calcule un checksum simple sur data_bits.
    num_ecc_bits détermine la taille du checksum en bits (doit être un multiple de 8, ex: 8, 16, 24, 32).
    Retourne les bits du checksum.
    """
    if num_ecc_bits <= 0 or num_ecc_bits % 8 != 0:
        raise ValueError("Number of ECC bits must be a positive multiple of 8 for this checksum implementation.")

    checksum_val = 0
    # Traiter data_bits par blocs de 8 bits (octets)
    for i in range(0, len(data_bits), 8):
        block_str = data_bits[i:i+8]
        # Si le dernier bloc est incomplet, le padder avec des 0 à droite pour former un octet
        if len(block_str) < 8:
            block_str = block_str.ljust(8, '0')
        
        block_int = int(block_str, 2)
        checksum_val = (checksum_val + block_int) % (2**num_ecc_bits) # Modulo 2^N où N est num_ecc_bits
        
    return format(checksum_val, f'0{num_ecc_bits}b')


def format_metadata_bits(
    protocol_version: int, 
    ecc_level_code: int, # Par exemple, un code simple pour le % d'ECC (0-15 si 4 bits)
    message_encrypted_len: int, # Longueur en bits du message après cryptage
    xor_key_actual_bits: str,     # La chaîne de bits de la clé XOR réellement utilisée
    metadata_cfg: dict = None
) -> str:
    """
    Assemble les bits de métadonnées selon METADATA_CONFIG (or provided config).
    Gère la protection des métadonnées (répétition des bits d'info pour atteindre total_bits).
    """
    cfg = metadata_cfg or pc.METADATA_CONFIG
    
    # Convertir les entrées en chaînes de bits avec la bonne longueur
    version_b = format(protocol_version, f'0{cfg["version_bits"]}b')
    ecc_level_b = format(ecc_level_code, f'0{cfg["ecc_level_bits"]}b')
    msg_len_b = format(message_encrypted_len, f'0{cfg["msg_len_bits"]}b')
    
    # S'assurer que xor_key_actual_bits a la bonne longueur
    if len(xor_key_actual_bits) != cfg['key_bits']:
        raise ValueError(f"XOR key bits length mismatch. Expected {cfg['key_bits']}, got {len(xor_key_actual_bits)}")

    info_bits_list = [
        version_b,
        ecc_level_b,
        msg_len_b,
        xor_key_actual_bits # Déjà une chaîne de bits
    ]
    info_bits_str = "".join(info_bits_list)
    
    current_info_bits_len = len(info_bits_str)
    # Les bits d'information 'purs' sont ceux avant la protection.
    # La taille des bits d'information purs doit correspondre à total_bits - protection_bits
    expected_pure_info_len = cfg['total_bits'] - cfg['protection_bits']

    if current_info_bits_len != expected_pure_info_len:
        raise ValueError(f"Constructed pure info bits length ({current_info_bits_len}) does not match "
                         f"expected based on config (total_bits - protection_bits = {expected_pure_info_len}). "
                         f"Check METADATA_CONFIG bit allocations: version_bits + ecc_level_bits + msg_len_bits + key_bits.")

    # Protection: Répéter les info_bits_str si protection_bits est égal à la longueur des info_bits_str
    # et que total_bits est le double, comme spécifié dans METADATA_CONFIG (36+36=72)
    if cfg['protection_bits'] == current_info_bits_len and \
       cfg['total_bits'] == (current_info_bits_len + cfg['protection_bits']):
        protected_metadata_bits = info_bits_str + info_bits_str # Simple répétition
    elif cfg['protection_bits'] == 0: # Pas de bits de protection explicites, les info_bits remplissent tout
         protected_metadata_bits = info_bits_str
    else:
        # Cas où la protection n'est pas une simple répétition des info_bits_str ou pas nulle.
        # Le plan suggère "appliquer un ECC dédié plus simple sur les 36 bits d'info".
        # Pour l'instant, si ce n'est pas la répétition attendue, c'est une erreur de configuration ou une fonctionnalité non implémentée.
        raise NotImplementedError(
            f"Metadata protection scheme not fully implemented or METADATA_CONFIG is ambiguous. "
            f"Current info bits length: {current_info_bits_len}, protection_bits: {cfg['protection_bits']}, total_bits: {cfg['total_bits']}. "
            f"The implemented scheme is simple repetition if protection_bits equals info_bits_len and sum to total_bits, or no protection if protection_bits is 0."
        )

    if len(protected_metadata_bits) != cfg['total_bits']:
        raise ValueError(f"Final metadata stream length ({len(protected_metadata_bits)}) "
                         f"does not match METADATA_CONFIG total_bits ({cfg['total_bits']}).")
        
    return protected_metadata_bits 

# --- Functions for Phase 6: Decoder - Interpretation and Data Recovery ---

def parse_metadata_bits(metadata_stream: str, metadata_cfg: dict = None) -> dict:
    """
    Parses the metadata stream to extract protocol version, ECC level, 
    message length, and XOR key.
    Verifies metadata protection (simple repetition).
    """
    cfg = metadata_cfg or pc.METADATA_CONFIG
    expected_total_bits = cfg['total_bits']

    if len(metadata_stream) != expected_total_bits:
        raise ValueError(
            f"Metadata stream length is incorrect. Expected {expected_total_bits}, got {len(metadata_stream)}."
        )

    # Protection check: simple repetition
    # The first block of (total_bits - protection_bits) should be repeated.
    # (total_bits - protection_bits) is the length of the actual information block.
    info_block_len = expected_total_bits - cfg['protection_bits'] # e.g., 72 - 36 = 36 bits

    if info_block_len <= 0:
        raise ValueError("Calculated info_block_len is not positive. Check METADATA_CONFIG.")
    
    # Check if the metadata stream length is consistent with info_block_len for repetition
    if cfg['protection_bits'] != info_block_len or expected_total_bits != 2 * info_block_len:
        # This case implies the protection scheme isn't simple repetition of the first info_block_len bits,
        # or the config is inconsistent for such a scheme.
        # For now, we only support simple repetition as per format_metadata_bits.
        # If protection_bits is 0, then there's no repetition to check.
        if cfg['protection_bits'] == 0 and expected_total_bits == info_block_len:
            pass # No repetition to check, info_block_len is the whole stream
        else:
            raise ValueError(
                f"Metadata protection scheme mismatch or config inconsistency. "
                f"Expected simple repetition of a {info_block_len}-bit block. "
                f"Config: total_bits={expected_total_bits}, protection_bits={cfg['protection_bits']}."
            )

    if cfg['protection_bits'] > 0 : # Only check repetition if there are protection bits
        block1 = metadata_stream[:info_block_len]
        block2 = metadata_stream[info_block_len : info_block_len + cfg['protection_bits']] # protection_bits should be equal to info_block_len

        if block1 != block2:
            raise ValueError("Metadata protection check failed: repeated blocks do not match.")
    
    # Parse the first (and now verified) information block
    current_pos = 0
    
    # Protocol Version
    version_str = metadata_stream[current_pos : current_pos + cfg['version_bits']]
    protocol_version = int(version_str, 2)
    current_pos += cfg['version_bits']
    
    # ECC Level Code
    ecc_level_str = metadata_stream[current_pos : current_pos + cfg['ecc_level_bits']]
    ecc_level_code = int(ecc_level_str, 2)
    current_pos += cfg['ecc_level_bits']
    
    # Message Encrypted Length
    msg_len_str = metadata_stream[current_pos : current_pos + cfg['msg_len_bits']]
    message_encrypted_len = int(msg_len_str, 2)
    current_pos += cfg['msg_len_bits']
    
    # XOR Key
    xor_key = metadata_stream[current_pos : current_pos + cfg['key_bits']]
    current_pos += cfg['key_bits']

    if current_pos != info_block_len:
        raise ValueError(
            f"Error parsing metadata info block: consumed {current_pos} bits, expected {info_block_len}."
        )

    return {
        'protocol_version': protocol_version,
        'ecc_level_code': ecc_level_code,
        'message_encrypted_len': message_encrypted_len,
        'xor_key': xor_key
    }

def verify_simple_ecc(encrypted_data_bits: str, received_ecc_bits: str) -> bool:
    """
    Verifies the simple checksum ECC.
    Recalculates checksum on encrypted_data_bits and compares with received_ecc_bits.
    Returns True if ECC is OK (or no ECC bits), False otherwise.
    """
    num_received_ecc_bits = len(received_ecc_bits)

    if num_received_ecc_bits == 0:
        return True # No ECC to verify

    # calculate_simple_ecc expects num_ecc_bits to be a positive multiple of 8.
    if num_received_ecc_bits % 8 != 0:
        # This case should ideally not occur if encoder produces valid ECC bit lengths.
        # For robustness, we might log a warning or raise an error if strictness is needed.
        # For now, if it's not a multiple of 8, the check will likely fail anyway or error out
        # in calculate_simple_ecc. Let's assume calculate_simple_ecc handles this.
        # Or, more strictly:
        # raise ValueError("Received ECC bits length must be a multiple of 8 for this verification.")
        pass # Allow calculate_simple_ecc to handle it or potentially error.

    try:
        calculated_ecc = calculate_simple_ecc(encrypted_data_bits, num_received_ecc_bits)
    except ValueError:
        # This can happen if num_received_ecc_bits is not a positive multiple of 8.
        return False 
        
    return calculated_ecc == received_ecc_bits

def calculate_reed_solomon_ecc(data_bits: str, num_ecc_symbols: int, symbol_size_bits: int = 8) -> str:
    """
    Calcule les symboles ECC Reed-Solomon pour les data_bits donnés.
    - data_bits : chaîne de bits (ex: '101010...')
    - num_ecc_symbols : nombre de symboles ECC (octets si symbol_size_bits=8)
    - symbol_size_bits : taille d'un symbole (par défaut 8 bits)
    Retourne la concaténation des bits ECC (en string).
    ATTENTION :
      - Le dernier octet est paddé à droite avec des zéros si data_bits n'est pas un multiple de 8.
      - La taille totale (data_bytes) doit être <= 255 - num_ecc_symbols.
    """
    if num_ecc_symbols <= 0:
        return ''
    if reedsolo is None:
        raise ImportError("Le module 'reedsolo' n'est pas installé. Installez-le avec 'pip install reedsolo'.")
    if symbol_size_bits != 8:
        raise NotImplementedError("Seuls les symboles de 8 bits sont supportés pour l'instant.")
    # Validate input bits
    if set(data_bits) - {'0', '1'}:
        raise ValueError("data_bits must consist only of '0' and '1'")
    # Découper data_bits en octets (plus lisible et rapide)
    padded_bits = data_bits.ljust((len(data_bits) + 7) // 8 * 8, '0')
    data_bytes = [int(padded_bits[i:i+8], 2) for i in range(0, len(padded_bits), 8)]
    max_msg = 255 - num_ecc_symbols
    if len(data_bytes) > max_msg:
        raise ValueError(f"Data too long: {len(data_bytes)} bytes (max {max_msg}) for RS({max_msg}+{num_ecc_symbols}, {max_msg})")
    # Encoder avec Reed-Solomon
    rs = reedsolo.RSCodec(num_ecc_symbols)
    encoded = rs.encode(bytes(data_bytes))
    # Les symboles ECC sont à la fin
    ecc_bytes = encoded[-num_ecc_symbols:]
    # Retourner les bits ECC
    return ''.join(format(b, '08b') for b in ecc_bytes)


def verify_and_correct_reed_solomon_ecc(message_plus_ecc_bits: str, num_ecc_symbols: int, symbol_size_bits: int = 8) -> Tuple[bool, Optional[str]]:
    """
    Vérifie et corrige (si possible) les erreurs dans message_plus_ecc_bits (data+ecc).
    - message_plus_ecc_bits : bits concaténés (data + ecc)
    - num_ecc_symbols : nombre de symboles ECC (octets)
    - symbol_size_bits : taille d'un symbole (par défaut 8 bits)
    Retourne (is_valid, corrected_data_bits).
    Si la correction échoue, is_valid=False et corrected_data_bits=None.
    ATTENTION :
      - Le dernier octet est paddé à droite avec des zéros si data_bits n'est pas un multiple de 8.
      - La taille totale (data_bytes) doit être <= 255.
    """
    if num_ecc_symbols <= 0:
        return True, message_plus_ecc_bits  # Pas d'ECC à vérifier
    if reedsolo is None:
        raise ImportError("Le module 'reedsolo' n'est pas installé. Installez-le avec 'pip install reedsolo'.")
    if symbol_size_bits != 8:
        raise NotImplementedError("Seuls les symboles de 8 bits sont supportés pour l'instant.")
    # Validate input bits
    if set(message_plus_ecc_bits) - {'0', '1'}:
        raise ValueError("message_plus_ecc_bits must consist only of '0' and '1'")
    # Découper en octets
    padded_bits = message_plus_ecc_bits.ljust((len(message_plus_ecc_bits) + 7) // 8 * 8, '0')
    total_bytes = [int(padded_bits[i:i+8], 2) for i in range(0, len(padded_bits), 8)]
    if len(total_bytes) > 255:
        raise ValueError(f"Message trop long pour Reed-Solomon (max 255 octets, reçu {len(total_bytes)})")
    try:
        rs = reedsolo.RSCodec(num_ecc_symbols)
        decoded = rs.decode(bytes(total_bytes))
        # decoded est un tuple (data, ecc), on ne garde que data
        data_bytes = decoded[0]
        # Retourner les bits de data (sans ECC)
        data_bits = ''.join(format(b, '08b') for b in data_bytes)
        return True, data_bits
    except reedsolo.ReedSolomonError:
        return False, None

def padded_bits_to_text(data_bits: str, *, original_bit_length: int) -> str:
    """
    Convertit une chaîne de bits (padded UTF-8) en texte.
    - original_bit_length est obligatoire pour éviter toute perte de données.
    - Si original_bit_length n'est pas un multiple de 8, une ValueError est levée (aucune troncature silencieuse).
    """
    if original_bit_length % 8 != 0:
        raise ValueError(f"original_bit_length ({original_bit_length}) is not a multiple of 8. This would cause silent truncation of bits.")
    data_bits = data_bits[:original_bit_length]
    byte_list = []
    for i in range(0, len(data_bits), 8):
        byte_str = data_bits[i : i + 8]
        if len(byte_str) < 8:
            break
        byte_list.append(int(byte_str, 2))
    byte_array = bytes(byte_list)
    try:
        text = byte_array.decode('utf-8', errors='strict')
    except UnicodeDecodeError as e:
        raise ValueError(f"Failed to decode bits to UTF-8 text. Data may be corrupted or not valid text. Details: {e}") from e
    return text 