# AGENTS.md --- Projet d'inspection de la configuration réseau Linux

## 1. Objectif du projet

Cette application Python collecte et présente des informations sur la
configuration réseau d'un système Linux.

Elle doit fonctionner en **lecture seule** : elle peut observer l'état
réseau et lire les informations système nécessaires, mais elle ne doit
jamais modifier la configuration du système.

Exemples d'informations pouvant être exposées, selon leur disponibilité
: - interfaces réseau : nom, état, type, adresses MAC et MTU ; -
adresses IPv4 et IPv6 ; - routes et passerelles ; - serveurs DNS et
domaines de recherche ; - état des connexions et informations fournies
par NetworkManager ou systemd-networkd ; - informations générales sur
les outils et services réseau présents.

L'application doit fonctionner avec le minimum de privilèges. Elle ne
doit pas exiger `root` pour les opérations ordinaires. Mais si necessaire 
il faut l'indiquer à l'utilsateur.

## 2. Règle absolue : lecture seule

**Aucune fonctionnalité ne doit modifier l'état du système ou sa
configuration réseau.**

Il est strictement interdit de : - créer, supprimer, activer, désactiver
ou modifier une interface réseau ; - ajouter, supprimer ou modifier une
adresse IP, une route, une règle de routage ou une passerelle ; -
modifier les paramètres DNS, DHCP, Wi-Fi, VPN, pare-feu ou proxy ; -
démarrer, arrêter, redémarrer ou recharger un service réseau ; -
modifier des fichiers de configuration, même temporairement ; - écrire
dans `/etc`, `/run`, `/sys`, `/proc` ou dans les répertoires de
configuration des gestionnaires réseau ; - appeler une API ou une
commande ayant un effet de bord sur le système ; - installer,
désinstaller ou mettre à jour un paquet ou un service.

Les commandes système doivent être exclusivement des commandes
d'inspection, par exemple : - `ip -j address show` -
`ip -j route show` - `ip -j -6 route show` - `ip -j link show` -
`nmcli --terse --escape yes device status` -
`nmcli --terse --escape yes connection show --active` -
`resolvectl status` - `networkctl status`

N'utiliser une commande que si elle est disponible et si son invocation
est connue pour être non modificatrice. Préférer les interfaces et
fichiers système en lecture seule lorsque cela améliore la fiabilité.

Ne jamais utiliser de commande de configuration telle que `ip link set`,
`ip address add/del`, `ip route add/del`,
`nmcli connection modify/up/down`, `systemctl start/stop/restart`,
`ifconfig` en mode modification, `iw ... set`, `rfkill block/unblock` ou
équivalent.

Cette interdiction s'applique aussi aux scripts de test, exemples,
outils de diagnostic et scripts de développement. Aucun test ne doit
toucher au réseau réel de la machine.

## 3. Principes d'architecture

-   Séparer clairement la collecte des données, leur normalisation, leur
    validation et leur présentation.
-   Isoler les accès au système derrière des composants dédiés afin de
    pouvoir les remplacer par des doubles de test.
-   Préférer des fonctions et classes petites, avec une responsabilité
    unique.
-   Définir des modèles de données explicites et typés pour représenter
    les interfaces, adresses, routes et DNS.
-   Distinguer une information absente, une commande indisponible, une
    permission insuffisante et une erreur de parsing.
-   Une erreur sur une source ne doit pas nécessairement empêcher la
    collecte des autres sources.
-   Ne jamais supposer qu'une distribution Linux, un gestionnaire réseau
    ou un outil particulier est présent.
-   Détecter les capacités disponibles plutôt que de déduire le
    comportement à partir du nom de la distribution.
-   Garder les dépendances externes au minimum et justifier chaque
    nouvelle dépendance.

Architecture indicative :

``` text
src/
  <package>/
    __init__.py
    models.py          # Modèles de données
    collectors/        # Collecteurs en lecture seule
    system/            # Exécution contrôlée des commandes et lecture système
    services/          # Orchestration et normalisation
    cli.py             # Interface en ligne de commande, si nécessaire
tests/
  unit/
  integration/
```

Adapter cette structure à l'existant plutôt que de déplacer ou réécrire
inutilement le projet.

## 4. Conventions Python

Respecter les conventions Python standard (PEP 8 et idiomes Python).

-   Utiliser des noms explicites en `snake_case` pour les fonctions,
    méthodes et variables.
