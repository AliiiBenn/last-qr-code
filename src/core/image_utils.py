from PIL import Image, ImageDraw
import src.core.protocol_config as pc
import numpy as np
from typing import List, Tuple

def bits_to_rgb(bits_pair: str):
    """Convertit une paire de bits (ex: '01') en une couleur RVB en utilisant BITS_TO_COLOR_MAP."""
    if bits_pair not in pc.BITS_TO_COLOR_MAP:
        # Pourrait arriver si la bit_matrix contient None ou des valeurs incorrectes
        # print(f"Warning: bits_pair '{bits_pair}' not found in BITS_TO_COLOR_MAP. Defaulting to black.")
        return pc.BLACK # Retourner une couleur par défaut ou lever une erreur
    return pc.BITS_TO_COLOR_MAP[bits_pair]

def create_protocol_image(bit_matrix, cell_pixel_size: int, output_filename: str, margin_px: int = 0):
    """
    Crée une image graphique du protocole à partir de la bit_matrix.
    Sauvegarde l'image dans output_filename.
    Ajoute une marge blanche de margin_px pixels autour de la grille si margin_px > 0.
    """
    if margin_px < 0:
        raise ValueError("margin_px must be >= 0.")
    if not bit_matrix or not bit_matrix[0]:
        raise ValueError("bit_matrix is empty or invalid.")
    
    matrix_height = len(bit_matrix)
    matrix_width = len(bit_matrix[0])
    
    image_width = matrix_width * cell_pixel_size + 2 * margin_px
    image_height = matrix_height * cell_pixel_size + 2 * margin_px
    # Si besoin, arrondir la marge pour que image_width et image_height soient des multiples de cell_pixel_size
    if image_width % cell_pixel_size != 0:
        image_width += cell_pixel_size - (image_width % cell_pixel_size)
    if image_height % cell_pixel_size != 0:
        image_height += cell_pixel_size - (image_height % cell_pixel_size)
    
    image = Image.new("RGB", (image_width, image_height), pc.WHITE) # Fond blanc par défaut
    draw = ImageDraw.Draw(image)
    
    for r in range(matrix_height):
        for c in range(matrix_width):
            bits_pair = bit_matrix[r][c]
            if bits_pair is None:
                # Gérer les cellules non remplies (ex: DATA_ECC avant remplissage complet)
                # On pourrait les laisser blanches ou utiliser une couleur spéciale pour le débogage
                # Pour une image finale, elles devraient toutes être remplies.
                # print(f"Warning: Cell ({r},{c}) is None. Drawing as white.")
                color_rgb = pc.WHITE # Ou une autre couleur de débogage
            else:
                color_rgb = bits_to_rgb(bits_pair)
            
            # Coordonnées du rectangle pour la cellule (avec marge)
            x0 = c * cell_pixel_size + margin_px
            y0 = r * cell_pixel_size + margin_px
            x1 = x0 + cell_pixel_size
            y1 = y0 + cell_pixel_size
            
            draw.rectangle([x0, y0, x1, y1], fill=color_rgb)
            
    image.save(output_filename)
    # print(f"Image sauvegardée sous {output_filename}") 

def load_image_from_file(filepath: str):
    """Charge une image à partir du chemin de fichier spécifié."""
    try:
        image = Image.open(filepath)
        return image.convert("RGB") # S'assurer que l'image est en mode RGB
    except FileNotFoundError:
        raise FileNotFoundError(f"Le fichier image '{filepath}' n'a pas été trouvé.")
    except Exception as e:
        raise Exception(f"Erreur lors du chargement de l'image '{filepath}': {e}")

def rgb_to_bits(rgb_tuple: tuple[int, int, int], calibration_map: dict[str, tuple[int, int, int]]) -> str:
    """
    Convertit un tuple RVB en la paire de bits la plus proche en utilisant la calibration_map.
    La calibration_map est un dictionnaire comme {'00': (r,g,b), '01': (r,g,b), ...}.
    Utilise la distance euclidienne pour trouver la couleur la plus proche.
    """
    if not calibration_map:
        raise ValueError("La calibration_map est vide.")

    min_distance = float('inf')
    closest_bits = None

    r1, g1, b1 = rgb_tuple

    for bits_repr, ref_rgb_tuple in calibration_map.items():
        r2, g2, b2 = ref_rgb_tuple
        # Distance euclidienne au carré (pas besoin de sqrt pour la comparaison)
        distance = (r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2
        
        if distance < min_distance:
            min_distance = distance
            closest_bits = bits_repr
            
    if closest_bits is None:
        # Ne devrait pas arriver si calibration_map n'est pas vide
        raise RuntimeError("Impossible de déterminer les bits les plus proches à partir de la calibration_map.")
        
    return closest_bits 

def sample_line_profile(
    image: Image.Image,
    start_px: tuple[float, float],
    end_px: tuple[float, float],
    num_samples: int
) -> List[Tuple[int, int, int]]:
    """
    Échantillonne la couleur (RVB) le long d'un segment entre start_px et end_px (inclus),
    en num_samples points également espacés.
    Retourne une liste de tuples RVB (ou valeurs de gris si image convertie).
    """
    x0, y0 = start_px
    x1, y1 = end_px
    if num_samples <= 0:
        raise ValueError("num_samples must be a positive integer.")
    profile: List[Tuple[int, int, int]] = []
    for i in range(num_samples):
        t = i / (num_samples - 1) if num_samples > 1 else 0
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < image.width and 0 <= yi < image.height:
            profile.append(image.getpixel((xi, yi)))
        else:
            profile.append((0, 0, 0))  # Valeur par défaut si hors image
    return profile 

def perform_color_calibration(image: Image.Image, cell_px_size: int) -> dict[str, tuple[int, int, int]]:
    # ... code existant ...
    for i in range(len(expected_ccp_colors)):
        patch_zone_name = f"{ccp_patch_base_name}{i}"
        # ... code existant ...
        avg_r = int(round(sum_r / num_pixels_sampled))
        avg_g = int(round(sum_g / num_pixels_sampled))
        avg_b = int(round(sum_b / num_pixels_sampled))
        sampled_rgb = (avg_r, avg_g, avg_b)
        print(f"[CALIBRATION] CCP patch {i}: sampled_rgb={sampled_rgb}, expected={theoretical_color_of_this_patch}")
        # ... existing code ... 