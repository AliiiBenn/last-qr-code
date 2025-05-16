import numpy as np
import src.core.protocol_config as pc
import src.core.matrix_layout as ml
import src.core.data_processing as dp

def initialize_bit_matrix():
    """
    Crée une matrice MATRIX_DIM x MATRIX_DIM pour stocker les paires de bits (chaînes '00', '01', etc.).
    Initialisée avec des chaînes vides ou None.
    """
    # Le plan suggère numpy.empty avec dtype=object ou une liste de listes.
    # Utiliser une liste de listes de chaînes vides est simple et correspond à l'attente de stocker des paires de bits.
    return [[None for _ in range(pc.MATRIX_DIM)] for _ in range(pc.MATRIX_DIM)]
    # Alternative avec NumPy si préféré plus tard pour des opérations vectorielles:
    # return np.full((pc.MATRIX_DIM, pc.MATRIX_DIM), None, dtype=object) 

def populate_fixed_zones(bit_matrix):
    """
    Remplit la bit_matrix avec les motifs fixes (FP, TP, CCP).
    Les zones METADATA et DATA_ECC sont laissées vides (None).
    """
    for r in range(pc.MATRIX_DIM):
        for c in range(pc.MATRIX_DIM):
            zone_type = ml.get_cell_zone_type(r, c)

            # Les zones de métadonnées et de données/ECC ne sont pas remplies ici.
            if zone_type == 'METADATA_AREA' or zone_type == 'DATA_ECC':
                continue

            # Calculer les coordonnées relatives pour get_fixed_pattern_bits
            # Cela nécessite de connaître le coin supérieur gauche de la zone spécifique
            relative_r, relative_c = -1, -1

            if zone_type.startswith('FP_TL'):
                base_coords = ml.get_zone_coordinates('FP_TL')
                if 'CORE' in zone_type: core_coords = ml.get_zone_coordinates('FP_TL_CORE'); relative_r, relative_c = r - core_coords[0], c - core_coords[2]
                else: relative_r, relative_c = r - base_coords[0], c - base_coords[2] # Pour la marge, relative à FP_TL
            elif zone_type.startswith('FP_TR'):
                base_coords = ml.get_zone_coordinates('FP_TR')
                if 'CORE' in zone_type: core_coords = ml.get_zone_coordinates('FP_TR_CORE'); relative_r, relative_c = r - core_coords[0], c - core_coords[2]
                else: relative_r, relative_c = r - base_coords[0], c - base_coords[2]
            elif zone_type.startswith('FP_BL'):
                base_coords = ml.get_zone_coordinates('FP_BL')
                if 'CORE' in zone_type: core_coords = ml.get_zone_coordinates('FP_BL_CORE'); relative_r, relative_c = r - core_coords[0], c - core_coords[2]
                else: relative_r, relative_c = r - base_coords[0], c - base_coords[2]
            elif zone_type == 'TP_H':
                tp_h_coords = ml.get_zone_coordinates('TP_H')
                relative_r = r - tp_h_coords[0] # Devrait être 0
                relative_c = c - tp_h_coords[2]
            elif zone_type == 'TP_V':
                tp_v_coords = ml.get_zone_coordinates('TP_V')
                relative_r = r - tp_v_coords[0]
                relative_c = c - tp_v_coords[2] # Devrait être 0
            elif zone_type.startswith('CCP_PATCH_'):
                patch_coords = ml.get_zone_coordinates(zone_type)
                relative_r = r - patch_coords[0]
                relative_c = c - patch_coords[2]
            else:
                # Should not happen if zone_type is not METADATA or DATA_ECC
                # print(f"Warning: Unhandled zone type {zone_type} in populate_fixed_zones for cell ({r},{c})")
                continue
            
            if relative_r >= 0 and relative_c >= 0: # Check if relative coords were set
                 bit_matrix[r][c] = ml.get_fixed_pattern_bits(zone_type, relative_r, relative_c)
            # else: 
                # This case indicates an issue with relative coordinate calculation logic for a zone_type
                # print(f"Error: Could not determine relative coords for {zone_type} at ({r},{c})")

    return bit_matrix

