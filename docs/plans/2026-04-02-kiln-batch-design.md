# /kiln:batch — Multi-Asset Batch Pipeline

## Vue d'ensemble

`/kiln:batch` ajoute un mode batch au pipeline blender-kiln. Il sépare la prise de décision (wizard interactif) de l'exécution (runner autonome) via un fichier manifest YAML.

```
[WIZARD]  →  [MANIFEST]  →  [RUNNER]
interactif    fichier YAML    autonome
```

**Cas d'usage :**
- Générer 5-15 assets d'une même scène/thème en une seule session
- Lancer avant de dormir (machine + Blender allumés), review le matin
- Relancer les échecs ou affiner des assets individuels via le manifest

**Contrainte technique :** nécessite Blender MCP en local (machine allumée + Blender ouvert). Pas compatible avec le schedule remote de Claude (cloud).

---

## Commandes

| Commande | Action |
|----------|--------|
| `/kiln:batch` | Lance le wizard → génère le manifest → propose de lancer |
| `/kiln:batch run <dossier>` | Exécute un manifest existant (assets non-done) |
| `/kiln:batch run <dossier> --all` | Force le rerun de tous les assets |
| `/kiln:batch run <dossier> --asset <name>` | Rerun un seul asset |

---

## Wizard

Le wizard pose les questions dans cet ordre, une à la fois.

### Étape 1 — Contexte global

1. **Thème/scène** : description libre ("Bureau d'entreprise moderne")
2. **Style visuel** : réaliste / stylisé / low-poly / cartoon
3. **Target d'export** : glTF-web / Unity FBX / Unreal FBX / USDZ AR / multi
4. **Tier par défaut** : lightweight / balanced / detailed

### Étape 2 — Liste d'assets

L'utilisateur liste les assets avec une brève description :
```
desk: bureau rectangulaire moderne, plateau bois, pieds métal
chair: chaise ergonomique, mesh noir
keyboard: clavier mécanique compact
...
```

### Étape 3 — Matériaux

Le wizard demande : "Tu veux définir la palette matériaux ou je la déduis du thème ?"

- **"Déduis"** → le wizard propose une palette avec description humaine + ref technique :
  ```
  wood:    Bois clair vieilli, chaleureux     (polyhaven: wood_cabinet_worn_long)
  metal:   Métal noir brossé, semi-mat        (procédural: metallic 1.0, roughness 0.3)
  ```
  L'utilisateur valide ou ajuste.

- **"Je définis"** → le wizard demande les matériaux un par un avec description + source.

La palette est partagée entre tous les assets du batch pour garantir la cohérence visuelle.

### Étape 4 — Recap & ajustements

Le wizard infère la méthode de création par asset et affiche le manifest résumé :

```
── Manifest généré ─────────────────────────
Scène: corporate-office │ réaliste │ balanced │ gltf-web

  #  Asset     Méthode         Matériaux        Tier
  1  desk      scripted        wood + metal     balanced
  2  chair     hunyuan3d       fabric + plastic balanced
  3  keyboard  marketplace     plastic          lightweight
  ...

⚠️ Estimation : ~350K-550K tokens (marge ±50%)
   Retries réseau, complexité matériaux et erreurs peuvent
   doubler un asset individuel. Compter x1.5 en marge de sécurité.
```

**Heuristiques de recommandation de méthode :**
- Props géométriques simples (table, étagère, porte) → scripted
- Props organiques/complexes (chaise ergonomique, lampe articulée) → hunyuan3d
- Personnages → hunyuan3d (toujours)
- Patterns répétitifs (câbles, grilles) → geometry-nodes
- Assets très standards (clavier, écran, souris) → marketplace

L'utilisateur peut ajuster n'importe quelle ligne avant validation.

### Étape 5 — Lancement

```
Lancer maintenant ? (oui / plus tard)
```

Si "plus tard" → le manifest est écrit, l'utilisateur lance quand il veut avec `/kiln:batch run`.

---

## Runner

Le runner lit le manifest et exécute chaque asset séquentiellement, de manière autonome (zero interaction).

### Boucle principale

```
Pour chaque asset où status ≠ "done" :
  1. Ouvrir une scène Blender vierge (clear scene)
  2. Exécuter le pipeline : BRIEF → CHOIX → IMPORT → CLEANUP → TEXTURING → OPTIMIZE → EXPORT
  3. Sauvegarder dans batch-folder/asset-name/
  4. Prendre screenshot viewport finale
  5. Mettre à jour le manifest : status → "done" + stats (faces, taille, durée)
  6. Logger dans batch-report.md
  
  Si erreur :
    → Log l'erreur dans le manifest (status: "failed", error: "message")
    → Passer à l'asset suivant
    → Pas de retry, pas de fallback inter-méthode (cohérence DA)
```

### Différences avec /kiln interactif

