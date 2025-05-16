import src.core.protocol_config as pc
import numpy as np

# Cache pour les coordonnées des zones afin d'éviter les recalculs
_zone_coords_cache = {}
_all_defined_zones_cache = None # Cache pour les noms de toutes les zones spécifiques

def _get_fp_core_coords(fp_r_start, fp_c_start):
    fp_s = pc.FP_CONFIG['size']
    fp_m = pc.FP_CONFIG['margin']
    return (fp_r_start + fp_m, fp_r_start + fp_s - 1 - fp_m,
            fp_c_start + fp_m, fp_c_start + fp_s - 1 - fp_m)

def get_zone_coordinates(zone_name):
    """
    Retourne les coordonnées (r_start, r_end, c_start, c_end) pour une zone donnée.
    Pour 'CCP_AREA', retourne une liste de coordonnées pour chaque patch.
    Les coordonnées des marges FP sont implicites et gérées par get_cell_zone_type.
    """
    if zone_name in _zone_coords_cache:
        return _zone_coords_cache[zone_name]

    fp_s = pc.FP_CONFIG['size']
    md_dim = pc.MATRIX_DIM
    
    coords = None

    # Finder Patterns (FP) - Coordonnées globales de l'emprise du FP (incluant marge)
    fp_tl_r_start, fp_tl_c_start = 0, 0
    fp_tr_r_start, fp_tr_c_start = 0, md_dim - fp_s
    fp_bl_r_start, fp_bl_c_start = md_dim - fp_s, 0

    if zone_name == 'FP_TL': coords = (fp_tl_r_start, fp_tl_r_start + fp_s - 1, fp_tl_c_start, fp_tl_c_start + fp_s - 1)
    elif zone_name == 'FP_TR': coords = (fp_tr_r_start, fp_tr_r_start + fp_s - 1, fp_tr_c_start, fp_tr_c_start + fp_s - 1)
    elif zone_name == 'FP_BL': coords = (fp_bl_r_start, fp_bl_r_start + fp_s - 1, fp_bl_c_start, fp_bl_c_start + fp_s - 1)
    
    elif zone_name == 'FP_TL_CORE': coords = _get_fp_core_coords(fp_tl_r_start, fp_tl_c_start)
    elif zone_name == 'FP_TR_CORE': coords = _get_fp_core_coords(fp_tr_r_start, fp_tr_c_start)
    elif zone_name == 'FP_BL_CORE': coords = _get_fp_core_coords(fp_bl_r_start, fp_bl_c_start)

    # Timing Patterns (TP)
    # Situés à la ligne/colonne juste à l'extérieur du noyau des FP (index fp_s - 1 - margin -1),
    # ou plus classiquement à l'index 6 pour des FP de taille 7 (fp_s -1)
    tp_idx = fp_s - 1 # Exemple: index 6 si fp_s = 7
    if zone_name == 'TP_H': coords = (tp_idx, tp_idx, fp_s, md_dim - 1 - fp_s)
    elif zone_name == 'TP_V': coords = (fp_s, md_dim - 1 - fp_s, tp_idx, tp_idx)
    
    # Metadata Area
    md_rows = pc.METADATA_CONFIG['rows']
    md_cols = pc.METADATA_CONFIG['cols']
    if zone_name == 'METADATA_AREA':
        # Placée à gauche du FP_TR
        r_start = 0
        c_start = md_dim - fp_s - md_cols # 35 - 7 - 6 = 22
        coords = (r_start, r_start + md_rows - 1, c_start, c_start + md_cols - 1)

    # Calibration Color Patches (CCP)
    ccp_ps = pc.CCP_CONFIG['patch_size']
    if zone_name.startswith('CCP_PATCH_'):
        patch_index = int(zone_name.split('_')[-1])
        # Placés à droite du FP_BL, en ligne
        r_start = md_dim - fp_s # row 28
        c_start = fp_s + (patch_index * ccp_ps) # col 7, 9, 11, 13 for patches 0,1,2,3
        coords = (r_start, r_start + ccp_ps - 1, c_start, c_start + ccp_ps - 1)
    elif zone_name == 'CCP_AREA': # Fournit les coordonnées de tous les patches
        coords_list = []
        for i in range(len(pc.CCP_CONFIG['colors'])):
             # Placés à droite du FP_BL, en ligne
            r_start_patch = md_dim - fp_s 
            c_start_patch = fp_s + (i * ccp_ps)
            coords_list.append((r_start_patch, r_start_patch + ccp_ps - 1, c_start_patch, c_start_patch + ccp_ps - 1))
        coords = coords_list


    if coords is not None:
        _zone_coords_cache[zone_name] = coords
        return coords
    raise ValueError(f"Unknown or non-cacheable zone name: {zone_name}")

