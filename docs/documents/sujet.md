# RESEAUX 2 - TP PROTOCOLE GRAPHIQUE

## Objectif du TP

L’objectif de ce TP est de concevoir un protocole de communication « graphique ». Un exemple de protocole de communication graphique est le QR-CODE (voir en haut à droite de cette feuille pour un exemple de message graphique).

Vous devrez concevoir un nouveau protocole de A à Z. Vous pouvez vous inspirer du QR-CODE mais devrez proposer vos propres solutions aux différents problèmes posés.

## Conception de la Matrice

Les informations seront « dessinées » dans une matrice dont vous proposerez vous même les dimensions (plusieurs tailles « fixes » ou formes peuvent être proposées en fonction de la taille du message). Chaque « cellule » de votre matrice constitue l’unité d’information de base (par exemple, pour le QR-CODE, cette unité d’information est le bit).

Votre matrice devra contenir trois types d’informations :

-   Le message à transmettre en lui même
-   Les informations permettant de détecter et éventuellement corriger des erreurs
-   Les informations spécifiques à votre protocole

N’oubliez pas que votre message graphique sera imprimé et que lors de l’impression la taille des cellules (en pixel) peut être modifiée et les couleurs altérées (si vous utilisez des couleurs différentes). De même, l’orientation de votre dessin peut être modifiée.

## Exemples d’informations spécifiques à votre protocole (non exhaustif) :

-   Information permettant de repérer la matrice au milieu d’une page pouvant contenir d’autres informations
-   Information permettant de calculer la taille d’une cellule en pixel
-   Information permettant de connaître la position du premier bit du message
-   Information permettant de connaître la taille du message
-   Information permettant de connaître combien de bits sont codés dans chaque cellule.
-   Si vous utilisez des couleurs, informations permettant de retrouver chacune des couleurs utilisées et les bits qu’elles codent
-   …

## Travail à rendre

1.  **Rapport détaillé** présentant votre protocole graphique et justifiant vos choix. Vous devrez en particulier expliquer le rôle de chacune des cellules de votre matrice ainsi que la taille maximum du message pouvant être transmis à l’aide de votre protocole.
2.  **Un programme** permettant de saisir un message texte quelconque et qui générera la matrice correspondante respectant votre protocole (vous pouvez utiliser le langage de votre choix, en justifiant éventuellement ce choix).
3.  **Optionnel :** proposer une méthode permettant d’ajouter un logo dans votre matrice sans que cela n’altère la fonction de décodage et sans perdre de cellules « codantes ».
