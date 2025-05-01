#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import argparse
import logging
import ast
from lxml import etree
import shutil
from pathlib import Path
from datetime import datetime
import colorama
from colorama import Fore, Style, Back
import concurrent.futures
import json

# Initialiser colorama pour les couleurs dans le terminal
colorama.init()

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('odoo18_converter')

class InteractiveMode:
    """Classe pour gérer le mode interactif de l'application"""
    def __init__(self):
        self.source_dir = None
        self.options = {
            'output_dir': None,
            'backup': True,
            'verbose': False,
            'extensions': ['.xml'],
            'skip_patterns': [],
            'report_file': None,
            'workers': 1,
            'dry_run': False,
            'interactive': False,
            'convert_python': False,
            'advanced_conditions': False
        }
    
    def print_header(self):
        """Affiche l'en-tête du mode interactif"""
        header = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║                                                                     ║
║  {Fore.YELLOW}Odoo 18 - Convertisseur de Syntaxe - Mode Interactif{Fore.CYAN}║
║  {Fore.WHITE}Version 1.2.0{Fore.CYAN}                                ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

Ce mode vous guide étape par étape dans le processus de conversion.
Vous pouvez quitter à tout moment en appuyant sur Ctrl+C.

"""
        print(header)
    
    def prompt_source_dir(self):
        """Demande à l'utilisateur le répertoire source"""
        while True:
            source_dir = input(f"{Fore.GREEN}1. Entrez le chemin du module Odoo à convertir :{Style.RESET_ALL} ")
            if not source_dir:
                print(f"{Fore.RED}Erreur: Le chemin ne peut pas être vide.{Style.RESET_ALL}")
                continue
                
            # Vérifier si le répertoire existe
            if os.path.isdir(source_dir):
                self.source_dir = source_dir
                return True
            else:
                create_dir = input(f"{Fore.YELLOW}Le répertoire n'existe pas. Voulez-vous le créer ? (o/n) :{Style.RESET_ALL} ")
                if create_dir.lower() in ['o', 'oui', 'y', 'yes']:
                    try:
                        os.makedirs(source_dir, exist_ok=True)
                        self.source_dir = source_dir
                        return True
                    except Exception as e:
                        print(f"{Fore.RED}Erreur lors de la création du répertoire: {str(e)}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Veuillez entrer un chemin valide.{Style.RESET_ALL}")
    
    def prompt_options(self):
        """Demande à l'utilisateur les options de conversion"""
        # Choisir le type de conversion
        print(f"\n{Fore.GREEN}2. Choisissez les options de conversion :{Style.RESET_ALL}")
        
        # Option pour la conversion Python
        convert_python = input(f"{Fore.CYAN}   Convertir les fichiers Python (.py) ? (o/n) [n]: {Style.RESET_ALL}")
        self.options['convert_python'] = convert_python.lower() in ['o', 'oui', 'y', 'yes']
        
        # Option pour le traitement avancé des conditions
        advanced_conditions = input(f"{Fore.CYAN}   Activer le traitement avancé des conditions ? (o/n) [n]: {Style.RESET_ALL}")
        self.options['advanced_conditions'] = advanced_conditions.lower() in ['o', 'oui', 'y', 'yes']
        
        # Option pour la sauvegarde
        backup = input(f"{Fore.CYAN}   Créer des sauvegardes des fichiers originaux ? (o/n) [o]: {Style.RESET_ALL}")
        self.options['backup'] = backup.lower() not in ['n', 'non', 'no']
        
        # Option pour le mode verbeux
        verbose = input(f"{Fore.CYAN}   Activer le mode verbeux ? (o/n) [n]: {Style.RESET_ALL}")
        self.options['verbose'] = verbose.lower() in ['o', 'oui', 'y', 'yes']
        
        # Option pour le répertoire de sortie
        output_dir = input(f"{Fore.CYAN}   Répertoire de sortie (vide pour modifier les fichiers en place): {Style.RESET_ALL}")
        if output_dir:
            self.options['output_dir'] = output_dir
            # Créer le répertoire de sortie s'il n'existe pas
            if not os.path.isdir(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except Exception as e:
                    print(f"{Fore.RED}Erreur lors de la création du répertoire de sortie: {str(e)}{Style.RESET_ALL}")
                    return False
        
        # Option pour le nombre de workers
        workers = input(f"{Fore.CYAN}   Nombre de processus parallèles (1-{os.cpu_count() or 4}) [1]: {Style.RESET_ALL}")
        if workers.isdigit() and 1 <= int(workers) <= (os.cpu_count() or 4):
            self.options['workers'] = int(workers)
        
        # Option pour le mode test
        dry_run = input(f"{Fore.CYAN}   Mode test (aucune modification réelle) ? (o/n) [n]: {Style.RESET_ALL}")
        self.options['dry_run'] = dry_run.lower() in ['o', 'oui', 'y', 'yes']
        
        # Option pour les extensions
        extensions = input(f"{Fore.CYAN}   Extensions à traiter (séparées par des espaces) [.xml]: {Style.RESET_ALL}")
        if extensions:
            self.options['extensions'] = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions.split()]
        
        # Option pour le rapport
        report = input(f"{Fore.CYAN}   Générer un rapport (chemin du fichier, vide pour aucun rapport): {Style.RESET_ALL}")
        if report:
            self.options['report_file'] = report
        
        return True
    
    def confirm_conversion(self):
        """Demande à l'utilisateur de confirmer la conversion"""
        print(f"\n{Fore.GREEN}3. Résumé des options :{Style.RESET_ALL}")
        print(f"   - Module source: {self.source_dir}")
        
        if self.options['output_dir']:
            print(f"   - Répertoire de sortie: {self.options['output_dir']}")
        else:
            print(f"   - Mode: Modification en place")
            
        if self.options['backup']:
            print(f"   - Sauvegarde: Oui (.bak)")
        else:
            print(f"   - Sauvegarde: Non")
            
        if self.options['convert_python']:
            print(f"   - Conversion Python: Oui")
        else:
            print(f"   - Conversion Python: Non")
            
        if self.options['advanced_conditions']:
            print(f"   - Traitement conditions avancées: Oui")
        else:
            print(f"   - Traitement conditions avancées: Non")
            
        if self.options['dry_run']:
            print(f"   - Mode test: Oui (aucune modification réelle)")
        else:
            print(f"   - Mode test: Non")
            
        print(f"   - Extensions: {', '.join(self.options['extensions'])}")
        print(f"   - Workers: {self.options['workers']}")
        
        if self.options['report_file']:
            print(f"   - Rapport: {self.options['report_file']}")
        else:
            print(f"   - Rapport: Non")
            
        confirm = input(f"\n{Fore.YELLOW}Confirmer la conversion ? (o/n) [o]: {Style.RESET_ALL}")
        return confirm.lower() not in ['n', 'non', 'no']
    
    def run(self):
        """Exécute le mode interactif"""
        try:
            self.print_header()
            
            if not self.prompt_source_dir():
                return None
                
            if not self.prompt_options():
                return None
                
            if not self.confirm_conversion():
                print(f"{Fore.YELLOW}Conversion annulée.{Style.RESET_ALL}")
                return None
                
            # Retourner les options pour exécution
            return {
                'source_dir': self.source_dir,
                **self.options
            }
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Opération annulée par l'utilisateur.{Style.RESET_ALL}")
            return None

