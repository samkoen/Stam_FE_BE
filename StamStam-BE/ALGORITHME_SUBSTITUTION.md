# Algorithme de correction pour les substitutions

## Définition d'une substitution

Une **substitution** est détectée quand :
- `op == -1` (lettre supprimée dans le texte détecté)
- **ET** `op == 1` suit immédiatement (lettre ajoutée dans le texte détecté)

Cela signifie qu'une lettre attendue a été remplacée par une autre lettre détectée.

**Exemple :**
- Référence : `"שמע ישראל"`
- Détecté : `"שמע שראל"`
- Diff : `[(0, "שמע "), (-1, "י"), (1, "ש"), (0, "ראל")]`
- → Substitution : `"י"` remplacé par `"ש"`

## Algorithme de correction

Quand une substitution est détectée, l'algorithme suit cette logique :

### Étape 1 : Analyser les dimensions

```python
expected_text = text  # Texte attendu (ex: "י")
added_text = diff[diff_idx + 1][1]  # Texte détecté (ex: "ש")
```

### Étape 2 : Choisir la stratégie selon les dimensions

#### **CAS 1 : N rectangles détectés au lieu d'1 lettre attendue**

**Condition :**
```python
len(added_text) >= 2 and len(expected_text) == 1
```

**Exemple :**
- Attendu : `"ז"` (1 lettre)
- Détecté : `"צלי"` (3 rectangles = 3 lettres)

**Stratégie : Fusion**
- Utilise `FusionCorrection` via `CorrectionManager`
- Fusionne les N rectangles en 1 lettre
- Teste si la fusion donne la lettre attendue

**Code :**
```python
result = correction_manager.try_correct_error(
    rect_idx=rect_idx,
    valid_rects_final=corrected_rects,
    valid_codes=corrected_codes,
    expected_char=expected_text[0],  # "ז"
    detected_char=added_text[0],     # "צ"
    detected_chars=added_text,        # "צלי"
    ...
)
```

**Si succès :**
- Remplace les N rectangles par 1 rectangle fusionné
- Met à jour les codes
- Recalcule le diff

**Si échec :**
- Continue avec les autres cas (si applicable)

---

#### **CAS 2 : 1 rectangle détecté au lieu d'1 lettre attendue**

**Condition :**
```python
len(added_text) == 1 and len(expected_text) == 1
```

**Exemple :**
- Attendu : `"ק"` (1 lettre)
- Détecté : `"ה"` (1 rectangle = 1 lettre)

**Stratégie : Extension hauteur OU Réunification**

Le `CorrectionManager` applique cette logique :

##### **Sous-cas 2.1 : Cas spécial 'ה' → 'ק'**

**Condition :**
```python
detected_char == 'ה' and expected_char == 'ק'
```

**Stratégie : Extension de hauteur**
- Utilise `HeightExtensionCorrection`
- Étend le rectangle vers le haut pour capturer la partie manquante du 'ק'
- Re-prédit la lettre avec le rectangle étendu

**Code :**
```python
result = height_extension.try_correct(
    rect_idx=rect_idx,
    expected_char='ק',
    detected_char='ה',
    ...
)
```

**Si succès :** Correction appliquée

**Si échec :** Passe au sous-cas 2.2

##### **Sous-cas 2.2 : Cas général (ou si 2.1 échoue)**

**Stratégie : Réunification**
- Utilise `ReunificationCorrection`
- Essaie de trouver la lettre attendue en combinant le rectangle actuel avec les rectangles adjacents
- Teste différentes combinaisons (rect_idx-1 + rect_idx, rect_idx + rect_idx+1, etc.)

**Code :**
```python
result = reunification.try_correct(
    rect_idx=rect_idx,
    expected_char=expected_char,
    detected_char=detected_char,
    ...
)
```

**Si succès :** Correction appliquée

**Si échec :** Aucune correction possible, l'erreur reste

---

## Flux complet de l'algorithme

