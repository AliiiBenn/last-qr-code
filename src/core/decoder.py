from PIL import Image
import src.core.protocol_config as pc
import src.core.matrix_layout as ml
import src.core.image_utils as iu
import src.core.data_processing as dp

def estimate_image_parameters(image: Image.Image) -> int:
    """
    Estime la taille d'une cellule en pixels (version simplifiée).
    Prend la largeur de l'image et la divise par MATRIX_DIM.
    Retourne cell_px_size (entier).
    """
    if image is None:
        raise ValueError("L'image fournie est None.")
    
    # Algorithme simplifié : cell_px = image.width // MATRIX_DIM
    # Pour une version plus robuste, il faudrait détecter les Finder Patterns
    # pour déterminer l'orientation, la perspective, et la taille réelle des cellules.
    cell_px_size = image.width // pc.MATRIX_DIM
    
    if cell_px_size <= 0:
        raise ValueError(f"La taille de cellule estimée ({cell_px_size}px) est invalide. "
                         f"L'image est peut-être trop petite (largeur: {image.width}px) pour la dimension de la matrice ({pc.MATRIX_DIM}).")
    return cell_px_size

def perform_color_calibration(image: Image.Image, cell_px_size: int) -> dict[str, tuple[int, int, int]]:
    """
    Effectue la calibration des couleurs en échantillonnant les couleurs RVB moyennes
    des zones centrales des patches de calibration (CCP).
    Retourne une calibration_map: {'00': sampled_white_rgb, '01': sampled_black_rgb, ...}
    """
    if image is None:
        raise ValueError("L'image fournie est None pour la calibration.")
    if cell_px_size <= 0:
        raise ValueError("La taille de cellule (cell_px_size) doit être positive.")

    calibration_map = {}
    ccp_patch_base_name = 'CCP_PATCH_'
    expected_ccp_colors = pc.CCP_CONFIG['colors'] # Liste des couleurs RVB attendues pour les patches
    
    # Les bits correspondants aux pc.CCP_CONFIG['colors']
    # Il faut mapper la couleur attendue du patch à sa représentation en bits
    # pc.COLOR_TO_BITS_MAP: { (R,G,B) : 'bits' }
    # pc.CCP_CONFIG['colors']: [(R,G,B)_0, (R,G,B)_1, ...]
    # calibration_map doit être { 'bits_0': sampled_rgb_for_patch_0, ... }

    bits_for_ccp_color = {color: bits for bits, color in pc.BITS_TO_COLOR_MAP.items()}

    for i in range(len(expected_ccp_colors)):
        patch_zone_name = f"{ccp_patch_base_name}{i}"
        try:
            r_start, r_end, c_start, c_end = ml.get_zone_coordinates(patch_zone_name)
        except ValueError:
            raise ValueError(f"Coordonnées pour {patch_zone_name} non trouvées. Vérifiez matrix_layout.py.")

        # Échantillonner la couleur au centre du patch
        # Pour un patch de 2x2 cellules, le centre est entre les cellules.
        # Nous allons prendre le pixel central de la première cellule du patch (en haut à gauche du patch).
        # Ou, mieux, une petite zone au centre du patch global.
        
        # Coordonnées en pixels du patch
        patch_x_start_px = c_start * cell_px_size
        patch_y_start_px = r_start * cell_px_size
        patch_width_px = (c_end - c_start + 1) * cell_px_size
        patch_height_px = (r_end - r_start + 1) * cell_px_size

        # Définir une petite zone d'échantillonnage au centre du patch (par exemple, 1/4 de la taille du patch)
        sample_area_width = max(1, patch_width_px // 2)
        sample_area_height = max(1, patch_height_px // 2)
        
        sample_x_offset = (patch_width_px - sample_area_width) // 2
        sample_y_offset = (patch_height_px - sample_area_height) // 2
        
        sample_x_start = patch_x_start_px + sample_x_offset
        sample_y_start = patch_y_start_px + sample_y_offset
        
        num_pixels_sampled = 0
        sum_r, sum_g, sum_b = 0, 0, 0
        
        for x_px in range(sample_x_start, sample_x_start + sample_area_width):
            for y_px in range(sample_y_start, sample_y_start + sample_area_height):
                if 0 <= x_px < image.width and 0 <= y_px < image.height:
                    r_val, g_val, b_val = image.getpixel((x_px, y_px))
                    sum_r += r_val
                    sum_g += g_val
                    sum_b += b_val
                    num_pixels_sampled += 1
        
        if num_pixels_sampled == 0:
            raise ValueError(f"Impossible d'échantillonner des pixels pour {patch_zone_name} à ({r_start},{c_start}). "
                             f"Vérifiez les coordonnées et la taille de l'image/cellule.")

        avg_r = int(round(sum_r / num_pixels_sampled))
        avg_g = int(round(sum_g / num_pixels_sampled))
        avg_b = int(round(sum_b / num_pixels_sampled))
        
        sampled_rgb = (avg_r, avg_g, avg_b)
        
        # Quelle paire de bits cette couleur de patch représente-t-elle ?
        # pc.CCP_CONFIG['colors'] est la liste des couleurs *théoriques* des patches dans l'ordre 0, 1, 2, 3
        # Nous avons besoin des bits que ces couleurs théoriques représentent.
        theoretical_color_of_this_patch = expected_ccp_colors[i]
        bits_representation = bits_for_ccp_color.get(theoretical_color_of_this_patch)
        
        if bits_representation is None:
            raise ValueError(f"La couleur théorique {theoretical_color_of_this_patch} du patch CCP {i} "
                             f"n'a pas de correspondance dans BITS_TO_COLOR_MAP.")
            
        calibration_map[bits_representation] = sampled_rgb
        # print(f"Calibré {bits_representation} (patch {i}, théorique {theoretical_color_of_this_patch}) -> {sampled_rgb}")

    if len(calibration_map) != len(expected_ccp_colors):
        raise RuntimeError(f"La calibration des couleurs a échoué: {len(calibration_map)} couleurs calibrées, "
                         f"{len(expected_ccp_colors)} attendues.")
                         
    return calibration_map

# --- Fonctions des Phases 5 et 6 à ajouter ici ---

def extract_bit_matrix_from_image(
    image: Image.Image, 
    cell_px_size: int, 
    calibration_map: dict[str, tuple[int, int, int]]
    ) -> list[list[str]]:
    """
    Convertit l'image en matrice de bits.
    Échantillonne la couleur au centre de chaque cellule et utilise iu.rgb_to_bits.
    """
    if image is None:
        raise ValueError("L'image fournie est None.")
    if cell_px_size <= 0:
        raise ValueError("La taille de cellule (cell_px_size) doit être positive.")
    if not calibration_map:
        raise ValueError("La calibration_map est vide.")

    # S'attendre à ce que l'image ait des dimensions qui sont des multiples de cell_px_size
    # et correspondent à MATRIX_DIM
    expected_width = pc.MATRIX_DIM * cell_px_size
    expected_height = pc.MATRIX_DIM * cell_px_size
    if image.width != expected_width or image.height != expected_height:
        print(f"Warning: Image dimensions ({image.width}x{image.height}) ne correspondent pas exactement "
              f"aux dimensions attendues ({expected_width}x{expected_height}) basées sur MATRIX_DIM et cell_px_size.")

    bit_matrix = [[None for _ in range(pc.MATRIX_DIM)] for _ in range(pc.MATRIX_DIM)]
    pixel_offset_within_cell = cell_px_size // 2 # Échantillonner au centre de la cellule

    for r_cell in range(pc.MATRIX_DIM): # Ligne de la cellule dans la matrice
        for c_cell in range(pc.MATRIX_DIM): # Colonne de la cellule dans la matrice
            # Calculer le centre en pixels de la cellule
            center_x_px = c_cell * cell_px_size + pixel_offset_within_cell
            center_y_px = r_cell * cell_px_size + pixel_offset_within_cell

            # S'assurer que les coordonnées du pixel sont dans les limites de l'image
            if 0 <= center_x_px < image.width and 0 <= center_y_px < image.height:
                sampled_rgb = image.getpixel((center_x_px, center_y_px))
                bits_pair = iu.rgb_to_bits(sampled_rgb, calibration_map)
                bit_matrix[r_cell][c_cell] = bits_pair
            else:
                # Cela ne devrait pas arriver si l'image a la bonne taille et cell_px_size est correct
                print(f"Warning: Coordonnées de pixel ({center_x_px},{center_y_px}) hors limites pour la cellule ({r_cell},{c_cell}). Laissant à None.")
                # bit_matrix[r_cell][c_cell] reste None
    
    return bit_matrix

def extract_metadata_stream(bit_matrix: list[list[str]]) -> str:
    """
    Extrait le flux de bits des métadonnées à partir de la bit_matrix.
    Lit les bits des cellules METADATA (définies par matrix_layout) et les concatène.
    """
    if not bit_matrix or not bit_matrix[0] or len(bit_matrix) != pc.MATRIX_DIM or len(bit_matrix[0]) != pc.MATRIX_DIM:
        raise ValueError("bit_matrix fournie est invalide ou de mauvaise dimension.")

    metadata_bits_list = []
    md_coords = ml.get_zone_coordinates('METADATA_AREA')
    md_r_start, md_r_end, md_c_start, md_c_end = md_coords

    # Ordre de lecture: balayage ligne par ligne dans la zone de métadonnées
    for r in range(md_r_start, md_r_end + 1):
        for c in range(md_c_start, md_c_end + 1):
            # Vérifier si la cellule est bien de type METADATA_AREA
            # Normalement, get_zone_coordinates nous donne la bonne zone, mais une vérification supplémentaire est possible.
            # if ml.get_cell_zone_type(r, c) == 'METADATA_AREA': 
            cell_bits = bit_matrix[r][c]
            if cell_bits is None or len(cell_bits) != pc.BITS_PER_CELL:
                raise ValueError(f"Cellule de métadonnées ({r},{c}) n'a pas de bits valides (valeur: {cell_bits}).")
            metadata_bits_list.append(cell_bits)
            # else: # Ne devrait pas arriver si md_coords est correct
            #     raise RuntimeError(f"Cell ({r},{c}) dans les coordonnées METADATA_AREA n'est pas de type METADATA_AREA.")
                
    metadata_stream = "".join(metadata_bits_list)
    
    # Vérifier si la longueur correspond à METADATA_CONFIG['total_bits']
    expected_total_metadata_bits = pc.METADATA_CONFIG['total_bits']
    if len(metadata_stream) != expected_total_metadata_bits:
        raise ValueError(f"Longueur du flux de métadonnées extrait ({len(metadata_stream)}) "
                         f"ne correspond pas à METADATA_CONFIG total_bits ({expected_total_metadata_bits}).")
    return metadata_stream

def extract_payload_stream(bit_matrix: list[list[str]]) -> str:
    """
    Extrait le flux de bits du payload (données cryptées + ECC) à partir de la bit_matrix.
    Utilise matrix_layout.get_data_ecc_fill_order().
    """
    if not bit_matrix or not bit_matrix[0] or len(bit_matrix) != pc.MATRIX_DIM or len(bit_matrix[0]) != pc.MATRIX_DIM:
        raise ValueError("bit_matrix fournie est invalide ou de mauvaise dimension.")

    payload_bits_list = []
    data_ecc_fill_order = ml.get_data_ecc_fill_order()

    for r, c in data_ecc_fill_order:
        cell_bits = bit_matrix[r][c]
        if cell_bits is None or len(cell_bits) != pc.BITS_PER_CELL:
            raise ValueError(f"Cellule de données/ECC ({r},{c}) n'a pas de bits valides (valeur: {cell_bits}).")
        payload_bits_list.append(cell_bits)
        
    payload_stream = "".join(payload_bits_list)
    
    # La longueur attendue du payload_stream est le nombre de cellules DATA_ECC * BITS_PER_CELL
    expected_payload_bits = len(data_ecc_fill_order) * pc.BITS_PER_CELL
    if len(payload_stream) != expected_payload_bits:
        # Cette erreur ne devrait pas se produire si data_ecc_fill_order est correct
        # et que toutes les cellules correspondantes ont été remplies.
        raise ValueError(f"Longueur du flux de payload extrait ({len(payload_stream)}) "
                         f"ne correspond pas à la longueur attendue de l'espace DATA_ECC ({expected_payload_bits}).")

    return payload_stream

# --- Main Decoding Orchestration (Phase 6/7) ---

def decode_image_to_message(image_path: str) -> str:
    """
    Decodes a protocol image from the given path and returns the embedded message.
    Orchestrates the full decoding process.
    """
    # 1. Load Image and Estimate Parameters
    try:
        image = iu.load_image_from_file(image_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Decoder: Image file not found at {image_path}")
    except Exception as e:
        raise ValueError(f"Decoder: Error loading image '{image_path}'. Details: {e}")

    cell_px_size = estimate_image_parameters(image)
    calibration_map = perform_color_calibration(image, cell_px_size)

    # 2. Extract Bit Matrix and Streams
    try:
        bit_matrix = extract_bit_matrix_from_image(image, cell_px_size, calibration_map)
        metadata_stream = extract_metadata_stream(bit_matrix)
        payload_stream = extract_payload_stream(bit_matrix)
    except ValueError as e:
        # Errors from extract_* functions (e.g. invalid bits, wrong length)
        raise ValueError(f"Decoder: Error extracting bitstreams from image. Details: {e}")

    # 3. Interpret Metadata and Recover Data
    try:
        parsed_metadata = dp.parse_metadata_bits(metadata_stream)
    except ValueError as e:
        raise ValueError(f"Decoder: Error parsing metadata. Details: {e}")

    # --- Protocol Version Check (Future enhancement) ---
    # if parsed_metadata.get('protocol_version') != 1: # Assuming 1 is current/supported version
    #     raise ValueError(f"Decoder: Unsupported protocol version {parsed_metadata.get('protocol_version')}.")

    xor_key = parsed_metadata['xor_key']
    message_encrypted_len = parsed_metadata['message_encrypted_len']
    # ecc_level_code = parsed_metadata['ecc_level_code'] # This is the ecc_level_percent, currently not directly used for ECC bit count here

    # Separate encrypted message and ECC bits from payload_stream
    if not isinstance(message_encrypted_len, int) or message_encrypted_len < 0:
        raise ValueError(
            f"Decoder: Invalid 'message_encrypted_len' ({message_encrypted_len}) from metadata."
        )
    if message_encrypted_len > len(payload_stream):
        raise ValueError(
            f"Decoder: Metadata 'message_encrypted_len' ({message_encrypted_len}) "
            f"is greater than actual payload stream length ({len(payload_stream)})."
        )
    
    encrypted_message_bits = payload_stream[:message_encrypted_len]
    received_ecc_bits = payload_stream[message_encrypted_len:]
    
    # Verify ECC
    # verify_simple_ecc will also handle received_ecc_bits length checks (must be multiple of 8 or zero)
    is_ecc_valid = dp.verify_simple_ecc(encrypted_message_bits, received_ecc_bits)
    if not is_ecc_valid:
        raise ValueError("Decoder: ECC verification failed. Data may be corrupted.")

    # Decrypt message
    try:
        padded_message_bits = dp.apply_xor_cipher(encrypted_message_bits, xor_key)
    except ValueError as e: # e.g. empty XOR key from metadata (though parse_metadata should prevent this)
        raise ValueError(f"Decoder: Error applying XOR cipher. Details: {e}")
    
    # Convert to text
    try:
        final_message = dp.padded_bits_to_text(padded_message_bits)
    except ValueError as e: # e.g. UTF-8 decoding error
        raise ValueError(f"Decoder: Error converting bits to text. Data may be corrupted or not valid text. Details: {e}")
        
    return final_message 