class Odoo18Converter:
    def __init__(self, source_dir, output_dir=None, backup=True, verbose=False, 
                extensions=None, skip_patterns=None, report_file=None, 
                workers=1, dry_run=False, interactive=False, 
                convert_python=False, advanced_conditions=False):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.backup = backup
        self.verbose = verbose
        self.extensions = extensions or ['.xml']
        self.skip_patterns = skip_patterns or []
        self.report_file = report_file
        self.workers = max(1, min(workers, os.cpu_count() or 1))
        self.dry_run = dry_run
        self.interactive = interactive
        self.convert_python = convert_python
        self.advanced_conditions = advanced_conditions
        
        # Statistiques
        self.stats = {
            'files_processed': 0,
            'files_changed': 0,
            'files_skipped': 0,
            'files_error': 0,
            'changes': {
                'tree_to_list': 0,
                'attrs_conversion': 0,
                'states_conversion': 0,
                'daterange_update': 0,
                'chatter_simplified': 0,
                'settings_structure': 0,
                'python_states_removed': 0,
                'complex_conditions': 0
            },
            'start_time': datetime.now(),
            'end_time': None,
            'duration': None
        }
        
        # Configuration de la sortie
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        # Créer un handler pour le fichier log si spécifié
        if report_file:
            file_handler = logging.FileHandler(report_file, mode='w')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
            
    def log(self, message, level='info', file_path=None):
        """Log un message avec le niveau spécifié"""
        if self.verbose or level != 'debug':
            formatted_message = message
            if file_path:
                formatted_message = f"{file_path}: {message}"
                
            if level == 'debug':
                logger.debug(formatted_message)
            elif level == 'info':
                logger.info(formatted_message)
            elif level == 'warning':
                logger.warning(formatted_message)
                print(f"{Fore.YELLOW}{formatted_message}{Style.RESET_ALL}")
            elif level == 'error':
                logger.error(formatted_message)
                print(f"{Fore.RED}{formatted_message}{Style.RESET_ALL}")
            elif level == 'success':
                logger.info(formatted_message)
                print(f"{Fore.GREEN}{formatted_message}{Style.RESET_ALL}")

    def print_banner(self):
        """Affiche une bannière stylisée au démarrage"""
        banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║                                                          ║
