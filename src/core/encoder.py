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

def encode_message_to_matrix(message_text: str, ecc_level_percent: int, custom_xor_key_str: str = None) -> list[list[str]]:
    """
    Orchestre l'encodage complet d'un message texte en une matrice de bits.
    1. Initialise la matrice de bits.
    2. Place les motifs fixes.
    3. Prépare les données (texte -> bits, cryptage, ECC).
    4. Prépare les métadonnées.
    5. Place les métadonnées et le payload (données cryptées + ECC) dans la matrice.
    Retourne la bit_matrix complétée.
    """
    # 1. Initialiser bit_matrix
    bit_matrix = initialize_bit_matrix()

    # 2. Remplir les zones fixes (FP, TP, CCP)
    populate_fixed_zones(bit_matrix)

    # 3. Obtenir l'ordre de remplissage pour les données et ECC
    data_ecc_fill_order = ml.get_data_ecc_fill_order()
    available_data_ecc_bits = len(data_ecc_fill_order) * pc.BITS_PER_CELL

    # 4. Calculer num_ecc_bits
    # Doit être un multiple de BITS_PER_CELL (donc pair) et un multiple de 8 (pour calculate_simple_ecc)
    # Donc, multiple de lcm(2, 8) = 8.
    if not (0 <= ecc_level_percent <= 100):
        raise ValueError("ecc_level_percent must be between 0 and 100.")
    
    # Calculer le nombre brut de bits ECC
    raw_num_ecc_bits = available_data_ecc_bits * (ecc_level_percent / 100.0)
    
    # Arrondir au multiple de 8 inférieur ou égal (pour être sûr d'avoir assez de place et de respecter la contrainte ECC)
    num_ecc_bits = int(raw_num_ecc_bits // 8) * 8

    if num_ecc_bits < 0: num_ecc_bits = 0 # Ne peut pas être négatif
    # S'assurer qu'on ne demande pas plus de bits ECC que disponibles, moins une marge pour les données
    min_data_bits_needed = 8 # Au moins 1 octet de données utiles
    if num_ecc_bits > available_data_ecc_bits - min_data_bits_needed :
        num_ecc_bits = int((available_data_ecc_bits - min_data_bits_needed) // 8) * 8
        if num_ecc_bits < 0: num_ecc_bits = 0 # Au cas où available_data_ecc_bits est très petit

    # 5. Calculer la longueur cible pour les bits du message (avant cryptage)
    target_message_bit_length = available_data_ecc_bits - num_ecc_bits
    if target_message_bit_length < 0:
        raise ValueError(f"Not enough space for message and ECC. Target message bits: {target_message_bit_length}")

    # 6. Convertir le message texte en bits paddés
    message_bits = dp.text_to_padded_bits(message_text, target_message_bit_length)

    # 7. Gérer la clé XOR
    # La clé XOR pour les métadonnées est de pc.METADATA_CONFIG['key_bits']
    # La clé XOR pour les données peut être la même, ou différente si on le souhaitait.
    # Pour l'instant, on va supposer que la clé XOR générée/fournie est celle stockée dans les métadonnées.
    xor_key_for_metadata_and_data: str
    if custom_xor_key_str:
        if len(custom_xor_key_str) != pc.METADATA_CONFIG['key_bits']:
            raise ValueError(f"Custom XOR key length must be {pc.METADATA_CONFIG['key_bits']} bits, got {len(custom_xor_key_str)}.")
        xor_key_for_metadata_and_data = custom_xor_key_str
    else:
        xor_key_for_metadata_and_data = dp.generate_xor_key(pc.METADATA_CONFIG['key_bits'])

    # 8. Crypter les bits du message
    encrypted_message_bits = dp.apply_xor_cipher(message_bits, xor_key_for_metadata_and_data)
    encrypted_message_len_bits = len(encrypted_message_bits) # Devrait être target_message_bit_length

    # 9. Calculer les bits ECC sur les données cryptées
    # S'assurer que calculate_simple_ecc peut gérer le cas où num_ecc_bits est 0.
    # Ma fonction actuelle lève une erreur si num_ecc_bits est 0 ou non multiple de 8.
    # Si ecc_level_percent est 0, num_ecc_bits sera 0. Il faut gérer ce cas.
    if num_ecc_bits == 0:
        ecc_bits = ""
    else:
        ecc_bits = dp.calculate_simple_ecc(encrypted_message_bits, num_ecc_bits)
    
    # 10. Préparer les bits de métadonnées
    # L'ecc_level_code pour les métadonnées pourrait être le ecc_level_percent lui-même si c'est un code.
    # Le plan indique: format_metadata_bits(1, ecc_level_percent, len(encrypted_bits), xor_key)
    # Assumons que ecc_level_percent peut être directement utilisé comme code si < 16 (pour 4 bits)
    # Ou alors, il faut définir un mappage. Pour l'instant, passons ecc_level_percent.
    # La fonction format_metadata_bits s'attend à un entier pour ecc_level_code.
    # On va utiliser ecc_level_percent comme code pour l'instant.
    # S'assurer qu'il tient sur METADATA_CONFIG['ecc_level_bits']
    max_ecc_code = (2**pc.METADATA_CONFIG['ecc_level_bits']) - 1
    ecc_code_for_metadata = min(int(ecc_level_percent), max_ecc_code) # Simple troncature

    metadata_stream = dp.format_metadata_bits(
        protocol_version=1, # Version du protocole
        ecc_level_code=ecc_code_for_metadata, 
        message_encrypted_len=encrypted_message_len_bits,
        xor_key_actual_bits=xor_key_for_metadata_and_data
    )
    
    # 11. Placer metadata_stream dans les cellules METADATA de bit_matrix
    # Il faut un ordre de remplissage pour les métadonnées.
    # Utilisons un simple balayage ligne par ligne dans la zone METADATA_AREA.
    md_coords = ml.get_zone_coordinates('METADATA_AREA')
    md_r_start, md_r_end, md_c_start, md_c_end = md_coords
    
    current_bit_index_metadata = 0
    for r in range(md_r_start, md_r_end + 1):
        for c in range(md_c_start, md_c_end + 1):
            # Vérifier si la cellule est bien de type METADATA_AREA (au cas où la définition de zone serait complexe)
            # Normalement, toutes les cellules dans ces boucles le sont.
            if ml.get_cell_zone_type(r,c) == 'METADATA_AREA':
                if current_bit_index_metadata < len(metadata_stream):
                    bits_to_place = metadata_stream[current_bit_index_metadata : current_bit_index_metadata + pc.BITS_PER_CELL]
                    if len(bits_to_place) == pc.BITS_PER_CELL:
                         bit_matrix[r][c] = bits_to_place
                    else: # Fin du stream, ne remplit pas une cellule entière (ne devrait pas arriver si total_bits est multiple de BITS_PER_CELL)
                        # print(f"Warning: Trailing metadata bits not filling a full cell at ({r},{c}). Bits: {bits_to_place}")
                        # On pourrait padder ici ou lever une erreur si METADATA_CONFIG est mal alignée.
                        # Pour l'instant, on s'attend à un alignement parfait.
                        if bits_to_place: # S'il reste des bits
                             raise ValueError(f"Metadata stream length not a multiple of BITS_PER_CELL. Remainder: {bits_to_place}")
                    current_bit_index_metadata += pc.BITS_PER_CELL
                # else: # Plus de bits de métadonnées à placer (normal)
    
    if current_bit_index_metadata != len(metadata_stream):
        raise ValueError(f"Metadata stream not fully placed. Expected {len(metadata_stream)} bits, placed {current_bit_index_metadata}.")

    # 12. Concaténer payload_stream = encrypted_message_bits + ecc_bits
    payload_stream = encrypted_message_bits + ecc_bits
    if len(payload_stream) != target_message_bit_length + num_ecc_bits: # target_message_bit_length = len(encrypted_message_bits)
         raise ValueError(\
            f"Payload stream length mismatch. Expected {target_message_bit_length + num_ecc_bits}, " \
            f"got {len(payload_stream)} (Encrypted: {len(encrypted_message_bits)}, ECC: {len(ecc_bits)})")


    # 13. Remplir les cellules DATA_ECC de bit_matrix avec payload_stream
    current_bit_index_payload = 0
    for r_coord, c_coord in data_ecc_fill_order:
        if current_bit_index_payload < len(payload_stream):
            bits_to_place = payload_stream[current_bit_index_payload : current_bit_index_payload + pc.BITS_PER_CELL]
            if len(bits_to_place) == pc.BITS_PER_CELL:
                bit_matrix[r_coord][c_coord] = bits_to_place
            else: # Fin du payload_stream, ne remplit pas une cellule entière
                  # Cela ne devrait pas arriver si available_data_ecc_bits était correct
                  # et que payload_stream correspond à cette longueur.
                if bits_to_place:
                    raise ValueError(f"Payload stream length not a multiple of BITS_PER_CELL for DATA_ECC. Remainder: {bits_to_place}")
            current_bit_index_payload += pc.BITS_PER_CELL
        # else: # Plus de bits de payload à placer (peut arriver si payload plus court que l'espace dispo)
              # Ce cas est géré par text_to_padded_bits et le calcul de num_ecc_bits
              # qui s'assurent que le payload utilise tout l'espace disponible.

    if current_bit_index_payload != len(payload_stream):
        raise ValueError(f"Payload stream not fully placed in DATA_ECC area. Expected {len(payload_stream)} bits, placed {current_bit_index_payload}.")
    
    if len(payload_stream) != available_data_ecc_bits:
        # This is a critical check. The payload (encrypted data + ECC) MUST exactly fill the available DATA_ECC space.
        # Our calculations for target_message_bit_length and num_ecc_bits are designed to ensure this.
        raise ValueError(
            f"Final payload stream length ({len(payload_stream)}) does not match "
            f"available_data_ecc_bits ({available_data_ecc_bits}). This indicates an issue "
            f"in calculating message/ECC bit lengths."
        )

    # 14. Retourner la bit_matrix complétée
    return bit_matrix

# --- Fonctions de la Phase 3 et suivantes seraient ajoutées ici ---
# def encode_message_to_matrix(...) 