# DESIGN.md --- Référentiel UI/UX de Difence

> **Statut :** référentiel de conception frontend\
> **Produit :** Difence by Shinary\
> **Type d'application :** plateforme SaaS B2B de supervision, de
> contrôle et de cybersécurité\
> **Langue de l'interface :** français par défaut\
> **Priorités :** lisibilité, cohérence, efficacité opérationnelle,
> sobriété et qualité d'exécution

Ce document définit les règles visuelles et comportementales de
l'interface de Difence. Il constitue la référence à respecter pour toute
création ou modification frontend.

Toute évolution doit renforcer la cohérence du produit. En cas de doute,
privilégier la solution la plus simple, lisible, accessible et cohérente
avec les composants existants.

------------------------------------------------------------------------

## 1. Vision produit et direction artistique

Difence est un outil métier utilisé pour surveiller des sites, suivre
des contrôles, traiter des alertes et gérer des incidents. L'interface
doit inspirer confiance et permettre de comprendre rapidement une
situation opérationnelle.

### 1.1 Positionnement visuel

Adopter une esthétique :

-   Professionnelle, moderne et sobre.
-   Technique, précise et rassurante.
-   Élégante, sans être luxueuse ou décorative.
-   Dense juste ce qu'il faut pour un outil de supervision.
-   Cohérente avec les standards des meilleurs produits SaaS B2B.

Références d'inspiration :

-   **Linear** : sobriété, typographie, espacements et qualité des
    interactions.
-   **Vercel** : interfaces techniques, tableaux et composants.
-   **Sentry** : alertes, incidents et informations de supervision.
-   **Grafana** : visualisation et lecture de données opérationnelles.

Ces références sont des sources d'inspiration, pas des modèles à
recopier. Difence doit conserver sa propre identité.

### 1.2 Principes fondamentaux

1.  La fonction prime sur la décoration.
2.  Les informations importantes doivent être visibles immédiatement.
3.  Les composants similaires doivent avoir le même comportement et le
    même rendu.
4.  Les couleurs ont une signification fonctionnelle.
5.  Les animations doivent aider à comprendre une interaction, jamais
    ralentir l'utilisateur.
6.  La densité d'information doit rester adaptée à un outil
    professionnel.
7.  Chaque page doit sembler appartenir au même produit.

------------------------------------------------------------------------

## 2. Identité visuelle et couleurs

La marque conserve une dominante bleue, mais le bleu ne doit pas envahir
toute l'interface. Il est utilisé pour la navigation, les actions
principales et les éléments interactifs.

### 2.1 Palette de référence

Les valeurs ci-dessous constituent la palette de départ. Les centraliser
dans les design tokens du projet afin d'éviter les couleurs codées en
dur dans les composants.

  Token                    Valeur      Usage
  ------------------------ ----------- ----------------------------------
  `color-brand-900`        `#1E3A8A`   Bleu profond, éléments de marque
  `color-brand-800`        `#1E40AF`   Sidebar et identité principale
  `color-primary`          `#2563EB`   Actions principales et liens
  `color-primary-hover`    `#1D4ED8`   Survol des actions principales
  `color-primary-active`   `#1E40AF`   État actif
  `color-primary-subtle`   `#EFF6FF`   Fonds bleus légers
  `color-primary-border`   `#BFDBFE`   Bordures de focus ou sélection
  `color-background`       `#F8FAFC`   Fond général de l'application
  `color-surface`          `#FFFFFF`   Cartes, panneaux et fenêtres
  `color-surface-muted`    `#F1F5F9`   Surfaces secondaires
  `color-text-primary`     `#172033`   Texte principal
  `color-text-secondary`   `#64748B`   Texte secondaire
  `color-text-muted`       `#94A3B8`   Métadonnées et aides
  `color-border`           `#E2E8F0`   Bordures standard
  `color-border-strong`    `#CBD5E1`   Séparateurs plus visibles
  `color-success`          `#16A36A`   État opérationnel
  `color-success-bg`       `#DCFCE7`   Fond de succès
  `color-warning`          `#D97706`   Avertissement
  `color-warning-bg`       `#FEF3C7`   Fond d'avertissement
  `color-danger`           `#DC4C4C`   Erreur et criticité
  `color-danger-bg`        `#FEE2E2`   Fond d'erreur
  `color-info`             `#2563EB`   Information
  `color-info-bg`          `#DBEAFE`   Fond informatif
  `color-success-strong`   `#0B7A4B`   Texte vert sur fond teinté
  `color-warning-strong`   `#92400E`   Texte ambre sur fond teinté
  `color-danger-strong`    `#B91C1C`   Texte rouge sur fond teinté
  `color-info-strong`      `#1D4ED8`   Texte bleu sur fond teinté