# --- Fonctions de la Phase 3 et suivantes seraient ajoutées ici ---
# def encode_message_to_matrix(...)

def encode_message_to_matrix(message_text: str, ecc_level_percent: int, custom_xor_key_str: str = None, ecc_mode: str = 'simple') -> list[list[str]]:
    """
    Orchestre l'encodage complet d'un message texte en une matrice de bits.
    Ajoute la prise en charge de Reed-Solomon (ecc_mode='rs').
    """
    bit_matrix = initialize_bit_matrix()
    populate_fixed_zones(bit_matrix)
    data_ecc_fill_order = ml.get_data_ecc_fill_order()
    available_data_ecc_bits = len(data_ecc_fill_order) * pc.BITS_PER_CELL

    if not (0 <= ecc_level_percent <= 100):
        raise ValueError("ecc_level_percent must be between 0 and 100.")

    # ECC mode: 'simple' (checksum) ou 'rs' (Reed-Solomon)
    if ecc_mode not in ('simple', 'rs'):
        raise ValueError(f"ecc_mode must be 'simple' or 'rs', got {ecc_mode}")

    # 1. Calcul du nombre de bits/symboles ECC
    if ecc_mode == 'rs':
        # Reed-Solomon: symboles de 8 bits (octets)
        total_bits = available_data_ecc_bits
        total_bytes = total_bits // 8
        if total_bytes > 255:
            raise ValueError(f"Trop de place pour RS: {total_bytes} octets (max 255). Réduisez la taille de la matrice ou la zone DATA_ECC.")
        # Nombre de symboles ECC (octets)
        num_ecc_symbols = int((total_bytes * ecc_level_percent) // 100)
        if num_ecc_symbols < 0: num_ecc_symbols = 0
        # Clamp to [1, total_bytes-1] -> must leave at least one data byte
        num_ecc_symbols = max(1, min(num_ecc_symbols, total_bytes - 1))
        num_data_bytes = total_bytes - num_ecc_symbols
        target_message_bit_length = num_data_bytes * 8
        # Pour la métadonnée, on encode le nombre de symboles ECC sur ecc_level_code (4 bits, max 15)
        ecc_code_for_metadata = min(num_ecc_symbols, (2**pc.METADATA_CONFIG['ecc_level_bits'])-1)
    else:
        # ECC simple: bits, multiple de 8
        raw_num_ecc_bits = available_data_ecc_bits * (ecc_level_percent / 100.0)
        num_ecc_bits = int(raw_num_ecc_bits // 8) * 8
        if num_ecc_bits < 0:
            num_ecc_bits = 0
        min_data_bits_needed = 8
        if num_ecc_bits > available_data_ecc_bits - min_data_bits_needed:
            num_ecc_bits = int((available_data_ecc_bits - min_data_bits_needed) // 8) * 8
            if num_ecc_bits < 0: num_ecc_bits = 0
        target_message_bit_length = available_data_ecc_bits - num_ecc_bits
        ecc_code_for_metadata = min(int(ecc_level_percent), (2**pc.METADATA_CONFIG['ecc_level_bits'])-1)

    if target_message_bit_length < 0:
        raise ValueError(f"Not enough space for message and ECC. Target message bits: {target_message_bit_length}")

    message_bits = dp.text_to_padded_bits(message_text, target_message_bit_length)

    if custom_xor_key_str:
        if len(custom_xor_key_str) != pc.METADATA_CONFIG['key_bits']:
            raise ValueError(f"Custom XOR key length must be {pc.METADATA_CONFIG['key_bits']} bits, got {len(custom_xor_key_str)}.")
        xor_key_for_metadata_and_data = custom_xor_key_str
    else:
        xor_key_for_metadata_and_data = dp.generate_xor_key(pc.METADATA_CONFIG['key_bits'])

    encrypted_message_bits = dp.apply_xor_cipher(message_bits, xor_key_for_metadata_and_data)
    encrypted_message_len_bits = len(encrypted_message_bits)

    # 2. Calcul des bits ECC
    if ecc_mode == 'rs':
        # Reed-Solomon: data + ecc = total_bytes*8 bits
        # On pad les données si besoin
        data_bits_padded = encrypted_message_bits.ljust(num_data_bytes*8, '0')
        ecc_bits = dp.calculate_reed_solomon_ecc(data_bits_padded, num_ecc_symbols)
        payload_stream = data_bits_padded + ecc_bits
        if len(payload_stream) != total_bytes*8:
            raise ValueError(f"Payload RS length mismatch: {len(payload_stream)} vs {total_bytes*8}")
        # Pour la métadonnée, on encode la longueur des données chiffrées (en bits)
        message_encrypted_len_for_metadata = len(data_bits_padded)
    else:
        if num_ecc_bits == 0:
            ecc_bits = ""
        else:
            ecc_bits = dp.calculate_simple_ecc(encrypted_message_bits, num_ecc_bits)
        payload_stream = encrypted_message_bits + ecc_bits
        if len(payload_stream) != target_message_bit_length + (num_ecc_bits if ecc_mode=='simple' else 0):
            raise ValueError(
                f"Payload stream length mismatch. Expected {target_message_bit_length + (num_ecc_bits if ecc_mode=='simple' else 0)}, "
                f"got {len(payload_stream)} (Encrypted: {len(encrypted_message_bits)}, ECC: {len(ecc_bits)})")
        message_encrypted_len_for_metadata = len(encrypted_message_bits)

    # 3. Préparer les métadonnées
    metadata_stream = dp.format_metadata_bits(
        protocol_version=1,
        ecc_level_code=ecc_code_for_metadata,
        message_encrypted_len=message_encrypted_len_for_metadata,
        xor_key_actual_bits=xor_key_for_metadata_and_data
    )

    # 4. Placer les métadonnées dans la matrice
    md_coords = ml.get_zone_coordinates('METADATA_AREA')
    md_r_start, md_r_end, md_c_start, md_c_end = md_coords
    current_bit_index_metadata = 0
    for r in range(md_r_start, md_r_end + 1):
        for c in range(md_c_start, md_c_end + 1):
            if ml.get_cell_zone_type(r,c) == 'METADATA_AREA':
                if current_bit_index_metadata >= len(metadata_stream):
                    continue

                bits_to_place = metadata_stream[
                    current_bit_index_metadata : current_bit_index_metadata + pc.BITS_PER_CELL
                ]

                if len(bits_to_place) != pc.BITS_PER_CELL:
                    raise ValueError(
                        "Metadata stream length not a multiple of BITS_PER_CELL. "
                        f"Remainder: {bits_to_place}"
                    )

                bit_matrix[r][c] = bits_to_place
                current_bit_index_metadata += pc.BITS_PER_CELL
    if current_bit_index_metadata != len(metadata_stream):
        raise ValueError(f"Metadata stream not fully placed. Expected {len(metadata_stream)} bits, placed {current_bit_index_metadata}.")

    # 5. Placer le payload (data+ecc) dans la matrice
    current_bit_index_payload = 0
    for r_coord, c_coord in data_ecc_fill_order:
        if current_bit_index_payload < len(payload_stream):
            bits_to_place = payload_stream[current_bit_index_payload : current_bit_index_payload + pc.BITS_PER_CELL]
            if len(bits_to_place) == pc.BITS_PER_CELL:
                bit_matrix[r_coord][c_coord] = bits_to_place
            else:
                if bits_to_place:
                    raise ValueError(f"Payload stream length not a multiple of BITS_PER_CELL for DATA_ECC. Remainder: {bits_to_place}")
            current_bit_index_payload += pc.BITS_PER_CELL
    if current_bit_index_payload != len(payload_stream):
        raise ValueError(f"Payload stream not fully placed in DATA_ECC area. Expected {len(payload_stream)} bits, placed {current_bit_index_payload}.")
    if len(payload_stream) != available_data_ecc_bits:
        raise ValueError(
            f"Final payload stream length ({len(payload_stream)}) does not match "
            f"available_data_ecc_bits ({available_data_ecc_bits}). This indicates an issue "
            f"in calculating message/ECC bit lengths.")
    return bit_matrix

# --- Fonctions de la Phase 3 et suivantes seraient ajoutées ici ---
# def encode_message_to_matrix(...) 