def _get_all_defined_zone_names():
    """Retourne une liste de tous les noms de zones spécifiques pour get_cell_zone_type."""
    global _all_defined_zones_cache
    if _all_defined_zones_cache is None:
        zones = [
            'FP_TL_CORE', 'FP_TR_CORE', 'FP_BL_CORE',
            'FP_TL', 'FP_TR', 'FP_BL', # Pour identifier les marges par différence
            'TP_H', 'TP_V',
            'METADATA_AREA'
        ]
        for i in range(len(pc.CCP_CONFIG['colors'])):
            zones.append(f'CCP_PATCH_{i}')
        _all_defined_zones_cache = zones
    return _all_defined_zones_cache

def get_cell_zone_type(row, col):
    """Détermine le type de zone pour une cellule (row, col)."""
    
    # Vérifier les zones les plus spécifiques/petites en premier (cores, patches)
    # Puis les zones plus larges (FP global pour les marges, TP, Metadata)
    
    # Check Cores first
    for fp_core_name in ['FP_TL_CORE', 'FP_TR_CORE', 'FP_BL_CORE']:
        r_start, r_end, c_start, c_end = get_zone_coordinates(fp_core_name)
        if r_start <= row <= r_end and c_start <= col <= c_end:
            return fp_core_name # ex: 'FP_TL_CORE'

    # Check CCP Patches
    for i in range(len(pc.CCP_CONFIG['colors'])):
        patch_name = f'CCP_PATCH_{i}'
        r_start, r_end, c_start, c_end = get_zone_coordinates(patch_name)
        if r_start <= row <= r_end and c_start <= col <= c_end:
            return patch_name # ex: 'CCP_PATCH_0'

    # Check full FPs to identify Margins
    # Margin is part of FP_XX but not FP_XX_CORE
    for fp_name in ['FP_TL', 'FP_TR', 'FP_BL']:
        r_start, r_end, c_start, c_end = get_zone_coordinates(fp_name)
        if r_start <= row <= r_end and c_start <= col <= c_end:
            # At this point, we know it's not a core cell of this FP
            return f"{fp_name}_MARGIN" # ex: 'FP_TL_MARGIN'

    # Check Timing Patterns
    for tp_name in ['TP_H', 'TP_V']:
        r_start, r_end, c_start, c_end = get_zone_coordinates(tp_name)
        if r_start <= row <= r_end and c_start <= col <= c_end:
            return tp_name # ex: 'TP_H'

    # Check Metadata Area
    md_r_start, md_r_end, md_c_start, md_c_end = get_zone_coordinates('METADATA_AREA')
    if md_r_start <= row <= md_r_end and md_c_start <= col <= md_c_end:
        return 'METADATA_AREA'

    return 'DATA_ECC' # Par défaut, c'est une cellule de données/ECC

def _color_to_bits(color_tuple):
    bits = pc.COLOR_TO_BITS_MAP.get(color_tuple)
    if bits is None:
        raise ValueError(f"Color {color_tuple} not found in COLOR_TO_BITS_MAP.")
    return bits

