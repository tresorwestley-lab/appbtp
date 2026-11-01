# Application de Génie Civil (Python Shiny)

Calcul d'une pièce en béton soumise à un effort axial : contrainte, déformation,
allongement, résistance de calcul, taux de travail et verdict.

## Formules utilisées (unités : N, mm, MPa)
| Grandeur | Formule |
|---|---|
| Contrainte | σ = F / S |
| Déformation | ε = σ / E = F / (E·S) (sans unité) |
| Allongement | ΔL = ε · L = F·L / (E·S) |
| Déformation transversale | ε_t = −ν · ε |
| Module de cisaillement | G = E / [2(1+ν)] |
| Résistance de calcul | f_cd = f_ck / γc (γc = 1,5) |
| Taux de travail | σ / f_cd (≤ 100 % pour être vérifié) |
| Effort admissible | N_Rd = f_cd · S |
| Module du béton (Eurocode 2) | E_cm = 22·((f_ck+8)/10)^0,3 |
| BAEL | E_ij = 11000·f_cj^(1/3) ; f_tj = 0,6 + 0,06·f_cj |
| Essais | f_c = F/S ; f_t = 2F/(π·L·D) ; σ = 3Fl/(2bh²) |

## Lancer en local
    pip install -r requirements.txt
    shiny run app.py --port 8000
Puis ouvrir http://127.0.0.1:8000

## Tests des formules
    pip install pytest
    pytest

## Déploiement Railway
Le fichier `Procfile` est fourni : poussez le dossier tel quel.

## Fichiers
- `app.py` : interface et serveur Shiny
- `calculs.py` : formules (sans interface, testables)
- `test_calculs.py` : tests

Outil pédagogique : ne remplace pas le calcul d'un ingénieur.
