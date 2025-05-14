Absolument ! Le plan précédent est déjà très complet. Voici une version révisée et améliorée, avec quelques ajustements pour renforcer la clarté, la modularité, et l'alignement avec les attentes d'un projet universitaire visant l'excellence. Les améliorations se concentrent sur :

*   **Modularité et Testabilité Accrues :** Découpage plus fin de certaines fonctions, suggestions pour des tests plus ciblés.
*   **Robustesse (Conceptuelle) :** Insister sur la *description* des aspects robustes dans le rapport, même si l'implémentation est simplifiée.
*   **Rapport :** S'assurer que le rapport est le reflet fidèle de la conception et des justifications.
*   **Interface Utilisateur :** Proposer une interface CLI plus structurée.

---

**PLAN DE DÉVELOPPEMENT AMÉLIORÉ - PROTOCOLE GRAPHIQUE CUSTOM**

**Langage de Programmation :** Python
**Bibliothèques requises :** `Pillow` (ou `PIL`), `numpy` (fortement recommandé).

**Structure du Projet (Rappel et Justification) :**

```
reseaux2_tp_graphique/
├── src/
│   ├── protocol_config.py  # Constantes et paramètres de configuration du protocole
│   ├── matrix_layout.py    # Logique de la disposition des zones dans la matrice
│   ├── data_processing.py  # Encodage texte, cryptage, ECC
│   ├── encoder.py          # Logique principale de l'encodeur (bits -> image)
│   ├── decoder.py          # Logique principale du décodeur (image -> bits -> texte)
│   ├── image_utils.py      # Utilitaires de manipulation d'image (Pillow)
│   ├── main_cli.py         # Interface utilisateur en ligne de commande
│   └── __init__.py         # Pour faire de src un package
├── tests/                  # (Optionnel mais FORTEMENT recommandé pour 20/20)
│   ├── test_matrix_layout.py
│   ├── test_data_processing.py
│   └── # ... autres fichiers de test unitaires
├── report/
│   └── rapport_protocole_graphique.pdf  # Fichier du rapport
├── images_generes/
    └── # Dossier pour sauvegarder les codes générés et les images de test
```
*Justification :* Cette structure favorise la séparation des préoccupations, rendant le code plus facile à comprendre, à maintenir et à tester.

---

**PHASE 0 : FONDATIONS ET CONFIGURATION DU PROTOCOLE**

*   **Objectif :** Définir de manière centralisée et claire tous les paramètres immuables du protocole.
*   **Fichiers à Créer :**
    *   `src/protocol_config.py`
*   **Contenu de `src/protocol_config.py` :**
    *   **Constantes Générales :** `MATRIX_DIM = 35`, `BITS_PER_CELL = 2`.
    *   **Mappages :** `COLOR_TO_BITS_MAP`, `BITS_TO_COLOR_MAP` (ex: `{'00': (255,255,255), ...}`).
    *   **Configuration des Zones Fixes :**
        *   `FP_CONFIG = {'size': 7, 'margin': 1, 'pattern_colors': [RED, BLUE, BLACK, WHITE]}` (définir les couleurs RVB).
        *   `TP_CONFIG = {'line_color1': BLACK, 'line_color2': WHITE}`.
        *   `CCP_CONFIG = {'patch_size': 2, 'colors': [WHITE, BLACK, BLUE, RED]}`.
        *   `METADATA_CONFIG = {'rows': 6, 'cols': 6, 'total_bits': 72, 'version_bits': 4, 'ecc_level_bits': 4, 'msg_len_bits': 12, 'key_bits': 16, 'protection_bits': 36}`.
    *   **Paramètres ECC :** `DEFAULT_ECC_LEVEL_PERCENT = 20`.
    *   **Paramètres de Cryptage :** `DEFAULT_XOR_KEY_BITS = 16`.
    *   **Paramètres de Génération d'Image :** `DEFAULT_CELL_PIXEL_SIZE = 10`.
*   **Tests Associés (si `tests/` est créé) :** Aucun test direct ici, mais ce fichier sera importé partout.

---

**PHASE 1 : LOGIQUE DE LA MATRICE ET PLACEMENT DES MOTIFS**

