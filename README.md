# Odoo 18 - Syntax Converter

![Odoo 18 converter interface](Screenshot%2025-05-30%021259.png)

This Python script automatically converts Odoo files (mainly XML) from the old syntax to the new Odoo 18 syntax.

## Features

The script performs the following conversions:

1. **XML tag conversion**: Replaces `<tree>` with `<list>`
2. **Conditional attribute simplification**: Converts `attrs` and `states` attributes to the new simplified syntax
3. **Daterange widget update**: Migrates to the new daterange widget configuration
4. **Chatter simplification**: Replaces complex chatter structure with the simplified `<chatter/>` tag
5. **res.config.settings conversion**: Adapts settings page structure to the new syntax
6. **Python file conversion**: Removes `states` attributes from field definitions in Python models
7. **Advanced condition processing**: Converts complex conditions with multiple OR/AND operators

## Prerequisites

- Python 3.6 or higher
- lxml module (`pip install lxml`)
- colorama module (`pip install colorama`)

## Installation

```bash
pip install lxml colorama
```

## Usage

### Interactive mode

Simply run the script without arguments to use the interactive mode that will guide you step by step:

```bash
python odoo18_converter.py
```

This mode will ask you for:
1. The path to the Odoo module to convert
2. Various conversion options
3. Confirmation before starting the conversion

### Command line mode

```bash
python odoo18_converter.py path/to/module [options]
```

### Options

- `source_dir`: Path to the directory containing files to convert (required)
- `-o`, `--output-dir`: Output directory for converted files (if not specified, modifies files in place)
- `--no-backup`: Don't create backup of original files (default: backup enabled)
- `-v`, `--verbose`: Display detailed information about the process
- `-e`, `--extensions`: File extensions to process (default: .xml)
- `-s`, `--skip`: Regex patterns to ignore certain files
- `-r`, `--report`: Path to save the conversion report file (JSON)
- `-w`, `--workers`: Number of worker processes for parallel processing (default: 1)
- `-d`, `--dry-run`: Test mode - don't modify files, just show what would be done
- `-i`, `--interactive`: Interactive mode - ask for confirmation before each modification
- `-l`, `--show-limitations`: Show only known script limitations and exit

### Options to overcome limitations

- `--convert-python`: Also convert Python files (.py) to remove states attributes
- `--advanced-conditions`: Enable advanced processing of complex conditions in attrs attributes
- `--overcome-all`: Enable all features to overcome limitations

### Examples

```bash
# Interactive mode (recommended for new users)
python odoo18_converter.py

# Convert all XML files in a module
python odoo18_converter.py ./my_module/

# Convert with more information
python odoo18_converter.py ./my_module/ -v

# Convert without creating backups
python odoo18_converter.py ./my_module/ --no-backup

# Convert files with different extensions
python odoo18_converter.py ./my_module/ -e .xml .qweb

# Convert in test mode (no actual modifications)
python odoo18_converter.py ./my_module/ -d

# Save converted files to another directory
python odoo18_converter.py ./my_module/ -o ./my_module_odoo18/

# Ignore certain files
python odoo18_converter.py ./my_module/ -s "test_" "demo_"

# Parallel processing with 4 workers
python odoo18_converter.py ./my_module/ -w 4

# Generate detailed report
python odoo18_converter.py ./my_module/ -r conversion_report.json

# Convert with Python file analysis (remove states)
python odoo18_converter.py ./my_module/ --convert-python

# Enable advanced complex condition processing
python odoo18_converter.py ./my_module/ --advanced-conditions

# Enable all advanced features
python odoo18_converter.py ./my_module/ --overcome-all
```

## How it works

The script recursively scans the specified directory and its subdirectories, searches for all files with the indicated extensions, and applies the necessary transformations to make the code compatible with Odoo 18.

For each modified file, a backup is created with the `.bak` extension (unless the `--no-backup` option is used or an output directory is specified with `--output-dir`).

## Advanced features

### Python file conversion

The `--convert-python` option allows the script to analyze and modify Python files to remove `states` attributes from field definitions, like this:

```python
# Before
date = fields.Date(
    string='Date',
    required=True,
    states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
    copy=False,
)

# After
date = fields.Date(
    string='Date',
    required=True,
    copy=False,
)
```

### Complex condition processing

The `--advanced-conditions` option activates advanced algorithms to handle more complex conditions in XML attributes, especially those using multiple nested logical operators (`|` and `&`).

```xml
<!-- Before (very complex) -->
<field name="project_id" attrs="{'invisible': ['|', '|', '&', ('state', '=', 'done'), ('type', '=', 'service'), ('type', '=', 'consu'), ('type', '=', 'product')]}"/>

<!-- After -->
<field name="project_id" invisible="(state == 'done' and type == 'service') or type == 'consu' or type == 'product'"/>
```

## Interactive mode

The script now offers an interactive mode that guides the user step by step through the conversion process:

1. **Directory selection**: The script first asks for the path to the Odoo module to convert
2. **Option configuration**: It then offers to configure the various conversion options
3. **Confirmation**: Before starting the conversion, a summary of options is displayed for confirmation

This mode is particularly useful for users discovering the tool or who prefer a guided approach rather than specifying all options on the command line.

## Supported changes

### 1. From `<tree>` to `<list>`

```xml
<!-- Before -->
<tree>
    <field name="name"/>
</tree>

<!-- After -->
<list>
    <field name="name"/>
</list>
```

### 2. Simplified conditional attributes

```xml
<!-- Before -->
<field name="shift_id" attrs="{'invisible': [('shift_schedule', '=', [])]}"/>

<!-- After -->
<field name="shift_id" invisible="not shift_schedule"/>
```

### 3. Daterange widget

```xml
<!-- Before -->
<field name="start_date" widget="daterange" options="{'related_end_date': 'end_date'}"/>
<field name="end_date" widget="daterange" options="{'related_start_date': 'start_date'}"/>

<!-- After -->
<field name="start_date" widget="daterange" options="{'end_date_field': 'end_date'}"/>
```

### 4. Simplified chatter

```xml
<!-- Before -->
<div class="oe_chatter">
    <field name="message_follower_ids" widget="mail_followers"/>
    <field name="activity_ids" widget="mail_activity"/>
    <field name="message_ids" widget="mail_thread"/>
</div>

<!-- After -->
<chatter/>
```

### 5. Simplified res.config structure

```xml
<!-- Before -->
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

<!-- After -->
<app string="Application Settings">
    <block title="Example Settings">
        <setting string="Example Setting" help="Description for the example setting">
            <field name="example_setting"/>
        </setting>
    </block>
</app>
```

## New features

1. **Colorized interface**: Uses colors in the terminal for better readability
2. **Detailed reporting**: Complete statistics on performed conversions
3. **Parallel mode**: Multi-process processing for faster conversion
4. **Test mode**: Ability to simulate conversions without modifying files
5. **Preservation mode**: Save converted files to a separate directory
6. **Advanced filtering**: Ignore certain files based on regex patterns
7. **Report generation**: Export statistics in JSON format
8. **Python conversion**: Analysis and modification of Python files to remove `states` attributes
9. **Complex condition processing**: Support for conditions with multiple logical operators
10. **Interactive mode**: Guided interface to easily configure the conversion

## Remaining limitations

While the script now offers options to overcome most of the initial limitations, some very specific cases may still require manual intervention:

1. Some very customized or complex XML structures
2. Special cases of conditional attributes with very complex expressions
3. Python field definitions using non-standard approaches

It's always recommended to review the converted files, especially in complex cases.
