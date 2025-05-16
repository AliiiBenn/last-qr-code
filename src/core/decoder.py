from PIL import Image
import src.core.protocol_config as pc
import src.core.matrix_layout as ml
import src.core.image_utils as iu
import src.core.data_processing as dp
import numpy as np
from scipy.ndimage import label, find_objects
import cv2

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

def detect_finder_patterns(image: Image.Image) -> list[tuple[int, int]]:
    """
    Détecte les 3 Finder Patterns (FP) dans l'image.
    Retourne la liste des centres (x, y) en pixels des FP détectés.
    Méthode améliorée :
      - Convertit en niveaux de gris, seuillage Otsu (plus robuste).
      - Cherche les 3 plus grands carrés noirs/blancs (motif FP) par analyse de blocs.
      - Retourne les centres (x, y) en pixels.
    Plus tolérant aux artefacts de rotation et d'interpolation.
    """
    # Convertir en niveaux de gris
    gray = image.convert('L')
    arr = np.array(gray)
    # Seuillage Otsu (plus robuste que la moyenne)
    try:
        _, binary = cv2.threshold(arr, 0, 1, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    except ImportError:
        # fallback: simple mean
        thresh = arr.mean()
        binary = (arr < thresh).astype(np.uint8)
    # (DEBUG) Sauvegarder l'image seuillée si besoin
    # from PIL import Image as PILImage
    # PILImage.fromarray((binary*255).astype(np.uint8)).save('debug_fp_thresh.png')
    # Chercher les plus grands carrés noirs (FP core)
    labeled, num = label(binary)
    objects = find_objects(labeled)
    h, w = arr.shape
    min_size = min(h, w) * 0.04  # encore plus tolérant (avant: 0.07)
    max_aspect_ratio = 3.0  # tolère des rectangles jusqu'à 3:1
    candidates = []
    for _, sl in enumerate(objects):
        if sl is None:
            continue
        y0, y1 = sl[0].start, sl[0].stop
        x0, x1 = sl[1].start, sl[1].stop
        height = y1 - y0
        width = x1 - x0
        aspect = max(width / height, height / width) if min(width, height) > 0 else 0
        # Tolérance accrue sur la forme et la taille
        if (height >= min_size and width >= min_size and aspect <= max_aspect_ratio):
            # Calculer le centre
            cx = (x0 + x1) // 2
            cy = (y0 + y1) // 2
            candidates.append(((cx, cy), width * height))
    # Garder les 3 plus grands
    candidates.sort(key=lambda tup: -tup[1])
    num_candidates = len(candidates)
    centers = [c[0] for c in candidates[:3]]
    if len(centers) != 3:
        raise RuntimeError(f"Finder Patterns non détectés correctement (trouvés: {len(centers)}, candidats: {num_candidates}).")
    return centers

def identify_fp_corners(centers: list[tuple[int, int]]) -> dict:
    """
    Identifie les coins logiques (TL, TR, BL) à partir des 3 centres FP détectés.
    Retourne un dict {'TL': (x,y), 'TR': (x,y), 'BL': (x,y)}.
    - TL : le FP dont la somme des distances aux deux autres est la plus faible.
    - TR/BL : déterminés par orientation (produit vectoriel).
    """
    if len(centers) != 3:
        raise ValueError("Il faut exactement 3 centres FP pour identifier les coins.")
    if not all(
        isinstance(center, tuple) and len(center) == 2 and
        all(isinstance(coord, (int, float)) for coord in center)
        for center in centers
    ):
        raise ValueError("Les centres doivent être des tuples de coordonnées (x,y).")
    # Calculer la somme des distances pour chaque point
    dists = []
    for i in range(3):
        s = 0
        for j in range(3):
            if i != j:
                s += np.linalg.norm(np.array(centers[i]) - np.array(centers[j]))
        dists.append(s)
    tl_idx = int(np.argmin(dists))
    TL = centers[tl_idx]
    # Les deux autres
    idx = [0,1,2]
    idx.remove(tl_idx)
    A = np.array(TL)
    B = np.array(centers[idx[0]])
    C = np.array(centers[idx[1]])
    # Vecteurs
    v1 = B - A
    v2 = C - A
    # Produit vectoriel (z) pour savoir qui est à droite (TR) et en bas (BL)
    cross = np.cross(v1, v2)
    if cross > 0:
        TR = tuple(centers[idx[0]])
        BL = tuple(centers[idx[1]])
    else:
        TR = tuple(centers[idx[1]])
        BL = tuple(centers[idx[0]])
    return {'TL': TL, 'TR': TR, 'BL': BL}

def compute_rotation_angle(fp_corners: dict) -> float:
    """
    Calcule l'angle de rotation (en degrés) à appliquer pour aligner le segment TL→TR sur l'axe horizontal.
    - fp_corners : dict {'TL': (x,y), 'TR': (x,y), 'BL': (x,y)}
    Retourne l'angle en degrés (0 = déjà horizontal, positif = tourner dans le sens trigo).
    """
    required_keys = ['TL', 'TR', 'BL']
    if not all(key in fp_corners for key in required_keys):
        raise ValueError(f"fp_corners doit contenir les clés: {required_keys}")
    TL = np.array(fp_corners['TL'])
    TR = np.array(fp_corners['TR'])
    v = TR - TL
    angle_rad = np.arctan2(v[1], v[0])
    angle_deg = np.degrees(angle_rad)
    return angle_deg

def rotate_image(image: Image.Image, angle: float) -> Image.Image:
    """
    Tourne l'image de l'angle donné (en degrés, sens trigo) autour de son centre.
    - angle > 0 : sens anti-horaire (trigo)
    - angle < 0 : sens horaire
    Retourne une nouvelle image PIL de taille ajustée (expand=True pour ne rien couper).
    """
    # Utiliser expand=True pour éviter de couper les FP lors de la rotation
    return image.rotate(-angle, resample=Image.BICUBIC, expand=True, center=(image.width//2, image.height//2))

def estimate_cell_size_from_fp(fp_corners: dict, matrix_dim: int) -> float:
    """
    Estime la taille d'une cellule (en pixels) à partir des coins FP et de la dimension de la matrice.
    Utilise la distance TL→TR (largeur) et TL→BL (hauteur), puis fait la moyenne.
    """
    required_keys = ['TL', 'TR', 'BL']
    if not all(key in fp_corners for key in required_keys):
        raise ValueError(f"fp_corners doit contenir les clés: {required_keys}")
    if matrix_dim <= 1:
        raise ValueError("matrix_dim doit être supérieur à 1")
    TL = np.array(fp_corners['TL'])
    TR = np.array(fp_corners['TR'])
    BL = np.array(fp_corners['BL'])
    width = np.linalg.norm(TR - TL)
    height = np.linalg.norm(BL - TL)
    cell_size = (width + height) / 2 / (matrix_dim - 1)
    return cell_size

def extract_bit_matrix_from_rotated_image(
    image: Image.Image,
    fp_corners: dict,
    cell_size: float,
    matrix_dim: int,
    calibration_map: dict[str, tuple[int, int, int]],
    sampling_window: int = 2
) -> list[list[str]]:
    """
    Extrait la matrice de bits d'une image redressée (après rotation) en utilisant une transformation affine basée sur les 3 FP.
    Args:
        image: L'image à traiter
        fp_corners: Dictionnaire des coins des finder patterns {'TL': (x,y), 'TR': (x,y), 'BL': (x,y)}
        cell_size: Taille estimée d'une cellule en pixels
        matrix_dim: Dimension de la matrice (nombre de cellules par côté)
        calibration_map: Mapping des couleurs vers les bits
        sampling_window: Taille de la fenêtre d'échantillonnage (sampling_window=2 donne une fenêtre 5x5)
    Note: Cette fonction gère la rotation et le redimensionnement via une transformation affine,
    mais ne corrige pas complètement les distorsions de perspective. Pour des images avec
    une forte distorsion perspective, une transformation homographique (à 4 points) serait nécessaire.
    """
    # Validation des paramètres
    required_keys = ['TL', 'TR', 'BL']
    if not all(key in fp_corners for key in required_keys):
        raise ValueError(f"fp_corners doit contenir les clés: {required_keys}")
    if not calibration_map:
        raise ValueError("La calibration_map est vide.")
    if cell_size <= 0:
        raise ValueError("cell_size doit être positif")
    if matrix_dim <= 1:
        raise ValueError("matrix_dim doit être supérieur à 1")
    # 1. Positions logiques attendues des FP dans la grille (en pixels)
    fp_s = pc.FP_CONFIG['size']
    # Coordonnées logiques (centre de chaque FP en pixels dans la grille)
    tl_logical = np.array([(fp_s//2 + 0.5) * cell_size, (fp_s//2 + 0.5) * cell_size])
    tr_logical = np.array([(matrix_dim - fp_s//2 - 0.5) * cell_size, (fp_s//2 + 0.5) * cell_size])
    bl_logical = np.array([(fp_s//2 + 0.5) * cell_size, (matrix_dim - fp_s//2 - 0.5) * cell_size])
    # 2. Centres détectés (ordre TL, TR, BL)
    TL = np.array(fp_corners['TL'])
    TR = np.array(fp_corners['TR'])
    BL = np.array(fp_corners['BL'])
    src = np.stack([tl_logical, tr_logical, bl_logical])
    dst = np.stack([TL, TR, BL])
    # 3. Calcul de la matrice affine (2x3)
    affine = cv2.getAffineTransform(np.float32(src), np.float32(dst))
    # 4. Pour chaque cellule, calculer le centre logique puis transformer
    bit_matrix = [[None for _ in range(matrix_dim)] for _ in range(matrix_dim)]
    w, h = image.width, image.height
    for i in range(matrix_dim):
        for j in range(matrix_dim):
            pt = np.array([[(j + 0.5) * cell_size, (i + 0.5) * cell_size]], dtype=np.float32)
            mapped = cv2.transform(pt[None, :, :], affine)[0,0]
            x, y = int(round(mapped[0])), int(round(mapped[1]))
            x = max(0, min(w-1, x))
            y = max(0, min(h-1, y))
            rgb_vals = []
            for dx in range(-sampling_window, sampling_window+1):
                for dy in range(-sampling_window, sampling_window+1):
                    xx = x + dx
                    yy = y + dy
                    if 0 <= xx < w and 0 <= yy < h:
                        rgb_vals.append(image.getpixel((xx,yy)))
            if not rgb_vals:
                raise ValueError(f"Impossible d'échantillonner la cellule ({i},{j}) en ({x},{y}) : hors image.")
            avg_rgb = tuple(int(round(sum(c)/len(rgb_vals))) for c in zip(*rgb_vals))
            bits_pair = iu.rgb_to_bits(avg_rgb, calibration_map)
            bit_matrix[i][j] = bits_pair
    return bit_matrix

def get_tp_line_coords(fp_corners: dict, cell_size: float, matrix_dim: int, fp_size: int) -> dict:
    """
    Calcule les coordonnées (en pixels) de la ligne TP horizontale et de la colonne TP verticale
    à partir des coins FP, de la taille de cellule et de la dimension de matrice.
    Retourne un dict :
      {
        'TP_H': (start_px, end_px),
        'TP_V': (start_px, end_px)
      }
    start_px, end_px : tuples (x, y) en pixels
    """
    # Ligne TP horizontale : relie le FP TL au FP TR, à la ligne (fp_size-1) (juste sous le FP)
    TL = np.array(fp_corners['TL'])
    TR = np.array(fp_corners['TR'])
    BL = np.array(fp_corners['BL'])
    # Vecteurs de base
    vec_h = (TR - TL) / (matrix_dim - 1)
    vec_v = (BL - TL) / (matrix_dim - 1)
    # Ligne TP horizontale : ligne fp_size-1
    tp_h_row = fp_size - 1
    tp_h_start = TL + vec_v * tp_h_row
    tp_h_end = TR + vec_v * tp_h_row
    # Colonne TP verticale : colonne fp_size-1
    tp_v_col = fp_size - 1
    tp_v_start = TL + vec_h * tp_v_col
    tp_v_end = BL + vec_h * tp_v_col
    return {
        'TP_H': (tuple(tp_h_start), tuple(tp_h_end)),
        'TP_V': (tuple(tp_v_start), tuple(tp_v_end))
    }

def sample_tp_profile(image: Image.Image, tp_coords: tuple, num_samples: int) -> list:
    """
    Extrait le profil de couleurs (RVB) le long d'une Timing Pattern (TP).
    tp_coords : (start_px, end_px) en pixels
    num_samples : nombre d'échantillons (doit être >= au nombre de cellules sur la TP)
    Retourne une liste de tuples RVB.
    """
    from src.core.image_utils import sample_line_profile
    start_px, end_px = tp_coords
    return sample_line_profile(image, start_px, end_px, num_samples)

def detect_tp_transitions(profile: list, threshold: int = 50) -> list:
    """
    Détecte les indices de transitions de couleur dans un profil de TP.
    profile : liste de tuples RVB (ou valeurs de gris)
    threshold : seuil de différence pour considérer une transition (par défaut 50)
    Retourne la liste des indices où une transition est détectée.
    """
    transitions = []
    for i in range(1, len(profile)):
        c1 = profile[i-1]
        c2 = profile[i]
        # Distance euclidienne RVB
        dist = sum((a-b)**2 for a, b in zip(c1, c2)) ** 0.5
        if dist > threshold:
            transitions.append(i)
    return transitions

def interpolate_grid_positions(transitions: list, num_cells: int) -> list:
    """
    Calcule la position (en pixels) du centre de chaque cellule à partir des indices de transitions.
    transitions : liste des indices (en pixels) des transitions détectées (frontières de cellules)
    num_cells : nombre de cellules à interpoler (ex: MATRIX_DIM)
    Retourne une liste de positions (float) des centres de cellules.
    """
    if len(transitions) < num_cells + 1:
        # Si transitions manquantes, extrapoler en bordure
        # On suppose que transitions[0] est le bord gauche, transitions[-1] le bord droit
        # On interpole linéairement entre les extrêmes
        x0 = transitions[0]
        x1 = transitions[-1]
        positions = [x0 + (x1 - x0) * (i + 0.5) / num_cells for i in range(num_cells)]
        return positions
    # Sinon, transitions[i] = bord gauche de la cellule i
    positions = []
    for i in range(num_cells):
        left = transitions[i]
        right = transitions[i+1]
        positions.append((left + right) / 2)
    return positions

def extract_bit_matrix_with_tp(
    image: Image.Image,
    x_positions: list,
    y_positions: list,
    calibration_map: dict[str, tuple[int, int, int]]
    ) -> list[list[str]]:
    """
    Extrait la matrice de bits en utilisant les positions interpolées (x, y) pour chaque cellule.
    x_positions : liste des positions (en pixels) des centres de colonnes
    y_positions : liste des positions (en pixels) des centres de lignes
    calibration_map : pour la conversion couleur->bits
    Retourne la bit_matrix (len(y_positions) x len(x_positions))
    """
    matrix_dim_y = len(y_positions)
    matrix_dim_x = len(x_positions)
    bit_matrix = [[None for _ in range(matrix_dim_x)] for _ in range(matrix_dim_y)]
    w, h = image.width, image.height
    for i in range(matrix_dim_y):
        for j in range(matrix_dim_x):
            x = int(round(x_positions[j]))
            y = int(round(y_positions[i]))
            x = max(0, min(w-1, x))
            y = max(0, min(h-1, y))
            rgb_vals = []
            for dx in [-2,-1,0,1,2]:
                for dy in [-2,-1,0,1,2]:
                    xx = x+dx
                    yy = y+dy
                    if 0 <= xx < w and 0 <= yy < h:
                        rgb_vals.append(image.getpixel((xx,yy)))
            if not rgb_vals:
                raise ValueError(f"Impossible d'échantillonner la cellule ({i},{j}) en ({x},{y}) : hors image.")
            avg_rgb = tuple(int(round(sum(c)/len(rgb_vals))) for c in zip(*rgb_vals))
            bits_pair = iu.rgb_to_bits(avg_rgb, calibration_map)
            bit_matrix[i][j] = bits_pair
    return bit_matrix

def round_angle_to_90(angle):
    """Arrondit l'angle au multiple de 90° le plus proche (0, 90, 180, 270)."""
    angle = angle % 360
    return int(round(angle / 90.0)) * 90 % 360

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

    # 1.5 Detect rotation if applicable and correct it
    fp_corners = None
    try:
        # Detect finder patterns
        fp_centers = detect_finder_patterns(image)
        fp_corners = identify_fp_corners(fp_centers)
        # Calculate rotation and round to nearest 90°
        angle = compute_rotation_angle(fp_corners)
        angle_90 = round_angle_to_90(angle)
        if angle_90 != 0:  # Only rotate if angle is not 0
            image = rotate_image(image, angle_90)
            # Re-detect finder patterns after rotation
            fp_centers = detect_finder_patterns(image)
            fp_corners = identify_fp_corners(fp_centers)
        # Estimate cell size from finder patterns
        cell_px_size = estimate_cell_size_from_fp(fp_corners, pc.MATRIX_DIM)
    except Exception as e:
        # Fall back to simple parameter estimation if finder pattern detection fails
        print(f"Warning: Finder pattern detection failed: {e}. Falling back to simple estimation.")
        cell_px_size = estimate_image_parameters(image)

    calibration_map = perform_color_calibration(image, int(round(cell_px_size)))

    # 2. Extract Bit Matrix and Streams
    try:
        # Try to use the rotation-aware extraction if we have finder patterns
        if fp_corners is not None and cell_px_size is not None:
            bit_matrix = extract_bit_matrix_from_rotated_image(
                image, fp_corners, cell_px_size, pc.MATRIX_DIM, calibration_map
            )
        else:
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
        final_message = dp.padded_bits_to_text(padded_message_bits, original_bit_length=len(encrypted_message_bits))
    except ValueError as e: # e.g. UTF-8 decoding error
        raise ValueError(f"Decoder: Error converting bits to text. Data may be corrupted or not valid text. Details: {e}")
        
    return final_message 