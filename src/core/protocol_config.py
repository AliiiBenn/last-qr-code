# Constantes et paramètres de configuration du protocole

# Constantes Générales
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