-   Utiliser `PascalCase` pour les classes.
-   Utiliser `UPPER_SNAKE_CASE` pour les constantes.
-   Ajouter des annotations de types aux fonctions publiques, méthodes
    et attributs importants.
-   Utiliser `dataclasses` ou des modèles simples typés lorsque cela
    clarifie les données.
-   Préférer la composition à l'héritage lorsqu'aucune relation « est-un
    » ne le justifie.
-   Éviter les classes qui ne font que regrouper des fonctions sans état
    ni responsabilité cohérente.
-   Garder les fonctions courtes et limiter les effets de bord.
-   Utiliser `pathlib.Path` pour manipuler les chemins.
-   Utiliser `with` pour gérer les ressources.
-   Utiliser `Enum` pour les ensembles fermés de valeurs lorsque cela
    améliore la lisibilité.
-   Ne pas utiliser de `except Exception` général sans raison précise et
    traitement explicite.
-   Ne pas masquer les erreurs avec `pass`, des valeurs par défaut
    trompeuses ou des retours silencieux.
-   Documenter les API publiques et les comportements non évidents avec
    des docstrings claires.
-   Éviter les variables globales mutables.
-   Ne pas introduire de dépendance ou de fonctionnalité asynchrone sans
    besoin démontré.

## 5. Sécurité

La sécurité doit être prise en compte dès la conception.

### Exécution de commandes

-   Utiliser `subprocess.run()` avec une liste d'arguments, jamais avec
    `shell=True`.
-   Ne jamais construire une commande à partir d'une chaîne fournie par
    l'utilisateur.
-   Utiliser des chemins absolus lorsque cela est pertinent et maîtrisé.
-   Définir systématiquement un délai d'expiration (`timeout`).
-   Capturer `stdout` et `stderr` et contrôler le code de retour.
-   Limiter la taille des sorties si nécessaire pour éviter une
    consommation excessive de mémoire.
-   Ne lancer que des exécutables connus et explicitement autorisés par
    le code.
-   Ne pas utiliser `sudo`, ne pas demander de mot de passe et ne pas
    tenter d'élever les privilèges.
-   Ne jamais exécuter de commande obtenue depuis une configuration, une
    sortie système ou une entrée utilisateur.

### Lecture des informations système

-   Considérer les données provenant du système comme non fiables :
    elles peuvent être absentes, malformées ou inattendues.
-   Valider les données avant de les convertir ou de les exposer.
-   Gérer les fichiers ou pseudo-fichiers absents, inaccessibles ou
    modifiés pendant la lecture.
-   N'ouvrir que les chemins nécessaires et connus.
-   Ne pas suivre aveuglément des liens symboliques vers des
    emplacements non prévus.
-   Ne jamais écrire dans les fichiers consultés.
-   Ne pas collecter ni afficher de secrets : clés privées, mots de
    passe Wi-Fi, secrets VPN, jetons, identifiants ou contenus de
    fichiers de credentials.
-   Masquer les données sensibles si une sortie système les contient
    malgré tout.

### Robustesse et exposition

-   Limiter la durée des commandes, la taille des sorties et le nombre
    de tentatives.
-   Ne pas exposer de détails internes, chemins sensibles ou traces
    complètes dans les messages destinés aux utilisateurs.
-   Utiliser les journaux pour le diagnostic sans y inscrire de secrets
    ni de données sensibles.
-   Ne pas ouvrir de port, créer de socket d'écoute ou exposer de
    service réseau.
-   Ne pas transmettre les informations collectées à un service externe.
-   Ne pas ajouter de télémétrie ou de collecte distante sans demande
    explicite.

## 6. Collecte et normalisation réseau

-   Privilégier les formats structurés (notamment JSON) plutôt que le
    parsing de sorties destinées à un humain.
-   Pour `iproute2`, utiliser les options JSON lorsqu'elles sont
    disponibles.
-   Vérifier et documenter les différences entre distributions et
    versions d'outils.
-   Ne pas supposer que les noms d'interfaces, adresses ou routes ont un
    format fixe.
-   Gérer IPv4 et IPv6.
-   Utiliser le module standard `ipaddress` pour valider et manipuler
    les adresses et réseaux IP.
-   Distinguer les interfaces physiques, virtuelles, loopback, bridges,
    tunnels et autres types lorsque l'information est disponible.