*   **Objectif :** Implémenter la logique de la disposition des zones dans la matrice et le placement initial des motifs fixes.
*   **Fichiers à Créer/Modifier :**
    *   `src/matrix_layout.py`
    *   `src/encoder.py` (pour l'initialisation et l'appel)
*   **Fonctions à Créer (`src/matrix_layout.py`) :**
    *   `get_zone_coordinates(zone_name)`: Retourne un dictionnaire de coordonnées `{'TL': (r,c), 'TR':(r,c), ...}` ou des plages `(start_row, end_row, start_col, end_col)` pour une zone donnée (FP_TL, METADATA_AREA, CCP_AREA, etc.) en utilisant `protocol_config.py`.
    *   `get_cell_zone_type(row, col)`: Prend `(row, col)` et retourne le type de zone (`'FP_CORE'`, `'FP_MARGIN'`, `'TP_H'`, `'METADATA'`, `'DATA_ECC'`, etc.) en utilisant `get_zone_coordinates`.
    *   `get_fixed_pattern_bits(zone_type, relative_row, relative_col)`: Si `zone_type` est un motif fixe (FP core, TP, CCP), retourne les 2 bits spécifiques à placer dans cette cellule. `relative_row/col` sont les coordonnées à l'intérieur du motif.
        *   *Algorithme pour FP_CORE :* Logique concentrique des couleurs.
        *   *Algorithme pour TP :* Alternance des couleurs.
        *   *Algorithme pour CCP :* Attribution des couleurs pures aux patches.
    *   `get_data_ecc_fill_order()`: Retourne une liste ordonnée de `(row, col)` pour les cellules `DATA_ECC`, définissant l'ordre de balayage.
        *   *Algorithme :* Parcourir toutes les cellules, si `get_cell_zone_type` est `'DATA_ECC'`, ajouter à la liste.
*   **Fonctions à Créer (`src/encoder.py`) :**
    *   `initialize_bit_matrix()`: Crée une matrice `numpy.empty((MATRIX_DIM, MATRIX_DIM), dtype=object)` ou liste de listes, pour stocker les paires de bits (chaînes '00', '01', etc.).
    *   `populate_fixed_zones(bit_matrix)`:
        *   *Algorithme :* Parcourir toutes les cellules. Si `get_cell_zone_type` indique une zone fixe *non-métadonnées*, utiliser `get_fixed_pattern_bits` pour obtenir les bits et les placer dans `bit_matrix`. Laisser les zones `METADATA` et `DATA_ECC` vides pour l'instant.
*   **Tests (`tests/test_matrix_layout.py`) :**
    *   Vérifier `get_cell_zone_type` pour des coordonnées clés (coins, centres des zones).
    *   Vérifier `get_fixed_pattern_bits` pour des cellules spécifiques des FP, TP, CCP.
    *   Vérifier la longueur et l'unicité des coordonnées dans `get_data_ecc_fill_order`.

---

**PHASE 2 : TRAITEMENT DES DONNÉES (ENCODAGE)**

*   **Objectif :** Gérer la conversion texte-bits, le cryptage, le calcul de l'ECC, et la préparation des bits de métadonnées.
*   **Fichiers à Créer/Modifier :**
    *   `src/data_processing.py`
*   **Fonctions à Créer (`src/data_processing.py`) :**
    *   `text_to_padded_bits(text, target_bit_length)`: Convertit texte en UTF-8 bits. Ajoute un padding (ex: '0') pour atteindre `target_bit_length`.
    *   `generate_xor_key(bit_length)`: Génère une clé XOR aléatoire de la longueur spécifiée.
    *   `apply_xor_cipher(data_bits, key_bits)`: Applique XOR (réutilisable pour encrypt/decrypt).
    *   `calculate_simple_ecc(data_bits, ecc_percentage)`:
        *   *Algorithme (Checksum) :* Somme de tous les entiers représentés par des blocs de 8 bits, modulo 2^N (ex: N=16). Retourne les N bits du checksum.
        *   *Algorithme (Parité de Bloc) :* Diviser `data_bits` en blocs. Calculer parité ligne/colonne pour chaque bloc. Concaténer ces bits de parité. S'assurer que le nombre de bits ECC correspond à `ecc_percentage`.
    *   `format_metadata_bits(protocol_version, ecc_level_code, message_encrypted_len_bits, xor_key_bits)`:
        *   *Algorithme :* Assemble les bits selon `METADATA_CONFIG`. Gère la protection des métadonnées (ex: répéter les 36 bits d'info pour atteindre 72 bits ou appliquer un ECC dédié plus simple sur les 36 bits d'info).
