#!/usr/bin/env python3
"""
DayZ Mod Manager - Steam Workshop Integration
Handles mod detection, installation status, and launch parameters
"""

import os
import json
import re
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import aiohttp
import asyncio

@dataclass
class ModInfo:
    """Mod information structure"""
    workshop_id: str
    name: str = ""
    installed: bool = False
    local_path: Path = None
    size_mb: float = 0.0
    last_updated: float = 0.0
    required_by_server: bool = False

class DZModManager:
    """DayZ Mod Manager for Steam Workshop integration"""
    
    def __init__(self):
        # Steam paths (Linux)
        self.steam_root = Path.home() / ".steam" / "steam"
        self.workshop_path = self.steam_root / "steamapps" / "workshop" / "content" / "221100"  # DayZ App ID
        self.dayz_path = self.steam_root / "steamapps" / "common" / "DayZ"
        
        # Alternative paths to check
        self.alt_paths = [
            Path.home() / ".local" / "share" / "Steam" / "steamapps" / "workshop" / "content" / "221100",
            Path("/usr/games") / ".steam" / "steamapps" / "workshop" / "content" / "221100"
        ]
        
        # Detect actual workshop path
        self.workshop_path = self._find_workshop_path()
        
        print(f"Workshop path: {self.workshop_path}")
    
    def _find_workshop_path(self) -> Path:
        """Find the actual Steam Workshop path"""
        paths_to_check = [self.workshop_path] + self.alt_paths
        
        for path in paths_to_check:
            if path.exists():
                print(f"✓ Found workshop directory: {path}")
                return path
        
        print(f"⚠️ Workshop directory not found, using default: {self.workshop_path}")
        return self.workshop_path
    
    def get_installed_mods(self, use_steam_api: bool = True) -> List[ModInfo]:
        """Get list of installed mods from Steam Workshop"""
        mods = []
        
        if not self.workshop_path.exists():
            print(f"Workshop path does not exist: {self.workshop_path}")
            return mods
        
        try:
            # Each subdirectory is a mod by workshop ID
            mod_dirs = []
            for mod_dir in self.workshop_path.iterdir():
                if mod_dir.is_dir() and mod_dir.name.isdigit():
                    mod_dirs.append(mod_dir)
            
            # Try to get names from Steam API first (batch operation)
            steam_names = {}
            if use_steam_api and mod_dirs:
                try:
                    workshop_ids = [mod_dir.name for mod_dir in mod_dirs[:50]]  # Limit to avoid API limits
                    steam_mod_info = asyncio.run(self.get_mod_info_from_steam(workshop_ids))
                    steam_names = {mod_id: info.get('name', f'Mod {mod_id}') 
                                 for mod_id, info in steam_mod_info.items()}
                    print(f"✓ Got names for {len(steam_names)} mods from Steam API")
                except Exception as e:
                    print(f"Failed to get mod names from Steam API: {e}")
            
            # Process each mod directory
            for mod_dir in mod_dirs:
                workshop_id = mod_dir.name
                
                # Get mod name (try Steam API first, then local files)
                mod_name = steam_names.get(workshop_id)
                if not mod_name or mod_name == f"Mod {workshop_id}":
                    mod_name = self._get_mod_name(mod_dir)
                
                # Get mod size
                size_mb = self._get_directory_size_mb(mod_dir)
                
                # Get last modified time
                last_updated = mod_dir.stat().st_mtime
                
                mod_info = ModInfo(
                    workshop_id=workshop_id,
                    name=mod_name or f"Mod {workshop_id}",
                    installed=True,
                    local_path=mod_dir,
                    size_mb=size_mb,
                    last_updated=last_updated
                )
                
                mods.append(mod_info)
            
            print(f"Found {len(mods)} installed mods")
            
        except Exception as e:
            print(f"Error scanning mods: {e}")
        
        return mods
    
    def _get_mod_name(self, mod_dir: Path) -> str:
        """Extract mod name from various mod files"""
        
        # Priority order for name detection
        name_sources = [
            # Standard DayZ mod files
            ("meta.cpp", [r'name\s*=\s*"([^"]+)"', r'title\s*=\s*"([^"]+)"']),
            ("mod.cpp", [r'name\s*=\s*"([^"]+)"', r'title\s*=\s*"([^"]+)"']),
            ("config.cpp", [r'name\s*=\s*"([^"]+)"', r'displayName\s*=\s*"([^"]+)"']),
            
            # Alternative files that might contain names
            ("@mod_name.txt", None),  # Some mods have this
            ("readme.txt", [r'name:\s*([^\n\r]+)', r'title:\s*([^\n\r]+)']),
            
            # Workshop metadata (if available)
            ("workshop.meta", [r'"title"\s*:\s*"([^"]+)"']),
        ]
        
        for filename, patterns in name_sources:
            file_path = mod_dir / filename
            if file_path.exists():
                try:
                    # Special handling for simple text files
                    if filename == "@mod_name.txt":
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            name = f.read().strip()
                            if name and len(name) < 100:  # Reasonable name length
                                return name
                        continue
                    
                    # Pattern matching for structured files
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    if patterns:
                        for pattern in patterns:
                            name_match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                            if name_match:
                                name = name_match.group(1).strip()
                                if name and len(name) < 100:
                                    return name
                        
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue
        
        # Skip Steam API lookup in this function to avoid async issues
        # Steam API names should be handled in get_installed_mods()
        
        # Final fallback: try to extract from directory structure
        try:
            # Look for subdirectories that might indicate mod name
            subdirs = [d for d in mod_dir.iterdir() if d.is_dir()]
            if len(subdirs) == 1:
                subdir_name = subdirs[0].name
                # Clean up common prefixes/suffixes
                if subdir_name.startswith('@'):
                    subdir_name = subdir_name[1:]
                if not subdir_name.isdigit():
                    return subdir_name.replace('_', ' ').title()
        except Exception:
            pass
        
        # Last resort: use workshop ID
        return f"Mod {mod_dir.name}"
    
    def _get_directory_size_mb(self, directory: Path) -> float:
        """Get directory size in MB"""
        try:
            total_size = sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
            return round(total_size / (1024 * 1024), 2)
        except Exception:
            return 0.0
    
    async def get_server_mods(self, server_ip: str, server_port: int) -> List[str]:
        """Get required mods for a server using DayZ SA Launcher API"""
        try:
            # Try DayZ SA Launcher API (commonly used)
            api_url = f"https://dayzsalauncher.com/api/v1/query/{server_ip}/{server_port}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract mod IDs from response
                        if 'mods' in data:
                            return [str(mod['workshopId']) for mod in data['mods']]
                        elif 'modIds' in data:
                            return [str(mod_id) for mod_id in data['modIds']]
            
        except Exception as e:
            print(f"Error getting server mods via API: {e}")
        
        # Fallback: Try A2S rules query
        try:
            return await self._get_server_mods_a2s(server_ip, server_port)
        except Exception as e:
            print(f"Error getting server mods via A2S: {e}")
        
        return []
    
    async def _get_server_mods_a2s(self, server_ip: str, server_port: int) -> List[str]:
        """Get server mods using A2S rules query"""
        try:
            from a2s import rules
            
            # Query server rules
            server_rules = await asyncio.get_event_loop().run_in_executor(
                None, lambda: rules((server_ip, server_port + 1))
            )
            
            mod_ids = []
            
            # Look for mod-related rules
            for key, value in server_rules.items():
                if 'mod' in key.lower():
                    # Extract workshop IDs from the value
                    workshop_ids = re.findall(r'\b\d{9,10}\b', str(value))
                    mod_ids.extend(workshop_ids)
            
            return list(set(mod_ids))  # Remove duplicates
            
        except Exception as e:
            print(f"A2S rules query failed: {e}")
            return []
    
    def check_missing_mods(self, required_mod_ids: List[str]) -> Tuple[List[str], List[str]]:
        """Check which required mods are missing"""
        installed_mods = self.get_installed_mods()
        installed_ids = {mod.workshop_id for mod in installed_mods}
        
        missing = []
        available = []
        
        for mod_id in required_mod_ids:
            if mod_id in installed_ids:
                available.append(mod_id)
            else:
                missing.append(mod_id)
        
        return missing, available
    
    def generate_mod_params(self, mod_ids: List[str]) -> str:
        """Generate -mod parameter string for DayZ launch"""
        if not mod_ids:
            return ""
        
        # Filter only installed mods
        installed_mods = self.get_installed_mods()
        installed_ids = {mod.workshop_id for mod in installed_mods}
        
        valid_mods = [mod_id for mod_id in mod_ids if mod_id in installed_ids]
        
        if not valid_mods:
            return ""
        
        # Build mod paths for -mod parameter
        mod_paths = []
        for mod_id in valid_mods:
            mod_path = self.workshop_path / mod_id
            if mod_path.exists():
                mod_paths.append(str(mod_path))
        
        if mod_paths:
            return f'-mod="{";".join(mod_paths)}"'
        
        return ""
    
    def get_steam_workshop_url(self, mod_id: str) -> str:
        """Get Steam Workshop URL for manual mod subscription"""
        return f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
    
    async def get_mod_info_from_steam(self, mod_ids: List[str]) -> Dict[str, dict]:
        """Get mod information from Steam Workshop API (public endpoint)"""
        if not mod_ids:
            return {}
        
        try:
            # Use the working Steam Workshop API (ISteamRemoteStorage - no key required)
            api_url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
            
            # Prepare form data for POST request
            form_data = {
                'itemcount': len(mod_ids[:20]),  # Limit to 20 mods per request
                'format': 'json'
            }
            
            # Add mod IDs to the form data
            for i, mod_id in enumerate(mod_ids[:20]):
                form_data[f'publishedfileids[{i}]'] = mod_id
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, data=form_data, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        mod_info = {}
                        published_files = data.get('response', {}).get('publishedfiledetails', [])
                        
                        for item in published_files:
                            mod_id = str(item.get('publishedfileid', ''))
                            result = item.get('result', 0)
                            
                            # Result 1 = success
                            if result == 1:
                                mod_info[mod_id] = {
                                    'name': item.get('title', f'Mod {mod_id}'),
                                    'description': item.get('description', ''),
                                    'size': item.get('file_size', 0),
                                    'updated': item.get('time_created', 0),  # Use time_created instead of time_updated
                                    'subscriptions': 0,  # Not available in this API
                                    'tags': []  # Not available in this API
                                }
                            else:
                                print(f"Failed to get info for mod {mod_id}, result code: {result}")
                        
                        return mod_info
                    else:
                        print(f"Steam API returned status {response.status}")
        
        except Exception as e:
            print(f"Error getting mod info from Steam: {e}")
        
        # Fallback: try alternative Steam Workshop scraping approach
        try:
            return await self._get_mod_info_fallback(mod_ids)
        except Exception as e:
            print(f"Fallback mod info failed: {e}")
        
        return {}
    
    async def _get_mod_info_fallback(self, mod_ids: List[str]) -> Dict[str, dict]:
        """Fallback method to get mod info via web scraping"""
        mod_info = {}
        
        # Only try for first few mods to avoid overwhelming requests
        for mod_id in mod_ids[:10]:
            try:
                workshop_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(workshop_url, timeout=10) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Extract title from HTML (simple regex)
                            import re
                            title_match = re.search(r'<div class="workshopItemTitle">([^<]+)</div>', html)
                            if title_match:
                                title = title_match.group(1).strip()
                                mod_info[mod_id] = {
                                    'name': title,
                                    'description': '',
                                    'size': 0,
                                    'updated': 0,
                                    'subscriptions': 0
                                }
                
                # Add small delay between requests
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Failed to get fallback info for mod {mod_id}: {e}")
                continue
        
        return mod_info
    
    def cleanup_unused_mods(self, keep_mod_ids: List[str] = None) -> int:
        """Remove unused mods to save disk space"""
        if keep_mod_ids is None:
            keep_mod_ids = []
        
        installed_mods = self.get_installed_mods()
        removed_count = 0
        
        for mod in installed_mods:
            if mod.workshop_id not in keep_mod_ids:
                try:
                    if mod.local_path and mod.local_path.exists():
                        shutil.rmtree(mod.local_path)
                        removed_count += 1
                        print(f"Removed unused mod: {mod.name} ({mod.workshop_id})")
                except Exception as e:
                    print(f"Error removing mod {mod.workshop_id}: {e}")
        
        return removed_count


# Singleton instance
_mod_manager = None

def get_mod_manager() -> DZModManager:
    """Get singleton mod manager instance"""
    global _mod_manager
    if _mod_manager is None:
        _mod_manager = DZModManager()
    return _mod_manager