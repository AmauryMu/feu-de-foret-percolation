"""
Propagation d'un feu de forêt par automate cellulaire.

Grille N x N de cellules (vide, arbre, en feu, brûlé). Un arbre en feu
brûle pendant `duree_feu` pas de temps ; un arbre voisin (haut, bas,
gauche, droite) d'un arbre en feu s'enflamme avec la probabilité
`coef_propagation`. Deux scénarios :

  - classique : un seul départ de feu dans une forêt dense ;
  - coupe-feu : une ligne de la forêt est brûlée à l'avance (feu contrôlé),
    ce qui empêche l'incendie de la franchir.

On étudie aussi l'effet de la densité d'arbres : avec une propagation
certaine (p = 1), le feu brûle exactement l'amas d'arbres connectés au
départ de feu, c'est un problème de percolation de sites.

Projet L3 Physique, CY Cergy Paris Université (octobre 2024).

Utilisation :
    python feu_de_foret.py                     # scénario classique
    python feu_de_foret.py --coupe-feu         # scénario avec coupe-feu
    python feu_de_foret.py --seuil             # propagation certaine au seuil de percolation
    python feu_de_foret.py --densite           # effet de la densité (environ 2 min)
    python feu_de_foret.py --sauver            # enregistre les GIF et la figure dans figures/
"""

import os
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

# Paramètres du modèle
N = 100               # Taille de la grille
densite_forets = 0.9  # Densité des arbres dans la forêt
duree_feu = 3         # Nombre de pas pendant lesquels un arbre reste en feu
LIGNE_COUPE_FEU = 50  # Ligne brûlée à l'avance dans le scénario coupe-feu

# États possibles d'une cellule
VIDE, ARBRE, EN_FLAMME, BRULE = 0, 1, 2, 3


def initialiser_foret(N, densite, coupe_feu=False):
    """Forêt aléatoire, éventuellement un coupe-feu, puis un arbre en feu."""
    foret = np.random.choice([VIDE, ARBRE], size=(N, N), p=[1 - densite, densite])
    temps_feu = np.zeros((N, N), dtype=int)

    # Coupe-feu : toute une ligne est déjà brûlée avant le départ du feu
    if coupe_feu:
        foret[LIGNE_COUPE_FEU] = BRULE

    # On allume un arbre choisi au hasard
    arbres = np.argwhere(foret == ARBRE)
    x, y = arbres[np.random.choice(len(arbres))]
    foret[x, y] = EN_FLAMME
    temps_feu[x, y] = duree_feu

    return foret, temps_feu


def propager_feu(foret, temps_feu, coef_propagation):
    """Un pas de temps de l'automate cellulaire."""
    nouvelle_foret = foret.copy()
    for i in range(N):
        for j in range(N):
            if foret[i, j] == EN_FLAMME:
                # Un arbre en feu se consume puis devient brûlé
                temps_feu[i, j] -= 1
                if temps_feu[i, j] <= 0:
                    nouvelle_foret[i, j] = BRULE
            elif foret[i, j] == ARBRE:
                # Voisins en feu (haut, bas, gauche, droite)
                voisins_en_feu = [
                    foret[i + di, j + dj] == EN_FLAMME
                    for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    if 0 <= i + di < N and 0 <= j + dj < N
                ]
                if any(voisins_en_feu) and np.random.rand() < coef_propagation:
                    nouvelle_foret[i, j] = EN_FLAMME
                    temps_feu[i, j] = duree_feu
    return nouvelle_foret, temps_feu


def simulation(coef_propagation, coupe_feu=False, densite=densite_forets, titre="classique",
               fichier_gif=None, max_images=1000):
    """
    Anime l'incendie jusqu'à son extinction (au plus max_images pas), puis
    marque une pause sur l'état final. L'enregistre en GIF si fichier_gif est donné.
    """
    foret, temps_feu = initialiser_foret(N, densite, coupe_feu)

    fig, ax = plt.subplots()
    cmap = plt.get_cmap("hot_r", 4)  # "hot_r" : colormap inversée
    norm = plt.Normalize(VIDE, BRULE)
    mat = ax.matshow(foret, cmap=cmap, norm=norm)
    plt.colorbar(mat, label="État (0 : vide, 1 : arbre, 2 : en feu, 3 : brûlé)")

    def animer(frame):
        nonlocal foret, temps_feu
        foret, temps_feu = propager_feu(foret, temps_feu, coef_propagation)
        mat.set_data(foret)
        ax.set_title(f"Feu de forêt ({titre}, p = {coef_propagation})  |  pas {frame}")
        return [mat]

    def images():
        """Numéros d'image tant que le feu brûle, puis 30 images de pause."""
        k = 0
        while k < max_images and np.any(foret == EN_FLAMME):
            yield k
            k += 1
        for _ in range(30):
            yield k

    anim = FuncAnimation(fig, animer, frames=images, interval=50, blit=False,
                         save_count=max_images + 30, cache_frame_data=False)

    if fichier_gif:
        anim.save(fichier_gif, writer=PillowWriter(fps=20), dpi=70)
        plt.close(fig)
        brule = np.sum(foret == BRULE) / np.sum(foret != VIDE)
        print(f"{fichier_gif} : {brule * 100:.0f} % des arbres brûlés")
    else:
        plt.show()