Les variantes `*-strong` servent uniquement au texte posé sur un fond
teinté de la même famille. Elles garantissent un contraste suffisant pour
les badges et les libellés de statut de petite taille.

### 2.2 Règles d'utilisation

-   Utiliser `color-background` pour le fond principal, et
    `color-surface` pour les zones de contenu.
-   Réserver le bleu saturé aux actions, à la navigation active et aux
    éléments qui nécessitent l'attention.
-   Ne pas utiliser le bleu comme couleur de texte pour tous les
    contenus.
-   Utiliser les couleurs de statut uniquement lorsqu'elles portent une
    signification métier.
-   Vérifier le contraste entre texte et arrière-plan.
-   Ne pas multiplier les couleurs d'accentuation dans une même zone.
-   Ne pas ajouter de dégradés décoratifs sans justification
    fonctionnelle.

### 2.3 Couleurs des statuts

Les statuts doivent être identifiables par la couleur, le texte et,
lorsque pertinent, une icône ou un point indicateur. Ne jamais
communiquer une information uniquement par la couleur.

  -----------------------------------------------------------------------
  Statut                  Couleur                 Présentation
  ----------------------- ----------------------- -----------------------
  Opérationnel            Vert                    Fond vert pâle, texte
                                                  vert foncé

  Sous surveillance       Bleu                    Fond bleu pâle, texte
                                                  bleu foncé

  Avertissement / Élevée  Ambre                   Fond ambre pâle, texte
                                                  ambre foncé

  Indisponible            Ambre ou rouge selon la Fond teinté, libellé
                          règle métier            explicite

  Anomalie détectée       Rouge                   Fond rouge pâle, texte
                                                  rouge foncé

  Critique                Rouge                   Mise en évidence forte
                                                  mais sobre

  Information             Bleu                    Fond bleu pâle, texte
                                                  bleu foncé

  Inactif / Inconnu       Gris                    Fond gris pâle, texte
                                                  gris foncé
  -----------------------------------------------------------------------

Ne pas assimiler automatiquement « indisponible », « anomalie » et «
critique » : conserver les distinctions métier définies par
l'application.

------------------------------------------------------------------------

## 3. Typographie

Utiliser **Inter** en priorité, ou la police sans-serif déjà intégrée au
projet si elle offre un rendu équivalent. Éviter de multiplier les
familles typographiques.

### 3.1 Échelle typographique

  Usage                         Taille    Graisse   Ligne indicative
  -------------------- --------------- ---------- ------------------
  Titre de page              26--28 px        700                1.2
  Titre de section           18--20 px        600                1.3
  Titre de carte             15--16 px        600                1.4
  Texte courant                  14 px        400                1.5
  Navigation                 13--14 px        500                1.4
  Bouton                     13--14 px   500--600                1.2
  Label                      12--13 px        500                1.4
  Métadonnée             12 px minimum        400                1.4
  En-tête de tableau         11--12 px        600                1.3

Les tailles peuvent être adaptées à la densité d'une page, mais les
textes essentiels ne doivent pas devenir difficiles à lire. Éviter les
textes de 10 px ou moins.

### 3.2 Hiérarchie

-   Un seul titre principal `h1` par page.
-   Structurer les sections avec des titres de niveau inférieur
    cohérents.
