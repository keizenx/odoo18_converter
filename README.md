# Odoo 18 - Convertisseur de Syntaxe

Ce script Python permet de convertir automatiquement les fichiers Odoo (principalement XML) de l'ancienne syntaxe vers la nouvelle syntaxe d'Odoo 18.

## Fonctionnalités

Le script effectue les conversions suivantes:

1. **Conversion des tags XML** : Remplace `<tree>` par `<list>`
2. **Simplification des attributs conditionnels** : Convertit les attributs `attrs` et `states` vers la nouvelle syntaxe simplifiée
3. **Mise à jour du widget daterange** : Passe à la nouvelle configuration du widget daterange
4. **Simplification du chatter** : Remplace la structure complexe du chatter par la balise simplifiée `<chatter/>`
5. **Conversion des res.config.settings** : Adapte la structure des pages de paramètres à la nouvelle syntaxe
6. **Conversion des fichiers Python** : Supprime les attributs `states` des définitions de champs dans les modèles Python
7. **Traitement avancé des conditions** : Conversion des conditions complexes avec plusieurs opérateurs OR/AND

## Prérequis

- Python 3.6 ou supérieur
- Module lxml (`pip install lxml`)
- Module colorama (`pip install colorama`)

## Installation

```bash
pip install lxml colorama
```

## Utilisation

### Mode interactif

Lancez simplement le script sans arguments pour utiliser le mode interactif qui vous guidera pas à pas :

```bash
python odoo18_converter.py
```

Ce mode vous demandera successivement :
1. Le chemin du module Odoo à convertir
2. Les différentes options de conversion
3. Une confirmation avant de lancer la conversion

### Mode ligne de commande

```bash
python odoo18_converter.py chemin/vers/module [options]
```

### Options

- `source_dir` : Chemin vers le répertoire contenant les fichiers à convertir (obligatoire)
- `-o`, `--output-dir` : Répertoire de sortie pour les fichiers convertis (si non spécifié, modifie les fichiers en place)
- `--no-backup` : Ne pas créer de sauvegarde des fichiers originaux (par défaut: sauvegarde activée)
- `-v`, `--verbose` : Afficher des informations détaillées sur le processus
- `-e`, `--extensions` : Extensions de fichiers à traiter (par défaut: .xml)
- `-s`, `--skip` : Patterns regex pour ignorer certains fichiers
- `-r`, `--report` : Chemin du fichier pour sauvegarder le rapport de conversion (JSON)
- `-w`, `--workers` : Nombre de processus worker pour le traitement parallèle (par défaut: 1)
- `-d`, `--dry-run` : Mode test - ne pas modifier les fichiers, simplement afficher ce qui serait fait
- `-i`, `--interactive` : Mode interactif - demande confirmation avant chaque modification
- `-l`, `--show-limitations` : Afficher uniquement les limitations connues du script et quitter

### Options pour surmonter les limitations

- `--convert-python` : Convertir également les fichiers Python (.py) pour supprimer les attributs states
- `--advanced-conditions` : Activer le traitement avancé des conditions complexes dans les attributs attrs
- `--overcome-all` : Activer toutes les fonctionnalités pour surmonter les limitations

### Exemples

```bash
# Mode interactif (recommandé pour les nouveaux utilisateurs)
python odoo18_converter.py

# Convertir tous les fichiers XML d'un module
python odoo18_converter.py ./mon_module/

# Convertir avec plus d'informations
python odoo18_converter.py ./mon_module/ -v

# Convertir sans créer de sauvegardes
python odoo18_converter.py ./mon_module/ --no-backup

# Convertir des fichiers avec différentes extensions
python odoo18_converter.py ./mon_module/ -e .xml .qweb

# Convertir en mode test (aucune modification réelle)
python odoo18_converter.py ./mon_module/ -d

# Sauvegarder les fichiers convertis dans un autre répertoire
python odoo18_converter.py ./mon_module/ -o ./mon_module_odoo18/

# Ignorer certains fichiers
python odoo18_converter.py ./mon_module/ -s "test_" "demo_"

# Traitement parallèle avec 4 workers
python odoo18_converter.py ./mon_module/ -w 4

# Générer un rapport détaillé
python odoo18_converter.py ./mon_module/ -r rapport_conversion.json

# Convertir avec analyse des fichiers Python (suppression des states)
python odoo18_converter.py ./mon_module/ --convert-python

# Activer le traitement avancé des conditions complexes
python odoo18_converter.py ./mon_module/ --advanced-conditions

# Activer toutes les fonctionnalités avancées
python odoo18_converter.py ./mon_module/ --overcome-all
```

## Fonctionnement

Le script parcourt récursivement le répertoire spécifié et ses sous-répertoires, recherche tous les fichiers avec les extensions indiquées, et applique les transformations nécessaires pour rendre le code compatible avec Odoo 18.

Pour chaque fichier modifié, une sauvegarde est créée avec l'extension `.bak` (sauf si l'option `--no-backup` est utilisée ou si un répertoire de sortie est spécifié avec `--output-dir`).