def feu_complet(densite, coef_propagation, max_pas=2000):
    """Fait brûler une forêt jusqu'à extinction, sans affichage."""
    foret, temps_feu = initialiser_foret(N, densite)
    n_arbres = np.sum(foret != VIDE)
    for _ in range(max_pas):
        if not np.any(foret == EN_FLAMME):
            break
        foret, temps_feu = propager_feu(foret, temps_feu, coef_propagation)
    fraction_brulee = np.sum(foret == BRULE) / n_arbres
    return foret, fraction_brulee


# Seuil de percolation de sites sur réseau carré (4 voisins), valeur connue
SEUIL_PERCOLATION = 0.593

# Graine du GIF au seuil : départ de feu dans un grand amas (sinon le feu
# s'éteint souvent tout de suite à cette densité)
GRAINE_SEUIL = 3


def effet_densite(fichier=None):
    """
    Propagation certaine (p = 1) : le feu brûle tout l'amas d'arbres relié au
    départ. On montre l'état final pour trois densités, puis la fraction
    d'arbres brûlés en fonction de la densité (moyenne sur plusieurs forêts).
    """
    np.random.seed(3)  # graine fixe : figure reproductible
    cmap = plt.get_cmap("hot_r", 4)
    norm = plt.Normalize(VIDE, BRULE)

    fig, axs = plt.subplots(1, 4, figsize=(18, 4.6), gridspec_kw={"width_ratios": [1, 1, 1, 1.25]})
    for ax, d in zip(axs[:3], [0.50, 0.60, 0.70]):
        foret, fraction = feu_complet(d, 1.0)
        ax.matshow(foret, cmap=cmap, norm=norm)
        ax.set_title(f"Densité {d:.2f} : {fraction * 100:.0f} % des arbres brûlés", fontsize=11)
        ax.set_xticks([])
        ax.set_yticks([])

    densites = np.arange(0.40, 0.81, 0.04)
    n_forets = 6
    moyennes = []
    for d in densites:
        fractions = [feu_complet(d, 1.0)[1] for _ in range(n_forets)]
        moyennes.append(np.mean(fractions))
        print(f"densité {d:.2f} : {np.mean(fractions) * 100:5.1f} % des arbres brûlés")

    ax = axs[3]
    ax.plot(densites, moyennes, "o-", color="firebrick")
    ax.axvline(SEUIL_PERCOLATION, color="gray", ls="--", label=f"seuil de percolation ≈ {SEUIL_PERCOLATION}")
    ax.set_xlabel("Densité d'arbres")
    ax.set_ylabel("Fraction des arbres brûlés")
    ax.set_title(f"Moyenne sur {n_forets} forêts (p = 1)", fontsize=11)
    ax.grid(True, alpha=0.4)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()

    if fichier:
        fig.savefig(fichier, dpi=70)
        plt.close(fig)
        print(f"Figure enregistrée : {fichier}")
    else:
        plt.show()


if __name__ == "__main__":
    if "--sauver" in sys.argv:
        os.makedirs("figures", exist_ok=True)
        np.random.seed(0)  # graines fixes : GIF reproductibles
        simulation(0.3, fichier_gif="figures/feu_classique.gif")
        simulation(0.6, coupe_feu=True, titre="avec coupe-feu", fichier_gif="figures/feu_coupe_feu.gif")
        np.random.seed(GRAINE_SEUIL)
        simulation(1.0, densite=0.6, titre="densité 0.6", fichier_gif="figures/feu_seuil.gif")
        effet_densite("figures/effet_densite.png")
    elif "--densite" in sys.argv:
        effet_densite()
    elif "--coupe-feu" in sys.argv:
        simulation(0.6, coupe_feu=True, titre="avec coupe-feu")
    elif "--seuil" in sys.argv:
        simulation(1.0, densite=0.6, titre="densité 0.6")
    else:
        simulation(0.3)
