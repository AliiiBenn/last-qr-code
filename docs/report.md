# Rapport d'Audit Qualité & Robustesse du Code

## 1. **Synthèse des Résultats de Test**

- **Nombre total de tests exécutés** : 60
- **Succès** : 59
- **Échec critique** : 1 (test d'intégration rotation/décodage)
- **Pipeline principal (`src/main.py`)** : s'exécute, mais le message décodé ne correspond pas toujours à l'original (problème de robustesse à la rotation ou à la lecture des métadonnées).

### **Erreur principale détectée**
- **Test échoué** : `test_integration_encode_rotate90_decode`
- **Cause** : `ValueError: Metadata protection check failed: repeated blocks do not match.`
- **Debug** : Les deux blocs de métadonnées censés être identiques divergent après rotation/redressement, ce qui indique une corruption lors de la lecture de la zone METADATA (erreur d'orientation, de mapping, ou de calibration couleur).

---

## 2. **Analyse détaillée des problèmes**

### 2.1 **Robustesse à la rotation et orientation**

- **Problème** : La détection des Finder Patterns (FP) et leur identification par couleur ne sont pas toujours robustes après rotation. Les logs montrent que la couleur centrale de certains FP est mal détectée ou que deux FP sont identifiés avec la même couleur, ce qui fausse l'orientation.
- **Conséquence** : Si l'orientation n'est pas correctement restaurée, la lecture ligne/colonne de la zone METADATA ne correspond plus à l'ordre d'écriture, d'où la divergence des deux blocs répétés.
- **Correction possible** :
  - Améliorer la détection des FP (meilleure tolérance aux variations de couleur, prise en compte de la position géométrique en plus de la couleur).
  - Ajouter une étape de validation croisée (par exemple, vérifier que les trois couleurs centrales sont bien distinctes et correspondent à l'attendu).
  - En cas de doute, tenter toutes les orientations possibles (0°, 90°, 180°, 270°) et choisir celle qui donne des métadonnées valides (protection OK).

### 2.2 **Calibration couleur et mapping bits/couleur**

- **Problème** : La calibration couleur repose sur l'échantillonnage de petites zones, ce qui peut être bruité après rotation ou interpolation. Cela peut entraîner un mauvais mapping couleur→bits, surtout pour les FP ou la zone METADATA.
- **Correction possible** :
  - Élargir la zone d'échantillonnage pour la calibration.
  - Ajouter une vérification de cohérence sur la calibration (par exemple, s'assurer que les distances entre couleurs calibrées sont suffisantes).
  - Envisager un recalibrage adaptatif si la lecture des FP ou des METADATA échoue.

### 2.3 **Placement et extraction des métadonnées**

- **Problème** : L'ordre de placement des bits dans la zone METADATA est strictement ligne-par-ligne, colonne-par-colonne. Si la matrice est lue dans une orientation incorrecte, la protection (répétition) ne peut plus jouer son rôle.
- **Correction possible** :
  - Après extraction, si la protection échoue, tenter de relire la zone METADATA dans les trois autres orientations (rotation de la grille).
  - Ajouter un checksum ou une signature simple sur les métadonnées pour détecter l'orientation correcte.

### 2.4 **Lisibilité et maintenabilité**

- **Points forts** :
  - Séparation claire des modules (core, tests, utils).
  - Utilisation de caches pour les coordonnées de zones.
  - Docstrings et commentaires explicites.
  - Tests unitaires nombreux et précis.
- **Points faibles** :
  - Beaucoup de logique "hardcodée" pour la version V1 (dimensions, tailles, couleurs).
  - Les fonctions critiques (décodage, calibration, détection FP) sont longues et pourraient être davantage découpées.
  - Les logs de debug sont écrits dans des fichiers, mais il manque une vraie gestion de logs (niveau, activation/désactivation, etc.).
- **Correction possible** :
  - Refactoriser les fonctions longues en sous-fonctions.
  - Centraliser la gestion des logs (utiliser le module `logging` de Python).
  - Rendre la configuration (dimensions, couleurs, etc.) plus dynamique et paramétrable.

### 2.5 **Extensibilité**

- **Problème** : Le support multi-tailles, multi-versions, et l'intégration du logo sont prévus mais peu factorisés dans la logique d'encodage/décodage.
- **Correction possible** :
  - Refondre la gestion des versions dans `protocol_config.py` pour permettre un passage de version dynamique à tous les modules.
  - Prévoir des hooks pour l'ajout de nouvelles zones (logo, extensions) sans modifier la logique centrale.

### 2.6 **Sécurité**

- **Problème** : Le chiffrement XOR est faible (sécurité "cosmétique"). Les erreurs de parsing des métadonnées ou de l'ECC ne sont pas toujours gérées de façon sécurisée (ex : exceptions non catchées, pas de rollback).
- **Correction possible** :
  - Documenter explicitement la faiblesse du chiffrement dans le rapport.
  - Ajouter des try/except plus fins autour des étapes critiques du décodage.
  - Envisager une option de chiffrement plus robuste si la sécurité est un enjeu.

---

## 3. **Recommandations de corrections et d'améliorations**

### 3.1 **Robustesse à la rotation**
- Ajouter une fonction qui, en cas d'échec de la protection des métadonnées, tente automatiquement les trois autres orientations de la grille.
- Ajouter un test d'intégration qui encode, tourne, puis décode dans toutes les orientations.

### 3.2 **Détection et validation des FP**
- Améliorer la robustesse de la détection des FP :
  - Prendre en compte la position relative des FP (géométrie du triangle rectangle).
  - Vérifier que les couleurs centrales sont bien distinctes et correspondent à l'attendu.
  - Si deux FP sont détectés avec la même couleur, relancer la détection avec des seuils différents.

### 3.3 **Calibration couleur**
- Élargir la zone d'échantillonnage pour la calibration.
- Ajouter une étape de validation croisée (distances inter-couleurs, cohérence avec les couleurs attendues des FP).

### 3.4 **Logs et debug**
- Remplacer les fichiers de debug par un vrai logger Python, configurable (niveau DEBUG/INFO/WARNING/ERROR).
- Ajouter des logs sur la détection des FP, la calibration, et la lecture des métadonnées.

### 3.5 **Extensibilité et configuration**
- Refactoriser la gestion des versions et des tailles de matrice pour permettre l'ajout de nouvelles versions sans dupliquer la logique.
- Prévoir des hooks pour l'ajout de nouvelles zones (logo, extensions).

### 3.6 **Sécurité et robustesse du parsing**
- Ajouter des try/except plus fins autour des étapes critiques du décodage.
- Documenter explicitement la faiblesse du chiffrement XOR.

---

## 4. **Conclusion**

Le projet est **très bien structuré** et la couverture de tests est excellente pour un projet académique. La principale faiblesse actuelle est la **robustesse à la rotation et à la lecture des métadonnées** en conditions réelles (rotation, bruit, interpolation). Les corrections proposées sont principalement des améliorations de robustesse et de maintenabilité, et peuvent être mises en œuvre sans refonte majeure de l'architecture.

---

## 5. **Plan d'action prioritaire**

1. **Robustesse rotation/orientation** : Ajout d'une tentative automatique sur les 4 orientations si la protection des métadonnées échoue.
2. **Validation FP/couleurs** : Améliorer la détection et la validation des FP.
3. **Logs** : Centraliser la gestion des logs pour faciliter le debug.
4. **Refactorisation** : Découper les fonctions critiques et rendre la configuration plus dynamique.
5. **Documentation** : Ajouter une section "Limites et perspectives" dans le rapport pour expliciter les choix de sécurité et de robustesse.

---

*Ce rapport doit être intégré dans `docs/report.md` et servir de base à toute discussion ou refonte du code. Il est recommandé de traiter en priorité les points 1 et 2 pour garantir la robustesse du pipeline d'encodage/décodage, puis d'itérer sur les autres axes d'amélioration.*

---

**Mentor IA – Audit Qualité Logicielle, 2024**