## Fonctionnalités avancées

### Conversion des fichiers Python

L'option `--convert-python` permet au script d'analyser et de modifier les fichiers Python pour supprimer les attributs `states` des définitions de champs, comme ceci :

```python
# Avant
date = fields.Date(
    string='Date',
    required=True,
    states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
    copy=False,
)

# Après
date = fields.Date(
    string='Date',
    required=True,
    copy=False,
)
```

### Traitement des conditions complexes

L'option `--advanced-conditions` active des algorithmes avancés pour traiter des conditions plus complexes dans les attributs XML, notamment celles utilisant plusieurs opérateurs logiques (`|` et `&`) imbriqués.

```xml
<!-- Avant (très complexe) -->
<field name="project_id" attrs="{'invisible': ['|', '|', '&', ('state', '=', 'done'), ('type', '=', 'service'), ('type', '=', 'consu'), ('type', '=', 'product')]}"/>

<!-- Après -->
<field name="project_id" invisible="(state == 'done' and type == 'service') or type == 'consu' or type == 'product'"/>
```

## Mode interactif

Le script propose désormais un mode interactif qui guide l'utilisateur pas à pas dans le processus de conversion :

1. **Sélection du répertoire** : Le script demande d'abord le chemin du module Odoo à convertir
2. **Configuration des options** : Il propose ensuite de configurer les différentes options de conversion
3. **Confirmation** : Avant de lancer la conversion, un résumé des options est affiché pour confirmation

Ce mode est particulièrement utile pour les utilisateurs qui découvrent l'outil ou qui préfèrent une approche guidée plutôt que de spécifier toutes les options en ligne de commande.

## Changements supportés

### 1. De `<tree>` à `<list>`

```xml
<!-- Avant -->
<tree>
    <field name="name"/>
</tree>

<!-- Après -->
<list>
    <field name="name"/>
</list>
```

### 2. Attributs conditionnels simplifiés

```xml
<!-- Avant -->
<field name="shift_id" attrs="{'invisible': [('shift_schedule', '=', [])]}"/>

<!-- Après -->
<field name="shift_id" invisible="not shift_schedule"/>
```

### 3. Widget daterange

```xml
<!-- Avant -->
<field name="start_date" widget="daterange" options="{'related_end_date': 'end_date'}"/>
<field name="end_date" widget="daterange" options="{'related_start_date': 'start_date'}"/>

<!-- Après -->
<field name="start_date" widget="daterange" options="{'end_date_field': 'end_date'}"/>
```

### 4. Chatter simplifié

```xml
<!-- Avant -->
<div class="oe_chatter">
    <field name="message_follower_ids" widget="mail_followers"/>
    <field name="activity_ids" widget="mail_activity"/>
    <field name="message_ids" widget="mail_thread"/>
</div>

<!-- Après -->
<chatter/>
```

### 5. Structure res.config simplifiée

```xml
<!-- Avant -->
<div class="app_settings_block" data-string="Application Settings" string="Application Settings" data-key="key_example">
    <h2>Example Settings</h2>
    <div class="row mt16 o_settings_container">
        <label for="example_setting" string="Example Setting" class="ml-4 mt-4"/>
    </div>
    <div class="row mt16 o_settings_container" name="example_setting_container">
        <field class="ml-4" name="example_setting"/>
    </div>
    <div class="row mt16 o_settings_container">
        <div class="text-muted ml-4">
            Description for the example setting.
        </div>
    </div>
</div>

<!-- Après -->
<app string="Application Settings">
    <block title="Example Settings">
        <setting string="Example Setting" help="Description for the example setting">
            <field name="example_setting"/>
        </setting>
    </block>
</app>
```

## Nouvelles fonctionnalités

1. **Interface colorée** : Utilisation de couleurs dans le terminal pour une meilleure lisibilité
2. **Rapport détaillé** : Statistiques complètes sur les conversions effectuées
3. **Mode parallèle** : Traitement multi-processus pour une conversion plus rapide
4. **Mode test** : Possibilité de simuler les conversions sans modifier les fichiers
5. **Mode préservation** : Sauvegarde des fichiers convertis dans un répertoire séparé
6. **Filtrage avancé** : Ignorer certains fichiers selon des patterns regex
7. **Génération de rapport** : Export des statistiques au format JSON
8. **Conversion Python** : Analyse et modification des fichiers Python pour supprimer les attributs `states`
9. **Traitement de conditions complexes** : Support pour les conditions avec plusieurs opérateurs logiques
10. **Mode interactif** : Interface guidée pour configurer facilement la conversion

## Limitations résiduelles

Bien que le script offre maintenant des options pour surmonter la plupart des limitations initiales, certains cas très spécifiques peuvent encore nécessiter une intervention manuelle :

1. Certaines structures XML très personnalisées ou complexes
2. Cas spéciaux d'attributs conditionnels avec des expressions très complexes
3. Définitions de champs Python utilisant des approches non standard

Il est toujours recommandé de vérifier les fichiers convertis, surtout dans les cas complexes. 