-   Distinguer les titres, descriptions, valeurs et métadonnées par la
    taille, la graisse et la couleur.
-   Ne pas utiliser le gras partout.
-   Ne pas utiliser une couleur vive pour compenser une hiérarchie
    typographique insuffisante.
-   Les valeurs KPI doivent être visuellement dominantes par rapport à
    leur libellé.

### 3.3 Données numériques

-   Utiliser des chiffres tabulaires lorsque possible pour les
    compteurs, durées, dates et métriques.
-   Conserver un format cohérent pour les dates, heures, pourcentages et
    durées.
-   Éviter les changements de largeur visuelle lors de l'actualisation
    des compteurs.

------------------------------------------------------------------------

## 4. Espacements et grille

Utiliser une échelle d'espacement cohérente basée sur des multiples de 4
px.

  Token          Valeur Usage indicatif
  ------------ -------- -----------------------------------
  `space-1`        4 px Écart minimal entre éléments liés
  `space-2`        8 px Écart entre icône et libellé
  `space-3`       12 px Espacement compact
  `space-4`       16 px Espacement standard
  `space-5`       20 px Espacement intermédiaire
  `space-6`       24 px Séparation de blocs
  `space-8`       32 px Séparation de sections
  `space-10`      40 px Grande séparation
  `space-12`      48 px Respiration importante

Règles :

-   Aligner les composants sur une grille commune.
-   Garder des espacements internes homogènes dans les cartes.
-   Éviter les éléments collés aux bords.
-   Éviter les espaces vides excessifs qui réduisent la quantité
    d'informations utiles visibles.
-   Ne pas corriger un problème de mise en page en ajoutant des marges
    arbitraires.
-   Préférer une grille responsive aux largeurs fixes.

------------------------------------------------------------------------

## 5. Formes, bordures et ombres

### 5.1 Rayons

  Élément                    Rayon recommandé
  ------------------------ ------------------
  Petit contrôle, badge                  6 px
  Bouton, champ, menu                    8 px
  Carte, panneau                        10 px
  Grande fenêtre / modal                12 px
  Avatar                                 50 %

Éviter de mélanger de nombreux rayons différents. Ne pas arrondir
systématiquement tous les éléments en forme de pilule.

### 5.2 Bordures

-   Utiliser principalement une bordure de 1 px en `color-border`.
-   Réserver les bordures plus contrastées aux séparations nécessaires,
    aux sélections et aux états de focus.
-   Éviter les contours gris épais.
-   Ne pas cumuler bordure forte, ombre et fond contrasté sur un même
    composant sans raison.

### 5.3 Ombres

Les ombres doivent être discrètes et exprimer une élévation réelle :
menu, popover, modal ou élément flottant.

-   Les cartes ordinaires peuvent se passer d'ombre.
-   Ne pas utiliser d'ombres sombres ou de reliefs donnant un aspect
    natif Windows.
-   Préférer une séparation par fond et bordure légère.
-   Les états hover ne doivent pas provoquer de saut de layout.

------------------------------------------------------------------------

## 6. Boutons et actions

Tous les boutons doivent être construits à partir d'un petit nombre de
variantes réutilisables. Ne pas créer un style spécifique pour chaque
page.

### 6.1 Variantes

  -----------------------------------------------------------------------
  Variante                Apparence               Usage
  ----------------------- ----------------------- -----------------------
  Primary                 Fond bleu, texte blanc  Action principale de la
                                                  page ou du formulaire

  Secondary               Fond blanc, bordure     Action secondaire
                          discrète                

  Tertiary / Ghost        Sans bordure permanente Actions peu fréquentes
                                                  ou intégrées

  Danger                  Fond ou texte rouge     Action destructive

  Icon button             Contrôle carré homogène Action représentée
                                                  clairement par une
                                                  icône
  -----------------------------------------------------------------------

### 6.2 Dimensions

-   Hauteur standard : 36 à 40 px.
-   Hauteur compacte : 32 px, uniquement pour les contextes denses.
-   Hauteur large : 44 px, pour les actions importantes ou certains
    formulaires.
