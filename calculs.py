"""Formules de résistance des matériaux et de béton (module sans interface).

Unités utilisées partout dans ce fichier :
    forces       : N          contraintes / modules : MPa (= N/mm²)
    longueurs    : mm         sections              : mm²
Les conversions depuis l'interface (kN, m, cm², GPa) sont faites dans
`calculer_structure`.
"""
from dataclasses import dataclass
import math

# Classes de béton -> fck (MPa) : résistance caractéristique en compression à 28 j
CLASSES_BETON = {"C20": 20, "C25": 25, "C30": 30, "C35": 35, "C40": 40, "C50": 50}

POIDS_VOLUMIQUE_BETON = 25.0  # kN/m³


# ---------------------------------------------------------------------------
# 1. Contraintes
# ---------------------------------------------------------------------------
def contrainte_normale(F, S):
    """σ = F / S   (F en N, S en mm²  ->  σ en MPa)"""
    return F / S


def contrainte_cisaillement(T, S):
    """τ = T / S"""
    return T / S


def contrainte_flexion(M, y, I):
    """σ = M·y / I   (M en N·mm, y en mm, I en mm⁴)"""
    return M * y / I


# ---------------------------------------------------------------------------
# 2-3. Allongement et déformation
# ---------------------------------------------------------------------------
def deformation_longitudinale(sigma, E):
    """ε = σ / E = F / (E·S)   (sans unité)"""
    return sigma / E


def allongement(epsilon, L0):
    """ΔL = ε · L0 = F·L / (E·S)"""
    return epsilon * L0


def deformation_transversale(epsilon_l, nu):
    """ε_t = −ν · ε_l"""
    return -nu * epsilon_l


# ---------------------------------------------------------------------------
# 4. Élasticité
# ---------------------------------------------------------------------------
def module_cisaillement(E, nu):
    """G = E / [2(1 + ν)]"""
    return E / (2 * (1 + nu))


def module_ecm_eurocode_gpa(fck):
    """E_cm = 22 · (f_cm / 10)^0,3   avec f_cm = f_ck + 8   (résultat en GPa)"""
    return 22 * ((fck + 8) / 10) ** 0.3


def module_eij_bael(fcj):
    """E_ij = 11 000 · f_cj^(1/3)   (MPa)"""
    return 11000 * fcj ** (1 / 3)


# ---------------------------------------------------------------------------
# 5. Résistances
# ---------------------------------------------------------------------------
def resistance_compression(Fmax, S):
    """f_c = F_max / S"""
    return Fmax / S


def resistance_traction_acier(Fmax, S0):
    """R_m = F_max / S0"""
    return Fmax / S0


def resistance_fendage(F, L, D):
    """f_t = 2F / (π·L·D)"""
    return 2 * F / (math.pi * L * D)


def resistance_traction_bael(fcj):
    """f_tj = 0,6 + 0,06 · f_cj"""
    return 0.6 + 0.06 * fcj


def resistance_flexion_3pts(F, l, b, h):
    """σ = 3·F·l / (2·b·h²)"""
    return 3 * F * l / (2 * b * h**2)


def resistance_calcul_beton(fck, gamma_c=1.5, alpha_cc=1.0):
    """f_cd = α_cc · f_ck / γ_c   (Eurocode 2 ; on RÉDUIT la résistance)"""
    return alpha_cc * fck / gamma_c


# ---------------------------------------------------------------------------
# Calcul complet d'une pièce en béton soumise à un effort axial
# ---------------------------------------------------------------------------
@dataclass
class ResultatStructure:
    sigma: float            # contrainte appliquée (MPa)
    epsilon: float          # déformation longitudinale (sans unité)
    epsilon_pct: float      # idem en %
    delta_L_mm: float       # allongement / raccourcissement (mm)
    epsilon_t: float        # déformation transversale
    G_gpa: float            # module de cisaillement (GPa)
    fcd: float              # résistance de calcul (MPa)
    taux: float             # σ / fcd
    coef_securite: float    # fcd / σ  (inf si σ = 0)
    effort_max_kn: float    # effort admissible N_Rd
    poids_propre_kn: float  # poids propre de la pièce
    verdict: str            # "ok", "limite" ou "non"


def _positif(valeur, nom, strict=True):
    if valeur is None or isinstance(valeur, str):
        raise ValueError(f"« {nom} » est vide ou invalide.")
    try:
        v = float(valeur)
    except (TypeError, ValueError):
        raise ValueError(f"« {nom} » doit être un nombre.")
    if math.isnan(v) or (v <= 0 if strict else v < 0):
        raise ValueError(f"« {nom} » doit être {'strictement ' if strict else ''}positif.")
    return v


def calculer_structure(E_gpa, F_kn, L_m, S_cm2, fck, nu=0.2, gamma_c=1.5,
                       inclure_poids_propre=False):
    """Calcule déformation, allongement, contrainte et résistance.

    Lève ValueError avec un message clair si une entrée est invalide.
    """
    E_gpa = _positif(E_gpa, "Module d'élasticité")
    F_kn = _positif(F_kn, "Effort appliqué", strict=False)
    L_m = _positif(L_m, "Longueur")
    S_cm2 = _positif(S_cm2, "Section")
    fck = _positif(fck, "Résistance fck")
    gamma_c = _positif(gamma_c, "Coefficient γc")
    if nu is None or not (0 <= float(nu) <= 0.5):
        raise ValueError("Le coefficient de Poisson doit être compris entre 0 et 0,5.")
    nu = float(nu)
    if gamma_c < 1:
        raise ValueError("Le coefficient γc doit être supérieur ou égal à 1.")

    # Conversions vers N, mm, MPa
    E = E_gpa * 1000.0            # GPa -> MPa
    S = S_cm2 * 100.0             # cm² -> mm²
    L = L_m * 1000.0              # m   -> mm
    pp_kn = POIDS_VOLUMIQUE_BETON * (S_cm2 / 1e4) * L_m
    F = (F_kn + (pp_kn if inclure_poids_propre else 0.0)) * 1000.0

    sigma = contrainte_normale(F, S)
    eps = deformation_longitudinale(sigma, E)
    dL = allongement(eps, L)
    eps_t = deformation_transversale(eps, nu)
    G = module_cisaillement(E, nu) / 1000.0
    fcd = resistance_calcul_beton(fck, gamma_c)
    taux = sigma / fcd
    coef = math.inf if sigma == 0 else fcd / sigma
    n_rd = fcd * S / 1000.0

    verdict = "ok" if taux <= 0.8 else ("limite" if taux <= 1.0 else "non")
    return ResultatStructure(sigma, eps, eps * 100, dL, eps_t, G, fcd, taux,
                             coef, n_rd, pp_kn, verdict)