║  {Fore.YELLOW}Odoo 18 - Convertisseur de Syntaxe{Fore.CYAN}                     ║
║  {Fore.WHITE}Version 1.2.0{Fore.CYAN}                                         ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)

    def should_skip_file(self, file_path):
        """Détermine si un fichier doit être ignoré"""
        # Vérifier si le fichier correspond à l'un des patterns à ignorer
        for pattern in self.skip_patterns:
            if re.search(pattern, file_path):
                return True
        return False

    def convert_all(self):
        """Parcourir tous les fichiers et appliquer les conversions"""
        self.print_banner()
        
        # Afficher les limitations du script (si pas surmontées)
        if not self.convert_python and not self.advanced_conditions and not self.dry_run:
            self.show_limitations()
        else:
            self.show_advanced_features()
        
        self.stats['start_time'] = datetime.now()
        
        # Déterminer les types de fichiers à traiter
        all_extensions = list(self.extensions)
        if self.convert_python:
            if '.py' not in all_extensions:
                all_extensions.append('.py')
        
        print(f"📋 {Fore.CYAN}Recherche de fichiers {', '.join(all_extensions)} dans {self.source_dir}...{Style.RESET_ALL}")
        
        # Collecter tous les fichiers à traiter
        files_to_process = []
        total_files_found = 0
        
        # Dossiers standards d'Odoo à vérifier en priorité (liste plus complète)
        odoo_standard_dirs = [
            'views', 'security', 'data', 'wizard', 'report', 
            'static/src/xml', 'static/src/js', 'static/description',
            'controllers', 'demo', 'i18n', 'templates', 'tests'
        ]
        
        # Fonction pour ajouter un fichier à la liste de traitement
        def process_file_path(file_path):
            nonlocal total_files_found
            total_files_found += 1
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Traiter selon le type de fichier
            if file_ext in all_extensions:
                if not self.should_skip_file(file_path):
                    files_to_process.append((file_path, file_ext))
                    return True
                else:
                    self.stats['files_skipped'] += 1
                    self.log(f"Fichier ignoré selon les patterns: {file_path}", level='debug')
            else:
                # Fichier avec une extension non traitée
                self.stats['files_skipped'] += 1
                self.log(f"Fichier ignoré (extension non traitée): {file_path}", level='debug')
            return False
        
        # On s'assure que le répertoire source existe
        if not os.path.exists(self.source_dir):
            self.log(f"Le répertoire source {self.source_dir} n'existe pas.", level='error')
            return
            
        # On fait une recherche exhaustive de tous les fichiers XML et Python dans le répertoire
        xml_files_found = 0
        py_files_found = 0
        
        # D'abord, vérifier chaque dossier standard Odoo
        for standard_dir in odoo_standard_dirs:
            standard_path = os.path.join(self.source_dir, standard_dir)
            if os.path.isdir(standard_path):
                self.log(f"Vérification du dossier standard Odoo: {standard_dir}", level='info')
                for root, _, files in os.walk(standard_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_ext = os.path.splitext(file)[1].lower()
                        if file_ext == '.xml':
                            xml_files_found += 1
                        elif file_ext == '.py':
                            py_files_found += 1
                        process_file_path(file_path)
        
        # Ensuite, parcourir tous les autres fichiers dans le répertoire source
        # pour trouver des fichiers XML ou Python qui pourraient être dans des emplacements non standards
        processed_paths = set()
        for root, dirs, files in os.walk(self.source_dir):
            # Vérifier si on est dans un dossier standard déjà traité
            is_standard_subdir = False
            for standard_dir in odoo_standard_dirs:
                standard_path = os.path.join(self.source_dir, standard_dir)
                if root.startswith(standard_path):
                    is_standard_subdir = True
                    break
            
            # Si c'est un sous-dossier standard déjà traité, on le saute
            if is_standard_subdir:
                continue
                
            # Traiter les fichiers de ce dossier
            for file in files:
                file_path = os.path.join(root, file)
                
                # Éviter de traiter deux fois le même fichier
                if file_path in processed_paths:
                    continue
                processed_paths.add(file_path)
                
                # Compter les fichiers par type
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext == '.xml':
                    xml_files_found += 1
                elif file_ext == '.py':
                    py_files_found += 1
                
                # Ajouter à la liste de traitement si c'est un type valide
                process_file_path(file_path)
        
        # Afficher des statistiques sur les fichiers trouvés
        self.log(f"Fichiers XML trouvés: {xml_files_found}", level='info')
        if self.convert_python:
            self.log(f"Fichiers Python trouvés: {py_files_found}", level='info')
        
        total_files = len(files_to_process)
        self.log(f"Total des fichiers trouvés: {total_files_found}", level='info')
        self.log(f"Fichiers à traiter: {total_files}", level='info')
        self.log(f"Fichiers ignorés: {self.stats['files_skipped']}", level='info')
        print(f"🔍 {Fore.CYAN}Trouvé {total_files} fichier(s) à traiter{Style.RESET_ALL}")
        
        # Afficher les fichiers qui seront traités en mode verbeux
        if self.verbose:
            print(f"\n{Fore.CYAN}Liste des fichiers à traiter:{Style.RESET_ALL}")
            for i, (file_path, _) in enumerate(files_to_process):
                rel_path = os.path.relpath(file_path, self.source_dir)
                print(f"  {Fore.WHITE}{i+1}. {rel_path}{Style.RESET_ALL}")
            print("")
        
        if self.dry_run:
            print(f"\n{Fore.YELLOW}Mode test activé - aucune modification ne sera appliquée{Style.RESET_ALL}")
            return
            
        # Traitement des fichiers
        if self.workers > 1 and total_files > 1:
            print(f"⚙️ {Fore.CYAN}Traitement en parallèle avec {self.workers} workers{Style.RESET_ALL}")
            with concurrent.futures.ProcessPoolExecutor(max_workers=self.workers) as executor:
                results = list(executor.map(self._process_file_wrapper, files_to_process))
            
            # Mettre à jour les statistiques
            for result in results:
                if result:
                    self.update_stats(result)
        else:
            print(f"⚙️ {Fore.CYAN}Traitement séquentiel des fichiers{Style.RESET_ALL}")
            for i, (file_path, file_ext) in enumerate(files_to_process):
                progress = f"[{i+1}/{total_files}]"
                print(f"{progress} Traitement de {file_path}...", end="\r")
                result = self._process_file(file_path, file_ext)
                self.update_stats(result)
                
        # Mettre à jour le nombre total de fichiers traités
        self.stats['files_processed'] = total_files
                
        # Afficher le rapport final
        self.stats['end_time'] = datetime.now()
        self.stats['duration'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        self.print_report()
        
        # Sauvegarder le rapport si demandé
        if self.report_file:
            self.save_report()
            
        # Rappeler les limitations à la fin (si pas surmontées)
        if not self.convert_python and not self.advanced_conditions:
            self.show_limitations()
    
    def _process_file_wrapper(self, args):
        """Wrapper pour permettre l'utilisation avec map() en parallèle"""
        file_path, file_ext = args
        return self._process_file(file_path, file_ext)
        
    def _process_file(self, file_path, file_ext):
        """Traite un fichier selon son extension"""
        if file_ext == '.py':
            return self.convert_python_file(file_path)
        else:
            return self.convert_file(file_path)

    def show_advanced_features(self):
        """Afficher les fonctionnalités avancées activées"""
        features = []
        if self.convert_python:
            features.append("✅ Conversion des attributs 'states' dans les modèles Python")
        if self.advanced_conditions:
            features.append("✅ Traitement avancé des conditions complexes")
            
        if not features:
            return
            
        message = f"""
{Fore.GREEN}╔══════════════════════════════════════════════════════════╗
║ {Fore.WHITE}              FONCTIONNALITÉS AVANCÉES                  {Fore.GREEN}║
╠══════════════════════════════════════════════════════════╣
"""
        for i, feature in enumerate(features):
            message += f"║ {Fore.WHITE}{feature}{Fore.GREEN}{' ' * (55 - len(feature))}║\n"
            
        message += f"""╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(message)

    def convert_python_file(self, file_path):
        """Convertir un fichier Python pour Odoo 18"""
        file_stats = {
            'files_processed': 1,
            'files_changed': 0,
            'files_error': 0,
            'changes': {
                'tree_to_list': 0,
                'attrs_conversion': 0,
                'states_conversion': 0,
                'daterange_update': 0,
                'chatter_simplified': 0,
                'settings_structure': 0,
                'python_states_removed': 0,
                'complex_conditions': 0
            }
        }
        
        try:
            # Déterminer le chemin de sortie
            if self.output_dir:
                rel_path = os.path.relpath(file_path, self.source_dir)
                out_path = os.path.join(self.output_dir, rel_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
            else:
                out_path = file_path
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Sauvegarde du fichier original si demandé
            if self.backup and not self.dry_run and self.output_dir is None:
                backup_path = f"{file_path}.bak"
                shutil.copy2(file_path, backup_path)
            
            # Analyser et modifier le code Python
            new_content, state_changes = self.process_python_code(content)
            file_stats['changes']['python_states_removed'] = state_changes
            
            # Si des changements ont été effectués, sauvegarder le fichier
            if new_content != content:
                file_stats['files_changed'] = 1
                if not self.dry_run:
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                self.log(f"Fichier Python mis à jour: {out_path}", level='success')
            else:
                self.log(f"Aucun changement nécessaire dans le fichier Python: {file_path}", level='debug')
                
            return file_stats
                
        except Exception as e:
            self.log(f"Erreur lors du traitement du fichier Python {file_path}: {str(e)}", level='error')
            file_stats['files_error'] = 1
            return file_stats

    def process_python_code(self, content):
        """Analyser et modifier le code Python pour Odoo 18"""
        # Compteur pour les changements
        state_changes = 0
        
        # Pattern pour les attributs states dans les définitions de champs
        states_pattern = r'states\s*=\s*{([^}]*)}'
        
        def remove_states_param(match):
            nonlocal state_changes
            state_changes += 1
            # On enlève juste le paramètre states
            return ""
        
        # Remplacer les attributs states dans les définitions de champs
        new_content = re.sub(r',\s*states\s*=\s*{[^}]*}', remove_states_param, content)
        
        # Recherche et traitement plus avancé si nécessaire avec l'AST
        if new_content == content:
            try:
                # Parse le code avec AST
                tree = ast.parse(content)
                
                # TODO: Implémentation plus avancée avec manipulation AST
                # Cette partie nécessiterait une analyse plus poussée de l'arbre syntaxique
                # pour identifier les définitions de champs et modifier leurs paramètres
                
            except Exception as e:
                self.log(f"Erreur lors de l'analyse AST: {str(e)}", level='warning')
        
        return new_content, state_changes

    def convert_file(self, file_path):
        """Convertir un fichier XML"""
        file_stats = {
            'files_processed': 1,
            'files_changed': 0,
            'files_error': 0,
            'changes': {
                'tree_to_list': 0,
                'attrs_conversion': 0,
                'states_conversion': 0,
                'daterange_update': 0,
                'chatter_simplified': 0,
                'settings_structure': 0,
                'python_states_removed': 0,
                'complex_conditions': 0
            }
        }
        
        try:
            # Déterminer le chemin de sortie
            if self.output_dir:
                rel_path = os.path.relpath(file_path, self.source_dir)
                out_path = os.path.join(self.output_dir, rel_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
            else:
                out_path = file_path
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Sauvegarde du fichier original si demandé
            if self.backup and not self.dry_run and self.output_dir is None:
                backup_path = f"{file_path}.bak"
                shutil.copy2(file_path, backup_path)
            
            # Effectuer les transformations
            new_content, change_stats = self.apply_transformations(content, file_path)
            
            # Mettre à jour les statistiques
            for key, value in change_stats.items():
                file_stats['changes'][key] = value
                
            # Si des changements ont été effectués, sauvegarder le fichier
            if new_content != content:
                file_stats['files_changed'] = 1
                if not self.dry_run:
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    self.log(f"Fichier mis à jour: {out_path}", level='success')
                
                # Afficher les détails des changements en mode verbeux
                if self.verbose:
                    changes_made = sum(change_stats.values())
                    if changes_made > 0:
                        self.log(f"Changements effectués dans {file_path}:", level='info')
                        for change_type, count in change_stats.items():
                            if count > 0:
                                self.log(f"  - {change_type}: {count}", level='info')
            else:
                self.log(f"Aucun changement nécessaire: {file_path}", level='debug')
                
            return file_stats
                
        except Exception as e:
            self.log(f"Erreur lors du traitement de {file_path}: {str(e)}", level='error')
            file_stats['files_error'] = 1
            return file_stats

    def apply_transformations(self, content, file_path):
        """Appliquer toutes les transformations"""
        original_content = content
        change_stats = {
            'tree_to_list': 0,
            'attrs_conversion': 0,
            'states_conversion': 0,
            'daterange_update': 0,
            'chatter_simplified': 0,
            'settings_structure': 0,
            'python_states_removed': 0,
            'complex_conditions': 0
        }
        
        # Essayer d'analyser le fichier comme du XML valide
        is_valid_xml = False
        try:
            # Vérifier si c'est un XML bien formé
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring("<odoo_root>" + content + "</odoo_root>", parser)
            is_valid_xml = True
            self.log(f"Fichier analysé comme XML valide", level='debug')
        except Exception as e:
            self.log(f"Le fichier n'est pas un XML bien formé, traitement en mode texte: {str(e)}", level='debug')
        
        # Compter le nombre de motifs avant les transformations pour vérification
        tree_count_before = content.count('<tree')
        attrs_count_before = len(re.findall(r'attrs="{\'(invisible|readonly|required)\':', content))
        states_count_before = len(re.findall(r'states="([^"]*)"', content))
        chatter_count_before = content.count('<div class="oe_chatter">')
        daterange_count_before = len(re.findall(r'widget="daterange"', content))
        
        # Log des comptages initiaux en mode verbeux
        if self.verbose:
            self.log(f"Comptage initial - tree: {tree_count_before}, attrs: {attrs_count_before}, states: {states_count_before}, chatter: {chatter_count_before}, daterange: {daterange_count_before}", level='debug')
        
        # 1. Convertir tree en list
        content, tree_count = self.convert_tree_to_list(content)
        change_stats['tree_to_list'] = tree_count
        
        # 2. Convertir les attributs attrs et states
        content, attrs_count, states_count, complex_count = self.convert_attrs(content)
        change_stats['attrs_conversion'] = attrs_count
        change_stats['states_conversion'] = states_count
        change_stats['complex_conditions'] = complex_count
        
        # 3. Mettre à jour le widget daterange
        content, daterange_count = self.update_daterange_widget(content)
        change_stats['daterange_update'] = daterange_count
        
        # 4. Simplifier le chatter
        content, chatter_count = self.simplify_chatter(content)
        change_stats['chatter_simplified'] = chatter_count
        
        # 5. Convertir la structure des res.config
        # En mode XML (plus précis) si le fichier est un XML valide, sinon en mode texte
        if is_valid_xml and '<app_settings_block' in content or 'data-key=' in content:
            content, settings_count = self.convert_settings_structure(content)
            change_stats['settings_structure'] = settings_count
        
        # 6. Vérification finale pour s'assurer que toutes les transformations ont été effectuées
        remaining_tree = content.count('<tree')
        if remaining_tree > 0:
            self.log(f"Attention: {remaining_tree} balises tree n'ont pas été converties. Tentative supplémentaire...", level='warning')
            # Tenter une approche plus agressive si des balises tree restent
            content = content.replace('<tree', '<list').replace('</tree>', '</list>')
            tree_count += remaining_tree - content.count('<tree')
            change_stats['tree_to_list'] = tree_count
            
            # Vérification finale
            final_remaining = content.count('<tree')
            if final_remaining > 0:
                self.log(f"Il reste encore {final_remaining} balises tree non converties dans {file_path}", level='warning')
        
        # Vérification et log pour le débogage
        if original_content != content:
            # Fichier modifié, vérifier quels types de modifications
            self.log(f"Modifications appliquées à {file_path}:", level='debug')
            for key, value in change_stats.items():
                if value > 0:
                    self.log(f"  - {key}: {value}", level='debug')
        else:
            self.log(f"Aucune modification nécessaire pour {file_path}", level='debug')
            
        return content, change_stats

    def convert_tree_to_list(self, content):
        """Convertir les balises tree en list"""
        # Compter le nombre de remplacements pour le rapport
        tree_count_before = content.count('<tree')
        
        # Expression régulière plus précise pour détecter les balises tree
        tree_pattern = re.compile(r'<tree(\s+[^>]*>|>)')
        matches = tree_pattern.findall(content)
        real_tree_count = len(matches)
        
        if real_tree_count != tree_count_before:
            self.log(f"Détection différente: simple count {tree_count_before}, regex {real_tree_count}", level='debug')
            # Utiliser le comptage le plus précis
            tree_count_before = real_tree_count
        
        # Conversion de <tree> à <list>
        content_new = re.sub(r'<tree(\s|>)', r'<list\1', content)
        content_new = re.sub(r'</tree>', '</list>', content_new)
        
        # Vérifier si toutes les balises ont été converties
        remaining_trees = content_new.count('<tree')
        if remaining_trees > 0:
            self.log(f"Attention: {remaining_trees} balises tree n'ont pas été converties correctement", level='warning')
            
            # Tentative de conversion plus agressive
            content_new = re.sub(r'<tree', r'<list', content_new)
            content_new = re.sub(r'</tree>', r'</list>', content_new)
            
            # Vérifier à nouveau
            still_remaining = content_new.count('<tree')
            if still_remaining > 0:
                self.log(f"Il reste toujours {still_remaining} balises tree non converties", level='warning')
        
        # Compter les changements réels
        tree_count = tree_count_before - remaining_trees
        
        self.log(f"Balises tree détectées: {tree_count_before}, converties: {tree_count}", level='debug')
        
        return content_new, tree_count

    def convert_attrs(self, content):
        """Convertir les attributs attrs en conditions directes"""
        attrs_count = 0
        states_count = 0
        complex_count = 0
        
        # Trouver tous les attributs attrs avec leurs valeurs
        attrs_pattern = r'attrs="{\'(invisible|readonly|required)\': \[(.*?)\]}"'
        
        def replace_attrs(match):
            nonlocal attrs_count, complex_count
            attr_type = match.group(1)
            conditions = match.group(2)
            
            # Mode avancé pour les conditions complexes
            if self.advanced_conditions and ('|' in conditions or '&' in conditions):
                try:
                    # Tenter de convertir des conditions complexes avec opérateurs | et &
                    converted = self._convert_complex_condition(conditions, attr_type)
                    if converted:
                        complex_count += 1
                        return converted
                except Exception as e:
                    self.log(f"Erreur lors de la conversion complexe: {conditions}. Erreur: {str(e)}", level='warning')
            
            # Traiter les conditions OR (|)
            if conditions.startswith("'|',"):
                # Extraire les deux conditions après le '|'
                parts = conditions.split("'|',")[1].strip()
                cond_parts = re.findall(r'\(\'(.*?)\',\s*\'(.*?)\',\s*([^\)]*)\)', parts)
                
                if len(cond_parts) >= 2:
                    # Construire l'expression OR
                    cond1 = self._format_condition(cond_parts[0][0], cond_parts[0][1], cond_parts[0][2])
                    cond2 = self._format_condition(cond_parts[1][0], cond_parts[1][1], cond_parts[1][2])
                    attrs_count += 1
                    return f'{attr_type}="{cond1} or {cond2}"'
            
            # Traiter les conditions AND (conditions multiples sans '|')
            elif "," in conditions and not conditions.startswith("'|',"):
                cond_parts = re.findall(r'\(\'(.*?)\',\s*\'(.*?)\',\s*([^\)]*)\)', conditions)
                if len(cond_parts) >= 2:
                    conditions_formatted = []
                    for part in cond_parts:
                        conditions_formatted.append(self._format_condition(part[0], part[1], part[2]))
                    attrs_count += 1
                    return f'{attr_type}="{" and ".join(conditions_formatted)}"'
            
            # Traiter une condition simple
            else:
                try:
                    cond_parts = re.findall(r'\(\'(.*?)\',\s*\'(.*?)\',\s*([^\)]*)\)', conditions)
                    if cond_parts:
                        field, operator, value = cond_parts[0]
                        # Gérer la condition spéciale pour les listes vides
                        if value == "[]" and operator == "=":
                            attrs_count += 1
                            return f'{attr_type}="not {field}"'
                        else:
                            attrs_count += 1
                            return f'{attr_type}="{self._format_condition(field, operator, value)}"'
                except Exception as e:
                    self.log(f"Erreur lors du parsing de la condition: {conditions}. Erreur: {str(e)}", level='warning')
            
            # Si aucune des règles ne s'applique, garder l'original
            return match.group(0)
        
        # Appliquer les remplacements
        content = re.sub(attrs_pattern, replace_attrs, content)
        
        # Conversion des states en invisible
        states_pattern = r'states="([^"]*)"'
        
        def replace_states(match):
            nonlocal states_count
            state_value = match.group(1)
            states_count += 1
            return f'invisible="state != \'{state_value}\'"'
        
        content = re.sub(states_pattern, replace_states, content)
        
        return content, attrs_count, states_count, complex_count

    def _format_condition(self, field, operator, value):
        """Formater une condition pour la nouvelle syntaxe"""
        # Traiter la valeur en fonction de son type
        cleaned_value = value.strip("'")
        
        if operator == "=":
            if value == "[]":  # Cas spécial pour les listes vides
                return f"not {field}"
            elif value == "False":
                return f"not {field}"
            elif value == "True":
                return field
            else:
                return f"{field} == {value}"
        elif operator == "!=":
            if value == "[]":  # Cas spécial pour les listes vides
                return field
            elif value == "False":
                return field
            elif value == "True":
                return f"not {field}"
            else:
                return f"{field} != {value}"
        elif operator in ["<", ">", "<=", ">="]:
            return f"{field} {operator} {value}"
        else:
            return f"{field} {operator} {value}"

    def update_daterange_widget(self, content):
        """Mettre à jour les widgets daterange"""
        daterange_count = 0
        
        # Chercher les widgets daterange avec l'ancienne syntaxe
        old_pattern = r'<field name="([^"]*)" widget="daterange" options="{\'related_end_date\': \'([^\']*)\'}"/>'
        new_format = r'<field name="\1" widget="daterange" options="{\'end_date_field\': \'\2\'}"/>'
        
        # Compter les occurrences avant remplacement
        daterange_count += len(re.findall(old_pattern, content))
        
        content = re.sub(old_pattern, new_format, content)
        
        # Supprimer les champs end_date avec le widget daterange qui sont maintenant inutiles
        end_date_pattern = r'<field name="([^"]*)" widget="daterange" options="{\'related_start_date\': \'([^\']*)\'}"/>'
        
        # Compter les occurrences avant suppression
        daterange_count += len(re.findall(end_date_pattern, content))
        
        content = re.sub(end_date_pattern, '', content)
        
        return content, daterange_count

    def simplify_chatter(self, content):
        """Simplifier la structure du chatter"""
        chatter_count = 0
        
        # Pattern pour détecter l'ancien format de chatter (standard)
        old_chatter_pattern = r'<div class="oe_chatter">\s*<field name="message_follower_ids" widget="mail_followers"/>\s*<field name="activity_ids" widget="mail_activity"/>\s*<field name="message_ids" widget="mail_thread"/>\s*</div>'
        
        # Pattern alternatif avec espaces et ordre différent
        alt_chatter_pattern1 = r'<div class="oe_chatter">\s*<field name="message_follower_ids"[^>]*widget="mail_followers"[^>]*>\s*</field>\s*<field name="activity_ids"[^>]*widget="mail_activity"[^>]*>\s*</field>\s*<field name="message_ids"[^>]*widget="mail_thread"[^>]*>\s*</field>\s*</div>'
        
        # Pattern alternatif avec ordre différent des champs
        alt_chatter_pattern2 = r'<div class="oe_chatter">\s*(<field[^>]*widget="mail_followers"[^>]*/>|<field[^>]*widget="mail_followers"[^>]*>\s*</field>)\s*(<field[^>]*widget="mail_thread"[^>]*/>|<field[^>]*widget="mail_thread"[^>]*>\s*</field>)\s*(<field[^>]*widget="mail_activity"[^>]*/>|<field[^>]*widget="mail_activity"[^>]*>\s*</field>)\s*</div>'
        
        # Pattern alternatif avec seulement message_ids et followers
        alt_chatter_pattern3 = r'<div class="oe_chatter">\s*(<field[^>]*widget="mail_followers"[^>]*/>|<field[^>]*widget="mail_followers"[^>]*>\s*</field>)\s*(<field[^>]*widget="mail_thread"[^>]*/>|<field[^>]*widget="mail_thread"[^>]*>\s*</field>)\s*</div>'
        
        # Effectuer les conversions avec les différents patterns
        # 1. Pattern standard
        matches1 = re.findall(old_chatter_pattern, content)
        count1 = len(matches1)
        if count1 > 0:
            self.log(f"Détecté {count1} structures de chatter standard", level='debug')
            content = re.sub(old_chatter_pattern, '<chatter/>', content)
            chatter_count += count1
            
        # 2. Pattern alternatif 1
        matches2 = re.findall(alt_chatter_pattern1, content)
        count2 = len(matches2)
        if count2 > 0:
            self.log(f"Détecté {count2} structures de chatter alternatives (type 1)", level='debug')
            content = re.sub(alt_chatter_pattern1, '<chatter/>', content)
            chatter_count += count2
            
        # 3. Pattern alternatif 2
        matches3 = re.findall(alt_chatter_pattern2, content)
        count3 = len(matches3)
        if count3 > 0:
            self.log(f"Détecté {count3} structures de chatter alternatives (type 2)", level='debug')
            content = re.sub(alt_chatter_pattern2, '<chatter/>', content)
            chatter_count += count3
            
        # 4. Pattern alternatif 3
        matches4 = re.findall(alt_chatter_pattern3, content)
        count4 = len(matches4)
        if count4 > 0:
            self.log(f"Détecté {count4} structures de chatter alternatives (type 3)", level='debug')
            content = re.sub(alt_chatter_pattern3, '<chatter/>', content)
            chatter_count += count4
            
        # Détection simple pour cas non couverts par les expressions régulières
        if '<div class="oe_chatter">' in content and chatter_count == 0:
            self.log(f"Des structures de chatter ont été détectées mais n'ont pas pu être converties automatiquement", level='warning')
            # On tente une approche XML avec lxml si possible
            try:
                parser = etree.XMLParser(recover=True)
                root = etree.fromstring("<root>" + content + "</root>", parser)
                
                # Trouver toutes les div oe_chatter
                chatter_divs = root.xpath("//div[@class='oe_chatter']")
                if chatter_divs:
                    self.log(f"Tentative de conversion XML pour {len(chatter_divs)} chatters", level='debug')
                    for chatter_div in chatter_divs:
                        # Remplacer par un élément chatter
                        new_chatter = etree.Element("chatter")
                        parent = chatter_div.getparent()
                        if parent is not None:
                            parent.replace(chatter_div, new_chatter)
                            chatter_count += 1
                    
                    # Convertir l'arbre XML modifié en texte
                    content = etree.tostring(root, pretty_print=True, encoding='unicode')
                    # Supprimer les tags root ajoutés
                    content = content.replace("<root>", "").replace("</root>", "")
            except Exception as e:
                self.log(f"Erreur lors de la conversion XML des chatters: {str(e)}", level='warning')
        
        if chatter_count > 0:
            self.log(f"Remplacé {chatter_count} structures de chatter par la balise simplifiée", level='debug')
        
        return content, chatter_count

    def convert_settings_structure(self, content):
        """Convertir la structure des paramètres res.config.settings"""
        settings_count = 0
        
        try:
            # Cette conversion est plus complexe car elle nécessite de parser l'XML
            if '<app_settings_block' in content or 'data-key=' in content:
                parser = etree.XMLParser(recover=True)
                try:
                    root = etree.fromstring(content, parser)
                    
                    # Chercher toutes les div app_settings_block
                    app_blocks = root.xpath("//div[@class='app_settings_block']")
                    settings_count = len(app_blocks)
                    
                    for app_block in app_blocks:
                        # Créer un nouvel élément app
                        app_element = etree.Element("app")
                        
                        # Copier les attributs pertinents
                        if app_block.get('string'):
                            app_element.set('string', app_block.get('string'))
                        elif app_block.get('data-string'):
                            app_element.set('string', app_block.get('data-string'))
                        
                        # Parcourir les éléments enfants
                        for child in app_block:
                            # Convertir les balises h2 en blocks
                            if child.tag == 'h2':
                                block = etree.SubElement(app_element, "block")
                                block.set('title', child.text.strip())
                            
                            # Convertir les conteneurs de paramètres
                            elif child.tag == 'div' and 'o_settings_container' in child.get('class', ''):
                                # Chercher les labels, champs et descriptions
                                labels = child.xpath(".//label")
                                fields = child.xpath(".//field")
                                descriptions = child.xpath(".//div[@class='text-muted']")
                                
                                # Créer un élément setting
                                if labels and fields:
                                    setting = etree.SubElement(app_element, "setting")
                                    
                                    # Ajouter l'attribut string (label)
                                    if labels[0].get('string'):
                                        setting.set('string', labels[0].get('string'))
                                    
                                    # Ajouter l'attribut help (description)
                                    if descriptions and descriptions[0].text:
                                        setting.set('help', descriptions[0].text.strip())
                                    
                                    # Ajouter les champs
                                    for field in fields:
                                        setting.append(field)
                        
                        # Remplacer l'ancien bloc par le nouveau
                        app_block.getparent().replace(app_block, app_element)
                    
                    # Convertir l'arbre XML modifié en texte
                    content = etree.tostring(root, pretty_print=True, encoding='unicode')
                except Exception as e:
                    self.log(f"Erreur lors de la conversion de la structure des paramètres: {str(e)}", level='warning')
        except Exception as e:
            self.log(f"Erreur lors de l'analyse XML: {str(e)}", level='warning')
        
        return content, settings_count

    def _convert_complex_condition(self, condition, attr_type):
        """Convertir des conditions complexes avec plusieurs opérateurs OR et AND"""
        # Cette méthode est une ébauche pour traiter des cas plus complexes
        # Il faudrait implémenter un véritable parseur/évaluateur de conditions Odoo

        # Exemple simplifié pour quelques cas courants
        # 1. Plusieurs OR consécutifs: '|', '|', cond1, cond2, cond3
        if condition.startswith("'|',") and "'|'," in condition[4:]:
            try:
                # Compter les opérateurs OR
                or_count = 0
                idx = 0
                while True:
                    next_idx = condition.find("'|',", idx)
                    if next_idx == -1:
                        break
                    or_count += 1
                    idx = next_idx + 4
                
                # Extraire toutes les conditions
                cond_parts = re.findall(r'\(\'(.*?)\',\s*\'(.*?)\',\s*([^\)]*)\)', condition)
                
                if len(cond_parts) == or_count + 1:
                    # Formater toutes les conditions
                    formatted_conditions = []
                    for part in cond_parts:
                        formatted_conditions.append(self._format_condition(part[0], part[1], part[2]))
                    
                    # Construire l'expression avec OR
                    return f'{attr_type}="{" or ".join(formatted_conditions)}"'
            except Exception as e:
                self.log(f"Erreur traitement condition OR multiple: {condition}. Erreur: {str(e)}", level='warning')
        
        # 2. Conditions AND imbriquées dans des OR: '|', cond1, '&', cond2, cond3
        elif "'|'," in condition and "'&'," in condition:
            # Ce cas est très complexe et nécessiterait un parser complet
            # Implémentation simplifiée pour certains cas spécifiques
            pass
            
        # Pas de conversion possible, retourner None
        return None

    def print_report(self):
        """Affiche un rapport détaillé des conversions effectuées"""
        duration = self.stats['duration']
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        # Ajouter les nouvelles statistiques
        additional_stats = ""
        if self.convert_python:
            additional_stats += f"║ {Fore.WHITE}  - attrs states Python : {self.stats['changes']['python_states_removed']:<5}{Fore.CYAN}                       ║\n"
        if self.advanced_conditions:
            additional_stats += f"║ {Fore.WHITE}  - conditions complexes: {self.stats['changes']['complex_conditions']:<5}{Fore.CYAN}                       ║\n"
        
        report = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║ {Fore.YELLOW}                 RAPPORT DE CONVERSION                    {Fore.CYAN}║
╠══════════════════════════════════════════════════════════╣
║ {Fore.WHITE}Fichiers traités      : {self.stats['files_processed']:<5}{Fore.CYAN}                       ║
║ {Fore.GREEN}Fichiers modifiés     : {self.stats['files_changed']:<5}{Fore.CYAN}                       ║
║ {Fore.YELLOW}Fichiers ignorés      : {self.stats['files_skipped']:<5}{Fore.CYAN}                       ║
║ {Fore.RED}Fichiers en erreur     : {self.stats['files_error']:<5}{Fore.CYAN}                       ║
╠══════════════════════════════════════════════════════════╣
║ {Fore.WHITE}Temps d'exécution     : {minutes:02d}:{seconds:02d} min{Fore.CYAN}                      ║
╠══════════════════════════════════════════════════════════╣
║ {Fore.YELLOW}Détail des conversions:{Fore.CYAN}                                ║
║ {Fore.WHITE}  - tree → list       : {self.stats['changes']['tree_to_list']:<5}{Fore.CYAN}                       ║
║ {Fore.WHITE}  - attrs             : {self.stats['changes']['attrs_conversion']:<5}{Fore.CYAN}                       ║
║ {Fore.WHITE}  - states            : {self.stats['changes']['states_conversion']:<5}{Fore.CYAN}                       ║
║ {Fore.WHITE}  - daterange         : {self.stats['changes']['daterange_update']:<5}{Fore.CYAN}                       ║
║ {Fore.WHITE}  - chatter           : {self.stats['changes']['chatter_simplified']:<5}{Fore.CYAN}                       ║
║ {Fore.WHITE}  - settings          : {self.stats['changes']['settings_structure']:<5}{Fore.CYAN}                       ║
{additional_stats}╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(report)
        
        # Afficher des statistiques détaillées sur les dossiers et extensions
        self.show_statistics()
        
        # Afficher un message de réussite ou d'échec
        if self.stats['files_error'] > 0:
            print(f"{Fore.RED}⚠️ Des erreurs ont été rencontrées pendant la conversion.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}   Consultez le fichier journal pour plus de détails.{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}✅ Conversion terminée avec succès !{Style.RESET_ALL}")
            
        # Si les fichiers ont été sauvegardés dans un autre répertoire
        if self.output_dir:
            print(f"\n{Fore.CYAN}📁 Les fichiers convertis ont été sauvegardés dans: {self.output_dir}{Style.RESET_ALL}")
        elif self.backup and not self.dry_run:
            print(f"\n{Fore.CYAN}💾 Des sauvegardes des fichiers originaux ont été créées (.bak){Style.RESET_ALL}")

    def show_statistics(self):
        """Affiche des statistiques détaillées sur les dossiers et extensions traités"""
        # Collecter des informations sur les dossiers traités
        folder_stats = {}
        extension_stats = {}
        
        # Récupérer la liste des dossiers et des extensions traités
        for root, _, files in os.walk(self.source_dir):
            rel_path = os.path.relpath(root, self.source_dir)
            folder_key = rel_path if rel_path != '.' else 'racine'
            folder_stats[folder_key] = {
                'total': 0,
                'xml': 0,
                'py': 0,
                'other': 0,
                'processed': 0,
                'modified': 0
            }
            
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                # Incrémenter le compteur total pour ce dossier
                folder_stats[folder_key]['total'] += 1
                
                # Compter par extension
                if file_ext == '.xml':
                    folder_stats[folder_key]['xml'] += 1
                elif file_ext == '.py':
                    folder_stats[folder_key]['py'] += 1
                else:
                    folder_stats[folder_key]['other'] += 1
                
                # Compter les statistiques globales par extension
                if file_ext not in extension_stats:
                    extension_stats[file_ext] = 0
                extension_stats[file_ext] += 1
        
        # Afficher les statistiques par dossier (afficher seulement les plus pertinents)
        print(f"\n{Fore.CYAN}╔══════════════════════════════════════════════════════════╗")
        print(f"║ {Fore.YELLOW}           STATISTIQUES DÉTAILLÉES PAR DOSSIER            {Fore.CYAN}║")
        print(f"╠══════════════════════════════════════════════════════════╣")
        
        # Trier les dossiers par nombre de fichiers XML et Python
        relevant_folders = []
        for folder, stats in folder_stats.items():
            relevant_count = stats['xml'] + stats['py']
            if relevant_count > 0:
                relevant_folders.append((folder, stats, relevant_count))
        
        relevant_folders.sort(key=lambda x: x[2], reverse=True)
        
        # Afficher les statistiques des dossiers les plus pertinents
        for folder, stats, _ in relevant_folders[:10]:  # Afficher les 10 principaux dossiers
            print(f"║ {Fore.WHITE}{folder[:30]:<30}{Fore.CYAN} │ {Fore.WHITE}XML: {stats['xml']:<3} PY: {stats['py']:<3} Autres: {stats['other']:<3}{Fore.CYAN} ║")
        
        if len(relevant_folders) > 10:
            print(f"║ {Fore.WHITE}... et {len(relevant_folders) - 10} autres dossiers{Fore.CYAN}{' ' * 32}║")
        
        # Afficher les statistiques par extension
        print(f"╠══════════════════════════════════════════════════════════╣")
        print(f"║ {Fore.YELLOW}          STATISTIQUES DÉTAILLÉES PAR EXTENSION          {Fore.CYAN}║")
        print(f"╠══════════════════════════════════════════════════════════╣")
        
        # Trier les extensions par nombre de fichiers
        sorted_extensions = sorted(extension_stats.items(), key=lambda x: x[1], reverse=True)
        
        for ext, count in sorted_extensions[:10]:  # Afficher les 10 principales extensions
            if not ext:
                ext_name = "(sans extension)"
            else:
                ext_name = ext
            print(f"║ {Fore.WHITE}{ext_name:<15}{Fore.CYAN} │ {Fore.WHITE}Fichiers: {count:<5}{Fore.CYAN}{' ' * 27}║")
        
        if len(sorted_extensions) > 10:
            print(f"║ {Fore.WHITE}... et {len(sorted_extensions) - 10} autres extensions{Fore.CYAN}{' ' * 26}║")
            
        print(f"╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}")

    def save_report(self):
        """Sauvegarde le rapport au format JSON"""
        report = {
            'summary': {
                'files_processed': self.stats['files_processed'],
                'files_changed': self.stats['files_changed'],
                'files_skipped': self.stats['files_skipped'],
                'files_error': self.stats['files_error'],
                'execution_time_seconds': self.stats['duration'],
                'start_time': self.stats['start_time'].isoformat(),
                'end_time': self.stats['end_time'].isoformat()
            },
            'changes': self.stats['changes']
        }
        
        try:
            with open(self.report_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"{Fore.GREEN}✅ Rapport sauvegardé dans: {self.report_file}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ Erreur lors de la sauvegarde du rapport: {str(e)}{Style.RESET_ALL}")

    def show_limitations(self):
        """Afficher les limitations connues du script"""
        limitations = f"""
{Fore.YELLOW}╔══════════════════════════════════════════════════════════╗
║ {Fore.WHITE}                     LIMITATIONS                        {Fore.YELLOW}║
╠══════════════════════════════════════════════════════════╣
║ {Fore.WHITE}1. Certaines transformations complexes peuvent nécessiter {Fore.YELLOW}║
║ {Fore.WHITE}   des ajustements manuels.                              {Fore.YELLOW}║
║                                                          ║
║ {Fore.WHITE}2. Le script ne modifie pas la structure Python des       {Fore.YELLOW}║
║ {Fore.WHITE}   modèles (comme la suppression des attributs states    {Fore.YELLOW}║
║ {Fore.WHITE}   dans les définitions de champs).                      {Fore.YELLOW}║
║                                                          ║
║ {Fore.WHITE}3. Les expressions complexes dans les attributs           {Fore.YELLOW}║
║ {Fore.WHITE}   conditionnels peuvent ne pas être parfaitement         {Fore.YELLOW}║
║ {Fore.WHITE}   converties.                                           {Fore.YELLOW}║
╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.CYAN}Il est recommandé de vérifier manuellement les fichiers convertis
avant de les utiliser en production.{Style.RESET_ALL}
"""
        print(limitations)

    def update_stats(self, result):
        """Met à jour les statistiques avec le résultat d'une conversion"""
        if result:
            for key, value in result.items():
                if key in self.stats:
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            if subkey in self.stats[key]:
                                self.stats[key][subkey] += subvalue
                    else:
                        self.stats[key] += value


def main():
    # Vérifier si des arguments sont fournis
    if len(sys.argv) == 1:
        # Pas d'arguments, lancer le mode interactif
        interactive_mode = InteractiveMode()
        options = interactive_mode.run()
        
        if not options:
            return 0
            
        # Créer le convertisseur avec les options choisies
        converter = Odoo18Converter(
            source_dir=options['source_dir'],
            output_dir=options['output_dir'],
            backup=options['backup'],
            verbose=options['verbose'],
            extensions=options['extensions'],
            skip_patterns=options['skip_patterns'],
            report_file=options['report_file'],
            workers=options['workers'],
            dry_run=options['dry_run'],
            interactive=options['interactive'],
            convert_python=options['convert_python'],
            advanced_conditions=options['advanced_conditions']
        )
        
        try:
            converter.convert_all()
            return 0
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Conversion interrompue par l'utilisateur.{Style.RESET_ALL}")
            return 130
        except Exception as e:
            print(f"{Fore.RED}Erreur fatale: {str(e)}{Style.RESET_ALL}")
            return 1
    
    # Si des arguments sont fournis, utiliser l'interface en ligne de commande standard
    parser = argparse.ArgumentParser(
        description=f'{Fore.CYAN}Convertisseur de fichiers XML Odoo vers la syntaxe Odoo 18{Style.RESET_ALL}',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Arguments obligatoires
    parser.add_argument('source_dir', help='Répertoire source contenant les fichiers à convertir')
    
    # Arguments optionnels
    parser.add_argument('-o', '--output-dir', 
                      help='Répertoire de sortie pour les fichiers convertis (si non spécifié, modifie les fichiers en place)')
    parser.add_argument('--no-backup', action='store_false', dest='backup', 
                      help='Ne pas créer de sauvegarde des fichiers originaux')
    parser.add_argument('-v', '--verbose', action='store_true', 
                      help='Afficher des informations détaillées sur le processus')
    parser.add_argument('-e', '--extensions', nargs='+', default=['.xml'],
                      help='Extensions de fichiers à traiter')
    parser.add_argument('-s', '--skip', nargs='+', default=[],
                      help='Patterns regex pour ignorer certains fichiers')
    parser.add_argument('-r', '--report',
                      help='Chemin du fichier pour sauvegarder le rapport de conversion (JSON)')
    parser.add_argument('-w', '--workers', type=int, default=1,
                      help='Nombre de processus worker pour le traitement parallèle')
    parser.add_argument('-d', '--dry-run', action='store_true',
                      help='Mode test: ne pas modifier les fichiers, simplement afficher ce qui serait fait')
    parser.add_argument('-i', '--interactive', action='store_true',
                      help='Mode interactif: demande confirmation avant chaque modification')
    parser.add_argument('-l', '--show-limitations', action='store_true',
                      help='Afficher uniquement les limitations connues du script et quitter')
    
    # Nouveaux arguments pour surmonter les limitations
    parser.add_argument('--convert-python', action='store_true',
                      help='Convertir également les fichiers Python (.py) pour supprimer les attributs states')
    parser.add_argument('--advanced-conditions', action='store_true', 
                      help='Activer le traitement avancé des conditions complexes dans les attributs attrs')
    parser.add_argument('--overcome-all', action='store_true',
                      help='Activer toutes les fonctionnalités pour surmonter les limitations')
    
    args = parser.parse_args()
    
    # Afficher uniquement les limitations si demandé
    if args.show_limitations:
        converter = Odoo18Converter(source_dir=".")
        converter.show_limitations()
        return 0
    
    # Activer toutes les options si --overcome-all est spécifié
    if args.overcome_all:
        args.convert_python = True
        args.advanced_conditions = True
    
    if not os.path.isdir(args.source_dir):
        print(f"{Fore.RED}Erreur: Le répertoire {args.source_dir} n'existe pas{Style.RESET_ALL}")
        return 1
    
    converter = Odoo18Converter(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        backup=args.backup,
        verbose=args.verbose,
        extensions=args.extensions,
        skip_patterns=args.skip,
        report_file=args.report,
        workers=args.workers,
        dry_run=args.dry_run,
        interactive=args.interactive,
        convert_python=args.convert_python, 
        advanced_conditions=args.advanced_conditions
    )
    
    try:
        converter.convert_all()
        return 0
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Conversion interrompue par l'utilisateur.{Style.RESET_ALL}")
        return 130
    except Exception as e:
        print(f"{Fore.RED}Erreur fatale: {str(e)}{Style.RESET_ALL}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 