*   **Tests (`tests/test_data_processing.py`) :**
    *   Tester `text_to_padded_bits` avec différents textes et longueurs.
    *   Tester `apply_xor_cipher` (encodage puis décodage doit redonner l'original).
    *   Tester `calculate_simple_ecc` et `format_metadata_bits` pour des entrées connues.

---

**PHASE 3 : ENCODEUR - ASSEMBLAGE ET GÉNÉRATION D'IMAGE**

*   **Objectif :** Assembler tous les bits (fixes, métadonnées, message, ECC) dans la matrice de bits, puis générer l'image graphique.
*   **Fichiers à Créer/Modifier :**
    *   `src/encoder.py`
    *   `src/image_utils.py`
*   **Fonctions à Créer (`src/image_utils.py`) :**
    *   `bits_to_rgb(bits_pair)`: Utilise `BITS_TO_COLOR_MAP` de `protocol_config.py`.
    *   `create_protocol_image(bit_matrix, cell_pixel_size, output_filename)`:
        *   *Algorithme :* Similaire à la Phase 3 du plan précédent, mais utilise `bits_to_rgb`. Utilise Pillow pour dessiner les rectangles colorés.
*   **Fonctions à Créer/Modifier (`src/encoder.py`) :**
    *   `encode_message_to_matrix(message_text, ecc_level_percent, custom_xor_key=None)`:
        *   *Algorithme :*
            1.  Initialiser `bit_matrix = initialize_bit_matrix()`.
            2.  Remplir les zones fixes (sauf métadonnées) : `populate_fixed_zones(bit_matrix)`.
            3.  Obtenir `data_ecc_fill_order = matrix_layout.get_data_ecc_fill_order()`.
            4.  Calculer `available_data_ecc_bits = len(data_ecc_fill_order) * BITS_PER_CELL`.
            5.  Calculer `num_ecc_bits = int(available_data_ecc_bits * (ecc_level_percent / 100.0))`. S'assurer que `num_ecc_bits` est pair (pour remplir des cellules entières).
            6.  Calculer `target_message_bit_length = available_data_ecc_bits - num_ecc_bits`.
            7.  `message_bits = data_processing.text_to_padded_bits(message_text, target_message_bit_length)`.
            8.  `xor_key = custom_xor_key or data_processing.generate_xor_key(METADATA_CONFIG['key_bits'])`.
            9.  `encrypted_bits = data_processing.apply_xor_cipher(message_bits, xor_key)`.
            10. `ecc_bits = data_processing.calculate_simple_ecc(encrypted_bits, ecc_level_percent)` (Ajuster `calculate_simple_ecc` pour retourner exactement `num_ecc_bits` si besoin de padding).
            11. `metadata_stream = data_processing.format_metadata_bits(1, ecc_level_percent, len(encrypted_bits), xor_key)`.
            12. Placer `metadata_stream` dans les cellules `METADATA` de `bit_matrix`.
            13. Concaténer `payload_stream = encrypted_bits + ecc_bits`.
            14. Remplir les cellules `DATA_ECC` de `bit_matrix` avec `payload_stream` en suivant `data_ecc_fill_order`.
            15. Retourner `bit_matrix`.
*   **Tests :** Générer une image et l'inspecter visuellement.

---

**PHASE 4 : DÉCODEUR - LECTURE D'IMAGE ET CALIBRATION**

*   **Objectif :** Charger une image, estimer les paramètres de cellule, et calibrer les couleurs en utilisant les CCP.
*   **Fichiers à Créer/Modifier :**
    *   `src/decoder.py`
    *   `src/image_utils.py`
*   **Fonctions à Créer (`src/image_utils.py`) :**
    *   `load_image_from_file(filepath)`: Charge l'image.
    *   `rgb_to_bits(rgb_tuple, calibration_map)`:
        *   *Algorithme :* Calcule la distance euclidienne entre `rgb_tuple` et chaque couleur de référence dans `calibration_map`. Retourne les bits correspondants à la référence la plus proche.
*   **Fonctions à Créer (`src/decoder.py`) :**
    *   `estimate_image_parameters(image)`:
        *   *Algorithme (simplifié) :* `cell_px = image.width // MATRIX_DIM`. Retourne `cell_px`.
        *   *Algorithme (plus robuste, pour le rapport) :* Expliquer comment on utiliserait la détection des FP pour trouver l'orientation, la perspective, et la taille réelle des cellules.
    *   `perform_color_calibration(image, cell_px_size)`:
        *   *Algorithme :*
            1.  Utiliser `matrix_layout.get_zone_coordinates('CCP_AREA')` et `protocol_config.CCP_CONFIG` pour localiser les 4 patches de calibration.
            2.  Pour chaque patch, échantillonner la couleur RVB moyenne d'une zone centrale du patch.
            3.  Créer et retourner `calibration_map = {'00': sampled_white_rgb, '01': sampled_black_rgb, ...}`.

---

**PHASE 5 : DÉCODEUR - EXTRACTION DE LA MATRICE DE BITS ET DES FLUX**

*   **Objectif :** Convertir l'image en matrice de bits et extraire les flux de bits des métadonnées et des données/ECC.
*   **Fichiers à Créer/Modifier :**
    *   `src/decoder.py`
*   **Fonctions à Créer (`src/decoder.py`) :**
    *   `extract_bit_matrix_from_image(image, cell_px_size, calibration_map)`:
        *   *Algorithme :*
            1.  Créer une matrice numpy pour les paires de bits.
            2.  Parcourir chaque cellule (r, c).
            3.  Calculer le centre en pixels de la cellule.
            4.  Échantillonner la couleur RVB du pixel au centre.
            5.  Utiliser `image_utils.rgb_to_bits(sampled_rgb, calibration_map)` pour obtenir la paire de bits.
            6.  Stocker dans la matrice.
            7.  Retourner la `bit_matrix`.
    *   `extract_metadata_stream(bit_matrix)`:
        *   *Algorithme :* Lire les bits des cellules `METADATA` (définies par `matrix_layout`) et les concaténer.
    *   `extract_payload_stream(bit_matrix)`:
        *   *Algorithme :* Utiliser `matrix_layout.get_data_ecc_fill_order()`. Lire les bits des cellules `DATA_ECC` dans cet ordre et les concaténer.

---

**PHASE 6 : DÉCODEUR - INTERPRÉTATION ET RÉCUPÉRATION DES DONNÉES**

*   **Objectif :** Décoder les métadonnées, vérifier/corriger l'ECC, décrypter et reconstituer le message texte.
*   **Fichiers à Créer/Modifier :**
    *   `src/decoder.py`
    *   `src/data_processing.py` (pour les fonctions inverses)
*   **Fonctions à Créer (`src/data_processing.py`) :**
    *   `parse_metadata_bits(metadata_stream)`:
        *   *Algorithme :* Vérifier la protection (ex: cohérence des parties répétées). Extraire `version, ecc_level, msg_len, xor_key` selon `METADATA_CONFIG`. Retourne un dictionnaire.
    *   `verify_and_correct_simple_ecc(encrypted_data_bits, ecc_bits, ecc_level_code)`:
        *   *Algorithme (Checksum) :* Recalculer le checksum sur `encrypted_data_bits`. Comparer avec `ecc_bits`. Retourne `True` si OK, `False` sinon (pas de correction pour un simple checksum).
        *   *Algorithme (Parité de Bloc) :* Décrire comment la correction pourrait fonctionner (localiser et inverser un bit erroné si une seule erreur par ligne/colonne de parité). Implémenter au moins la détection.
    *   `padded_bits_to_text(padded_bits)`: Supprimer le padding (si la longueur originale est connue ou si un marqueur de fin est utilisé, sinon juste convertir).
*   **Fonctions à Créer (`src/decoder.py`) :**
    *   `decode_matrix_to_message(bit_matrix)`:
        *   *Algorithme :*
            1.  `metadata_stream = extract_metadata_stream(bit_matrix)`.
            2.  `payload_stream = extract_payload_stream(bit_matrix)`.
            3.  `parsed_metadata = data_processing.parse_metadata_bits(metadata_stream)`. (Gérer erreurs si invalide).
            4.  Extraire `encrypted_bits` et `received_ecc_bits` de `payload_stream` en utilisant `parsed_metadata['msg_len']`.
            5.  `ecc_ok, corrected_encrypted_bits = data_processing.verify_and_correct_simple_ecc(encrypted_bits, received_ecc_bits, parsed_metadata['ecc_level'])`. (Si `ecc_ok` est `False`, lever une exception ou retourner une erreur).
            6.  `original_message_bits = data_processing.apply_xor_cipher(corrected_encrypted_bits, parsed_metadata['xor_key'])`.
            7.  `message_text = data_processing.padded_bits_to_text(original_message_bits)`.
            8.  Retourner `message_text`.

---

**PHASE 7 : INTERFACE UTILISATEUR ET TESTS D'INTÉGRATION**

*   **Objectif :** Fournir une interface en ligne de commande (CLI) pour utiliser l'encodeur/décodeur et effectuer des tests d'intégration.
*   **Fichiers à Créer/Modifier :**
    *   `src/main_cli.py`
*   **Contenu de `src/main_cli.py` (utilisation de `argparse`) :**
    *   Commande `encode`:
        *   Arguments : `--message <texte>`, `--output <fichier_image.png>`, `--ecc <pourcentage>`, `--key <cle_xor_hexa_optionnelle>`.
        *   Appelle `encoder.encode_message_to_matrix` puis `image_utils.create_protocol_image`.
    *   Commande `decode`:
        *   Arguments : `--input <fichier_image.png>`.
        *   Appelle `image_utils.load_image_from_file`, `decoder.estimate_image_parameters`, `decoder.perform_color_calibration`, `decoder.extract_bit_matrix_from_image`, puis `decoder.decode_matrix_to_message`. Affiche le résultat.
*   **Tests d'Intégration :**
    *   Encoder un message, puis décoder l'image générée. Vérifier que le message original est récupéré.
    *   Tester avec différents niveaux d'ECC.
    *   Simuler des erreurs en modifiant manuellement quelques pixels d'une image générée (changer une couleur) et voir si le décodeur (et l'ECC) s'en sort ou signale une erreur.

