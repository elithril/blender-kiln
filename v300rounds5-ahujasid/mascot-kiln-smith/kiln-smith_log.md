# Kiln Smith (mascotte kiln) — Production Log

## Config
- Type: character (mascotte humanoïde chibi, riggée, animée)
- Target: glTF/GLB web (rig humanoïde + clips walk en boucle + idle)
- Tier: detailed (brief « qualité vitrine », « la qualité prime sur le coût ») — visée 25-35K tris, rapporté, jamais bloqué (règle 4)
- Style: stylisé jeu vidéo, chibi (tête ≈ 1/2.5 de la hauteur)
- Mode: auto (personne ne valide le statique — fiche de design décidée et notée ici)
- Storage: compact
- 3D backend: none — scripted (pas de marketplace, pas d'IA, demandé par le brief)
- Live view: off (mode auto, personne pour regarder — rendus de revue à la place)
- Output: /private/tmp/kiln-bench/v300rounds5-ahujasid/mascot-kiln-smith/work/generated-assets/kiln-smith
- Environment: macOS arm64, Blender 5.2.2 LTS (MCP addon 1.8, protocol 14, à jour), SkinTokens installé (version testée), gltf-transform + gltfpack présents, polyhaven on / sketchfab off / polypizza off (non utilisés)

## Reference Image
- Path: none (brief texte ; palette reprise du logo blender-kiln décrit dans le brief : forge low-poly bleu ardoise, braises orange, cristal)
- Visual comparison: N/A

## Brief (reformulé, auto)
Petit forgeron chibi, mascotte de kiln : 1,00 m, tête ≈ 0,40 m (1/2,5), tablier de cuir, marteau de forge à la main droite,
lunettes de protection relevées sur le front, palette braise (orange/ambre lumineux) + ardoise (bleu-gris). Formes rondes et
propres, couleurs franches, mains avec pouce, visage expressif (yeux à reflets, sourcils, sourire ouvert), chaussures soignées.
Modélisé en T-pose (rig prévu, règle 13). Livrables : GLB web (Draco/WebP), preview GLB non compressé, rig humanoïde,
clips `walk_loop` et `idle`.

## Design sheet (décidée en auto — characters.md § Design sheet first)
- **Rôle** : « Braise », apprenti forgeron de la forge kiln. Jovial, sûr de lui, marteau en main.
- **Signature de silhouette** : une mèche-flamme ambre/orange qui se dresse au-dessus du crâne (deux volutes qui montent
  et se recourbent en arrière) + lunettes rondes cuivrées sur le front ; secondaire : le gros marteau.
- **Palette (rôles)** :
  - ardoise `#4B5B70` — vêtement principal (chemise) ; ardoise sombre `#2C3646` — pantalon, semelles
  - braise `#FF6A1A` — accent : cheveux (sous-mèches `#D4480F`), cristal de l'emblème
  - ambre lumineux `#FFB43A` (émissif) — verres des lunettes, cœur du cristal (accent lumineux, deux usages)
  - cuir `#7A4526` — tablier, ceinture, bottes, poignets (cuir clair `#9A5C33` pour le tablier, foncé `#5A3220` pour bottes/ceinture)
  - peau `#F2BE98`, joues `#F39A86`
  - métal : acier `#8E99A6` (tête du marteau), laiton/cuivre `#C98A3C` (montures des lunettes, boucle, rivets)
  - bois `#8A5A32` (manche du marteau)
- **Costume en couches** : chemise ardoise manches longues retroussées (revers) → pantalon ardoise sombre → tablier de cuir
  à bavette (projeté sur le corps), bretelle de cou, ceinture de cuir à boucle laiton → bottes de cuir à revers et semelle épaisse.
- **Matériaux (≥ 4)** : tissu (chemise, pantalon, rugosité 0.85), cuir (tablier, bottes, ceinture, 0.55-0.65), métal (acier
  0.35 métal 1 ; laiton 0.3 métal 1), verre ambre émissif (0.1), bois (0.7), peau (0.5), cheveux (0.6).
- **Accessoires** : marteau de forge (manche bois, tête acier, frette laiton), lunettes de protection (sangle cuir sur le volume des
  cheveux, deux montures cuivre, verres ambre).
- **Finitions (≥ 3)** : revers de manches, coutures pointillées du tablier + poche, rivets laiton aux angles de la bavette,
  boucle de ceinture, emblème cristal-braise sur la bavette, semelles et bouts de bottes distincts, frette du marteau.
- **Visage** : grands yeux ovales sombres, iris ambre en moitié basse, deux reflets émissifs chacun (objets séparés), sourcils
  courts arqués (extrémité extérieure haute), petit nez 16 mm, sourire ouvert (demi-ellipsoïde enfoncé, langue basse), joues roses.
- **Mains** : paume ellipsoïde plus large qu'épaisse + pouce capsule vers l'avant-haut.
- Méthode : une seule peau de métaballes (tête, cou, torse, bras, mains, jambes) → mesh → voxel remesh → QuadriFlow ;
  matériaux de la peau assignés par zone, frontières cachées par col/revers/ceinture/revers de bottes ; yeux, reflets, nez,
  bouche, sourcils, cheveux, vêtements rapportés en objets séparés (characters.md § One skin, § A stylised humanoid).

## Prompts (copy-paste ready)
- Concept art: none (scripted from the brief)

## Source
- Method: scripted (Blender Python, métaballes + voxel remesh + QuadriFlow), live Blender 5.2.2 via MCP (scène d'usine)

## Pipeline
- CONFIG/BRIEF: scène d'usine détectée (Cube, Light, Camera) — le Cube sera supprimé avant construction (règle 6, exception d'usine)
- SOURCE (scripted): peau = 1 famille de métaballes (tête, cou, torse, bras T-pose, mains avec pouce, jambes séparées 2,4-3,4 cm, bottes) → mesh → voxel 4 mm → fusion 1e-4 (7 sommets ; à 1e-5, QuadriFlow refusait « needs to be manifold ») → QuadriFlow 11 000 faces. Zones de matériaux par plans de coupe (col z 0,56, poignets |x| 0,355, taille 0,305, haut de botte 0,125, semelle 0,02). Le Cube d'usine supprimé (règle 6). Calibrage : rayon de surface = 0,574 × rayon métaballe (raideur 2).
- Review round 1 (review/round1.png, round1_clay.png) — relecteur neuf : « ne pas montrer tel quel » ; 55,6K tris
  1. close-up/front : la calotte de cheveux a un bord horizontal dur sous la frange → casque. Fix : calotte remontée sous les racines de la frange, 7 mèches de frange plus larges qui se chevauchent
  2. front clay : la flamme = une corne lisse, plus claire que les cheveux. Fix : flamme faite de mèches (même matériau), largeur sur X, trois langues qui s'ouvrent depuis une base commune
  3. back/side : sangle des lunettes = halo qui flotte. Fix : rayon de la sangle lu sur les cheveux (lancer de rayons, filtre max + lissage fort), +3 mm
  4. side/back : tempes et nuque dégarnies, mèches qui piquent dans le col. Fix : mèches de tempe (2 par côté), sous-couche de nuque collée, mèches arrière raccourcies
  5. front : marteau = brique sombre, boule laiton qui dépasse. Fix : tête plus grande et chanfreinée, acier clair, manche plus long avec grip cuir, bout bois arrondi
  6. front/q_left : main libre = palette. Fix : doigts plus fins et écartés, raideur plus forte, pouce plus long
  7. toutes vues : bottes = œufs. Fix : semelle épaisse séparée débordante, talon, lacets croisés + œillets
  8. toutes vues : peau terne gris-beige. Cause : palette saisie en sRGB dans des champs linéaires — toute la palette délavée. Fix : conversion sRGB → linéaire
  9. back : mèches = cartes raides à pointes de paille. Fix : section plus épaisse, pointes arrondies
  10. close-up : bouche trop petite. Fix : 60 × 44 mm, moins enfoncée, langue visible
  11. clay : revers, revers de bottes, ceinture = élastiques fins. Fix : sections épaissies
  12. col bosselé. Fix : lissage ×6, col plus large
  13. lunettes petites. Fix : verres 36 mm
  14. side : ceinture décollée dans le dos. Fix : décalage 6 mm au dos, 20 mm devant (sur le tablier)
  15. back nu. Fix : nœud du tablier dans le dos + sacoche de cuir à la hanche
  16. palette : pas d'ambre lumineux, laiton dilué ×5. Fix : verres et cristal plus émissifs, virole du marteau en acier, bout du manche en bois
- Round 1 fixes applied → v2 (62,4K tris). Mesured: palette now linear (skin reads peach, not grey).
- Review round 2 (review/round2.png, round2_clay.png) — relecteur neuf : « pas tel quel »
  1. tous : tête du marteau = bloc rayé bois/acier (bug : indices de matériau perdus au subdivide/bevel) → matériau par position ; tête arrondie (bevel 20 mm), faces de frappe évasées, plus grosse (220 × 100 mm), manche raccourci
  2. back/side : nuque chauve, mèches arrière raides → calotte jusqu'à -55°, sous-couche jusqu'à -60°, mèches arrière courbées alternées
  3. back/side : sangle encore décollée → sangle plus haute au dos (el 22°, où les mèches sont plates), filtre max ±2
  4. front/side : main libre = palette (doigts fusionnés : QuadriFlow ~8 mm ne résout pas 5 mm d'écart) → mains en objets séparés, voxel 2,2 mm, doigts en éventail ; la peau garde une paume cachée pour le rig ; poing droit à doigts repliés
  5. front/close-up : flamme = planche à sommet coupé → langues effilées sur toute la longueur, section plus épaisse, 12 côtés
  6. back : dents de peau au-dessus du col → coupe droite à z 0,578 tout autour, col posé dessus
  7. front : ombres des mèches sur le front lisent comme de la saleté → frange moins décollée (lift 0,012)
  8. close-up : verres pêche délavés → ambre saturé, émission 1,0
  9. palette : cheveux rouge-orangé, pas d'ambre → cheveux ambre-orange (sRGB 1,0/0,47/0,11) ; emblème cristal agrandi
  10. side/back : sacoche en boîte → sac arrondi
  11. back : dos des bottes nu → languette de tirant cousue au talon
  12. close-up : sourire timide → bouche 66 × 50 mm, sourcils plus épais
  13. front : jambes cachées par le tablier → bas du tablier remonté à z 0,15
- Round 2 fixes applied → v3 (68,4K tris ; mains séparées 3,0K + 3,2K)
- Review round 3 (review/round3.png, round3_clay.png) — relecteur neuf : « pas tel quel »
  1. tous : marteau = canette chromée → tête rectangulaire arrondie (bevel), face plate + panne en coin (cross-peen), acier ardoise satiné (rugosité 0,45) au lieu du chrome
  2. close-up/front : taches de peau sur le dessus des épaules → la peau au-dessus de z 0,578 seulement dans le cylindre du cou (r 0,12)
  3. tous : flamme = aileron de requin + antennes → la langue arrière retirée ; langue centrale plus large et plus basse, deux langues latérales nées dans sa base, légère lueur braise
  4. back/side : sangle en halo → sous les mèches au-delà de ±75° (lue sur la calotte), sur les cheveux devant
  5. close-up : taches granuleuses sur le front (ombres des mèches) → frange plus collée (lift 6 mm)
  6. back/side : trous entre les mèches → 6 mèches intermédiaires
  7. front : main ouverte encore en palette → doigts en éventail plus large, légèrement repliés
  8. side : oreilles invisibles → mèches latérales reculées (az 98-128), oreilles dégagées
  9. boots : revers en tore → bande plate rabattue ; revers de manches idem
  10. palette : verres et cristal saumon, rien ne brille → ambre saturé, émission orange pure
  11. back : haut du dos vide → bretelles du tablier croisées dans le dos, anneau laiton au croisement
- Round 3 fixes applied → v4 (71,0K tris)
- Review round 4 (review/round4.png, round4_clay.png) — relecteur neuf : « pas tel quel » ; design, visage, bottes, palette « niveau vitrine »
  1. tous : marteau = brique facettée — 3e retour du même défaut → changement de méthode : cage basse (face évasée, panne en coin) + subdivision appliquée, ombrage lisse ; manche plus épais
  2. front/close-up/side : bande en zigzag sous la tête. Cause : ma règle de zone (z > 0,578 et r < 0,12) donnait le dessous de la mâchoire à la chemise → peau = cylindre du cou OU distance normalisée au centre de la tête < 1,25 ; col remonté à 0,585
  3. back : couches de mèches déchirées, plaques claires (mèches intermédiaires qui s'interpénètrent + bord en escalier de la calotte) → mèches intermédiaires retirées, 9 mèches arrière plus larges à décollement alterné ; calotte refaite en grille azimut/élévation qui suit la ligne de cheveux (bord lisse)
  4. side : tempe en escalier, pas d'oreille → oreilles qui sortent de 25 mm, favoris devant l'oreille
  5. front : ombres de frange = salissures → détail, laissé (ombres EEVEE de mèches réelles), frange déjà collée à 6 mm
  6-7. verres et cristal saumon (surexposés, le tone mapping les blanchit) → émission 0,35, base ambre saturée
  8. side : sacoche saillante → plus plate (12 mm)
  9. back chemise un peu nue → acceptable (bretelles croisées)
- Round 4 fixes applied → v5 (71,3K tris) ; marteau en cage subdivisée (1 432 faces)
- Review round 5 (review/round5.png, round5_clay.png) — relecteur neuf : « proche », pas encore
  1. front/q_right : manche pointé vers la caméra, la tête du marteau seule = rouleau/barre → marteau incliné de 37° vers le haut-avant autour du poing (en T-pose la tête est au-dessus du poing ; bras baissé, il pointe vers l'avant-extérieur)
  2. tous : flamme = aileron lisse → deux grandes volutes faites chacune de deux mèches côte à côte (sillon), longueurs et enroulements différents
  3. front/close-up : frange = rangée de dents égales → longueurs alternées, balayage plus fort, largeurs variées
  4. back : boucle/mèche qui dépasse à l'arrière droit → détail (verre droit vu de dos), laissé
  5. back : deux tons trop contrastés → HairDark rapproché
  6. lunettes : verres orange = cheveux → verres jaune-ambre plus clairs
  7. palette : orange partout → laissé (cheveux = signature braise ; lacets crème)
  8. lacets griffonnés → lacets plus épais et en relief
  9. jambes cachées → bas du tablier à z 0,175
  10. oreille = grand disque → oreille plus petite, avancée
- Round 5 fixes applied → v6 (71,9K tris)
- Review round 6 (review/round6.png, round6_clay.png) — relecteur neuf : « proche du niveau vitrine », 1 bloquant
  1. front/close-up : sourcil droit caché par la frange (balayée vers la droite, pointes à el 8° sous les sourcils à z 0,795) → pointes de frange à el ≥ 16°
  2. side : la tête du marteau dépasse devant la bouche → T-pose seulement (bras baissé, le marteau est devant-dehors) ; laissé, inclinaison ramenée à 30°
  3. side : cristal de l'emblème dépasse du tablier → cristal aplati (profondeur ×0,35)
  4. side : lacets en brindilles sur la pointe → lacets remontés sur la tige (z 0,072-0,108)
  5. front : tête de marteau = bloc → manche allongé (y 0,09 → -0,26) ; la forme est lisible de trois quarts et de dos
  6. q_left/q_right : doigts peu séparés → éventail plus large, doigts plus fins, voxel 1,8 mm
  7. legs : peu de jambe visible → accepté (chibi), le tablier est déjà remonté
  8. back : cheveux arrière lourds et longs → mèches arrière à -32°, sous-couche à -50°, calotte à -48°
  9. palette : orange répandu → accepté (les cheveux sont la signature)
- Round 6 fixes applied → v7 (73,2K tris) ; main gauche à quatre doigts séparés + pouce (vérifiée de près)
- Review round 7 (review/round7.png, round7_clay.png) — relecteur neuf : « je le montrerais tel quel », rien de bloquant → fin des rounds sur le modèle (7 rounds)
  détails corrigés (peu coûteux) : 1. bande de peau à la nuque → sous-couche à -58° ; 3. sourcils asymétriques (le droit mordu par la frange) → frange droite raccourcie (el ≥ 20°), sourcils remontés de 4 mm
  détails laissés, argumentés : 2. mèches toutes en goutte en argile (tient en couleur) ; 4-5. main ouverte « saucisses » de trois quarts, poing peu lisible de face (vu de dos : correct) ; 6. tête du marteau en « hachoir » de face, en T-pose seulement — bras baissé elle se présente de profil ; 7. « rien ne brille » : la lueur a été essayée (rounds 3-4) et blanchissait verres et cristal en saumon sous le tone mapping ; gardée faible (émission 0,30-0,45)
  note : le relecteur a écrit ses recadrages dans /tmp/crops (hors du dossier de l'asset) — déplacés dans review/round7_crops/
- v8 final static (round 7 details applied). Scripts: scripts/smith_skin.py, scripts/smith_build.py (build_all + cleanup)
- IMPORT (scripted, implicit): 20 objets SK_KilnSmith*, bbox 1,02 × 0,50 × 1,045 m (marteau compris ; peau 0,86 × 0,34 × 0,934 m), au sol (z min 0,000). Pose mesurée (règle 13, sections du bras) : -1,7° / 0,0° → T-pose
- CLEANUP: transforms identité ; fusion 1e-5 m (peau : 1 sommet) ; fusion du tablier annulée (elle créait 6 arêtes à > 2 faces) ; 0 sommet isolé ; normales recalculées ; 0 arête fusionnée sur tout le modèle ; orphelins purgés. 73 160 tris (tier detailed 20-80K : dans la fourchette ; postes : peau 21,0K, cheveux+calotte+flamme 15,2K, tablier 7,8K, mains 7,7K, lunettes 3,6K) — rapporté, pas de décimation (règle 4)
- TEXTURING: sauté — modélisé par script, matériaux Principled par valeurs assignés à la construction (20 matériaux M_*, aucune texture image, aucun nœud procédural), palette en sRGB convertie en linéaire. UV : aucune texture → uv_check sans objet
- RIG: tools/autorig.py (SkinTokens, installé, version testée) sur la peau soudée (10 916 sommets) → 30 os déformants nommés Mixamo, 363,9 sommets/os (règle 26), 0 os mort, 0 sommet non pondéré, ≤ 4 influences, 46,7 s. Post-traitement scripts/smith_rig.py : LeftEyelid/RightEyelid → LeftEye/RightEye + enfants LeftEyeShine/RightEyeShine (reflets à 100 %, clignement par écrasement) ; poids de la peau transférés (Data Transfer, face la plus proche interpolée, os de la région, ≤ 4, normalisés) sur tablier (Hips…Spine2 + cuisses), ceinture, col, revers, bottes, mains ; marteau 100 % RightFingers (doigts raides, --stiff-fingers). Validateur : 0 os mort, 0 sommet non pondéré. → rig/kiln-smith_rigged.glb / .blend
- ANIMATE: route humanoïde nommé kiln + mouvements de presets.py → `tools/presets.py animate --motion walk,idle --loop --calm --blink --stiff-fingers` (chibi : --calm ; yeux : --blink ; doigts dans la paume : --stiff-fingers). Prises A et B comparées :
  - walk_loop A : 1,03 s, glissement 33,9 mm/s, bras dans le corps 324 mm², jointure 1,18× ; B : 2,17 s, 48,3 mm/s, 19 mm², 0,77× → A retenue (glissement)
  - idle_loop A et B : 0,6 s seulement (jointure 1,43× / 0,71×) — trop court pour un idle → scripts/smith_anim.py : prise idle entière (3,97 s), dernières 24 images fondues vers la première pose, clé P = clé 0
  - défaut trouvé à l'export : le walk_loop de presets restait centré à y = -0,898 m (dérive retirée, pas le décalage) → recentré (os Hips, décalage converti dans son repère) ; idle décalé de 4 mm
  - livrés : 2 clips `walk` (31 images, 30 fps) et `idle` (119 images), en place. motion_measure : walk glissement 33,9 mm/s, 0 mm sous le sol, bras/corps 324 mm² moyen (pire 1 400), jointure 1,18×, 0 genou qui claque ; idle 0,1 mm/s, 0 mm, 6 mm², jointure 0,15×, 0. Semelles au sol 0-1 mm aux appuis (le foot_float ~10 mm de la mesure est la peau, posée sur la semelle séparée). 1 clignement dans walk, 3 dans idle (dont un double)
- Motion round 1 (review/motion1_walk.png, motion1_walk_matcap.png, motion1_idle.png) — relecteur neuf : ni l'un ni l'autre tel quel
  1. walk : clignement à chaque boucle de 1,03 s = un par seconde → clés d'échelle des yeux remises au repos dans walk (les clignements restent dans idle)
  2. walk : bras du marteau trop ample et asymétrique (avant-bras jusqu'à 76° contre 59° à gauche, marteau au niveau du visage) → oscillation de RightArm ×0,6 et RightForeArm ×0,4 autour de leur pose moyenne
  3. walk : bas du tablier suit chaque cuisse, genou qui bombe → détail, laissé (poids de cuisse transférés exprès pour que la jambe ne traverse pas)
  4-5. walk : paume ouverte en avant, doigts raides → détail, laissé (pas d'os de doigt dans la main séparée)
  6. idle : quasi figé → respiration (Spine2 ±1,8°, 2 cycles), rotation et balancement du buste (Spine1 ±2° / ±1,5°), regard (Head ±7° lacet, ±3° roulis), épaules sur la respiration — cycles entiers sur la boucle
  7. idle : bras à 41° de la verticale (pose en A, « mannequin ») → bras rapprochés de 6° (mesuré : 9° → 2 193 mm² de bras dans le corps, 6° → 0)
  bugs trouvés en route : Quaternion(Vector4) et Vector4.normalized() (4e composante non normalisée, Blender 5.2.2) donnaient un bras retourné derrière l'épaule (16 187 mm²) → moyenne normalisée à la main
  mesures après : walk glissement 33,9 mm/s, 0 mm sous le sol, bras/corps 274 mm² (pire 1 273), jointure 1,15×, 0 genou ; idle 0,1 mm/s, 0 mm, 0 mm², jointure 1,16×, 0 genou
- Motion round 2 (review/motion2_*.png) — relecteur neuf : walk non, idle « presque »
  1. walk front : la cuisse gauche levée passe devant le tablier, jupe fendue → scripts/smith_apron_weights.py : jupe en dégradé Hips (taille) → 85 % cuisse de son côté (ourlet), fondu sur ±6 cm au centre
  2. walk side : la main libre plonge dans le tablier → LeftArm ×0,75, LeftForeArm ×0,6 autour de la pose moyenne
  3. walk side : buste en arrière (tête 12-16 mm derrière les hanches) → Spine +4°, Spine1 +3° vers l'avant (signe mesuré sur la tête)
  4-6. jupe raide, bras du marteau écarté, marteau qui tourne avec l'avant-bras → détails, laissés
  idle : 1. « clin d'œil » f30 → mesuré : les deux yeux à la même échelle, c'est la rotation de tête — rien à corriger ; 2. marteau de face sur la main → poignet droit tourné de 35° ; 3. encore trop discret → amplitudes ×1,6-1,9 (tête ±13°, respiration ±3°, buste ±4° / ±2,5°)
  export : 20 NODE_SKINNED_MESH_NON_ROOT à la ré-exportation → maillages remis à la racine avant export → 0
  mesures après : walk 33,9 mm/s, 0 mm, bras/corps 282 mm² (pire 1 273), jointure 1,14×, 0 genou ; idle 0,1 mm/s, 0 mm, 0 mm², jointure 1,23×, 0 genou
  note : le relecteur a de nouveau écrit dans /tmp/crops → déplacé dans review/motion2_crops/, /tmp/crops supprimé
- Motion round 3 (review/motion3_*.png) — relecteur neuf : « je livrerais les deux », rien de bloquant → fin des rounds sur le mouvement (3)
  détail corrigé : arc du marteau vers l'avant encore ample → RightArm ×0,4 (au lieu de 0,6) ; mesures finales walk 33,9 mm/s, 0 mm, bras/corps 260 mm² (pire 1 152), jointure 1,14×, 0 genou
  laissés : pli du bas du tablier sur la cuisse levée, pas court « calme » plutôt que bondissant (style Kimodo --calm), idle discret ; œil « mi-clos » f30 = début du clignement (deux yeux à 0,69) vu tête tournée ; jointure idle 1,23× (cible 1,2 : les couches procédurales, pas le fondu — 24/30/36 images → 1,23/1,23/1,22)
- Matcap avant livraison (review/matcap/rest_matcap_*.png, au repos ; mi-pas : review/motion3_walk_matcap.png) : visage, main, nuque propres ; deux gros plans (épaule, botte) masqués par d'autres surfaces en T-pose, couverts par les planches de rounds
- OPTIMIZE: auto, glTF web — aucune texture (matériaux par valeurs) donc pas d'étape resize/WebP ; Draco seul (gltf-transform draco, position 14 bits, normales 10 bits) : 2,23 MB → 478,7 KB (-78 %). Géométrie non touchée (pas de simplify, règle 20). Draco demande un décodeur côté client (three.js : DRACOLoader)
- EXPORT: audit matériaux (règle 19) : 22 Principled, 0 nœud procédural, 0 texture, 0 slot vide. export_apply=False. Maillages skinnés à la racine (0 NODE_SKINNED_MESH_NON_ROOT). gltf-transform validate : exit 0 sur les trois fichiers ; sur le final, 1 UNSUPPORTED_EXTENSION (Draco non décodé par le validateur) + 48 UNUSED_OBJECT, sévérité info. 73 160 tris, 1 skin / 32 joints, 2 clips (walk 1,03 s, idle 3,97 s, 30 fps), KHR_materials_emissive_strength
  - web/kiln-smith_final.glb — 478,7 KB, Draco : pour le site
  - kiln-smith_preview.glb — 2,23 MB, sans Draco ni WebP (extensionsUsed : KHR_materials_emissive_strength seulement) : s'ouvre dans l'aperçu du Mac
  - kiln-smith_original.glb — 2,23 MB, la source non compressée
  - kiln-smith.blend — scène riggée + actions walk/idle (le statique se reconstruit par scripts/smith_build.py)
  - Studio checks : triangles OK ; notes voulues : 1,04 m (chibi, pas 1,75 m) ; origine au centre de la base des pieds, la boîte est décentrée par le marteau
- Intermédiaires gardés (mode compact, personne pour répondre — à supprimer sur demande) : review/ (sheets des rounds 1-7, planches mouvement 1-4, matcap, recadrages des relecteurs), rig/ (statique, rig SkinTokens + .blend), anim/ (clip assemblé + mesures), anim_try/ (sorties presets A/B), rig_test/ (essai de rig sur v6), scripts/

## Licenses
- Clips walk/idle : NVIDIA Kimodo (Kimodo-SOMA-RP-v1.1) — Licensed by NVIDIA Corporation under the NVIDIA Open Model License; NVIDIA claims no ownership of outputs; commercial use allowed. Retarget : image-to-3dlab, Apache-2.0 (plugin/NOTICE)
- SkinTokens (VAST-AI) : code et poids MIT ; patch Mac de kiln Apache-2.0 (plugin/NOTICE)
- Modèle, matériaux, rig post-traité, boucles : création originale de cette session (scripts/), aucun asset externe — libre d'usage pour le propriétaire du projet

## Checkpoint
- Last completed step: [7] EXPORT — done (web/kiln-smith_final.glb)
- Timestamp: 2026-10-28
