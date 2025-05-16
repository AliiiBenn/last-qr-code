# PLAN DE DÉVELOPPEMENT - PROTOCOLE GRAPHIQUE V2

## 1. Introduction et Objectifs de la V2

La Version 1 (V1) de notre protocole graphique a établi les fondations pour l'encodage et le décodage de messages texte en images. La Version 2 (V2) vise à significativement améliorer la robustesse, la flexibilité et les fonctionnalités du protocole, en s'appuyant sur les apprentissages de la V1 et en intégrant des techniques plus avancées.

**Objectifs Principaux de la V2 :**

*   **Robustesse Accrue :** Améliorer la capacité du système à décoder des images en conditions non idéales (rotations, légères perspectives, altérations de couleurs, erreurs de données).
*   **Flexibilité du Protocole :** Introduire la possibilité de gérer différentes tailles de messages et d'intégrer des éléments optionnels comme des logos.
*   **Capacités Étendues :** Explorer des optimisations pour la densité de données et enrichir les informations de contrôle.
*   **Interface Utilisateur Complète :** Fournir une interface en ligne de commande (CLI) conviviale.

## 2. Langage de Programmation et Bibliothèques

*   **Langage :** Python (pour sa rapidité de développement et ses bibliothèques).
*   **Bibliothèques Principales :**
    *   `Pillow` : Pour la manipulation et la génération d'images.
    *   `numpy` : Pour les opérations sur les matrices (particulièrement utile pour les transformations d'images, le traitement des FP/TP, et potentiellement pour l'implémentation de l'ECC).
    *   Une bibliothèque pour l'ECC Reed-Solomon (ex: `reedsolo`) ou implémentation manuelle si requis par le cadre du projet.
    *   `argparse` : Pour l'interface en ligne de commande.

## 3. Structure du Projet (similaire à V1, avec extensions)

```
last-qr-code/
├── src/
│   ├── core/
│   │   ├── protocol_config.py  # Configurations (multi-taille, logo, ECC avancé)
│   │   ├── matrix_layout.py    # Logique de disposition (gère versions/tailles)
│   │   ├── data_processing.py  # Encodage, cryptage, ECC Reed-Solomon
│   │   ├── encoder.py          # Logique de l'encodeur
│   │   ├── decoder.py          # Logique du décodeur (avec détection FP/TP)
│   │   ├── image_utils.py      # Utilitaires image (avec transformations si besoin)
│   │   └── __init__.py
│   ├── tests/
│   │   ├── test_protocol_config.py
│   │   ├── test_matrix_layout.py
│   │   ├── test_data_processing.py
│   │   ├── test_encoder.py
│   │   ├── test_decoder.py       # Tests spécifiques pour détection FP, rotation etc.
│   │   ├── test_image_utils.py
│   │   └── __init__.py           # Potentially
│   ├── main.py                 # Interface utilisateur CLI et/ou point d'entrée principal
│   └── __init__.py
├── docs/
│   ├── documents/
│   │   └── version_2.md
│   └── tasks/
│       └── (task files if any)
├── images_generes/ # Peut contenir les images de V1 et V2
├── assets/                   # Pour stocker les logos à intégrer, polices, etc.
├── report/
│   └── rapport_protocole_graphique_v2.pdf # Nom du rapport mis à jour
└── # ... (autres fichiers comme README.md, requirements.txt)
```

## 4. Phases de Développement V2

---

### PHASE A : PRÉREQUIS ET AMÉLIORATIONS FONDAMENTALES

#### A1. Révision de `protocol_config.py`

*   **Objectif :** Adapter la configuration pour supporter les nouvelles fonctionnalités (multi-tailles, options de logo, configurations pour ECC avancé, paramètres de détection FP/TP).
*   **Description :**
    *   Définir des structures pour différentes "versions" ou "tailles" de protocole. Initialement, au moins deux configurations seront définies :
        *   `V2_S` (Small) : Basée sur la dimension `MATRIX_DIM = 35`.
        *   `V2_M` (Medium) : Utilisant une dimension plus grande, par exemple `MATRIX_DIM = 51`.
    *   Les paramètres `FP_CONFIG` (taille du motif, marge), `TP_CONFIG` (couleurs), et `CCP_CONFIG` (taille des patchs) auront des valeurs de base constantes, mais leurs positions absolues et la longueur des TP s'adapteront dynamiquement aux `MATRIX_DIM` de chaque version. Un dictionnaire ou une structure similaire dans `protocol_config.py` contiendra ces paramètres spécifiques à chaque version.
    *   Ajouter des configurations pour le logo :
        *   **Zone du Logo :** Une zone carrée centrale sera réservée pour le logo, avec une dimension configurable (ex: `LOGO_CELL_DIMENSION = 7` cellules).
        *   **Signalisation :** 1 bit dans les métadonnées (ex: `LOGO_ENABLED_BIT`) indiquera la présence (1) ou l'absence (0) d'un logo.
    *   Paramètres pour l'algorithme ECC Reed-Solomon :
        *   Conserver `DEFAULT_ECC_LEVEL_PERCENT`.
        *   Le nombre de symboles ECC (octets, en supposant des symboles de 8 bits) sera calculé en fonction de ce pourcentage appliqué au nombre de symboles de données.
        *   Ajouter `ECC_SYMBOL_SIZE_BITS = 8`.
    *   Paramètres pour la détection des FP/TP (à affiner en Phase B) :
        *   Prévoir des entrées de configuration telles que `FP_EXPECTED_RATIOS` (ex: `[1,1,3,1,1]` pour un balayage 1D du cœur d'un FP), `FP_DETECTION_THRESHOLD`, et `TP_SCAN_WINDOW`.
*   **Impact sur les Modules :**
    *   Création/Refonte de `src/core/protocol_config.py`.
    *   Tous les modules (`src/core/matrix_layout.py`, `src/core/encoder.py`, `src/core/decoder.py`, `src/core/data_processing.py`) devront utiliser cette nouvelle configuration.
*   **Considérations pour les Tests :**
    *   Vérifier la cohérence et la validité des nouvelles structures de configuration.
    *   S'assurer que les valeurs par défaut sont raisonnables.

#### A2. Implémentation d'un Système ECC Avancé (Reed-Solomon)

*   **Objectif :** Remplacer le simple checksum par un algorithme ECC capable de *correction* d'erreurs, améliorant significativement la robustesse.
*   **Description :**
    *   **Choix/Intégration :** Utiliser la bibliothèque Python `reedsolo`.
    *   **Taille des Symboles :** Les symboles Reed-Solomon auront une taille de 8 bits (`ECC_SYMBOL_SIZE_BITS = 8`), correspondant à des octets.
    *   **Encodage ECC :** Fonction `calculate_reed_solomon_ecc(data_symbols, num_ecc_symbols)` qui génère les symboles (octets) de parité.
    *   **Décodage ECC :** Fonction `verify_and_correct_reed_solomon_ecc(message_plus_ecc_symbols, num_ecc_symbols)` qui tente de détecter et corriger les erreurs.
    *   **Gestion des Blocs :** L'encodage Reed-Solomon sera appliqué à l'ensemble du payload de données comme un unique bloc, tant que le nombre total de symboles de données + ECC ne dépasse pas la limite du codec (ex: 255 symboles pour GF(2^8)). Pour des messages plus grands, une taille de matrice supérieure (`V2_M`) sera utilisée. Si le message est trop volumineux même pour la plus grande taille de matrice, une erreur sera levée. La segmentation des données en plusieurs blocs RS au sein d'un même symbole graphique sera différée.
    *   **Nombre de Bits ECC :** Le nombre de symboles ECC sera déterminé par `DEFAULT_ECC_LEVEL_PERCENT` appliqué au nombre de symboles de données.
*   **Impact sur les Modules :**
    *   `src/core/data_processing.py` : Nouvelles fonctions pour l'ECC Reed-Solomon.
    *   `src/core/encoder.py` : Appelera la nouvelle fonction de génération d'ECC.
    *   `src/core/decoder.py` : Appelera la nouvelle fonction de vérification/correction d'ECC.
    *   `src/core/protocol_config.py` : Paramètres spécifiques à Reed-Solomon.
*   **Considérations pour les Tests :**
    *   Tests unitaires approfondis pour les fonctions ECC : génération, détection, correction (jusqu'à `t` erreurs), comportement au-delà de la capacité de correction.
    *   Tests d'intégration : introduire des erreurs dans un flux encodé et vérifier la correction.

---

### PHASE B : AMÉLIORATIONS MAJEURES DU DÉCODAGE (ROBUSTESSE VISUELLE)

#### B1. Détection des Finder Patterns (FP) et Gestion de la Rotation/Perspective

*   **Objectif :** Permettre au décodeur de lire des images qui ne sont pas parfaitement alignées ou qui présentent de légères distorsions de perspective.
*   **Description :**
    *   **Algorithme de Détection FP :** Développer une méthode pour localiser les trois Finder Patterns dans l'image. Cela pourrait impliquer des techniques de balayage, de détection de contours, d'analyse de ratios de motifs (comme les bandes noires/blanches/noires/blanches/noires des FP de QR codes).
    *   **Détermination de l'Orientation :** Une fois les FP localisés, leur position relative permet de déterminer l'angle de rotation de l'image (0, 90, 180, 270 degrés).
    *   **Correction de Perspective (Optionnelle/Simplifiée) :** Si les FP indiquent une déformation perspective, calculer une matrice de transformation homographique pour projeter les points de la grille de la matrice lue sur une grille idéale carrée.
    *   **Application :** Soit transformer l'image (coûteux), soit ajuster les coordonnées de lecture des cellules en fonction de la transformation calculée.
*   **Impact sur les Modules :**
    *   `src/core/decoder.py` : Refonte majeure de `estimate_image_parameters` qui deviendrait `locate_and_orient_protocol(image)`. Nouvelles fonctions pour la détection spécifique des FP et le calcul de la transformation.
    *   `src/core/image_utils.py` : Pourrait contenir des fonctions utilitaires pour les transformations d'image ou de coordonnées si nécessaire.
    *   `src/core/protocol_config.py` : Définition précise des motifs des FP pour faciliter leur détection.
*   **Considérations pour les Tests :**
    *   Créer un ensemble d'images tests avec différentes rotations (0, 90, 180, 270 degrés).
    *   Images avec de légères distorsions de perspective.
    *   Images où les FP sont partiellement obscurcis ou bruités (pour tester la robustesse de l'algorithme de détection).

#### B2. Utilisation des Timing Patterns (TP) pour le Calage Fin de la Grille

*   **Objectif :** Après une correction globale de l'orientation/perspective, utiliser les Timing Patterns pour affiner la position de la grille de lecture des cellules.
*   **Description :**
    *   Les TP (lignes alternées de couleurs) fournissent des repères pour déterminer la taille et la position exactes des cellules le long des axes.
    *   Une fois les FP détectés, localiser les TP. Échantillonner le long des TP pour identifier les transitions de couleurs, ce qui permet de déduire les frontières des cellules.
    *   Cela peut aider à compenser les distorsions locales ou les erreurs mineures dans l'estimation globale de la taille des cellules.
*   **Impact sur les Modules :**
    *   `src/core/decoder.py` : La fonction `extract_bit_matrix_from_image` utiliserait les informations des TP pour ajuster l'échantillonnage de chaque cellule, au lieu de se baser uniquement sur une taille de cellule fixe calculée globalement.
    *   `src/core/protocol_config.py` : Définition précise des motifs des TP.
*   **Considérations pour les Tests :**
    *   Images avec de légères variations d'échelle ou des distorsions non linéaires mineures que les FP seuls ne corrigeraient pas parfaitement.
    *   Images où les TP sont partiellement bruités.

---

### PHASE C : AMÉLIORATIONS DES DONNÉES ET DE LA CAPACITÉ

#### C1. Intégration d'un Logo (Optionnel)

*   **Objectif :** Permettre d'incruster un petit logo dans l'image du protocole, en minimisant l'impact sur la capacité de données.
*   **Description :**
    *   **Spécification de la Zone Logo :** Définir une ou plusieurs zones potentielles pour le logo dans `src/core/protocol_config.py` (par exemple, au centre de la matrice).
    *   **Gestion des Données :** Les cellules recouvertes par le logo sont perdues pour les données. Le protocole doit en tenir compte lors du calcul de la capacité et de l'allocation des bits de données/ECC.
    *   **Signalisation :** Un bit (ou plusieurs) dans les métadonnées pourrait indiquer la présence et potentiellement la forme/taille du logo.
    *   **Préparation du Logo :** Le logo fourni (ex: image PNG) devra être redimensionné, converti en une palette de couleurs compatible avec le protocole (ou binarisé), puis ses bits placés dans la zone désignée.
    *   **Impact sur la Lecture :** Le décodeur doit ignorer la zone du logo lors de l'extraction des données.
*   **Impact sur les Modules :**
    *   `src/core/protocol_config.py` : Définition des zones de logo et des bits de signalisation.
    *   `src/core/matrix_layout.py` : `get_cell_zone_type()` devra identifier les cellules du logo. `get_data_ecc_fill_order()` devra exclure ces cellules.
    *   `src/core/encoder.py` : Logique pour préparer et placer le logo. Ajustement du calcul de la capacité de données.
    *   `src/core/decoder.py` : Ignorer la zone du logo lors de la lecture.
    *   `src/core/image_utils.py` : Potentiellement des fonctions pour le traitement du logo.
*   **Considérations pour les Tests :**
    *   Encoder/décoder des messages avec et sans logo.
    *   Vérifier que le logo est correctement rendu et que les données adjacentes ne sont pas corrompues.
    *   Tester avec différentes tailles/types de logos (si le protocole le permet).

#### C2. Optimisation de la Densité de Données et Tailles de Matrice Variables (Suite de A1)

*   **Objectif :** Affiner la gestion de différentes tailles de matrice ou de configurations de protocole pour optimiser la capacité de données en fonction des besoins.
*   **Description :**
    *   S'appuyer sur les configurations `V2_SMALL`, `V2_MEDIUM`, etc., définies en A1 dans `src/core/protocol_config.py`.
    *   Chaque configuration spécifiera `MATRIX_DIM`, les tailles des zones fixes (FP, TP, CCP, Metadata), et donc la capacité de données résultante.
    *   Les métadonnées devront clairement indiquer la version/taille du protocole utilisé pour que le décodeur puisse s'adapter.
    *   Explorer des techniques pour minimiser l'overhead des zones fixes si possible (sans compromettre la robustesse).
*   **Impact sur les Modules :**
    *   Impact principal sur `src/core/protocol_config.py` et la manière dont les autres modules (surtout `src/core/matrix_layout.py`, `src/core/encoder.py`, `src/core/decoder.py`) sélectionnent et utilisent les configurations.
*   **Considérations pour les Tests :**
    *   Tests pour chaque taille/version de protocole définie.
    *   Vérifier la compatibilité ascendante/descendante si cela fait partie des objectifs.

#### C3. Compression des Données (Optionnel Avancé)

*   **Objectif :** Augmenter la quantité d'informations textuelles pouvant être stockées pour une taille de matrice donnée en compressant les données avant l'encodage.
*   **Description :**
    *   **Choix de l'Algorithme :** Sélectionner un algorithme de compression léger adapté aux données textuelles et dont l'implémentation en Python est disponible (ex: zlib, lzma simplifié, ou un codage de Huffman personnalisé si le gain est significatif pour de petits messages).
    *   **Signalisation :** Un bit dans les métadonnées pour indiquer si la compression a été appliquée.
    *   **Flux de Travail :** Texte -> Compression -> Chiffrement -> ECC -> Encodage. Inversement au décodage.
*   **Impact sur les Modules :**
    *   `src/core/data_processing.py` : Fonctions pour compresser et décompresser les données.
    *   `src/core/encoder.py` et `src/core/decoder.py` : Intégrer les étapes de compression/décompression dans le pipeline.
    *   `src/core/protocol_config.py` : Bit de signalisation pour la compression.
*   **Considérations pour les Tests :**
    *   Comparer la taille des données avant/après compression.
    *   S'assurer de la réversibilité parfaite de la compression/décompression.
    *   Évaluer le surcoût en termes de complexité et de temps de traitement.

---

### PHASE D : INTERFACE UTILISATEUR ET FINALISATION

#### D1. Interface en Ligne de Commande (CLI)

*   **Objectif :** Fournir une interface utilisateur conviviale pour utiliser l'encodeur et le décodeur.
*   **Description :**
    *   Utiliser `argparse` pour créer `src/main.py` en tant que CLI.
    *   **Fonctionnalités de l'Encodeur CLI :**
        *   `python src/main.py encode <message> -o <output_image.png> [--ecc <level>] [--key <xor_key>] [--logo <logo_path.png>] [--size <V2_SMALL|V2_MEDIUM>]`
    *   **Fonctionnalités du Décodeur CLI :**
        *   `python src/main.py decode <input_image.png> [--key <xor_key_if_not_in_metadata_or_override>]`
    *   Gestion claire des erreurs et des messages de statut.
*   **Impact sur les Modules :**
    *   Principalement `src/main.py`.
    *   Les fonctions principales de `src/core/encoder.py` et `src/core/decoder.py` devront être facilement appelables avec les paramètres adéquats.
*   **Considérations pour les Tests :**
    *   Tests de la CLI avec différents arguments valides et invalides.
    *   Vérifier les codes de sortie et les messages d'erreur.

#### D2. Tests Complets et Documentation du Code

*   **Objectif :** Assurer la fiabilité du code et fournir une documentation claire.
*   **Description :**
    *   **Tests Unitaires :** Compléter/améliorer les tests unitaires pour toutes les fonctions critiques dans `src/tests/`.
    *   **Tests d'Intégration :** Créer des scénarios de test de bout en bout qui simulent des cas d'utilisation réels (encodage -> image -> conditions variées -> décodage).
    *   **Tests de Robustesse :** Systématiquement tester avec des images dégradées (rotation, bruit, perspective légère, erreurs de bits introduites manuellement) pour valider les améliorations de la V2.
    *   **Documentation du Code (Docstrings) :** S'assurer que toutes les fonctions, classes et modules ont des docstrings claires et informatives (respectant par exemple le style Google ou NumPy).
    *   **README.md :** Mettre à jour le `README.md` du projet avec les instructions d'installation, d'utilisation de la CLI V2, et une description du protocole.
*   **Impact sur les Modules :** Tous les modules.

#### D3. Rapport Final et Nettoyage du Code

*   **Objectif :** Produire un rapport décrivant le protocole V2 et finaliser le code.
*   **Description :**
    *   **Rapport Technique :** Rédiger `report/rapport_protocole_graphique_v2.pdf` détaillant :
        *   Les spécifications du protocole V2 (structure de la matrice, zones fixes, métadonnées, ECC, gestion du logo, etc.).
        *   Les algorithmes clés utilisés (détection FP/TP, correction d'erreurs, etc.).
        *   Les choix de conception et leurs justifications.
        *   Une évaluation des performances (capacité de données, robustesse).
    *   **Nettoyage du Code :** Refactoring final, suppression du code mort, vérification du style de code.
*   **Impact sur les Modules :** Principalement documentaire, mais peut entraîner des petites retouches de code.

---

## Robustesse à la rotation et orientation : Finder Patterns différenciés

### Objectif
Garantir une robustesse maximale à la rotation (0°, 90°, 180°, 270°) et à l'orientation de la matrice, tout en simplifiant la détection et le décodage.

### Principe
- Utiliser des Finder Patterns (FP) de styles/couleurs différents dans chaque coin (par exemple, centre rouge pour TL, centre bleu pour TR, centre noir pour BL).
- Lors du décodage, détecter les FP et identifier immédiatement leur rôle (TL, TR, BL) par leur style, sans ambiguïté.
- Calculer l'angle de rotation comme multiple de 90° à partir de la position des FP, puis appliquer la rotation inverse pour remettre la grille droite.
- Extraire la grille à partir du coin (0,0) sans recadrage complexe.

### Avantages
- Détection instantanée de l'orientation, même en cas de bruit ou de FP partiellement masqué.
- Code de décodage plus simple et plus robuste (plus besoin de calculs géométriques complexes).
- Robustesse accrue aux erreurs d'impression, de scan ou de découpage.
- Créativité et originalité du protocole (bonus pour le rapport !).

### Implémentation
- Adapter la génération de la matrice pour donner à chaque FP un motif/couleur unique (voir src/core/matrix_layout.py et protocol_config.py).
- Adapter la détection des FP pour reconnaître leur style (par la couleur centrale, par exemple).
- Dans le pipeline de décodage, identifier les coins par leur style, calculer l'angle, appliquer la rotation inverse (toujours un multiple de 90°), puis lire la grille normalement.
- Ajouter des tests d'intégration pour chaque rotation (0°, 90°, 180°, 270°) et vérifier la robustesse de la détection et du décodage.

### Documentation et rapport
- Expliquer ce choix dans le rapport, illustrer par des exemples d'images tournées et décodées avec succès.
- Justifier la créativité et la simplicité de cette approche.

---

## [RÉALISÉ] Avancement au 2024-XX-XX

*   **Intégration complète de Reed-Solomon (RS) pour l'ECC** :
    *   L'encodeur permet désormais de choisir entre ECC simple (checksum) et Reed-Solomon (RS) pour la correction d'erreurs.
    *   Le nombre de symboles ECC utilisés (RS) est stocké dans les métadonnées.
    *   Le pipeline de décodage détecte automatiquement le mode ECC et applique la correction RS si besoin.
*   **Robustesse accrue sur les métadonnées** :
    *   Correction de la gestion des cas sans protection (protection_bits=0).
    *   Vérification et parsing robustes des métadonnées, padding, etc.
*   **Tests unitaires** :
    *   Tous les tests unitaires passent (hors robustesse Finder Patterns, traitée ailleurs).
    *   Pipeline complet validé (encodage, décodage, ECC, RS, métadonnées).
*   **Synchronisation du code** :
    *   Toutes les modifications ont été commit et push sur le dépôt distant.

---
