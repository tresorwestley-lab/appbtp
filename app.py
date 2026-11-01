from shiny import App, ui, reactive, render
import pandas as pd

import calculs as c

# ============================================================================
# STYLE
# ============================================================================
CSS = """
.carte {background:#eef6ff; border-left:5px solid #0066cc; border-radius:6px;
        padding:10px 14px; margin-bottom:10px;}
.carte .titre {font-weight:600; color:#004080;}
.carte .valeur {font-size:1.35rem; font-weight:700;}
.carte .formule {font-family:monospace; color:#555; font-size:.85rem;}
.verdict {padding:14px; border-radius:8px; font-weight:700; font-size:1.1rem;
          margin:12px 0;}
.verdict.ok {background:#e3f6e8; color:#14692b; border:2px solid #2e9e4f;}
.verdict.limite {background:#fff4dc; color:#8a5a00; border:2px solid #e0a100;}
.verdict.non {background:#fde8e8; color:#9b1c1c; border:2px solid #d33;}
.erreur {background:#fde8e8; color:#9b1c1c; padding:12px; border-radius:6px;}
.note {color:#666; font-size:.85rem; margin-top:14px;}
"""


def carte(titre, valeur, formule):
    return ui.tags.div(
        ui.tags.div(titre, class_="titre"),
        ui.tags.div(valeur, class_="valeur"),
        ui.tags.div(formule, class_="formule"),
        class_="carte",
    )


def fmt(x, n=4):
    return f"{x:.{n}f}".replace(".", ",")


def fmt_sci(x):
    return f"{x:.4e}".replace(".", ",")


# ============================================================================
# INTERFACE
# ============================================================================
app_ui = ui.page_fluid(
    ui.tags.style(CSS),
    ui.h2("Application de Génie Civil", style="color:#004080; margin-bottom:20px;"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_text("nom_projet", "Nom du projet", ""),
            ui.h5("Béton"),
            ui.input_select("type_beton", "Classe de béton", list(c.CLASSES_BETON), selected="C25"),
            ui.input_numeric("resistance_mpa", "Résistance fck (MPa)", 25, min=1),
            ui.input_numeric("module_elasticite", "Module d'élasticité E (GPa)", 31.5, min=0.1),
            ui.input_numeric("poisson", "Coefficient de Poisson ν", 0.2, min=0, max=0.5, step=0.05),
            ui.input_numeric("gamma_c", "Coefficient partiel γc", 1.5, min=1, step=0.05),
            ui.hr(),
            ui.h5("Pièce et chargement"),
            ui.input_numeric("effort", "Effort appliqué (kN)", 50, min=0),
            ui.input_numeric("longueur", "Longueur (m)", 3, min=0.01),
            ui.input_numeric("section", "Section (cm²)", 300, min=1),
            ui.input_checkbox("poids_propre", "Ajouter le poids propre à l'effort", False),
            ui.hr(),
            ui.h5("Ajouter un matériel"),
            ui.input_text("nom_materiel", "Nom du matériel"),
            ui.input_numeric("quantite_materiel", "Quantité", 1, min=1),
            ui.input_numeric("poids_unitaire", "Poids unitaire (kg)", 10, min=0),
            ui.input_action_button("ajouter_materiel", "Ajouter"),
            width=340,
        ),
        ui.navset_tab(
            ui.nav_panel("Résultats", ui.output_ui("resultats_ui"),
                         ui.download_button("telecharger", "Télécharger les résultats (CSV)")),
            ui.nav_panel(
                "Matériaux",
                ui.output_table("table_materiaux"),
                ui.output_ui("total_materiaux"),
                ui.input_action_button("supprimer_dernier", "Supprimer la dernière ligne"),
                ui.input_action_button("vider", "Tout vider"),
            ),
            ui.nav_panel(
                "Essais de résistance",
                ui.h4("Compression (f_c = F_max / S)"),
                ui.layout_columns(
                    ui.input_numeric("fc_F", "Charge de rupture (kN)", 500, min=0),
                    ui.input_numeric("fc_S", "Section éprouvette (cm²)", 225, min=0.1),
                ),
                ui.output_ui("res_compression"),
                ui.hr(),
                ui.h4("Fendage (f_t = 2F / π·L·D)"),
                ui.layout_columns(
                    ui.input_numeric("ft_F", "Charge (kN)", 100, min=0),
                    ui.input_numeric("ft_L", "Longueur L (mm)", 300, min=1),
                    ui.input_numeric("ft_D", "Diamètre D (mm)", 160, min=1),
                ),
                ui.output_ui("res_fendage"),
                ui.hr(),
                ui.h4("Flexion 3 points (σ = 3·F·l / 2·b·h²)"),
                ui.layout_columns(
                    ui.input_numeric("fl_F", "Charge (kN)", 10, min=0),
                    ui.input_numeric("fl_l", "Portée l (mm)", 300, min=1),
                    ui.input_numeric("fl_b", "Largeur b (mm)", 100, min=1),
                    ui.input_numeric("fl_h", "Hauteur h (mm)", 100, min=1),
                ),
                ui.output_ui("res_flexion"),
                ui.hr(),
                ui.h4("Règles BAEL à partir de f_cj"),
                ui.input_numeric("bael_fcj", "f_cj (MPa)", 25, min=1),
                ui.output_ui("res_bael"),
            ),
        ),
    ),
)