---

**PHASE 8 : DOCUMENTATION (RAPPORT FINAL)**

*   **Objectif :** Produire un rapport de haute qualité, détaillé et justifiant tous les choix.
*   **Contenu du Rapport :** Similaire à la Phase 8 du plan précédent, mais insister sur :
    *   **Justification de la structure du code** et de la modularité.
    *   **Description des algorithmes clés** pour chaque fonction importante.
    *   **Analyse critique des choix de conception :** Avantages et inconvénients des simplifications (ECC simple, calibration de base). Expliquer ce qui serait nécessaire pour une version "production".
    *   **Résultats des tests unitaires et d'intégration,** y compris la gestion des erreurs.
    *   **Schémas clairs et précis** pour la matrice, les flux de données, etc.
    *   **Respect strict des consignes du TP.**

---

**Pour viser le 20/20 :**

1.  **Complétude :** Implémenter toutes les fonctionnalités demandées (encodeur, décodeur, toutes les zones du protocole).
2.  **Qualité du Code :** Propre, commenté, modulaire, utilisant bien les structures Python.
3.  **Qualité du Rapport :** Très clair, détaillé, précis, bonnes justifications, analyse critique. C'est souvent la partie la plus importante.
4.  **Robustesse (Conceptuelle) :** Même si l'implémentation de certains aspects (ex: correction d'erreur avancée, détection de perspective) est simplifiée pour le TP, le rapport doit montrer que vous comprenez ces problèmes et comment ils seraient abordés.
5.  **Tests :** Avoir une stratégie de test (même simple) et en discuter les résultats montre une démarche rigoureuse. La présence de tests unitaires automatisés est un gros plus.
6.  **Originalité et Initiative :** Proposer des solutions bien pensées pour les différents aspects du protocole. La section optionnelle du logo, si bien traitée, peut apporter des points.

Ce plan amélioré devrait vous guider vers un projet solide et un excellent rapport. Bonne chance !