-   Padding horizontal cohérent, généralement 12 à 16 px.
-   Icône : 16 à 18 px.
-   Espace icône/texte : 8 px.
-   Rayon : 8 px.

### 6.3 États interactifs

Chaque bouton doit définir :

-   Default.
-   Hover.
-   Active / Pressed.
-   Focus visible.
-   Disabled.
-   Loading, si l'action est asynchrone.

Transitions recommandées : 150 à 200 ms, avec une courbe d'accélération
naturelle.

Règles :

-   Supprimer les styles natifs du navigateur.
-   Ne jamais laisser apparaître de bordure ou d'ombre native
    inattendue.
-   Ne pas utiliser une ombre épaisse pour donner du relief.
-   Préserver un feedback visuel clair.
-   Désactiver réellement un bouton indisponible, et expliquer la raison
    lorsque nécessaire.
-   Ne pas utiliser un bouton uniquement décoratif : toute action
    affichée doit fonctionner.

------------------------------------------------------------------------

## 7. Champs, filtres et formulaires

Les champs doivent être homogènes dans toutes les pages.

-   Hauteur standard : environ 40 px.
-   Rayon : 8 px.
-   Bordure : 1 px discrète.
-   Fond blanc ou surface adaptée au contexte.
-   Label visible et associé au champ.
-   Placeholder utilisé comme exemple, jamais comme seul label.
-   Icône intégrée uniquement si elle améliore la compréhension.
-   États focus, erreur, désactivé et lecture seule clairement définis.
-   Messages d'erreur courts, précis et placés près du champ concerné.

Les filtres, recherches et sélecteurs doivent conserver une hauteur et
un alignement cohérents. Les filtres actifs doivent être identifiables
sans surcharger l'interface.

------------------------------------------------------------------------

## 8. Cartes, panneaux et KPI

### 8.1 Cartes

Les cartes servent à regrouper des informations liées, pas à encadrer
chaque élément de l'interface.

-   Fond blanc.
-   Bordure légère.
-   Rayon de 10 px.
-   Padding homogène, généralement 16 à 20 px.
-   Titre, contenu et actions clairement hiérarchisés.
-   Ombre uniquement si nécessaire.
-   Pas de bordure épaisse ou de décoration superflue.

Ne pas multiplier les cartes imbriquées. Préférer une séparation par
espacement ou par fond secondaire lorsque cela suffit.

### 8.2 KPI

Les cartes KPI doivent afficher :

1.  Un libellé court.
2.  Une valeur principale lisible.
3.  Une variation ou un contexte secondaire, si disponible.
4.  Un indicateur visuel discret lorsque pertinent.

Les valeurs doivent être alignées et comparables entre elles. Les icônes
sont secondaires par rapport aux chiffres. Ne pas ajouter une icône à
chaque carte si elle n'apporte aucune information.

------------------------------------------------------------------------

## 9. Tableaux et listes de données

Les tableaux sont des composants centraux d'un outil de supervision. Ils
doivent permettre de parcourir rapidement de nombreuses lignes.

### 9.1 Structure

-   En-têtes clairement distingués du contenu.
-   Libellés d'en-tête lisibles et suffisamment contrastés.
-   Lignes d'une hauteur adaptée à la densité des données, généralement
    48 à 56 px.
-   Séparateurs horizontaux fins.
-   Alignement cohérent des valeurs d'une même colonne.
-   Largeurs de colonnes adaptées à leur contenu.
-   Actions regroupées dans une colonne dédiée ou un menu contextuel.
-   Pas de bordures verticales systématiques.

### 9.2 Interactions

-   Survol de ligne discret.
-   Ligne sélectionnée visuellement identifiable.
-   Tri indiqué clairement.
-   Pagination cohérente.
-   Menus d'action accessibles au clavier.
-   Les actions essentielles ne doivent pas être cachées inutilement.
-   Les tableaux doivent gérer proprement les états vide, chargement et
    erreur.

