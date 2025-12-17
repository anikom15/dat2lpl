#!/usr/bin/env python
"""
    dat2lpl.py: Convert DAT XML to LPL JSON playlist for RetroArch
    Copyright (C) 2025  W. M. Martinez

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
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
import re


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
        
def read_dat(xml_path, verbose=False):
    """
    Parse the DAT XML file and return (header_description, games) tuple.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Get header/description
    header = root.find('header')
    header_description = header.findtext('description') if header is not None else None

    # Collect game entries, extracting region from name
    games = []
    for game in root.findall('game'):
        name = game.get('name')
        # Only use the first valid parenthesis group at the end for region(s)
        regions = []
        if name:
            # Find the first parenthesis group from the start with valid region characters
            match = re.search(r'\(([A-Za-z .\-]+(?:,[A-Za-z .\-]+)*)\)', name)
            if match:
                region_text = match.group(1)
                # Split by comma, strip whitespace, filter out empty
                regions = [r.strip() for r in region_text.split(',') if r.strip()]
        game_info = {
            'name': name,
            'id': game.get('id'),
            'cloneofid': game.get('cloneofid'),
            'roms': [],
            'regions': regions
        }
        for rom in game.findall('rom'):
            rom_info = {
                'name': rom.get('name'),
                'crc': rom.get('crc')
            }
            game_info['roms'].append(rom_info)
        games.append(game_info)
    return header_description, games


def dat2lpl_split(args, games, header_description):
    """
    Convert DAT XML to LPL JSON playlist for Non-merged or Split sets.
    If games/header_description are provided, use them (for region split mode).
    Otherwise, read from the DAT file.
    """
    if games is None or header_description is None:
        header_description, games = read_dat(args.input, getattr(args, 'verbose', False))
    if getattr(args, 'verbose', False):
        print(f"Header description: {header_description}")
        print(f"Found {len(games)} games.")
        for g in games:
            print(g)

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

    for game in games:
        if not game['roms']:
            continue
        rom = game['roms'][0]
        if args.archive_format == 'None':
            path = os.path.join(args.input_path, game['name'], rom['name'])
        else:
            archive_file = f"{game['name']}{args.archive_format}"
            path = os.path.join(args.input_path, archive_file)
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

def dat2lpl_merged(args, games, header_description):
    """
    Convert DAT XML to LPL JSON playlist for merged sets.
    If games/header_description are provided, use them (for region split mode).
    Otherwise, read from the DAT file.
    """
    if games is None or header_description is None:
        header_description, games = read_dat(args.input, getattr(args, 'verbose', False))
    if getattr(args, 'verbose', False):
        print(f"Header description: {header_description}")
        print(f"Found {len(games)} games.")
        for g in games:
            print(g)

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
    id_to_name = {g['id']: g['name'] for g in games if g['id']}

    for game in games:
        if not game['roms']:
            continue
        rom = game['roms'][0]
        if game['cloneofid'] and game['cloneofid'] in id_to_name:
            archive_dir = id_to_name[game['cloneofid']]
        else:
            archive_dir = game['name']
        if args.archive_format == 'None':
            path = os.path.join(args.input_path, archive_dir, rom['name'])
        else:
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
        usage="%(prog)s [-h] --input-path INPUT_PATH [--archive-format {None,.zip,.7z}] [-s {Non-merged,Split,Merged}] [-o OUTPUT] -r --map MAPFILE [-v] input"
    )
    parser.add_argument("input", help="Input DAT XML file")
    parser.add_argument("--input-path", required=True, help="Root path for searching ROM files (required)")
    parser.add_argument("--archive-format", choices=["None", ".zip", ".7z"], default=".7z", help="Archive format for ROMs: None, .zip, or .7z (default: .7z)")
    parser.add_argument("-s", "--storage-mode", choices=["Non-merged", "Split", "Merged"], default="Merged", help="ROM storage mode: Non-merged, Split, or Merged (default: Merged)")
    parser.add_argument("-o", "--output", default="output.lpl", help="Output LPL JSON file")
    parser.add_argument("-r", "--region-split", action="store_true", help="Produce separate output files by region")
    parser.add_argument("--map", help="JSON file mapping country/region to output value (requires -r)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--enable-network-validation", action="store_true", help="Allow network access for XML schema validation")
    parser.add_argument("--version", action="version", version="dat2lpl 1.0")
    args = parser.parse_args()

    if not validate_xml(args.input, args.verbose, args.enable_network_validation):
        print("Input XML is not valid. Exiting.")
        sys.exit(1)

    if not args.region_split:
        if args.storage_mode == "Merged":
            lpl = dat2lpl_merged(args, None, None)
        else:
            lpl = dat2lpl_split(args, None, None)

        if args.verbose:
            print("LPL output object:")
            print(json.dumps(lpl, indent=2))

        # Write output file
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(lpl, f, indent=2)
        if args.verbose:
            print(f"Wrote LPL file to {args.output}")
        return

    # Region split mode with mapping
    header_description, games = read_dat(args.input, getattr(args, 'verbose', False))
    # Load mapping file
    if (args.map is not None):
        try:
            with open(args.map, 'r', encoding='utf-8') as mf:
                region_map_json = json.load(mf)
        except Exception as e:
            print(f"Failed to load mapping file {args.map}: {e}")
            sys.exit(1)
    else:
        region_map_json = {}

    # Build output_value -> list of games
    output_map = {}  # output_value -> list of games
    all_output_values = set(region_map_json.values())
    for g in games:
        regions = g['regions']
        if not regions:
            continue
        # If 'World' is present, add to all output files (except 'World' itself)
        if 'World' in regions:
            for outval in all_output_values:
                if outval != 'World':
                    output_map.setdefault(outval, []).append(g)
            continue
        # Otherwise, map each region to output value
        for region in regions:
            outval = region_map_json.get(region, region)
            if outval:
                output_map.setdefault(outval, []).append(g)

    # Remove duplicates in each output value
    for outval in output_map:
        seen = set()
        unique_games = []
        for g in output_map[outval]:
            key = g['name']
            if key not in seen:
                unique_games.append(g)
                seen.add(key)
        output_map[outval] = unique_games

    # Output a file for each output value
    for outval, out_games in output_map.items():
        if args.storage_mode == "Merged":
            lpl = dat2lpl_merged(args, out_games, header_description)
        else:
            lpl = dat2lpl_split(args, out_games, header_description)
        # Output file name: output-filename (output_value).lpl
        base, ext = os.path.splitext(args.output)
        safe_outval = re.sub(r'[\\/:*?"<>|]', '', outval)
        outname = f"{base} ({safe_outval}){ext}"
        if args.verbose:
            print(f"Writing region file: {outname} with {len(lpl['items'])} items.")
        with open(outname, 'w', encoding='utf-8') as f:
            json.dump(lpl, f, indent=2)

    # Output a special file for games with no region
    no_region_games = [g for g in games if not g['regions']]
    if no_region_games:
        if args.storage_mode == "Merged":
            lpl = dat2lpl_merged(args, no_region_games, header_description)
        else:
            lpl = dat2lpl_split(args, no_region_games, header_description)
        base, ext = os.path.splitext(args.output)
        outname = f"{base} (No Region){ext}"
        if args.verbose:
            print(f"Writing special file for games with no region: {outname} with {len(lpl['items'])} items.")
        with open(outname, 'w', encoding='utf-8') as f:
            json.dump(lpl, f, indent=2)

if __name__ == "__main__":
    main()