-   Ne pas confondre l'état administratif d'une interface et son état
    opérationnel.
-   Préserver la provenance d'une information lorsque plusieurs sources
    peuvent se contredire.
-   Éviter de présenter une information inconnue comme une valeur
    certaine.

Les informations collectées doivent être descriptives. Elles ne doivent
jamais déclencher automatiquement une correction ou une action de
remédiation.

## 7. Ruff et qualité du code

**Ruff doit passer sans erreur ni avertissement bloquant.**

Avant de considérer une modification terminée, exécuter les contrôles
configurés dans le projet. À défaut de configuration existante, utiliser
au minimum :

``` bash
ruff check .
ruff format --check .
```

Pour corriger automatiquement les problèmes de lint et de formatage :

``` bash
ruff check --fix .
ruff format .
```

Ne pas contourner Ruff en ajoutant des exclusions globales, en
désactivant des règles ou en multipliant les commentaires `noqa`. Toute
exception doit être locale, justifiée et aussi limitée que possible.

Respecter la configuration Ruff existante (`pyproject.toml`, `ruff.toml`
ou `.ruff.toml`). Ne pas modifier cette configuration uniquement pour
faire disparaître un problème sans comprendre sa cause.

## 8. Tests

Toute fonctionnalité doit être accompagnée de tests pertinents.

-   Utiliser `pytest` si le projet l'utilise déjà ; sinon respecter le
    framework de test existant.
-   Tester les cas nominaux, les erreurs, les données absentes et les
    données malformées.
-   Tester les environnements où une commande ou un service n'est pas
    installé.
-   Tester les permissions insuffisantes et les dépassements de délai.
-   Tester les sorties IPv4 et IPv6.
-   Utiliser `monkeypatch`, `unittest.mock` ou des fixtures pour simuler
    les commandes et fichiers système.
-   Ne jamais dépendre de la configuration réseau réelle de la machine
    pour les tests unitaires.
-   Ne jamais exécuter de commande réseau modificatrice dans les tests.
-   Vérifier explicitement que les commandes invoquées appartiennent à
    la liste autorisée.
-   Vérifier que `subprocess` est appelé sans `shell=True` et avec un
    délai d'expiration.
-   Ajouter des tests de non-régression pour chaque bug corrigé.

Avant livraison, exécuter au minimum :

``` bash
ruff check .
ruff format --check .
pytest
```

Adapter la dernière commande au framework réellement utilisé si le
projet n'emploie pas `pytest`.

## 9. Dépendances et compatibilité

-   Privilégier la bibliothèque standard Python.
-   Épingler ou borner les dépendances selon les pratiques déjà adoptées
    par le projet.
-   Ne pas ajouter de dépendance non maintenue ou inutile.
-   Respecter la version minimale de Python définie par le projet.
-   Ne pas supposer la présence de `nmcli`, `resolvectl`, `networkctl`
    ou d'un autre outil.
-   Prévoir un résultat explicite lorsque certaines informations ne
    peuvent pas être obtenues.
-   Ne pas rendre l'application dépendante d'un seul gestionnaire
    réseau.

## 10. Règles pour les agents de développement

Avant toute modification :

1.  Examiner la structure du dépôt et les conventions existantes.
2.  Lire la configuration Python, Ruff et les tests.
3.  Identifier les sources système qui seront consultées.
4.  Vérifier que chaque commande et chaque accès système sont
    strictement en lecture seule.
5.  Proposer une modification limitée au besoin demandé.

Pendant le développement :

-   Ne pas réécrire des composants sans nécessité.
-   Ne pas ajouter de fonctionnalité de configuration, de réparation ou
    d'administration réseau.
-   Ne pas augmenter les privilèges requis.
-   Ne pas introduire de dépendance inutile.
-   Ne pas supprimer de tests pour faire passer la suite.
-   Ne pas affaiblir les contrôles de sécurité ou la configuration Ruff.

Avant de terminer :

1.  Exécuter les tests pertinents.
2.  Exécuter `ruff check .`.
3.  Exécuter `ruff format --check .`.
4.  Vérifier le diff pour repérer toute écriture système, commande
    modificatrice, collecte de secret ou régression.
5.  Signaler clairement les contrôles non exécutés et les limites
    rencontrées.