### 9.3 Lisibilité

-   Éviter les textes trop petits.
-   Éviter les colonnes excessivement serrées.
-   Les informations secondaires peuvent être affichées sur une deuxième
    ligne, avec une taille lisible.
-   Les données importantes (nom, statut, date du dernier contrôle)
    doivent être faciles à repérer.

------------------------------------------------------------------------

## 10. Badges, alertes et niveaux de gravité

Les badges doivent être compacts, lisibles et cohérents.

-   Fond légèrement teinté.
-   Texte de couleur correspondante, suffisamment contrasté.
-   Padding horizontal régulier.
-   Taille de texte généralement 12 px.
-   Hauteur adaptée au contenu, sans devenir trop imposante.
-   Utiliser une pastille ou une icône uniquement si elle facilite la
    lecture.

Les niveaux de gravité doivent respecter les règles métier. Une alerte
critique doit être immédiatement identifiable, mais ne doit pas
transformer toute la page en zone rouge.

Les alertes et notifications doivent distinguer clairement :

-   Le niveau de gravité.
-   Le titre.
-   La ressource concernée.
-   L'ancienneté ou l'heure.
-   L'action attendue, si applicable.

Ne pas utiliser uniquement une couleur pour distinguer les niveaux.

------------------------------------------------------------------------

## 11. Sidebar et navigation

La navigation latérale est un élément structurant de Difence.

### 11.1 Identité et structure

-   Conserver l'identité bleue de Difence.
-   Éviter un bleu trop lumineux ou trop saturé sur toute la surface.
-   Préserver une bonne lisibilité des libellés.
-   Organiser les rubriques avec des titres de groupe discrets.
-   Conserver une séparation claire entre surveillance et
    administration.
-   Garder les informations de compte et de contexte utilisateur dans
    une zone dédiée.

### 11.2 Liens de navigation

-   Icônes cohérentes en taille et en style.
-   Hauteur de ligne homogène.
-   Espacement vertical régulier.
-   État actif clairement identifiable, avec un contraste suffisant.
-   État inactif plus discret.
-   Hover subtil.
-   Badges de compteur réservés aux informations réellement utiles.
-   Ne pas utiliser des fonds gris épais ou des bordures natives sur les
    éléments de navigation.

### 11.3 Navigation clavier

Tous les éléments de navigation doivent être accessibles au clavier et
présenter un focus visible.

------------------------------------------------------------------------

## 12. Icônes et illustrations

-   Utiliser une seule famille d'icônes, de préférence Lucide si elle
    est déjà disponible dans le projet.
-   Privilégier les icônes outline.
-   Utiliser des tailles cohérentes : 16 px pour les contrôles compacts,
    18 px pour la navigation, 20 à 24 px pour les éléments importants.
-   Ne pas mélanger des icônes outline, pleines, 3D et emoji.
-   Ne pas utiliser d'emoji comme icônes fonctionnelles.
-   Chaque icône doit avoir un sens compréhensible.
-   Les boutons contenant uniquement une icône doivent disposer d'un nom
    accessible ou d'un tooltip.

------------------------------------------------------------------------

## 13. Graphiques et cartographie

Les visualisations doivent privilégier la lecture et l'analyse.

### 13.1 Graphiques

-   Palette cohérente avec les couleurs fonctionnelles.
-   Axes, légendes et unités lisibles.
-   Éviter les effets 3D.
-   Éviter les dégradés décoratifs.
-   Ne pas multiplier les couleurs sans signification.
-   Afficher les valeurs et périodes utiles.
-   Prévoir des états sans données et des états de chargement.

### 13.2 Graphes de topologie et de règles

Les graphes de nœuds (topologie réseau, flux de règles de pare-feu)
suivent les mêmes tokens que le reste de l'interface.

-   Les nœuds de classification utilisent une palette restreinte : bleu de
    marque pour la machine locale et les passerelles, bleu d'information
    pour les bridges, ambre pour les VLAN, surfaces neutres pour les
    interfaces et les voisins.
