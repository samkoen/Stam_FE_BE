# -*- coding: utf-8 -*-
import sys
import diff_match_patch as dmp_module

# Forcer UTF-8 pour la sortie
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

dmp = dmp_module.diff_match_patch()

# Cas 1: Reference: "שמע ישראל" Detecte: "שמע שראל"
ref = "שמע ישראל"
det1 = "שמע שראל"

diff1 = dmp.diff_main(ref, det1)
dmp.diff_cleanupSemantic(diff1)

print("=" * 60)
print("CAS 1: Reference='שמע ישראל'  Detecte='שמע שראל'")
print("=" * 60)
for i, (op, text) in enumerate(diff1):
    op_name = {0: "EGAL", -1: "SUPPRIME", 1: "AJOUTE"}[op]
    print(f"  [{i}] op={op} ({op_name:8}) text='{text}' (len={len(text)})")
    if op == -1 and i + 1 < len(diff1) and diff1[i + 1][0] == 1:
        print(f"      -> SUBSTITUTION: '{text}' remplace par '{diff1[i + 1][1]}'")

print("\n" + "=" * 60)
print("CAS 2: Reference='שמע ישראל'  Detecte='שמע אל'")
print("=" * 60)

# Cas 2: Reference: "שמע ישראל" Detecte: "שמע אל"
det2 = "שמע אל"
diff2 = dmp.diff_main(ref, det2)
dmp.diff_cleanupSemantic(diff2)

for i, (op, text) in enumerate(diff2):
    op_name = {0: "EGAL", -1: "SUPPRIME", 1: "AJOUTE"}[op]
    print(f"  [{i}] op={op} ({op_name:8}) text='{text}' (len={len(text)})")
    if op == -1 and i + 1 < len(diff2) and diff2[i + 1][0] == 1:
        print(f"      -> SUBSTITUTION: '{text}' remplace par '{diff2[i + 1][1]}'")

print("\n" + "=" * 60)
print("RESUME:")
print("=" * 60)
print("\nCAS 1: 'שמע ישראל' vs 'שמע שראל'")
print("  - op=0: 'שמע ' (identique)")
print("  - op=-1: 'י' (supprime)")
print("  - op=0: 'שראל' (identique)")
print("  -> Pas de substitution detectee car diff_cleanupSemantic a regroupe")

print("\nCAS 2: 'שמע ישראל' vs 'שמע אל'")
print("  - op=0: 'שמע ' (identique)")
print("  - op=-1: 'ישר' (supprime - 3 lettres manquantes)")
print("  - op=0: 'אל' (identique)")
print("  -> Pas de substitution, juste des lettres manquantes")

