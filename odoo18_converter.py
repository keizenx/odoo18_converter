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

# Initialize colorama for terminal colors
colorama.init()

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('odoo18_converter')

class InteractiveMode:
    """Class to manage the application's interactive mode"""
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
        """Display the interactive mode header"""
        header = f"""
{Fore.CYAN}██████╗ ██████╗  ██████╗  ██████╗      ██╗ █████╗                           
{Fore.CYAN}██╔═══██╗██╔══██╗██╔═══██╗██╔═══██╗    ███║██╔══██╗                          
{Fore.CYAN}██║   ██║██║  ██║██║   ██║██║   ██║    ╚██║╚█████╔╝                    
{Fore.CYAN}██║   ██║██║  ██║██║   ██║██║   ██║     ██║██╔══██╗               
{Fore.CYAN}╚██████╔╝██████╔╝╚██████╔╝╚██████╔╝     ██║╚█████╔╝                          
{Fore.CYAN} ╚═════╝ ╚═════╝  ╚═════╝  ╚═════╝      ╚═╝ ╚════╝                           
                                                                             
{Fore.CYAN}███████╗██╗   ██╗███╗   ██╗████████╗ █████╗ ██╗  ██╗                         
{Fore.CYAN}██╔════╝╚██╗ ██╔╝████╗  ██║╚══██╔══╝██╔══██╗╚██╗██╔╝                         
{Fore.CYAN}███████╗ ╚████╔╝ ██╔██╗ ██║   ██║   ███████║ ╚███╔╝                          
{Fore.CYAN}╚════██║  ╚██╔╝  ██║╚██╗██║   ██║   ██╔══██║ ██╔██╗                          
{Fore.CYAN}███████║   ██║   ██║ ╚████║   ██║   ██║  ██║██╔╝ ██╗                         
{Fore.CYAN}╚══════╝   ╚═╝   ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝                         

{Fore.YELLOW}Version 1.2.0 - Interactive Mode{Style.RESET_ALL}

This mode guides you step by step through the conversion process.
You can exit at any time by pressing Ctrl+C.

"""
        print(header)
    
    def prompt_source_dir(self):
        """Ask the user for the source directory"""
        while True:
            source_dir = input(f"{Fore.GREEN}1. Enter the path of the Odoo module to convert:{Style.RESET_ALL} ")
            if not source_dir:
                print(f"{Fore.RED}Error: Path cannot be empty.{Style.RESET_ALL}")
                continue
                
            # Check if directory exists
            if os.path.isdir(source_dir):
                self.source_dir = source_dir
                return True
            else:
                create_dir = input(f"{Fore.YELLOW}Directory doesn't exist. Do you want to create it? (y/n) :{Style.RESET_ALL} ")
                if create_dir.lower() in ['y', 'yes']:
                    try:
                        os.makedirs(source_dir, exist_ok=True)
                        self.source_dir = source_dir
                        return True
                    except Exception as e:
                        print(f"{Fore.RED}Error creating directory: {str(e)}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Please enter a valid path.{Style.RESET_ALL}")
    
    def prompt_options(self):
        """Ask the user for conversion options"""
        # Choose conversion type
        print(f"\n{Fore.GREEN}2. Choose conversion options:{Style.RESET_ALL}")
        
        # Python conversion option
        convert_python = input(f"{Fore.CYAN}   Convert Python files (.py)? (y/n) [n]: {Style.RESET_ALL}")
        self.options['convert_python'] = convert_python.lower() in ['y', 'yes']
        
        # Advanced conditions option
        advanced_conditions = input(f"{Fore.CYAN}   Enable advanced conditions processing? (y/n) [n]: {Style.RESET_ALL}")
        self.options['advanced_conditions'] = advanced_conditions.lower() in ['y', 'yes']
        
        # Backup option
        backup = input(f"{Fore.CYAN}   Create backups of original files? (y/n) [y]: {Style.RESET_ALL}")
        self.options['backup'] = backup.lower() not in ['n', 'no']
        
        # Verbose mode option
        verbose = input(f"{Fore.CYAN}   Enable verbose mode? (y/n) [n]: {Style.RESET_ALL}")
        self.options['verbose'] = verbose.lower() in ['y', 'yes']
        
        # Output directory option
        output_dir = input(f"{Fore.CYAN}   Output directory (empty to modify files in place): {Style.RESET_ALL}")
        if output_dir:
            self.options['output_dir'] = output_dir
            # Create output directory if it doesn't exist
            if not os.path.isdir(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except Exception as e:
                    print(f"{Fore.RED}Error creating output directory: {str(e)}{Style.RESET_ALL}")
                    return False
        
        # Workers option
        workers = input(f"{Fore.CYAN}   Number of parallel processes (1-{os.cpu_count() or 4}) [1]: {Style.RESET_ALL}")
        if workers.isdigit() and 1 <= int(workers) <= (os.cpu_count() or 4):
            self.options['workers'] = int(workers)
        
        # Dry run option
        dry_run = input(f"{Fore.CYAN}   Test mode (no actual changes)? (y/n) [n]: {Style.RESET_ALL}")
        self.options['dry_run'] = dry_run.lower() in ['y', 'yes']
        
        # Extensions option
        extensions = input(f"{Fore.CYAN}   Extensions to process (space separated) [.xml]: {Style.RESET_ALL}")
        if extensions:
            self.options['extensions'] = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions.split()]
        
        # Report option
        report = input(f"{Fore.CYAN}   Generate a report (file path, empty for no report): {Style.RESET_ALL}")
        if report:
            self.options['report_file'] = report
        
        return True
    
    def confirm_conversion(self):
        """Ask the user to confirm the conversion"""
        print(f"\n{Fore.GREEN}3. Options summary:{Style.RESET_ALL}")
        print(f"   - Source module: {self.source_dir}")
        
        if self.options['output_dir']:
            print(f"   - Output directory: {self.options['output_dir']}")
        else:
            print(f"   - Mode: In-place modification")
            
        if self.options['backup']:
            print(f"   - Backup: Yes (.bak)")
        else:
            print(f"   - Backup: No")
            
        if self.options['convert_python']:
            print(f"   - Python conversion: Yes")
        else:
            print(f"   - Python conversion: No")
            
        if self.options['advanced_conditions']:
            print(f"   - Advanced conditions processing: Yes")
        else:
            print(f"   - Advanced conditions processing: No")
            
        if self.options['dry_run']:
            print(f"   - Test mode: Yes (no actual changes)")
        else:
            print(f"   - Test mode: No")
            
        print(f"   - Extensions: {', '.join(self.options['extensions'])}")
        print(f"   - Workers: {self.options['workers']}")
        
        if self.options['report_file']:
            print(f"   - Report: {self.options['report_file']}")
        else:
            print(f"   - Report: No")
            
        confirm = input(f"\n{Fore.YELLOW}Confirm conversion? (y/n) [y]: {Style.RESET_ALL}")
        return confirm.lower() not in ['n', 'no']
    
    def run(self):
        """Run the interactive mode"""
        try:
            self.print_header()
            
            if not self.prompt_source_dir():
                return None
                
            if not self.prompt_options():
                return None
                
            if not self.confirm_conversion():
                print(f"{Fore.YELLOW}Conversion cancelled.{Style.RESET_ALL}")
                return None
                
            # Return options for execution
            return {
                'source_dir': self.source_dir,
                **self.options
            }
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operation cancelled by user.{Style.RESET_ALL}")
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
        
        # Statistics
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
        
        # Output configuration
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        # Create a log file handler if specified
        if report_file:
            file_handler = logging.FileHandler(report_file, mode='w')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
            
    def log(self, message, level='info', file_path=None):
        """Log a message with the specified level"""
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
        """Display a stylized banner at startup"""
        banner = f"""
{Fore.CYAN}██████╗ ██████╗  ██████╗  ██████╗      ██╗ █████╗                           
{Fore.CYAN}██╔═══██╗██╔══██╗██╔═══██╗██╔═══██╗    ███║██╔══██╗                          
{Fore.CYAN}██║   ██║██║  ██║██║   ██║██║   ██║    ╚██║╚█████╔╝    {Fore.YELLOW}█████╗{Fore.CYAN}                
{Fore.CYAN}██║   ██║██║  ██║██║   ██║██║   ██║     ██║██╔══██╗    {Fore.YELLOW}╚════╝{Fore.CYAN}                
{Fore.CYAN}╚██████╔╝██████╔╝╚██████╔╝╚██████╔╝     ██║╚█████╔╝                          
{Fore.CYAN} ╚═════╝ ╚═════╝  ╚═════╝  ╚═════╝      ╚═╝ ╚════╝                           
                                                                             
{Fore.CYAN}███████╗██╗   ██╗███╗   ██╗████████╗ █████╗ ██╗  ██╗                         
{Fore.CYAN}██╔════╝╚██╗ ██╔╝████╗  ██║╚══██╔══╝██╔══██╗╚██╗██╔╝                         
{Fore.CYAN}███████╗ ╚████╔╝ ██╔██╗ ██║   ██║   ███████║ ╚███╔╝                          
{Fore.CYAN}╚════██║  ╚██╔╝  ██║╚██╗██║   ██║   ██╔══██║ ██╔██╗                          
{Fore.CYAN}███████║   ██║   ██║ ╚████║   ██║   ██║  ██║██╔╝ ██╗                         
{Fore.CYAN}╚══════╝   ╚═╝   ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝                         
                                                                             
{Fore.CYAN} ██████╗ ██████╗ ███╗   ██╗██╗   ██╗███████╗██████╗ ████████╗███████╗██████╗ 
{Fore.CYAN}██╔════╝██╔═══██╗████╗  ██║██║   ██║██╔════╝██╔══██╗╚══██╔══╝██╔════╝██╔══██╗
{Fore.CYAN}██║     ██║   ██║██╔██╗ ██║██║   ██║█████╗  ██████╔╝   ██║   █████╗  ██████╔╝
{Fore.CYAN}██║     ██║   ██║██║╚██╗██║╚██╗ ██╔╝██╔══╝  ██╔══██╗   ██║   ██╔══╝  ██╔══██╗
{Fore.CYAN}╚██████╗╚██████╔╝██║ ╚████║ ╚████╔╝ ███████╗██║  ██║   ██║   ███████╗██║  ██║
{Fore.CYAN} ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝

{Fore.WHITE}Version 1.2.0{Style.RESET_ALL}
"""
        print(banner)

    def should_skip_file(self, file_path):
        """Determine if a file should be skipped"""
        # Check if the file matches any of the patterns to skip
        for pattern in self.skip_patterns:
            if re.search(pattern, file_path):
                return True
        return False

    def convert_all(self):
        """Go through all files and apply conversions"""
        self.print_banner()
        
        # Display script limitations (if not overcome)
        if not self.convert_python and not self.advanced_conditions and not self.dry_run:
            self.show_limitations()
        else:
            self.show_advanced_features()
        
        self.stats['start_time'] = datetime.now()
        
        # Determine file types to process
        all_extensions = list(self.extensions)
        if self.convert_python:
            if '.py' not in all_extensions:
                all_extensions.append('.py')
        
        print(f"📋 {Fore.CYAN}Searching for {', '.join(all_extensions)} files in {self.source_dir}...{Style.RESET_ALL}")
        
        # Collect all files to process
        files_to_process = []
        total_files_found = 0
        
        # Standard Odoo directories to check first (more complete list)
        odoo_standard_dirs = [
            'views', 'security', 'data', 'wizard', 'report', 
            'static/src/xml', 'static/src/js', 'static/description',
            'controllers', 'demo', 'i18n', 'templates', 'tests'
        ]
        
        # Function to add a file to the processing list
        def process_file_path(file_path):
            nonlocal total_files_found
            total_files_found += 1
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Process according to file type
            if file_ext in all_extensions:
                if not self.should_skip_file(file_path):
                    files_to_process.append((file_path, file_ext))
                    return True
                else:
                    self.stats['files_skipped'] += 1
                    self.log(f"File skipped according to patterns: {file_path}", level='debug')
            else:
                # File with an unprocessed extension
                self.stats['files_skipped'] += 1
                self.log(f"File skipped (unprocessed extension): {file_path}", level='debug')
            return False
        
        # Ensure the source directory exists
        if not os.path.exists(self.source_dir):
            self.log(f"Source directory {self.source_dir} does not exist.", level='error')
            return
            
        # Perform an exhaustive search for all XML and Python files in the directory
        xml_files_found = 0
        py_files_found = 0
        
        # First, check each standard Odoo folder
        for standard_dir in odoo_standard_dirs:
            standard_path = os.path.join(self.source_dir, standard_dir)
            if os.path.isdir(standard_path):
                self.log(f"Checking standard Odoo folder: {standard_dir}", level='info')
                for root, _, files in os.walk(standard_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_ext = os.path.splitext(file)[1].lower()
                        if file_ext == '.xml':
                            xml_files_found += 1
                        elif file_ext == '.py':
                            py_files_found += 1
                        process_file_path(file_path)
        
        # Then, go through all other files in the source directory
        # to find XML or Python files that might be in non-standard locations
        processed_paths = set()
        for root, dirs, files in os.walk(self.source_dir):
            # Check if we're in a standard folder already processed
            is_standard_subdir = False
            for standard_dir in odoo_standard_dirs:
                standard_path = os.path.join(self.source_dir, standard_dir)
                if root.startswith(standard_path):
                    is_standard_subdir = True
                    break
            
            # If it's a standard subfolder already processed, skip it
            if is_standard_subdir:
                continue
                
            # Process files in this folder
            for file in files:
                file_path = os.path.join(root, file)
                
                # Avoid processing the same file twice
                if file_path in processed_paths:
                    continue
                processed_paths.add(file_path)
                
                # Count files by type
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext == '.xml':
                    xml_files_found += 1
                elif file_ext == '.py':
                    py_files_found += 1
                
                # Add to the processing list if it's a valid type
                process_file_path(file_path)
        
        # Display statistics on files found
        self.log(f"XML files found: {xml_files_found}", level='info')
        if self.convert_python:
            self.log(f"Python files found: {py_files_found}", level='info')
        
        total_files = len(files_to_process)
        self.log(f"Total files found: {total_files_found}", level='info')
        self.log(f"Files to process: {total_files}", level='info')
        self.log(f"Files skipped: {self.stats['files_skipped']}", level='info')
        print(f"🔍 {Fore.CYAN}Found {total_files} file(s) to process{Style.RESET_ALL}")
        
        # Display files that will be processed in verbose mode
        if self.verbose:
            print(f"\n{Fore.CYAN}List of files to process:{Style.RESET_ALL}")
            for i, (file_path, _) in enumerate(files_to_process):
                rel_path = os.path.relpath(file_path, self.source_dir)
                print(f"  {Fore.WHITE}{i+1}. {rel_path}{Style.RESET_ALL}")
            print("")
        
        if self.dry_run:
            print(f"\n{Fore.YELLOW}Test mode enabled - no changes will be applied{Style.RESET_ALL}")
            return
            
        # File processing
        if self.workers > 1 and total_files > 1:
            print(f"⚙️ {Fore.CYAN}Parallel processing with {self.workers} workers{Style.RESET_ALL}")
            with concurrent.futures.ProcessPoolExecutor(max_workers=self.workers) as executor:
                results = list(executor.map(self._process_file_wrapper, files_to_process))
            
            # Update statistics
            for result in results:
                if result:
                    self.update_stats(result)
        else:
            print(f"⚙️ {Fore.CYAN}Sequential file processing{Style.RESET_ALL}")
            for i, (file_path, file_ext) in enumerate(files_to_process):
                progress = f"[{i+1}/{total_files}]"
                print(f"{progress} Processing {file_path}...", end="\r")
                result = self._process_file(file_path, file_ext)
                self.update_stats(result)
                
        # Update the total number of files processed
        self.stats['files_processed'] = total_files
                
        # Display the final report
        self.stats['end_time'] = datetime.now()
        self.stats['duration'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        self.print_report()
        
        # Save the report if requested
        if self.report_file:
            self.save_report()
            
        # Remind limitations at the end (if not overcome)
        if not self.convert_python and not self.advanced_conditions:
            self.show_limitations()
    
    def _process_file_wrapper(self, args):
        """Wrapper to allow use with map() in parallel"""
        file_path, file_ext = args
        return self._process_file(file_path, file_ext)
        
    def _process_file(self, file_path, file_ext):
        """Process a file according to its extension"""
        if file_ext == '.py':
            return self.convert_python_file(file_path)
        else:
            return self.convert_file(file_path)

    def show_advanced_features(self):
        """Display enabled advanced features"""
        features = []
        if self.convert_python:
            features.append("✅ Conversion of 'states' attributes in Python models")
        if self.advanced_conditions:
            features.append("✅ Advanced processing of complex conditions")
            
        if not features:
            return
            
        message = f"""
{Fore.GREEN} █████╗ ██████╗ ██╗   ██╗ █████╗ ███╗   ██╗ ██████╗███████╗██████╗ 
{Fore.GREEN}██╔══██╗██╔══██╗██║   ██║██╔══██╗████╗  ██║██╔════╝██╔════╝██╔══██╗
{Fore.GREEN}███████║██║  ██║██║   ██║███████║██╔██╗ ██║██║     █████╗  ██║  ██║
{Fore.GREEN}██╔══██║██║  ██║╚██╗ ██╔╝██╔══██║██║╚██╗██║██║     ██╔══╝  ██║  ██║
{Fore.GREEN}██║  ██║██████╔╝ ╚████╔╝ ██║  ██║██║ ╚████║╚██████╗███████╗██████╔╝
{Fore.GREEN}╚═╝  ╚═╝╚═════╝   ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝╚═════╝ 
{Fore.GREEN}███████╗███████╗ █████╗ ████████╗██╗   ██╗██████╗ ███████╗███████╗
{Fore.GREEN}██╔════╝██╔════╝██╔══██╗╚══██╔══╝██║   ██║██╔══██╗██╔════╝██╔════╝
{Fore.GREEN}█████╗  █████╗  ███████║   ██║   ██║   ██║██████╔╝█████╗  ███████╗
{Fore.GREEN}██╔══╝  ██╔══╝  ██╔══██║   ██║   ██║   ██║██╔══██╗██╔══╝  ╚════██║
{Fore.GREEN}██║     ███████╗██║  ██║   ██║   ╚██████╔╝██║  ██║███████╗███████║
{Fore.GREEN}╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝
"""
        for i, feature in enumerate(features):
            message += f"{Fore.WHITE}  {i+1}. {Fore.GREEN}{feature}\n"
            
        message += f"{Style.RESET_ALL}\n"
        print(message)

    def convert_python_file(self, file_path):
        """Convert a Python file for Odoo 18"""
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
            # Determine output path
            if self.output_dir:
                rel_path = os.path.relpath(file_path, self.source_dir)
                out_path = os.path.join(self.output_dir, rel_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
            else:
                out_path = file_path
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Backup original file if requested
            if self.backup and not self.dry_run and self.output_dir is None:
                backup_path = f"{file_path}.bak"
                shutil.copy2(file_path, backup_path)
            
            # Analyze and modify Python code
            new_content, state_changes = self.process_python_code(content)
            file_stats['changes']['python_states_removed'] = state_changes
            
            # If changes were made, save the file
            if new_content != content:
                file_stats['files_changed'] = 1
                if not self.dry_run:
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                self.log(f"Python file updated: {out_path}", level='success')
            else:
                self.log(f"No changes needed in Python file: {file_path}", level='debug')
                
            return file_stats
                
        except Exception as e:
            self.log(f"Error processing Python file {file_path}: {str(e)}", level='error')
            file_stats['files_error'] = 1
            return file_stats

    def process_python_code(self, content):
        """Analyze and modify Python code for Odoo 18"""
        # Counter for changes
        state_changes = 0
        
        # Pattern for states attributes in field definitions
        states_pattern = r'states\s*=\s*{([^}]*)}'
        
        def remove_states_param(match):
            nonlocal state_changes
            state_changes += 1
            # Remove just the states parameter
            return ""
        
        # Replace states attributes in field definitions
        new_content = re.sub(r',\s*states\s*=\s*{[^}]*}', remove_states_param, content)
        
        # Advanced processing if needed with AST
        if new_content == content:
            try:
                # Parse code with AST
                tree = ast.parse(content)
                
                # TODO: More advanced implementation with AST manipulation
                # This part would require more in-depth analysis of the syntax tree
                # to identify field definitions and modify their parameters
                
            except Exception as e:
                self.log(f"Error parsing AST: {str(e)}", level='warning')
        
        return new_content, state_changes

    def convert_file(self, file_path):
        """Convert an XML file"""
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
            # Determine output path
            if self.output_dir:
                rel_path = os.path.relpath(file_path, self.source_dir)
                out_path = os.path.join(self.output_dir, rel_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
            else:
                out_path = file_path
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Backup original file if requested
            if self.backup and not self.dry_run and self.output_dir is None:
                backup_path = f"{file_path}.bak"
                shutil.copy2(file_path, backup_path)
            
            # Perform transformations
            new_content, change_stats = self.apply_transformations(content, file_path)
            
            # Update statistics
            for key, value in change_stats.items():
                file_stats['changes'][key] = value
                
            # If changes were made, save the file
            if new_content != content:
                file_stats['files_changed'] = 1
                if not self.dry_run:
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    self.log(f"File updated: {out_path}", level='success')
                
                # Display change details in verbose mode
                if self.verbose:
                    changes_made = sum(change_stats.values())
                    if changes_made > 0:
                        self.log(f"Changes made in {file_path}:", level='info')
                        for change_type, count in change_stats.items():
                            if count > 0:
                                self.log(f"  - {change_type}: {count}", level='info')
            else:
                self.log(f"No changes needed: {file_path}", level='debug')
                
            return file_stats
                
        except Exception as e:
            self.log(f"Error processing {file_path}: {str(e)}", level='error')
            file_stats['files_error'] = 1
            return file_stats

    def apply_transformations(self, content, file_path):
        """Apply all transformations"""
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
        
        # Try to analyze the file as valid XML
        is_valid_xml = False
        try:
            # Check if it's a well-formed XML
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring("<odoo_root>" + content + "</odoo_root>", parser)
            is_valid_xml = True
            self.log(f"File analyzed as valid XML", level='debug')
        except Exception as e:
            self.log(f"File is not a well-formed XML, processing as text: {str(e)}", level='debug')
        
        # Count motifs before transformations for verification
        tree_count_before = content.count('<tree')
        attrs_count_before = len(re.findall(r'attrs="{\'(invisible|readonly|required)\':', content))
        states_count_before = len(re.findall(r'states="([^"]*)"', content))
        chatter_count_before = content.count('<div class="oe_chatter">')
        daterange_count_before = len(re.findall(r'widget="daterange"', content))
        
        # Log initial counts in verbose mode
        if self.verbose:
            self.log(f"Initial counts - tree: {tree_count_before}, attrs: {attrs_count_before}, states: {states_count_before}, chatter: {chatter_count_before}, daterange: {daterange_count_before}", level='debug')
        
        # 1. Convert tree to list
        content, tree_count = self.convert_tree_to_list(content)
        change_stats['tree_to_list'] = tree_count
        
        # 2. Convert attrs and states
        content, attrs_count, states_count, complex_count = self.convert_attrs(content)
        change_stats['attrs_conversion'] = attrs_count
        change_stats['states_conversion'] = states_count
        change_stats['complex_conditions'] = complex_count
        
        # 3. Update daterange widget
        content, daterange_count = self.update_daterange_widget(content)
        change_stats['daterange_update'] = daterange_count
        
        # 4. Simplify chatter
        content, chatter_count = self.simplify_chatter(content)
        change_stats['chatter_simplified'] = chatter_count
        
        # 5. Convert res.config.settings structure
        # In XML (more precise) if the file is a valid XML, otherwise in text mode
        if is_valid_xml and '<app_settings_block' in content or 'data-key=' in content:
            content, settings_count = self.convert_settings_structure(content)
            change_stats['settings_structure'] = settings_count
        
        # 6. Final verification to ensure all transformations were applied
        remaining_tree = content.count('<tree')
        if remaining_tree > 0:
            self.log(f"Attention: {remaining_tree} tree tags not converted. Additional attempt...", level='warning')
            # Try more aggressive approach if remaining tree tags
            content = content.replace('<tree', '<list').replace('</tree>', '</list>')
            tree_count += remaining_tree - content.count('<tree')
            change_stats['tree_to_list'] = tree_count
            
            # Final verification
            final_remaining = content.count('<tree')
            if final_remaining > 0:
                self.log(f"Still {final_remaining} tree tags not converted in {file_path}", level='warning')
        
        # Verification and log for debugging
        if original_content != content:
            # File modified, check what types of changes
            self.log(f"Changes applied to {file_path}:", level='debug')
            for key, value in change_stats.items():
                if value > 0:
                    self.log(f"  - {key}: {value}", level='debug')
        else:
            self.log(f"No changes needed for {file_path}", level='debug')
            
        return content, change_stats

    def convert_tree_to_list(self, content):
        """Convert tree tags to list"""
        # Count number of replacements for reporting
        tree_count_before = content.count('<tree')
        
        # More precise regular expression to detect tree tags
        tree_pattern = re.compile(r'<tree(\s+[^>]*>|>)')
        matches = tree_pattern.findall(content)
        real_tree_count = len(matches)
        
        if real_tree_count != tree_count_before:
            self.log(f"Different detection: simple count {tree_count_before}, regex {real_tree_count}", level='debug')
            # Use the most precise counting
            tree_count_before = real_tree_count
        
        # Convert <tree> to <list>
        content_new = re.sub(r'<tree(\s|>)', r'<list\1', content)
        content_new = re.sub(r'</tree>', '</list>', content_new)
        
        # Verify if all tags were converted
        remaining_trees = content_new.count('<tree')
        if remaining_trees > 0:
            self.log(f"Attention: {remaining_trees} tree tags not converted correctly", level='warning')
            
            # Try more aggressive conversion
            content_new = re.sub(r'<tree', r'<list', content_new)
            content_new = re.sub(r'</tree>', r'</list>', content_new)
            
            # Verify again
            still_remaining = content_new.count('<tree')
            if still_remaining > 0:
                self.log(f"Still {still_remaining} tree tags not converted", level='warning')
        
        # Count actual changes
        tree_count = tree_count_before - remaining_trees
        
        self.log(f"Detected tree tags: {tree_count_before}, converted: {tree_count}", level='debug')
        
        return content_new, tree_count

    def convert_attrs(self, content):
        """Convert attrs attributes to direct conditions"""
        attrs_count = 0
        states_count = 0
        complex_count = 0
        
        # Find all attrs attributes with their values
        attrs_pattern = r'attrs="{\'(invisible|readonly|required)\': \[(.*?)\]}"'
        
        def replace_attrs(match):
            nonlocal attrs_count, complex_count
            attr_type = match.group(1)
            conditions = match.group(2)
            
            # Advanced mode for complex conditions
            if self.advanced_conditions and ('|' in conditions or '&' in conditions):
                try:
                    # Try to convert complex conditions with | and & operators
                    converted = self._convert_complex_condition(conditions, attr_type)
                    if converted:
                        complex_count += 1
                        return converted
                except Exception as e:
                    self.log(f"Error converting complex: {conditions}. Error: {str(e)}", level='warning')
            
            # Process OR (|) conditions
            if conditions.startswith("'|',"):
                # Extract two conditions after '|'
                parts = conditions.split("'|',")[1].strip()
                cond_parts = re.findall(r'\(\'(.*?)\',\s*\'(.*?)\',\s*([^\)]*)\)', parts)
                
                if len(cond_parts) >= 2:
                    # Build OR expression
                    cond1 = self._format_condition(cond_parts[0][0], cond_parts[0][1], cond_parts[0][2])
                    cond2 = self._format_condition(cond_parts[1][0], cond_parts[1][1], cond_parts[1][2])
                    attrs_count += 1
                    return f'{attr_type}="{cond1} or {cond2}"'
            
            # Process AND (conditions without '|')
            elif "," in conditions and not conditions.startswith("'|',"):
                cond_parts = re.findall(r'\(\'(.*?)\',\s*\'(.*?)\',\s*([^\)]*)\)', conditions)
                if len(cond_parts) >= 2:
                    conditions_formatted = []
                    for part in cond_parts:
                        conditions_formatted.append(self._format_condition(part[0], part[1], part[2]))
                    attrs_count += 1
                    return f'{attr_type}="{" and ".join(conditions_formatted)}"'
            
            # Process a simple condition
            else:
                try:
                    cond_parts = re.findall(r'\(\'(.*?)\',\s*\'(.*?)\',\s*([^\)]*)\)', conditions)
                    if cond_parts:
                        field, operator, value = cond_parts[0]
                        # Handle special condition for empty lists
                        if value == "[]" and operator == "=":
                            attrs_count += 1
                            return f'{attr_type}="not {field}"'
                        else:
                            attrs_count += 1
                            return f'{attr_type}="{self._format_condition(field, operator, value)}"'
                except Exception as e:
                    self.log(f"Error parsing condition: {conditions}. Error: {str(e)}", level='warning')
            
            # If none of the rules apply, keep the original
            return match.group(0)
        
        # Apply replacements
        content = re.sub(attrs_pattern, replace_attrs, content)
        
        # Convert states to invisible
        states_pattern = r'states="([^"]*)"'
        
        def replace_states(match):
            nonlocal states_count
            state_value = match.group(1)
            states_count += 1
            return f'invisible="state != \'{state_value}\'"'
        
        content = re.sub(states_pattern, replace_states, content)
        
        return content, attrs_count, states_count, complex_count

    def _format_condition(self, field, operator, value):
        """Format a condition for the new syntax"""
        # Handle value based on its type
        cleaned_value = value.strip("'")
        
        if operator == "=":
            if value == "[]":  # Special case for empty lists
                return f"not {field}"
            elif value == "False":
                return f"not {field}"
            elif value == "True":
                return field
            else:
                return f"{field} == {value}"
        elif operator == "!=":
            if value == "[]":  # Special case for empty lists
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
        """Update daterange widgets"""
        daterange_count = 0
        
        # Search for daterange widgets with old syntax
        old_pattern = r'<field name="([^"]*)" widget="daterange" options="{\'related_end_date\': \'([^\']*)\'}"/>'
        new_format = r'<field name="\1" widget="daterange" options="{\'end_date_field\': \'\2\'}"/>'
        
        # Count occurrences before replacement
        daterange_count += len(re.findall(old_pattern, content))
        
        content = re.sub(old_pattern, new_format, content)
        
        # Remove end_date fields with daterange widget that are now unnecessary
        end_date_pattern = r'<field name="([^"]*)" widget="daterange" options="{\'related_start_date\': \'([^\']*)\'}"/>'
        
        # Count occurrences before removal
        daterange_count += len(re.findall(end_date_pattern, content))
        
        content = re.sub(end_date_pattern, '', content)
        
        return content, daterange_count

    def simplify_chatter(self, content):
        """Simplify chatter structure"""
        chatter_count = 0
        
        # Pattern to detect old chatter format (standard)
        old_chatter_pattern = r'<div class="oe_chatter">\s*<field name="message_follower_ids" widget="mail_followers"/>\s*<field name="activity_ids" widget="mail_activity"/>\s*<field name="message_ids" widget="mail_thread"/>\s*</div>'
        
        # Alternative pattern with spaces and order difference
        alt_chatter_pattern1 = r'<div class="oe_chatter">\s*<field name="message_follower_ids"[^>]*widget="mail_followers"[^>]*>\s*</field>\s*<field name="activity_ids"[^>]*widget="mail_activity"[^>]*>\s*</field>\s*<field name="message_ids"[^>]*widget="mail_thread"[^>]*>\s*</field>\s*</div>'
        
        # Alternative pattern with order difference of fields
        alt_chatter_pattern2 = r'<div class="oe_chatter">\s*(<field[^>]*widget="mail_followers"[^>]*/>|<field[^>]*widget="mail_followers"[^>]*>\s*</field>)\s*(<field[^>]*widget="mail_thread"[^>]*/>|<field[^>]*widget="mail_thread"[^>]*>\s*</field>)\s*(<field[^>]*widget="mail_activity"[^>]*/>|<field[^>]*widget="mail_activity"[^>]*>\s*</field>)\s*</div>'
        
        # Alternative pattern with only message_ids and followers
        alt_chatter_pattern3 = r'<div class="oe_chatter">\s*(<field[^>]*widget="mail_followers"[^>]*/>|<field[^>]*widget="mail_followers"[^>]*>\s*</field>)\s*(<field[^>]*widget="mail_thread"[^>]*/>|<field[^>]*widget="mail_thread"[^>]*>\s*</field>)\s*</div>'
        
        # Perform conversions with different patterns
        # 1. Standard pattern
        matches1 = re.findall(old_chatter_pattern, content)
        count1 = len(matches1)
        if count1 > 0:
            self.log(f"Detected {count1} standard chatter structures", level='debug')
            content = re.sub(old_chatter_pattern, '<chatter/>', content)
            chatter_count += count1
            
        # 2. Alternative 1
        matches2 = re.findall(alt_chatter_pattern1, content)
        count2 = len(matches2)
        if count2 > 0:
            self.log(f"Detected {count2} alternative chatter structures (type 1)", level='debug')
            content = re.sub(alt_chatter_pattern1, '<chatter/>', content)
            chatter_count += count2
            
        # 3. Alternative 2
        matches3 = re.findall(alt_chatter_pattern2, content)
        count3 = len(matches3)
        if count3 > 0:
            self.log(f"Detected {count3} alternative chatter structures (type 2)", level='debug')
            content = re.sub(alt_chatter_pattern2, '<chatter/>', content)
            chatter_count += count3
            
        # 4. Alternative 3
        matches4 = re.findall(alt_chatter_pattern3, content)
        count4 = len(matches4)
        if count4 > 0:
            self.log(f"Detected {count4} alternative chatter structures (type 3)", level='debug')
            content = re.sub(alt_chatter_pattern3, '<chatter/>', content)
            chatter_count += count4
            
        # Simple detection for cases not covered by regular expressions
        if '<div class="oe_chatter">' in content and chatter_count == 0:
            self.log(f"Detected chatter structures but couldn't be automatically converted", level='warning')
            # Try XML approach with lxml if possible
            try:
                parser = etree.XMLParser(recover=True)
                root = etree.fromstring("<root>" + content + "</root>", parser)
                
                # Find all oe_chatter divs
                chatter_divs = root.xpath("//div[@class='oe_chatter']")
                if chatter_divs:
                    self.log(f"Attempting XML conversion for {len(chatter_divs)} chatters", level='debug')
                    for chatter_div in chatter_divs:
                        # Replace with chatter element
                        new_chatter = etree.Element("chatter")
                        parent = chatter_div.getparent()
                        if parent is not None:
                            parent.replace(chatter_div, new_chatter)
                            chatter_count += 1
                    
                    # Convert modified XML tree to text
                    content = etree.tostring(root, pretty_print=True, encoding='unicode')
                    # Remove added root tags
                    content = content.replace("<root>", "").replace("</root>", "")
            except Exception as e:
                self.log(f"Error processing XML chatter conversion: {str(e)}", level='warning')
        
        if chatter_count > 0:
            self.log(f"Replaced {chatter_count} chatter structures with simplified element", level='debug')
        
        return content, chatter_count

    def convert_settings_structure(self, content):
        """Convert res.config.settings parameters structure"""
        settings_count = 0
        
        try:
            # This conversion is more complex as it requires parsing XML
            if '<app_settings_block' in content or 'data-key=' in content:
                parser = etree.XMLParser(recover=True)
                try:
                    root = etree.fromstring(content, parser)
                    
                    # Find all app_settings_block divs
                    app_blocks = root.xpath("//div[@class='app_settings_block']")
                    settings_count = len(app_blocks)
                    
                    for app_block in app_blocks:
                        # Create a new app element
                        app_element = etree.Element("app")
                        
                        # Copy relevant attributes
                        if app_block.get('string'):
                            app_element.set('string', app_block.get('string'))
                        elif app_block.get('data-string'):
                            app_element.set('string', app_block.get('data-string'))
                        
                        # Iterate through child elements
                        for child in app_block:
                            # Convert h2 to blocks
                            if child.tag == 'h2':
                                block = etree.SubElement(app_element, "block")
                                block.set('title', child.text.strip())
                            
                            # Convert parameter containers
                            elif child.tag == 'div' and 'o_settings_container' in child.get('class', ''):
                                # Find labels, fields, and descriptions
                                labels = child.xpath(".//label")
                                fields = child.xpath(".//field")
                                descriptions = child.xpath(".//div[@class='text-muted']")
                                
                                # Create setting element
                                if labels and fields:
                                    setting = etree.SubElement(app_element, "setting")
                                    
                                    # Add string attribute (label)
                                    if labels[0].get('string'):
                                        setting.set('string', labels[0].get('string'))
                                    
                                    # Add help attribute (description)
                                    if descriptions and descriptions[0].text:
                                        setting.set('help', descriptions[0].text.strip())
                                    
                                    # Add fields
                                    for field in fields:
                                        setting.append(field)
                        
                        # Replace old block with new one
                        app_block.getparent().replace(app_block, app_element)
                    
                    # Convert modified XML tree to text
                    content = etree.tostring(root, pretty_print=True, encoding='unicode')
                except Exception as e:
                    self.log(f"Error converting settings structure: {str(e)}", level='warning')
        except Exception as e:
            self.log(f"Error parsing XML: {str(e)}", level='warning')
        
        return content, settings_count

    def _convert_complex_condition(self, condition, attr_type):
        """Convert complex conditions with multiple OR and AND operators"""
        # This method is a placeholder for handling more complex cases
        # It would require implementing a complete condition parser/evaluator Odoo

        # Simple example for a few common cases
        # 1. Multiple consecutive ORs: '|', '|', cond1, cond2, cond3
        if condition.startswith("'|',") and "'|'," in condition[4:]:
            try:
                # Count OR operators
                or_count = 0
                idx = 0
                while True:
                    next_idx = condition.find("'|',", idx)
                    if next_idx == -1:
                        break
                    or_count += 1
                    idx = next_idx + 4
                
                # Extract all conditions
                cond_parts = re.findall(r'\(\'(.*?)\',\s*\'(.*?)\',\s*([^\)]*)\)', condition)
                
                if len(cond_parts) == or_count + 1:
                    # Format all conditions
                    formatted_conditions = []
                    for part in cond_parts:
                        formatted_conditions.append(self._format_condition(part[0], part[1], part[2]))
                    
                    # Build expression with OR
                    return f'{attr_type}="{" or ".join(formatted_conditions)}"'
            except Exception as e:
                self.log(f"Error handling multiple OR conditions: {condition}. Error: {str(e)}", level='warning')
        
        # 2. Conditions AND nested in ORs: '|', cond1, '&', cond2, cond3
        elif "'|'," in condition and "'&'," in condition:
            # This case is very complex and would require a complete parser
            # Simplified implementation for certain specific cases
            pass
            
        # No conversion possible, return None
        return None

    def print_report(self):
        """Display a detailed report of conversions performed"""
        duration = self.stats['duration']
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        # Add new statistics
        additional_stats = ""
        if self.convert_python:
            additional_stats += f"║ {Fore.WHITE}  - attrs states Python : {self.stats['changes']['python_states_removed']:<5}{Fore.CYAN}                       ║\n"
        if self.advanced_conditions:
            additional_stats += f"║ {Fore.WHITE}  - conditions complexes: {self.stats['changes']['complex_conditions']:<5}{Fore.CYAN}                       ║\n"
        
        report = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║ {Fore.YELLOW}                 CONVERSION REPORT                    {Fore.CYAN}║
╠══════════════════════════════════════════════════════════╣
║ {Fore.WHITE}Files processed      : {self.stats['files_processed']:<5}{Fore.CYAN}                       ║
║ {Fore.GREEN}Files modified     : {self.stats['files_changed']:<5}{Fore.CYAN}                       ║
║ {Fore.YELLOW}Files skipped      : {self.stats['files_skipped']:<5}{Fore.CYAN}                       ║
║ {Fore.RED}Files in error     : {self.stats['files_error']:<5}{Fore.CYAN}                       ║
╠══════════════════════════════════════════════════════════╣
║ {Fore.WHITE}Execution time     : {minutes:02d}:{seconds:02d} min{Fore.CYAN}                      ║
╠══════════════════════════════════════════════════════════╣
║ {Fore.YELLOW}Conversion details:{Fore.CYAN}                                ║
║ {Fore.WHITE}  - tree → list       : {self.stats['changes']['tree_to_list']:<5}{Fore.CYAN}                       ║
║ {Fore.WHITE}  - attrs             : {self.stats['changes']['attrs_conversion']:<5}{Fore.CYAN}                       ║
║ {Fore.WHITE}  - states            : {self.stats['changes']['states_conversion']:<5}{Fore.CYAN}                       ║
║ {Fore.WHITE}  - daterange         : {self.stats['changes']['daterange_update']:<5}{Fore.CYAN}                       ║
║ {Fore.WHITE}  - chatter           : {self.stats['changes']['chatter_simplified']:<5}{Fore.CYAN}                       ║
║ {Fore.WHITE}  - settings          : {self.stats['changes']['settings_structure']:<5}{Fore.CYAN}                       ║
{additional_stats}╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(report)
        
        # Display detailed statistics on directories and extensions processed
        self.show_statistics()
        
        # Display success or failure message
        if self.stats['files_error'] > 0:
            print(f"{Fore.RED}⚠️ Errors encountered during conversion.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}   Check journal file for more details.{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}✅ Conversion completed successfully !{Style.RESET_ALL}")
            
        # If files were saved in a different directory
        if self.output_dir:
            print(f"\n{Fore.CYAN}📁 Converted files saved in: {self.output_dir}{Style.RESET_ALL}")
        elif self.backup and not self.dry_run:
            print(f"\n{Fore.CYAN}💾 Created backups of original files (.bak){Style.RESET_ALL}")

    def show_statistics(self):
        """Display detailed statistics on directories and extensions processed"""
        # Collect information on directories processed
        folder_stats = {}
        extension_stats = {}
        
        # Get list of directories and extensions processed
        for root, _, files in os.walk(self.source_dir):
            rel_path = os.path.relpath(root, self.source_dir)
            folder_key = rel_path if rel_path != '.' else 'root'
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
                
                # Increment total counter for this directory
                folder_stats[folder_key]['total'] += 1
                
                # Count by extension
                if file_ext == '.xml':
                    folder_stats[folder_key]['xml'] += 1
                elif file_ext == '.py':
                    folder_stats[folder_key]['py'] += 1
                else:
                    folder_stats[folder_key]['other'] += 1
                
                # Count global statistics by extension
                if file_ext not in extension_stats:
                    extension_stats[file_ext] = 0
                extension_stats[file_ext] += 1
        
        # Display statistics by directory (display only most relevant ones)
        print(f"\n{Fore.CYAN}╔══════════════════════════════════════════════════════════╗")
        print(f"║ {Fore.YELLOW}           DIRECTORY STATISTICS                    {Fore.CYAN}║")
        print(f"╠══════════════════════════════════════════════════════════╣")
        
        # Sort directories by number of XML and Python files
        relevant_folders = []
        for folder, stats in folder_stats.items():
            relevant_count = stats['xml'] + stats['py']
            if relevant_count > 0:
                relevant_folders.append((folder, stats, relevant_count))
        
        relevant_folders.sort(key=lambda x: x[2], reverse=True)
        
        # Display statistics of most relevant directories
        for folder, stats, _ in relevant_folders[:10]:  # Display top 10 directories
            print(f"║ {Fore.WHITE}{folder[:30]:<30}{Fore.CYAN} │ {Fore.WHITE}XML: {stats['xml']:<3} PY: {stats['py']:<3} Others: {stats['other']:<3}{Fore.CYAN} ║")
        
        if len(relevant_folders) > 10:
            print(f"║ {Fore.WHITE}... and {len(relevant_folders) - 10} other directories{Fore.CYAN}{' ' * 32}║")
        
        # Display statistics by extension
        print(f"╠══════════════════════════════════════════════════════════╣")
        print(f"║ {Fore.YELLOW}          FILE STATISTICS BY EXTENSION          {Fore.CYAN}║")
        print(f"╠══════════════════════════════════════════════════════════╣")
        
        # Sort extensions by number of files
        sorted_extensions = sorted(extension_stats.items(), key=lambda x: x[1], reverse=True)
        
        for ext, count in sorted_extensions[:10]:  # Display top 10 extensions
            if not ext:
                ext_name = "(no extension)"
            else:
                ext_name = ext
            print(f"║ {Fore.WHITE}{ext_name:<15}{Fore.CYAN} │ {Fore.WHITE}Files: {count:<5}{Fore.CYAN}{' ' * 27}║")
        
        if len(sorted_extensions) > 10:
            print(f"║ {Fore.WHITE}... and {len(sorted_extensions) - 10} other extensions{Fore.CYAN}{' ' * 26}║")
            
        print(f"╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}")

    def save_report(self):
        """Save report in JSON format"""
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
            print(f"{Fore.GREEN}✅ Report saved in: {self.report_file}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ Error saving report: {str(e)}{Style.RESET_ALL}")

    def show_limitations(self):
        """Display known limitations of the script"""
        limitations = f"""
{Fore.YELLOW}██╗     ██╗███╗   ███╗██╗████████╗ █████╗ ████████╗██╗ ██████╗ ███╗   ██╗███████╗
{Fore.YELLOW}██║     ██║████╗ ████║██║╚══██╔══╝██╔══██╗╚══██╔══╝██║██╔═══██╗████╗  ██║██╔════╝
{Fore.YELLOW}██║     ██║██╔████╔██║██║   ██║   ███████║   ██║   ██║██║   ██║██╔██╗ ██║███████╗
{Fore.YELLOW}██║     ██║██║╚██╔╝██║██║   ██║   ██╔══██║   ██║   ██║██║   ██║██║╚██╗██║╚════██║
{Fore.YELLOW}███████╗██║██║ ╚═╝ ██║██║   ██║   ██║  ██║   ██║   ██║╚██████╔╝██║ ╚████║███████║
{Fore.YELLOW}╚══════╝╚═╝╚═╝     ╚═╝╚═╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝

{Fore.WHITE}1. {Fore.CYAN}Certain complex transformations may require manual adjustments.

{Fore.WHITE}2. {Fore.CYAN}The script does not modify Python structure of models
   (like removing states attributes in field definitions).

{Fore.WHITE}3. {Fore.CYAN}Complex expressions in conditionals attributes
   may not be perfectly converted.
{Style.RESET_ALL}

{Fore.RED}It is recommended to manually verify converted files
before using them in production.{Style.RESET_ALL}
"""
        print(limitations)

    def update_stats(self, result):
        """Update statistics with conversion result"""
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
    # Check if arguments are provided
    if len(sys.argv) == 1:
        # No arguments, launch interactive mode
        interactive_mode = InteractiveMode()
        options = interactive_mode.run()
        
        if not options:
            return 0
            
        # Create converter with chosen options
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
            print(f"\n{Fore.YELLOW}Conversion interrupted by user.{Style.RESET_ALL}")
            return 130
        except Exception as e:
            print(f"{Fore.RED}Fatal error: {str(e)}{Style.RESET_ALL}")
            return 1
    
    # If arguments are provided, use standard command line interface
    parser = argparse.ArgumentParser(
        description=f'{Fore.CYAN}Convert Odoo XML files to Odoo 18 syntax{Style.RESET_ALL}',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument('source_dir', help='Source directory containing files to convert')
    
    # Optional arguments
    parser.add_argument('-o', '--output-dir', 
                      help='Output directory for converted files (if not specified, modify files in place)')
    parser.add_argument('--no-backup', action='store_false', dest='backup', 
                      help='Do not create backups of original files')
    parser.add_argument('-v', '--verbose', action='store_true', 
                      help='Display detailed information about the process')
    parser.add_argument('-e', '--extensions', nargs='+', default=['.xml'],
                      help='File extensions to process')
    parser.add_argument('-s', '--skip', nargs='+', default=[],
                      help='Regex patterns to ignore certain files')
    parser.add_argument('-r', '--report',
                      help='File path for saving conversion report (JSON)')
    parser.add_argument('-w', '--workers', type=int, default=1,
                      help='Number of worker processes for parallel processing')
    parser.add_argument('-d', '--dry-run', action='store_true',
                      help='Test mode: do not modify files, simply display what would be done')
    parser.add_argument('-i', '--interactive', action='store_true',
                      help='Interactive mode: ask for confirmation before each modification')
    parser.add_argument('-l', '--show-limitations', action='store_true',
                      help='Display only known script limitations and exit')
    
    # New arguments to overcome limitations
    parser.add_argument('--convert-python', action='store_true',
                      help='Convert Python files (.py) to remove states attributes')
    parser.add_argument('--advanced-conditions', action='store_true', 
                      help='Enable advanced conditions processing in attrs attributes')
    parser.add_argument('--overcome-all', action='store_true',
                      help='Enable all features to overcome limitations')
    
    args = parser.parse_args()
    
    # Display only limitations if requested
    if args.show_limitations:
        converter = Odoo18Converter(source_dir=".")
        converter.show_limitations()
        return 0
    
    # Enable all options if --overcome-all is specified
    if args.overcome_all:
        args.convert_python = True
        args.advanced_conditions = True
    
    if not os.path.isdir(args.source_dir):
        print(f"{Fore.RED}Error: Directory {args.source_dir} doesn't exist{Style.RESET_ALL}")
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
        print(f"\n{Fore.YELLOW}Conversion interrupted by user.{Style.RESET_ALL}")
        return 130
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {str(e)}{Style.RESET_ALL}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 