-   Le texte est blanc sur les remplissages saturés, et utilise la
    variante `*-strong` sur les fonds teintés.
-   Les verdicts de pare-feu reprennent les couleurs de statut : succès
    pour `accept`, danger pour `drop` et `reject`, information pour
    `jump`, avertissement pour `nat`, neutre pour `return`, `log` et les
    autres verdicts.
-   La forme des nœuds complète la couleur ; une information n'est jamais
    portée par la couleur seule.
-   Le fond du graphe est une surface secondaire unie, sans motif ni
    dégradé décoratif.

### 13.3 Cartographie

-   La carte doit rester lisible et ne pas dominer inutilement le
    dashboard.
-   Les marqueurs doivent être suffisamment distincts.
-   Les couleurs des marqueurs doivent correspondre aux statuts métier.
-   Les infobulles doivent présenter les informations essentielles.
-   Les contrôles cartographiques doivent être discrets et accessibles.
-   Ne pas sacrifier la lisibilité des alertes ou des données pour des
    effets graphiques.

------------------------------------------------------------------------

## 14. Animations et fluidité

Les animations doivent rendre l'interface plus naturelle et clarifier
les changements d'état.

### 14.1 Durées

  Interaction                      Durée indicative
  ------------------------------ ------------------
  Hover bouton ou lien                  120--180 ms
  Changement de couleur / état          150--200 ms
  Ouverture d'un menu                   150--200 ms
  Ouverture d'une popover               150--200 ms
  Ouverture d'une modal                 180--240 ms
  Transition de panneau                 180--250 ms

### 14.2 Animations autorisées

-   Transitions de couleur, bordure et opacité.
-   Légère translation lors de l'apparition d'un panneau.
-   Ouverture et fermeture de menus.
-   Feedback de chargement.
-   Apparition discrète d'une notification.
-   Animation d'un indicateur de progression.
-   Transitions d'état des contrôles.

### 14.3 À éviter

-   Animations longues ou répétitives.
-   Parallaxe décorative.
-   Effets de rebond excessifs.
-   Déplacements qui provoquent des changements de layout.
-   Animations systématiques à chaque chargement de page.
-   Animations qui ralentissent une tâche opérationnelle.

Respecter `prefers-reduced-motion`. Les animations doivent rester
performantes et ne pas compromettre la lisibilité.

------------------------------------------------------------------------

## 15. Notifications, menus, popovers et modales

Tous ces composants doivent partager les mêmes règles de forme, de
bordure, de typographie et d'élévation.

### Notifications

-   Position et comportement cohérents.
-   Message court et compréhensible.
-   Niveau de gravité explicite.
-   Durée d'affichage adaptée à l'importance.
-   Possibilité de fermer les notifications non bloquantes.
-   Ne pas masquer des contrôles essentiels.

### Menus et popovers

-   Ouverture rapide et fluide.
-   Alignement prévisible avec le déclencheur.
-   Espacement interne régulier.
-   Fermeture au clic extérieur et avec Escape lorsque pertinent.
-   Navigation clavier fonctionnelle.

### Modales

-   Taille adaptée à la tâche.
-   Titre et description explicites.
-   Actions principales et secondaires clairement distinguées.
-   Focus géré correctement.
-   Fermeture cohérente.
-   Ne pas utiliser une modal pour une information qui peut être
    affichée directement dans la page.

------------------------------------------------------------------------

## 16. Responsive design

L'application doit rester utilisable sur desktop, tablette et mobile.

### Desktop

-   Exploiter la largeur disponible sans étirer excessivement les
    contenus.
-   Conserver une navigation latérale stable.
-   Utiliser des grilles adaptatives pour les KPI et panneaux.

### Tablette

-   Adapter les grilles.
-   Réduire les espacements lorsque nécessaire.
-   Préserver la lisibilité des tableaux.
-   Permettre le repli de la sidebar.

### Mobile

-   Prévoir une navigation adaptée, par exemple une sidebar repliable ou
    un menu dédié.
