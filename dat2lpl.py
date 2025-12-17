#!/usr/bin/env python
"""
Copyright 2025 W. M. Martinez

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import json
import sys
import argparse
import os
from jsonschema import validate, ValidationError
import xml.etree.ElementTree as ET
try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

def validate_xml(xml_path, verbose=False, enable_network=False):
    """
    Validate XML file against its schema if possible.
    """
    if not LXML_AVAILABLE:
        if verbose:
            print("lxml not installed, skipping XML schema validation. Only checking for well-formed XML.")
        try:
            ET.parse(xml_path)
            if verbose:
                print(f"{xml_path} is well-formed.")
            return True
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
            return False
    else:
        try:
            tree = etree.parse(xml_path)
            root = tree.getroot()
            schema_location = root.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')
            if schema_location:
                # schemaLocation is a string: "namespace url"
                parts = schema_location.split()
                if len(parts) == 2:
                    schema_url = parts[1]
                    if not enable_network:
                        print("Network validation required for schema, but --enable-network-validation not set. Skipping schema validation.")
                        if verbose:
                            print(f"Would fetch schema from {schema_url} if network validation was enabled.")
                        return True
                    import requests
                    if verbose:
                        print(f"Fetching schema from {schema_url}")
                    resp = requests.get(schema_url)
                    resp.raise_for_status()
                    schema_doc = etree.XML(resp.content)
                    schema = etree.XMLSchema(schema_doc)
                    schema.assertValid(tree)
                    if verbose:
                        print(f"{xml_path} is valid against schema {schema_url}.")
                    return True
            # If no schema, just check well-formed
            if verbose:
                print(f"No schema found in {xml_path}, only checked for well-formed XML.")
            return True
        except Exception as e:
            print(f"XML validation error: {e}")
            return False
        
def dat2lpl_merged(args):
    """
    Convert DAT XML to LPL JSON playlist. Accepts argparse.Namespace as input.
    Returns the LPL dictionary.
    """
    # Parse XML and collect required information
    tree = ET.parse(args.input)
    root = tree.getroot()

    # Get header/description
    header = root.find('header')
    header_description = header.findtext('description') if header is not None else None
    if getattr(args, 'verbose', False):
        print(f"Header description: {header_description}")

    # Collect game entries
    games = []
    for game in root.findall('game'):
        game_info = {
            'name': game.get('name'),
            'id': game.get('id'),
            'cloneofid': game.get('cloneofid'),
            'roms': []
        }
        for rom in game.findall('rom'):
            rom_info = {
                'name': rom.get('name'),
                'crc': rom.get('crc')
            }
            game_info['roms'].append(rom_info)
        games.append(game_info)
    if getattr(args, 'verbose', False):
        print(f"Found {len(games)} games.")
        for g in games:
            print(g)

    # Prepare LPL output structure
    lpl = {
        "version": "1.5",
        "default_core_path": "",
        "default_core_name": "",
        "label_display_mode": 0,
        "right_thumbnail_mode": 0,
        "left_thumbnail_mode": 0,
        "thumbnail_match_mode": 0,
        "sort_mode": 0,
        "items": []
    }

    db_name = f"{header_description}.lpl" if header_description else "playlist.lpl"

    # Build a lookup for id -> game name
    id_to_name = {g['id']: g['name'] for g in games if g['id']}

    for game in games:
        # Use the first ROM for each game (can be extended later)
        if not game['roms']:
            continue
        rom = game['roms'][0]

        # Determine archive/directory name
        if game['cloneofid'] and game['cloneofid'] in id_to_name:
            archive_dir = id_to_name[game['cloneofid']]
        else:
            archive_dir = game['name']

        # Compose path in a platform-independent way
        if args.archive_format == 'None':
            # Directory: path/to/dir/romname
            path = os.path.join(args.input_path, archive_dir, rom['name'])
        else:
            # Archive: path/to/dir/archivename.ext#romname
            archive_file = f"{archive_dir}{args.archive_format}"
            path = os.path.join(args.input_path, archive_file) + '#' + rom['name']

        item = {
            "path": path,
            "label": game['name'],
            "core_path": "DETECT",
            "core_name": "DETECT",
            "crc32": f"{rom['crc'].upper()}|crc" if rom['crc'] else "|crc",
            "db_name": db_name
        }
        lpl["items"].append(item)

    return lpl

def main():

    parser = argparse.ArgumentParser(
        description="Convert DAT XML to LPL JSON playlist.",
        usage="%(prog)s [-h] --input-path INPUT_PATH [--archive-format {None,.zip,.7z}] [-o OUTPUT] [-v] input"
    )
    parser.add_argument("input", help="Input DAT XML file")
    parser.add_argument("--input-path", required=True, help="Root path for searching ROM files (required)")
    parser.add_argument("--archive-format", choices=["None", ".zip", ".7z"], default=".7z", help="Archive format for ROMs: None, .zip, or .7z (default: .7z)")
    parser.add_argument("-o", "--output", default="output.lpl", help="Output LPL JSON file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--enable-network-validation", action="store_true", help="Allow network access for XML schema validation")
    parser.add_argument("--version", action="version", version="dat2lpl 1.0")
    args = parser.parse_args()


    if not validate_xml(args.input, args.verbose, args.enable_network_validation):
        print("Input XML is not valid. Exiting.")
        sys.exit(1)

    lpl = dat2lpl_merged(args)

    if args.verbose:
        print("LPL output object:")
        print(json.dumps(lpl, indent=2))

    # Write output file
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(lpl, f, indent=2)
    if args.verbose:
        print(f"Wrote LPL file to {args.output}")

if __name__ == "__main__":
    main()
