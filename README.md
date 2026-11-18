# Toponux

Toponux est un outil Linux local qui cartographie la configuration réseau en **lecture seule**.

## Principes

- Aucune modification de configuration réseau.
- Aucune commande de scan, aucun paquet de test et aucune connexion vers des hôtes distants.
- Collecte locale via des commandes de consultation (`ip -j`, `nft list ruleset`, `iptables-save`).
- Les informations non accessibles sont signalées ; Toponux ne tente pas de contourner les permissions.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Lancement

```bash
toponux
```

Ouvrir http://127.0.0.1:8765 si le navigateur ne s'ouvre pas automatiquement.

Pour lire les règles du firewall, lancer éventuellement Toponux avec les permissions nécessaires :

```bash
sudo .venv/bin/toponux
```

Même avec des privilèges élevés, Toponux reste strictement en lecture seule.

## Vues

- **Vue globale** : machine locale, interfaces IP principales, bridges virtuels actifs et passerelles par défaut.
- **Interfaces** : inventaire complet, y compris loopback, veth et interfaces DOWN.
- **Routage** : toutes les routes IPv4/IPv6 et les règles de routage par politique.
- **Firewall** : état de collecte et règles disponibles.
- **Données brutes** : snapshot JSON complet.

La vue globale masque volontairement les routes locales, broadcast et multicast ainsi que les interfaces veth. Les détails restent disponibles dans les vues dédiées.

## Tests

```bash
pip install -e '.[dev]'
pytest
```


## Outils de diagnostic (V0.3)

L'onglet **Diagnostic** propose un ping borné, un traceroute/tracepath et un test de connexion TCP. Ces opérations émettent volontairement du trafic réseau, mais ne modifient aucune configuration locale. La route choisie par le noyau est consultée avec `ip route get`.

Le test TCP indique le résultat réellement observé ; il ne prétend pas identifier à lui seul la règle firewall responsable. Un timeout peut avoir plusieurs causes. Le traceroute utilise `tracepath` si disponible, sinon `traceroute`.