-   Empiler les cartes et les KPI.
-   Transformer les tableaux trop larges en vue adaptée ou permettre un
    défilement horizontal maîtrisé.
-   Conserver les actions essentielles accessibles.
-   Éviter les textes tronqués sans possibilité de consulter leur
    contenu.
-   Respecter des zones tactiles suffisamment grandes.

Le responsive ne doit pas être une simple réduction proportionnelle de
la version desktop.

------------------------------------------------------------------------

## 17. Accessibilité

Respecter les bonnes pratiques WCAG 2.2 niveau AA dans la mesure du
possible.

-   Contraste suffisant entre texte et fond.
-   Navigation complète au clavier.
-   Focus visible.
-   Labels associés aux champs.
-   Noms accessibles pour les boutons à icône.
-   Hiérarchie de titres logique.
-   Messages d'erreur compréhensibles.
-   Ne jamais transmettre une information uniquement par la couleur.
-   Respect de `prefers-reduced-motion`.
-   Zones interactives suffisamment grandes.
-   Utiliser les éléments HTML sémantiques appropriés.

------------------------------------------------------------------------

## 18. États de l'interface

Chaque composant affichant des données asynchrones doit prévoir les
états nécessaires :

-   Chargement.
-   Données disponibles.
-   Aucun résultat.
-   Erreur.
-   Accès non autorisé, si applicable.
-   Données obsolètes ou actualisation en cours, si applicable.

Les états vides doivent expliquer la situation et proposer une action
pertinente lorsque cela a du sens.

Ne pas afficher de faux indicateurs de chargement ou de données fictives
pour masquer une absence de données.

------------------------------------------------------------------------

## 19. Architecture et implémentation frontend

Le design system doit être implémenté de façon centralisée et
réutilisable.

### 19.1 Principes

-   Examiner l'architecture frontend existante avant toute modification.
-   Réutiliser les composants existants lorsqu'ils sont adaptés.
-   Créer ou consolider une bibliothèque de composants partagés.
-   Centraliser les tokens de design.
-   Éviter les valeurs visuelles codées en dur dans chaque page.
-   Éviter les styles inline dispersés.
-   Éviter les variantes de composants qui ne sont pas réellement
    nécessaires.
-   Ne pas ajouter de dépendance sans justification.
-   Ne pas dupliquer un composant simplement pour obtenir une légère
    différence visuelle.

### 19.2 Composants communs à privilégier

Selon l'architecture existante, maintenir des composants réutilisables
pour :

-   Button.
-   IconButton.
-   Input.
-   Select.
-   SearchInput.
-   Checkbox et Radio.
-   Badge / StatusBadge.
-   Card / Panel.
-   Table.
-   Pagination.
-   Tooltip.
-   Dropdown / Popover.
-   Modal / Dialog.
-   Alert / Notification.
-   EmptyState.
-   LoadingState.
-   PageHeader.
-   SidebarNavigation.

Ne pas imposer une nouvelle architecture si le projet dispose déjà d'une
organisation pertinente. Faire évoluer l'existant progressivement.

------------------------------------------------------------------------

## 20. Règles de cohérence entre les pages

Le design system s'applique à toutes les pages, pas uniquement au
dashboard.

Pages concernées, selon les fonctionnalités présentes :

-   Vue d'ensemble.
-   Sites surveillés.
-   Contrôles.
-   Alertes.
-   Incidents.
-   Organisations.
-   Utilisateurs.
-   Configuration.
-   Journal d'audit.

Un même type d'action, de champ, de badge, de tableau ou de panneau doit
conserver le même rendu partout.

Chaque page peut avoir une composition adaptée à son usage, mais ne doit
pas introduire une nouvelle identité visuelle.

------------------------------------------------------------------------

## 21. Interdictions et anti-patterns

Ne pas introduire les éléments suivants :