def get_fixed_pattern_bits(zone_type, relative_row, relative_col):
    """
    Retourne les 2 bits pour une cellule dans un motif fixe.
    relative_row/col sont relatives au coin supérieur gauche du motif spécifique (core, patch, ligne TP).
    Pour les marges FP, zone_type sera 'FP_TL_MARGIN', etc.
    """
    fp_m = pc.FP_CONFIG['margin']

    if 'CORE' in zone_type: # FP_TL_CORE, FP_TR_CORE, FP_BL_CORE
        # Core size is (FP_CONFIG['size'] - 2 * margin)
        core_dim = pc.FP_CONFIG['size'] - 2 * fp_m # e.g., 7 - 2*1 = 5
        # Pattern concentrique pour le core 5x5 (si size=7, margin=1)
        # pattern_colors = [RED, BLUE, BLACK, WHITE] (du centre vers l'extérieur pour le FP)
        # C0 (center) est maintenant spécifique à chaque coin
        center_coord = core_dim // 2 # e.g. 5//2 = 2
        dist_r = abs(relative_row - center_coord)
        dist_c = abs(relative_col - center_coord)
        max_dist = max(dist_r, dist_c)

        # Déterminer le coin (TL, TR, BL) à partir du zone_type
        if zone_type.startswith('FP_TL'):
            center_color = pc.FP_CONFIG['center_colors']['TL']
        elif zone_type.startswith('FP_TR'):
            center_color = pc.FP_CONFIG['center_colors']['TR']
        elif zone_type.startswith('FP_BL'):
            center_color = pc.FP_CONFIG['center_colors']['BL']
        else:
            center_color = pc.FP_CONFIG['pattern_colors'][0] # fallback

        if max_dist == 0: # Centre
            color = center_color
        elif max_dist == 1: # Premier anneau
            color = pc.FP_CONFIG['pattern_colors'][1]
        elif max_dist == 2: # Deuxième anneau (bord du core 5x5)
            color = pc.FP_CONFIG['pattern_colors'][2]
        else: # Ne devrait pas arriver pour un core 5x5 et rel_row/col 0-4
            raise ValueError("Relative coordinates out of bounds for FP core pattern.")
        return _color_to_bits(color)

    elif 'MARGIN' in zone_type: # FP_TL_MARGIN, etc.
        # La marge utilise la couleur la plus externe des pattern_colors
        color = pc.FP_CONFIG['pattern_colors'][3] # e.g. WHITE
        return _color_to_bits(color)

    elif zone_type.startswith('CCP_PATCH_'):
        patch_idx = int(zone_type.split('_')[-1])
        color = pc.CCP_CONFIG['colors'][patch_idx]
        return _color_to_bits(color)

    elif zone_type == 'TP_H': # Timing Pattern Horizontal
        # Alternance basée sur la colonne relative (relative_col est 0 pour la première cellule du TP)
        color = pc.TP_CONFIG['line_color1'] if relative_col % 2 == 0 else pc.TP_CONFIG['line_color2']
        return _color_to_bits(color)
    
    elif zone_type == 'TP_V': # Timing Pattern Vertical
        # Alternance basée sur la ligne relative (relative_row est 0 pour la première cellule du TP)
        color = pc.TP_CONFIG['line_color1'] if relative_row % 2 == 0 else pc.TP_CONFIG['line_color2']
        return _color_to_bits(color)

    raise ValueError(f"Unknown zone_type for get_fixed_pattern_bits: {zone_type}")


def get_data_ecc_fill_order():
    """
    Retourne une liste ordonnée de (row, col) pour les cellules DATA_ECC,
    définissant l'ordre de balayage (simple balayage ligne par ligne).
    """
    fill_order = []
    for r in range(pc.MATRIX_DIM):
        for c in range(pc.MATRIX_DIM):
            if get_cell_zone_type(r, c) == 'DATA_ECC':
                fill_order.append((r, c))
    return fill_order 