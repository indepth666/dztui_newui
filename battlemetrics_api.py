#!/usr/bin/env python3
"""
BattleMetrics API - Superior alternative to Steam API for DayZ servers
Provides comprehensive server information including mods, player counts, and real-time data
"""

import aiohttp
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
from dzgui_database import ServerRecord
import time

@dataclass
class BattleMetricsServer:
    """BattleMetrics server information"""
    id: str
    name: str
    ip: str
    port: int
    query_port: int
    players: int
    max_players: int
    queue: int
    map_name: str
    country: str
    rank: int
    mods: List[Dict[str, str]]  # List of {id: str, name: str}
    status: str
    private: bool
    password: bool
    details: Dict
    last_seen: str

class BattleMetricsAPI:
    """BattleMetrics API client for DayZ servers"""
    
    BASE_URL = "https://api.battlemetrics.com"
    
    def __init__(self):
        self.session = None
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_dayz_servers(self, limit: int = 100, page_size: int = 100, filters: Dict[str, str] = None) -> List[BattleMetricsServer]:
        """Get DayZ servers from BattleMetrics API - only online servers sorted by popularity
        Optimized sequential approach (BattleMetrics only supports cursor-based pagination)
        
        Args:
            limit: Maximum number of servers to fetch
            page_size: Servers per page (max 100)
            filters: Additional API filters (country, search term, etc.)
        """
        servers = []
        session = await self._get_session()
        
        try:
            print(f"🎯 Fetching {limit} online DayZ servers from BattleMetrics (optimized)...")
            
            # Use optimized sequential pagination with filters
            await self._fetch_sequential_pages(session, servers, limit, 1, filters)
            
            print(f"🎯 Total BattleMetrics servers fetched: {len(servers)}")
            
        except Exception as e:
            print(f"❌ Error fetching from BattleMetrics: {e}")
        
        return servers
    
    async def _fetch_single_page(self, session, page_num: int, params: dict) -> List[BattleMetricsServer]:
        """Fetch a single page of servers"""
        try:
            url = f"{self.BASE_URL}/servers"
            async with session.get(url, params=params, timeout=30) as response:
                if response.status != 200:
                    print(f"❌ Page {page_num} error: {response.status}")
                    return []
                
                data = await response.json()
                return self._parse_servers(data)
                
        except Exception as e:
            print(f"❌ Page {page_num} exception: {e}")
            return []
    
    async def _fetch_remaining_pages(self, session, servers: list, remaining: int, start_page: int):
        """Fetch remaining pages sequentially using cursor-based pagination"""
        # This would need cursor from last parallel request - for now use sequential
        await self._fetch_sequential_pages(session, servers, remaining, start_page)
    
    async def _fetch_sequential_pages(self, session, servers: list, limit: int, start_page: int = 1, filters: Dict[str, str] = None):
        """Fetch pages sequentially using cursor-based pagination"""
        next_url = None
        total_fetched = len(servers)
        page = start_page
        
        while total_fetched < limit:
            current_page_size = min(100, limit - total_fetched)
            
            if next_url:
                url = next_url
                params = {}
            else:
                url = f"{self.BASE_URL}/servers"
                params = {
                    'filter[game]': 'dayz',
                    'filter[status]': 'online',
                    'page[size]': current_page_size,
                    'sort': '-players'
                }
                
                # Add custom filters
                if filters:
                    for key, value in filters.items():
                        if key.startswith('filter[') or key.startswith('search'):
                            params[key] = value
                        else:
                            # Auto-prefix with filter[] if not already prefixed
                            params[f'filter[{key}]'] = value
            
            print(f"📡 Sequential page {page} ({current_page_size} servers)...")
            
            async with session.get(url, params=params, timeout=30) as response:
                if response.status != 200:
                    print(f"❌ BattleMetrics API error: {response.status}")
                    break
                
                data = await response.json()
                page_servers = self._parse_servers(data)
                servers.extend(page_servers)
                
                total_fetched += len(page_servers)
                print(f"✓ Got {len(page_servers)} servers (total: {total_fetched})")
                
                links = data.get('links', {})
                next_url = links.get('next')
                
                if not next_url or len(page_servers) == 0:
                    print("📄 No more pages available")
                    break
                
                page += 1
                await asyncio.sleep(0.1)
    
    def _parse_servers(self, data: Dict) -> List[BattleMetricsServer]:
        """Parse BattleMetrics API response into server objects"""
        servers = []
        
        try:
            server_list = data.get('data', [])
            included = data.get('included', [])
            
            # Create mapping of included serverInfo
            server_info_map = {}
            for item in included:
                if item.get('type') == 'serverInfo':
                    server_info_map[item['id']] = item['attributes']
            
            for server_data in server_list:
                try:
                    attributes = server_data.get('attributes', {})
                    relationships = server_data.get('relationships', {})
                    
                    # Basic server info
                    server_id = server_data.get('id', '')
                    name = attributes.get('name', 'Unknown Server')
                    ip = attributes.get('ip', '')
                    port = attributes.get('port', 2302)
                    
                    # Player information
                    players = attributes.get('players', 0)
                    max_players = attributes.get('maxPlayers', 0)
                    queue = attributes.get('details', {}).get('squad_publicQueue', 0)
                    
                    # Server details
                    details = attributes.get('details', {})
                    country = attributes.get('country', 'Unknown')
                    rank = attributes.get('rank', 0)
                    status = attributes.get('status', 'unknown')
                    private = attributes.get('private', False)
                    password = details.get('password', False)
                    
                    # Extract mod information first (needed for map detection)
                    mods = self._extract_mods(details)
                    
                    # Map information - will be enriched later by Steam API
                    map_name = self._extract_map_from_name(name)
                    if map_name != 'Unknown':  # Debug successful name-based detection
                        print(f"🗺️ BM Name detection: {name[:50]}... -> {map_name}")
                    elif 'chernarus' in name.lower() or 'livonia' in name.lower():  # Debug failed obvious cases
                        print(f"❌ BM Failed to detect: {name[:50]}... (should be obvious)")
                    
                    
                    if mods:  # Debug log only for servers with mods
                        print(f"🔧 {name[:40]}... has {len(mods)} mods: {[m.get('name', m.get('id')) for m in mods[:3]]}")
                    
                    # Calculate query port (DayZ uses port + 1, but BattleMetrics might provide query port directly)
                    query_port = details.get('queryPort', port + 1)
                    
                    # Last seen
                    last_seen = attributes.get('updatedAt', '')
                    
                    server = BattleMetricsServer(
                        id=server_id,
                        name=name,
                        ip=ip,
                        port=port,
                        query_port=query_port,
                        players=players,
                        max_players=max_players,
                        queue=queue,
                        map_name=map_name,
                        country=country,
                        rank=rank,
                        mods=mods,
                        status=status,
                        private=private,
                        password=password,
                        details=details,
                        last_seen=last_seen
                    )
                    
                    servers.append(server)
                    
                except Exception as e:
                    print(f"Error parsing server: {e}")
                    continue
            
        except Exception as e:
            print(f"Error parsing BattleMetrics response: {e}")
        
        return servers
    
    def _extract_mods(self, details: Dict) -> List[Dict[str, str]]:
        """Extract mod information from server details"""
        mods = []
        
        try:
            # BattleMetrics stores mods in various formats
            mod_keys = ['mods', 'modIds', 'serverMods', 'requiredMods']
            mod_names = details.get('modNames', [])
            mod_ids = details.get('modIds', [])
            
            # Debug: show what's in details for mod detection
            if any(key in details for key in ['modNames', 'modIds', 'modded']):
                print(f"🔍 Found mod data in {details.get('hostname', 'unknown')[:30]}:")
                if mod_names: print(f"  modNames: {mod_names[:3]}...")
                if mod_ids: print(f"  modIds: {mod_ids[:3]}...")
                if 'modded' in details: print(f"  modded: {details['modded']}")
            
            # First, try to pair modIds with modNames if both are available
            if mod_ids and mod_names and len(mod_ids) == len(mod_names):
                for mod_id, mod_name in zip(mod_ids, mod_names):
                    if str(mod_id).isdigit():
                        mods.append({'id': str(mod_id), 'name': mod_name or f'Mod {mod_id}'})
            elif mod_ids:
                # Only mod IDs available
                for mod_id in mod_ids:
                    if str(mod_id).isdigit():
                        mods.append({'id': str(mod_id), 'name': f'Mod {mod_id}'})
            
            # Also check other possible mod key formats
            for key in mod_keys:
                if key in details:
                    mod_data = details[key]
                    
                    if isinstance(mod_data, list):
                        for mod in mod_data:
                            if isinstance(mod, dict):
                                mod_id = str(mod.get('id', ''))
                                mod_name = mod.get('name', f'Mod {mod_id}')
                                if mod_id:
                                    mods.append({'id': mod_id, 'name': mod_name})
                            elif isinstance(mod, str) and mod.isdigit():
                                mods.append({'id': mod, 'name': f'Mod {mod}'})
                    
                    elif isinstance(mod_data, str):
                        # Parse comma-separated mod IDs
                        mod_ids = [mid.strip() for mid in mod_data.split(',') if mid.strip().isdigit()]
                        for mod_id in mod_ids:
                            mods.append({'id': mod_id, 'name': f'Mod {mod_id}'})
            
            # Look for mod information in other detail fields
            for key, value in details.items():
                if 'mod' in key.lower() and isinstance(value, str):
                    # Try to extract workshop IDs from various formats
                    import re
                    workshop_ids = re.findall(r'\b\d{9,10}\b', str(value))
                    for mod_id in workshop_ids:
                        if not any(mod['id'] == mod_id for mod in mods):
                            mods.append({'id': mod_id, 'name': f'Mod {mod_id}'})
            
        except Exception as e:
            print(f"Error extracting mods: {e}")
        
        return mods
    
    def _extract_map_from_name(self, server_name: str) -> str:
        """Extract map name from server name"""
        name_lower = server_name.lower()
        
        # Common DayZ map names
        map_patterns = {
            'chernarus': ['chernarus', 'cherno'],
            'livonia': ['livonia'],
            'namalsk': ['namalsk'],
            'sakhal': ['sakhal'],
            'banov': ['banov'],
            'esseker': ['esseker'],
            'deer_isle': ['deer isle', 'deerisle'],
            'takistan': ['takistan'],
            'alteria': ['alteria'],
            'pripyat': ['pripyat'],
            'valning': ['valning'],
            'melkart': ['melkart'],
            'rostow': ['rostow'],
            'iztek': ['iztek'],
            'swans_island': ['swans island', 'swansisland']
        }
        
        # Check for each map pattern
        for map_name, patterns in map_patterns.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return map_name.replace('_', ' ').title()
        
        # Default fallback
        return 'Unknown'
    
    def battlemetrics_to_server_record(self, bm_server: BattleMetricsServer) -> ServerRecord:
        """Convert BattleMetrics server to our ServerRecord format"""
        
        # Determine server type based on name and mods
        server_type = self._determine_server_type(bm_server.name, bm_server.mods, bm_server.private)
        
        # Store mods with both IDs and names as JSON
        import json
        mods_data = []
        for mod in bm_server.mods:
            mods_data.append({
                'id': mod.get('id', ''),
                'name': mod.get('name', f"Mod {mod.get('id', 'Unknown')}")
            })
        
        if mods_data:  # Debug log
            print(f"🔧 Converting {bm_server.name[:30]}... with {len(mods_data)} mods to ServerRecord")
        
        return ServerRecord(
            name=bm_server.name,
            ip=bm_server.ip,
            port=bm_server.port,
            query_port=bm_server.query_port,
            map_name=bm_server.map_name,
            players=bm_server.players,
            max_players=bm_server.max_players,
            queue=bm_server.queue,
            ping=-1,  # Will be measured later
            perspective="Unknown",  # Will be determined by A2S query
            server_type=server_type,
            online=bm_server.status == 'online',
            last_seen=time.time(),
            last_updated=time.time(),
            mods=json.dumps(mods_data)  # Store as JSON string with both IDs and names
        )
    
    def _determine_server_type(self, name: str, mods: List[Dict], private: bool) -> str:
        """Determine server type from BattleMetrics data"""
        name_lower = name.lower()
        
        # Private servers
        if private or any(keyword in name_lower for keyword in ['private', 'whitelist', 'closed']):
            return 'private'
        
        # Official servers (very strict criteria)
        if (('dayz' in name_lower and any(pattern in name_lower for pattern in [' de ', ' us ', ' eu ', ' uk ', ' fr ', ' au ', ' ca '])) and
            len(mods) == 0 and  # Official servers should have no mods
            not any(char in name_lower for char in ['[', ']', '|', '★', '♦', '●', '~', '!']) and
            not any(keyword in name_lower for keyword in ['discord', 'www', 'http', 'x10', 'loot+', 'rp', 'roleplay', 'clan'])):
            return 'official'
        
        # Default to community
        return 'community'

# Singleton instance
_battlemetrics_api = None

async def get_battlemetrics_api() -> BattleMetricsAPI:
    """Get singleton BattleMetrics API instance"""
    global _battlemetrics_api
    if _battlemetrics_api is None:
        _battlemetrics_api = BattleMetricsAPI()
    return _battlemetrics_api

async def close_battlemetrics_api():
    """Close BattleMetrics API session"""
    global _battlemetrics_api
    if _battlemetrics_api:
        await _battlemetrics_api.close()
        _battlemetrics_api = None