-   Boutons avec apparence native du navigateur ou de Windows.
-   Bordures grises épaisses.
-   Ombres fortes et reliefs artificiels.
-   Dégradés décoratifs omniprésents.
-   Glassmorphism systématique.
-   Accumulation de cartes imbriquées.
-   Une carte pour chaque petit élément.
-   Couleurs saturées sans signification fonctionnelle.
-   Textes trop petits.
-   Trop de graisses typographiques.
-   Mélange de familles d'icônes.
-   Emojis utilisés comme icônes d'interface.
-   Animations longues ou gratuites.
-   Composants visuellement différents pour une même fonction.
-   Faux boutons ou contrôles sans comportement.
-   Données fictives introduites dans l'interface de production.
-   Modifications de règles métier sous prétexte d'amélioration
    visuelle.

Éviter particulièrement le rendu générique « dashboard généré par IA » :
grille de cartes répétitives, mêmes icônes dans des carrés colorés,
bordures partout et dégradés décoratifs.

------------------------------------------------------------------------

## 22. Processus obligatoire pour les évolutions UI

Avant toute modification importante :

1.  Lire ce fichier `DESIGN.md`.
2.  Examiner les composants et styles existants.
3.  Identifier les composants partagés concernés.
4.  Vérifier si une règle ou un token existe déjà.
5.  Proposer une évolution cohérente avec le design system.

Pendant le développement :

1.  Modifier en priorité les composants communs.
2.  Éviter les corrections isolées qui créent des incohérences.
3.  Conserver les comportements métier.
4.  Vérifier les états interactifs.
5.  Vérifier la navigation clavier et les contrastes.

Après le développement :

1.  Contrôler visuellement les pages impactées.
2.  Vérifier les résolutions desktop, tablette et mobile.
3.  Tester les états hover, focus, active, disabled et loading.
4.  Vérifier l'absence de régression fonctionnelle.
5.  Corriger les écarts au présent référentiel.
6.  Mettre à jour ce document si une règle de design évolue réellement.

Ne pas considérer une modification comme terminée tant que le rendu
visuel n'a pas été vérifié.

------------------------------------------------------------------------

## 23. Checklist de validation

Avant de livrer une évolution frontend, vérifier les points suivants :

### Identité et cohérence

-   [ ] La page respecte la palette et les tokens.
-   [ ] La typographie respecte l'échelle définie.
-   [ ] Les composants réutilisés ont le même rendu que sur les autres
    pages.
-   [ ] Les espacements et alignements sont cohérents.
-   [ ] Aucun style natif inattendu n'est visible.

### Composants

-   [ ] Les boutons ont les bonnes variantes et les bons états.
-   [ ] Les champs et filtres sont cohérents.
-   [ ] Les cartes ne sont pas inutilement imbriquées.
-   [ ] Les tableaux restent lisibles.
-   [ ] Les badges respectent les couleurs de statut.
-   [ ] Les menus, popovers et modales fonctionnent correctement.

### Expérience utilisateur

-   [ ] Les actions principales sont faciles à identifier.
-   [ ] Les informations importantes sont visibles rapidement.
-   [ ] Les interactions sont fluides.
-   [ ] Les animations sont discrètes et utiles.
-   [ ] Les états de chargement, vide et erreur sont traités.

### Qualité

-   [ ] Le rendu desktop est vérifié.
-   [ ] Le rendu tablette et mobile est vérifié.
-   [ ] Le clavier et le focus sont fonctionnels.
-   [ ] Les contrastes sont suffisants.
-   [ ] Aucune fonctionnalité existante n'a été supprimée.
-   [ ] Aucune donnée fictive n'a été introduite.

------------------------------------------------------------------------

## 24. Règle finale

**La qualité de Difence doit venir de la précision de son interface, pas
de la quantité d'effets visuels.**

Chaque choix graphique doit améliorer la compréhension, la lisibilité ou
l'efficacité de l'utilisateur.

En cas d'hésitation entre une solution spectaculaire et une solution
sobre, choisir la solution sobre si elle répond mieux au besoin
opérationnel.

Ce document est la référence commune à toutes les évolutions de
l'interface de Difence.