En cas de doute sur le caractère strictement non modificatif d'une
opération, **ne pas l'implémenter**. Préférer une information
indisponible à une action qui pourrait modifier le système.

## 11. Critère d'acceptation principal

Une modification est acceptable uniquement si elle : - apporte une
collecte ou une présentation d'informations réseau ; - reste strictement
en lecture seule ; - fonctionne sans privilèges élevés lorsque c'est
possible ; - traite les erreurs et les données système comme non fiables
; - est couverte par des tests sans effet sur le réseau réel ; -
respecte les conventions Python du projet ; - passe les contrôles Ruff
configurés.

## 12. Gestion de Git et des commits

**L'utilisateur est le seul autorisé à effectuer des commits Git.**

Les agents IA doivent respecter strictement les règles suivantes :

- Ne jamais exécuter `git commit`, quelle que soit la situation.
- Ne jamais créer de commit automatiquement, même après validation des tests.
- Ne jamais effectuer de `git push`.
- Ne jamais modifier l'historique Git (`rebase`, `reset`, `amend`, `cherry-pick`, etc.) sans demande explicite de l'utilisateur.
- Ne jamais créer ou supprimer de branche sans demande explicite.
- Ne jamais utiliser `git stash` pour masquer des modifications sans autorisation.
- Ne jamais écraser ou supprimer des modifications existantes de l'utilisateur.
- Ne jamais effectuer d'opération susceptible de faire perdre du travail non sauvegardé.

Les agents peuvent utiliser les commandes Git en lecture seule pour examiner l'état du dépôt, notamment :

- `git status`
- `git diff`
- `git log`
- `git branch`
- `git show`

### Règle de livraison

À la fin d'une tâche, l'agent doit :
1. Présenter un résumé des modifications effectuées.
2. Indiquer les fichiers créés ou modifiés.
3. Présenter les résultats des tests et de Ruff.
4. Laisser toutes les modifications dans le répertoire de travail, sans commit.

**Le commit final est toujours une action manuelle réalisée exclusivement par l'utilisateur.**

## 13. Documentation et maintenance du README

**Le fichier README.md doit être maintenu à jour à chaque modification du projet.**

Les agents IA doivent respecter les règles suivantes :

### Mise à jour systématique

- Toute nouvelle fonctionnalité doit être documentée dans le README.md.
- Toute modification du comportement existant doit entraîner la mise à jour de la documentation correspondante.
- Toute fonctionnalité supprimée doit être retirée du README.md.
- Les commandes d'installation, de configuration et d'utilisation doivent rester conformes au fonctionnement réel de l'application.
- Les exemples de commandes et de sorties doivent être vérifiés et cohérents avec l'implémentation.

### Section Data Sources

La section du site **Data Sources** doit être mise à jour.

Cette section doit documenter de manière exhaustive toutes les sources de données utilisées par l'application.

Pour chaque source de données, préciser :

- **Nom de la source** : fichier système, pseudo-fichier, commande Linux, API ou service interrogé.
- **Localisation** : chemin complet du fichier ou nom de la commande utilisée.
- **Données collectées** : description précise de chaque information récupérée.
- **Méthode de collecte** : lecture de fichier, exécution de commande, interrogation d'une API locale, etc.
- **Permissions nécessaires** : préciser si les données sont accessibles à un utilisateur standard ou nécessitent des permissions particulières.
- **Compatibilité** : distributions Linux ou services concernés, lorsque pertinent.
- **Limites** : informations éventuellement indisponibles selon l'environnement.

### Exhaustivité et traçabilité

- Toute nouvelle donnée collectée doit impérativement être ajoutée à la section Data Sources.
- Toute modification ou suppression d'une collecte doit entraîner la mise à jour de cette section.
- Aucune source de données ne doit être utilisée sans être documentée.
- La documentation doit refléter exactement les sources réellement utilisées par le code.
- Ne jamais documenter une source ou une donnée qui n'est pas effectivement collectée.

### Règle de livraison

Avant de terminer une tâche, vérifier systématiquement :
1. Que le README.md a été mis à jour si nécessaire.
2. Que toutes les nouvelles données collectées sont documentées dans Data Sources.
3. Que les informations documentées correspondent à l'implémentation réelle.
4. Que les exemples et commandes du README sont toujours valides.

**Une fonctionnalité n'est considérée comme terminée que lorsque son implémentation et sa documentation sont cohérentes.**