```
Substitution détectée (op=-1 suivi de op=1)
    │
    ├─→ CAS 1: N rectangles → 1 lettre ?
    │       │
    │       ├─→ OUI → FusionCorrection
    │       │       │
    │       │       ├─→ Succès → Correction appliquée ✓
    │       │       └─→ Échec → Continue
    │       │
    │       └─→ NON → Continue
    │
    └─→ CAS 2: 1 rectangle → 1 lettre ?
            │
            ├─→ OUI → CorrectionManager
            │       │
            │       ├─→ Cas spécial 'ה'→'ק' ?
            │       │       │
            │       │       ├─→ OUI → HeightExtensionCorrection
            │       │       │       │
            │       │       │       ├─→ Succès → Correction appliquée ✓
            │       │       │       └─→ Échec → Continue
            │       │       │
            │       │       └─→ NON → Continue
            │       │
            │       └─→ ReunificationCorrection
            │               │
            │               ├─→ Succès → Correction appliquée ✓
            │               └─→ Échec → Erreur non corrigée ✗
            │
            └─→ NON → Aucune correction
```

## Exemples concrets

### Exemple 1 : Fusion (CAS 1)

**Situation :**
- Référence : `"שמע זראל"`
- Détecté : `"שמע צליראל"`
- Diff : `[(0, "שמע "), (-1, "ז"), (1, "צלי"), (0, "ראל")]`

**Correction :**
1. Détecte substitution : `"ז"` → `"צלי"`
2. CAS 1 : 3 rectangles (`"צלי"`) au lieu de 1 (`"ז"`)
3. Appelle `FusionCorrection`
4. Fusionne les 3 rectangles en 1
5. Re-prédit : doit donner `"ז"`
6. Si succès : remplace `"צלי"` par `"ז"`

### Exemple 2 : Extension hauteur (CAS 2.1)

**Situation :**
- Référence : `"שמע קראל"`
- Détecté : `"שמע הראל"`
- Diff : `[(0, "שמע "), (-1, "ק"), (1, "ה"), (0, "ראל")]`

**Correction :**
1. Détecte substitution : `"ק"` → `"ה"`
2. CAS 2 : 1 rectangle → 1 lettre
3. CAS 2.1 : `"ה"` → `"ק"` (cas spécial)
4. Appelle `HeightExtensionCorrection`
5. Étend le rectangle vers le haut
6. Re-prédit : doit donner `"ק"`
7. Si succès : remplace `"ה"` par `"ק"`

### Exemple 3 : Réunification (CAS 2.2)

**Situation :**
- Référence : `"שמע בראל"`
- Détecté : `"שמע הראל"`
- Diff : `[(0, "שמע "), (-1, "ב"), (1, "ה"), (0, "ראל")]`

**Correction :**
1. Détecte substitution : `"ב"` → `"ה"`
2. CAS 2 : 1 rectangle → 1 lettre
3. CAS 2.1 : Non applicable (pas 'ה'→'ק')
4. CAS 2.2 : Appelle `ReunificationCorrection`
5. Teste combinaisons avec rectangles adjacents
6. Si trouve `"ב"` : remplace `"ה"` par `"ב"`

## Points importants

1. **Ordre de priorité :**
   - CAS 1 (Fusion) est testé en premier
   - CAS 2.1 (Extension hauteur) est testé avant CAS 2.2
   - CAS 2.2 (Réunification) est le dernier recours

2. **Recalcul du diff :**
   - Après chaque correction réussie, le diff est recalculé
   - La boucle recommence depuis le début
   - Permet de corriger plusieurs erreurs en cascade

3. **Limite d'itérations :**
   - Maximum 100 itérations pour éviter les boucles infinies
   - Si limite atteinte, l'algorithme s'arrête

4. **Sauvegarde/restauration :**
   - Dans CAS 2, l'état est sauvegardé avant correction
   - Si échec, l'état est restauré
   - Évite de corrompre les données

