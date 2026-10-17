# Modifications MMODECON (branche mmodecon)

Usage personnel : extraction d'armes Destiny 2 pour le projet MMODECON. Les assets extraits ne sont jamais commités (data/ est ignoré).

## Modifications (destiny/extract/d2x/anim.py, Rig.decode)

1. **Os d'arme non retargetés** (`_unsolved_controls_to_bind`) : quand le composant de rig « arme » d'un clip diffère de celui du rig de l'arme (ex. La Recluse, clip fp_100 : C42D6707 contre 4D81B199), `calc_control_limit` s'arrête avant les contrôles d'arme (70-73). Leur matrice restait l'identité, donc les os (b_handle, b_magazine, ...) sortaient à l'origine du monde. Ils prennent maintenant leur pose locale de repos (bind).
2. **Pistes d'arme en deltas** (`_weapon_offsets_to_bind`) : pour La Recluse (clip fp_094_80BC11A9), les pistes des os d'arme sont des écarts depuis le repos, pas des positions absolues. Détection : valeur à l'image 0 proche de 0 alors que le bind local ne l'est pas. Le bind est ajouté (translation permutée comme le parser ; rotation bind x delta).

Raison : `weapon_clips` est vide pour La Recluse (l'entité 80BC126D n'a aucune ressource d'animation) ; le chargeur est animé dans les clips du rig joueur.

## À reprendre

**Direction du chargeur à reprendre.** La composition actuelle (translation permutée (b,c,a), sans rotation par le bind) est la plus plausible parmi les variantes testées (bind pivoté et 48 permutations rejetés) et ressemble à la vidéo de référence (chargeur détaché à droite, retiré, ramené par la main gauche), mais le calage n'est pas prouvé. Rotations du chargeur non variées.

Gnawing Hunger : clips de rechargement inchangés ; les clips sans rechargement à limite 70 gagnent des os d'arme qui suivent la main.

## Ré-extraire La Recluse

    ./port destiny extract 3354242550 --transparent --out data/destiny/extract/out/recluse_mmodecon

(ou `d2x extract 3354242550 --transparent --out DIR`). Sortie : DIR/the_recluse/ (manifest.json, GLB).