| Comportement | `/kiln` (interactif) | `/kiln:batch` runner |
|---|---|---|
| CHOIX (marketplace/create) | Demande à l'user | Pré-décidé dans le manifest |
| Méthode de création | Recommande, user choisit | Pré-décidée dans le manifest |
| Matériaux | Propose, user valide zones | Auto depuis la palette manifest |
| Décimation | Before/after, user valide | Auto si >50% hors range du tier |
| Optimization | User choisit outils/params | Preset du manifest |
| Screenshots | Affichées dans la conversation | Sauvegardées dans le dossier asset |

### Ce qui reste identique

- Toutes les iron rules (merge doubles, recalc normals, scale check, material audit, etc.)
- Le format des logs par asset
- La structure de fichiers (compact/full mode)
- Le .blend sauvegardé pour chaque asset

### Fin de batch

```
── Batch terminé ───────────────────────────
8/10 ✅ │ 2 ❌ (keyboard, lamp) │ ~25min

  1. Relancer les 2 échecs
  2. Relancer tout le batch
  3. Relancer un asset spécifique
  4. Éditer le manifest et relancer
  5. Terminé
```

---

## Structure de sortie

```
generated-assets/
└── batch-corporate-office-2026-04-02/
    ├── batch-manifest.yaml          ← brief d'entrée + statuts (reproductible)
    ├── batch-report.md              ← rapport global
    │
    ├── desk/
    │   ├── desk_final.glb
    │   ├── desk.blend
    │   ├── desk_screenshot.png
    │   └── desk_log.md
    │
    ├── chair/
    │   ├── chair_final.glb
    │   ├── chair.blend
    │   ├── chair_screenshot.png
    │   └── chair_log.md
    │
    └── keyboard/                    ← exemple d'échec
        └── keyboard_log.md          ← contient l'erreur + étape échouée
```

---

## Format du Manifest

```yaml
# batch-manifest.yaml — généré par /kiln:batch wizard
# Éditable manuellement. Le runner exécute les assets status ≠ done.

batch:
  name: corporate-office
  created: 2026-04-02T22:30:00
  description: "Bureau d'entreprise moderne, open space"

config:
  style: realistic
  target: gltf-web
  tier: balanced
  storage: compact
  backend: hf-spaces
  optimize_preset: resize-1k-webp-draco
  output_folder: ./generated-assets/batch-corporate-office-2026-04-02

palette:
  wood:
    description: "Bois clair vieilli, chaleureux"
    source: polyhaven
    id: wood_cabinet_worn_long
  metal:
    description: "Métal noir brossé, semi-mat"
    source: procedural
    params: { metallic: 1.0, roughness: 0.3, color: "#1a1a1a" }
  fabric:
    description: "Tissu gris anthracite chiné"
    source: polyhaven
    id: fabric_pattern_05
  plastic:
    description: "Plastique noir mat"
    source: procedural
    params: { metallic: 0.0, roughness: 0.6, color: "#2d2d2d" }

assets:
  - name: desk
    brief: "Bureau rectangulaire moderne, plateau bois clair, pieds métal tubulaire noir"
    method: scripted
    materials: [wood, metal]
    tier: balanced
    status: pending

  - name: chair
    brief: "Chaise ergonomique de bureau, assise mesh, structure plastique noir"
    method: hunyuan3d
    materials: [fabric, plastic]
    tier: balanced
    status: pending

  - name: keyboard
    brief: "Clavier mécanique compact, profil bas, gris foncé"
    method: marketplace
    materials: [plastic]
    tier: lightweight
    status: pending
```

### Statuts

| Status | Signification | Runner |
|--------|--------------|--------|
| `pending` | Pas encore traité | Exécute |
| `running` | En cours | Mis à jour en temps réel |
| `done` | Terminé avec succès | Skip |
| `failed` | Échoué (+ champ `error`) | Relance |
| `redo` | À refaire (marqué manuellement) | Relance |

### Champs ajoutés par le runner (après exécution)

```yaml
  - name: desk
    status: done
    result:
      faces: 2100
      file_size: 340KB
      duration: 180s
      screenshot: desk/desk_screenshot.png
```

---

## Gestion des erreurs

- **Pas de retry automatique** — skip + log + asset suivant
- **Pas de fallback inter-méthode** — cohérence DA prioritaire
- **Erreur loggée** dans le manifest (`error: "HF Space timeout"`) et dans `batch-report.md`
- **Relancement** via les options numérotées en fin de batch ou `/kiln:batch run`

---

## Budget / Tokens

- Le wizard affiche une **estimation** basée sur le nombre d'assets × méthode :
  - Scripted : ~30K tokens/asset
  - Marketplace : ~20K tokens/asset
  - Hunyuan3D : ~60-80K tokens/asset
  - Geometry Nodes : ~40K tokens/asset
- Warning explicite : "Estimation ±50%, retries et erreurs peuvent significativement augmenter la consommation"
- Pas de coupure automatique (pas de compteur weekly accessible)
- Garde-fou pragmatique : limiter le batch à un nombre raisonnable d'assets (5-10)

---

## Reproductibilité

- Le manifest est **versionnable** (git)
- Contient le brief complet de chaque asset → relançable tel quel
- Éditable pour ajuster un seul asset (`status: redo`) ou modifier des paramètres
- Même manifest + style différent = nouvelle variante de la scène
