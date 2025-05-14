import copy
# Constantes et paramètres de configuration du protocole

# --- V1 (Compatibilité) ---
MATRIX_DIM = 35
BITS_PER_CELL = 2

# Mappages Couleurs <-> Bits
# Définir les couleurs RVB (par exemple, NOIR, BLANC, ROUGE, BLEU)
# Ces valeurs sont des exemples, à ajuster si nécessaire
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0) # Ajouté pour plus d'options si besoin

COLOR_TO_BITS_MAP = {
    WHITE: '00',  # Exemple: Blanc pour '00'
    BLACK: '01',  # Exemple: Noir pour '01'
    RED:   '10',  # Exemple: Rouge pour '10'
    BLUE:  '11',  # Exemple: Bleu pour '11'
}

BITS_TO_COLOR_MAP = {v: k for k, v in COLOR_TO_BITS_MAP.items()}

# Configuration des Zones Fixes (FP - Finder Patterns, TP - Timing Patterns, CCP - Calibration Color Patches)
FP_CONFIG = {
    'size': 7,          # Taille du motif de détection (ex: 7x7 cellules)
    'margin': 1,        # Marge autour du motif de détection central
    'pattern_colors': [RED, BLUE, BLACK, WHITE] # Couleurs pour les motifs concentriques, du centre vers l'extérieur
}

TP_CONFIG = {
    'line_color1': BLACK, # Couleur 1 pour les motifs de synchronisation
    'line_color2': WHITE  # Couleur 2 pour les motifs de synchronisation
}

CCP_CONFIG = {
    'patch_size': 2,    # Taille de chaque patch de calibration (ex: 2x2 cellules)
    'colors': [WHITE, BLACK, BLUE, RED] # Couleurs utilisées pour les patchs de calibration (doivent correspondre à celles dans COLOR_TO_BITS_MAP)
}

# Configuration des Métadonnées
METADATA_CONFIG = {
    'rows': 6,                          # Nombre de lignes dédiées aux métadonnées
    'cols': 6,                          # Nombre de colonnes dédiées aux métadonnées
    'total_bits': 72,                   # Total de bits pour les métadonnées (rows * cols * BITS_PER_CELL)
    'version_bits': 4,                  # Bits pour la version du protocole
    'ecc_level_bits': 4,                # Bits pour le niveau de correction d'erreur (ECC)
    'msg_len_bits': 12,                 # Bits pour la longueur du message (après cryptage)
    'key_bits': 16,                     # Bits pour la clé XOR (si utilisée)
    'protection_bits': 36               # Bits pour la protection des métadonnées (ex: ECC sur métadonnées ou répétition)
                                        # Note: version_bits + ecc_level_bits + msg_len_bits + key_bits doit être <= (total_bits - protection_bits)
                                        # ou alors protection_bits est calculé sur les bits d'information.
                                        # Ici, 4+4+12+16 = 36. Si protection_bits = 36, cela signifie que les 36 bits d'info sont répétés ou protégés.
}

# Paramètres ECC (Error Correction Code)
DEFAULT_ECC_LEVEL_PERCENT = 20  # Pourcentage de bits dédiés à l'ECC par rapport aux bits de données

# Paramètres de Cryptage
DEFAULT_XOR_KEY_BITS = METADATA_CONFIG['key_bits'] # Longueur de la clé XOR par défaut (en bits)

# Paramètres de Génération d'Image
DEFAULT_CELL_PIXEL_SIZE = 10 # Taille par défaut d'une cellule en pixels lors de la génération de l'image 

# --- V2 (Multi-tailles, logo, ECC avancé, détection FP/TP) ---
ECC_SYMBOL_SIZE_BITS = 8  # Pour Reed-Solomon

# Config du logo (zone centrale, dimension en cellules)
LOGO_CONFIG = {
    'enabled': False,  # Par défaut désactivé
    'cell_dimension': 7,  # Taille du carré central réservé au logo
    # 'position': 'center'  # Peut être calculé dynamiquement
}
# Bit de signalisation logo dans les métadonnées (exemple, à intégrer dans METADATA_CONFIG V2)
# LOGO_ENABLED_BIT = 1  # Index du bit dans le bloc de métadonnées (à ajuster selon l'ordre)

# Paramètres pour la détection FP/TP
FP_EXPECTED_RATIOS = [1, 1, 3, 1, 1]  # Pour balayage 1D du FP
FP_DETECTION_THRESHOLD = 0.2  # Seuil de tolérance sur les ratios
TP_SCAN_WINDOW = 3  # Largeur de fenêtre pour l'analyse des TP

# Configurations multi-tailles/versions
PROTOCOL_VERSIONS = {
    'V2_S': {
        'MATRIX_DIM': 35,
        'BITS_PER_CELL': 2,
        'FP_CONFIG': {
            'size': 7,
            'margin': 1,
            'pattern_colors': [RED, BLUE, BLACK, WHITE]
        },
        'TP_CONFIG': {
            'line_color1': BLACK,
            'line_color2': WHITE
        },
        'CCP_CONFIG': {
            'patch_size': 2,
            'colors': [WHITE, BLACK, BLUE, RED]
        },
        'METADATA_CONFIG': {
            'rows': 6,
            'cols': 6,
            'total_bits': 72,
            'version_bits': 4,
            'ecc_level_bits': 4,
            'msg_len_bits': 12,
            'key_bits': 16,
            'protection_bits': 36,
            # 'logo_enabled_bit': 36,  # Exemple d'extension
        },
        'LOGO_CONFIG': LOGO_CONFIG.copy(),
        'ECC_SYMBOL_SIZE_BITS': ECC_SYMBOL_SIZE_BITS,
        'DEFAULT_CELL_PIXEL_SIZE': 10
    },
    'V2_M': {
        'MATRIX_DIM': 51,
        'BITS_PER_CELL': 2,
        'FP_CONFIG': {
            'size': 9,
            'margin': 1,
            'pattern_colors': [RED, BLUE, BLACK, WHITE]
        },
        'TP_CONFIG': {
            'line_color1': BLACK,
            'line_color2': WHITE
        },
        'CCP_CONFIG': {
            'patch_size': 2,
            'colors': [WHITE, BLACK, BLUE, RED]
        },
        'METADATA_CONFIG': {
            'rows': 8,
            'cols': 8,
            'total_bits': 128,
            'version_bits': 4,
            'ecc_level_bits': 4,
            'msg_len_bits': 16,
            'key_bits': 24,
            'protection_bits': 64,
            # 'logo_enabled_bit': 64,
        },
        'LOGO_CONFIG': LOGO_CONFIG.copy(),
        'ECC_SYMBOL_SIZE_BITS': ECC_SYMBOL_SIZE_BITS,
        'DEFAULT_CELL_PIXEL_SIZE': 10
    }
}

def get_protocol_config(version_name: str):
    """
    Retourne une copie défensive de la configuration complète pour une version donnée (ex: 'V2_S', 'V2_M').
    """
    if version_name not in PROTOCOL_VERSIONS:
        raise ValueError(f"Unknown protocol version: {version_name}")
    return copy.deepcopy(PROTOCOL_VERSIONS[version_name]) 