# ============================================================================
# SERVEUR
# ============================================================================
def server(input, output, session):

    # ---- Classe de béton -> fck et E remplis automatiquement (modifiables) ----
    @reactive.effect
    @reactive.event(input.type_beton)
    def _():
        fck = c.CLASSES_BETON[input.type_beton()]
        ui.update_numeric("resistance_mpa", value=fck)
        ui.update_numeric("module_elasticite", value=round(c.module_ecm_eurocode_gpa(fck), 1))
        ui.update_numeric("fc_F", value=fck * 20)
        ui.update_numeric("bael_fcj", value=fck)

    # ---- Calcul principal (erreurs affichées, jamais masquées) ----
    @reactive.calc
    def calcul():
        try:
            return c.calculer_structure(
                input.module_elasticite(), input.effort(), input.longueur(),
                input.section(), input.resistance_mpa(), input.poisson(),
                input.gamma_c(), input.poids_propre(),
            ), None
        except ValueError as e:
            return None, str(e)

    @render.ui
    def resultats_ui():
        r, erreur = calcul()
        titre = input.nom_projet().strip() or "Sans nom"
        if erreur:
            return ui.tags.div(ui.tags.h3(f"Projet : {titre}"),
                               ui.tags.div(f"⚠ {erreur}", class_="erreur"))

        messages = {
            "ok": f"✔ Structure vérifiée : taux de travail {fmt(r.taux*100, 1)} % (≤ 80 %)",
            "limite": f"⚠ Vérifiée mais marge faible : taux de travail {fmt(r.taux*100, 1)} %",
            "non": f"✘ Structure NON vérifiée : taux de travail {fmt(r.taux*100, 1)} % (> 100 %)",
        }
        coef = "∞" if r.coef_securite == float("inf") else fmt(r.coef_securite, 2)
        return ui.tags.div(
            ui.tags.h3(f"Projet : {titre}", style="color:#004080;"),
            ui.tags.div(messages[r.verdict], class_=f"verdict {r.verdict}"),

            ui.tags.h5("Contrainte appliquée", style="color:#0066cc;"),
            carte("Contrainte normale σ", f"{fmt(r.sigma)} MPa", "σ = F / S"),

            ui.tags.h5("Déformation et allongement", style="color:#0066cc;"),
            carte("Déformation longitudinale ε",
                  f"{fmt_sci(r.epsilon)}  ({fmt(r.epsilon_pct, 5)} %)",
                  "ε = σ / E = F / (E·S)   (sans unité)"),
            carte("Allongement ΔL", f"{fmt(r.delta_L_mm)} mm",
                  "ΔL = ε · L = F·L / (E·S)"),
            carte("Déformation transversale ε_t", fmt_sci(r.epsilon_t), "ε_t = −ν · ε"),
            carte("Module de cisaillement G", f"{fmt(r.G_gpa, 2)} GPa", "G = E / [2(1+ν)]"),

            ui.tags.h5("Résistance de la structure", style="color:#0066cc;"),
            carte("Résistance de calcul f_cd", f"{fmt(r.fcd, 2)} MPa", "f_cd = f_ck / γc"),
            carte("Taux de travail", f"{fmt(r.taux*100, 1)} %", "σ / f_cd   (doit rester ≤ 100 %)"),
            carte("Coefficient de sécurité", coef, "f_cd / σ"),
            carte("Effort maximal admissible", f"{fmt(r.effort_max_kn, 1)} kN",
                  "N_Rd = f_cd · S"),
            carte("Poids propre de la pièce", f"{fmt(r.poids_propre_kn, 2)} kN",
                  "25 kN/m³ · S · L"),

            ui.tags.p("Outil pédagogique : il ne remplace pas le calcul d'un ingénieur "
                      "(armatures, flambement, flexion, combinaisons d'actions).",
                      class_="note"),
        )

    @render.download_button(filename="resultats_beton.csv")
    def telecharger():
        r, erreur = calcul()
        if erreur:
            yield f"Erreur;{erreur}\n"
            return
        lignes = [
            ("Projet", input.nom_projet().strip() or "Sans nom", ""),
            ("Contrainte sigma", f"{r.sigma:.6f}", "MPa"),
            ("Deformation epsilon", f"{r.epsilon:.6e}", ""),
            ("Allongement dL", f"{r.delta_L_mm:.6f}", "mm"),
            ("Resistance de calcul fcd", f"{r.fcd:.4f}", "MPa"),
            ("Taux de travail", f"{r.taux:.4f}", ""),
            ("Effort max admissible", f"{r.effort_max_kn:.2f}", "kN"),
            ("Verdict", r.verdict, ""),
        ]
        yield "Grandeur;Valeur;Unite\n"
        for l in lignes:
            yield ";".join(l) + "\n"

    # ---- Matériaux ----
    materiaux = reactive.Value([])

    @reactive.effect
    @reactive.event(input.ajouter_materiel)
    def _():
        nom = (input.nom_materiel() or "").strip()
        q, p = input.quantite_materiel(), input.poids_unitaire()
        if not nom:
            ui.notification_show("Donnez un nom au matériel.", type="error")
            return
        if q is None or p is None or q <= 0 or p < 0:
            ui.notification_show("Quantité > 0 et poids ≥ 0 requis.", type="error")
            return
        ligne = {"Nom": nom, "Quantité": q, "Poids unitaire (kg)": p,
                 "Poids total (kg)": q * p}
        materiaux.set(materiaux() + [ligne])  # nouvelle liste -> le tableau se met à jour
        ui.update_text("nom_materiel", value="")

    @reactive.effect
    @reactive.event(input.supprimer_dernier)
    def _():
        materiaux.set(materiaux()[:-1])

    @reactive.effect
    @reactive.event(input.vider)
    def _():
        materiaux.set([])

    @render.table
    def table_materiaux():
        colonnes = ["Nom", "Quantité", "Poids unitaire (kg)", "Poids total (kg)"]
        return pd.DataFrame(materiaux(), columns=colonnes)

    @render.ui
    def total_materiaux():
        total = sum(m["Poids total (kg)"] for m in materiaux())
        return ui.tags.p(f"Poids total des matériels : {fmt(total, 2)} kg "
                         f"({fmt(total * 9.81 / 1000, 3)} kN)", style="font-weight:700;")

    # ---- Essais de résistance ----
    def bloc(fonction):
        try:
            return fonction()
        except (ValueError, TypeError, ZeroDivisionError):
            return ui.tags.div("⚠ Vérifiez les valeurs saisies (positives, non vides).",
                               class_="erreur")

    @render.ui
    def res_compression():
        def f():
            if input.fc_S() <= 0 or input.fc_F() < 0:
                raise ValueError
            v = c.resistance_compression(input.fc_F() * 1000, input.fc_S() * 100)
            return carte("Résistance en compression f_c", f"{fmt(v, 2)} MPa", "f_c = F_max / S")
        return bloc(f)

    @render.ui
    def res_fendage():
        def f():
            v = c.resistance_fendage(input.ft_F() * 1000, input.ft_L(), input.ft_D())
            return carte("Résistance en traction par fendage f_t", f"{fmt(v, 3)} MPa",
                         "f_t = 2F / (π·L·D)")
        return bloc(f)

    @render.ui
    def res_flexion():
        def f():
            v = c.resistance_flexion_3pts(input.fl_F() * 1000, input.fl_l(),
                                          input.fl_b(), input.fl_h())
            return carte("Contrainte de rupture en flexion", f"{fmt(v, 3)} MPa",
                         "σ = 3·F·l / (2·b·h²)")
        return bloc(f)

    @render.ui
    def res_bael():
        def f():
            fcj = input.bael_fcj()
            if fcj is None or fcj <= 0:
                raise ValueError
            return ui.tags.div(
                carte("Résistance en traction f_tj", f"{fmt(c.resistance_traction_bael(fcj), 3)} MPa",
                      "f_tj = 0,6 + 0,06·f_cj"),
                carte("Module instantané E_ij", f"{fmt(c.module_eij_bael(fcj), 0)} MPa",
                      "E_ij = 11 000 · f_cj^(1/3)"),
            )
        return bloc(f)


app = App(app_ui, server)

if __name__ == "__main__":
    app.run(port=8000)
