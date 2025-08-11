#!/usr/bin/env python3
"""
DZGUI Server Manager - Pure Python Implementation
Replaces bash logic with native Python server queries
"""

import asyncio
from a2s.info import info as a2s_info
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
import json
import time
import socket
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from PySide6.QtCore import QObject, QThread, Signal
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import our database manager
from dzgui_database import get_database, ServerRecord

@dataclass
class ServerInfo:
    """Server information structure"""
    name: str
    map: str
    perspective: str = "Unknown"
    time: str = "Unknown" 
    players: int = 0
    max_players: int = 0
    queue: int = 0
    ip: str = ""
    qport: str = "27016"
    online: bool = False
    ping: int = 999
    mods: List[str] = None
    
    def __post_init__(self):
        if self.mods is None:
            self.mods = []

class DZServerManager(QObject):
    """Native Python server manager for DZGUI"""
    
    # Signals
    serversUpdated = Signal(list)
    serverError = Signal(str)
    progressUpdate = Signal(int, str)  # percentage, message
    serverPingUpdated = Signal(dict)   # single server with fresh ping - FORWARDED from database
    
    def __init__(self):
        super().__init__()
        
        # Paths
        self.config_path = Path.home() / ".config" / "dztui"
        
        # Ensure paths exist
        self.config_path.mkdir(parents=True, exist_ok=True)
        
        # Database manager
        self.database = get_database()
        self.database.progressUpdate.connect(self.progressUpdate)
        self.database.serverPingUpdated.connect(self.serverPingUpdated)  # Forward real-time ping updates
        
        # Thread pool for concurrent queries
        self.executor = ThreadPoolExecutor(max_workers=50)
        
        print("Server manager initialized with SQLite database")
    
    async def query_server_a2s(self, ip: str, qport: int = 27016, fast_mode: bool = False) -> Optional[ServerInfo]:
        """Query a single server using A2S protocol"""
        try:
            # DayZ servers: query port = game port + 1
            actual_qport = qport + 1 if qport < 27000 else qport
            
            # Measure A2S query time for accurate ping
            start_time = time.time()
            
            # Timeout agressif pour fast mode (premiers 60%)
            timeout_value = 1.5 if fast_mode else 3.0
            
            # Query server info with timeout
            info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: a2s_info((ip, actual_qport), timeout=timeout_value)
            )
            
            # Calculate ping from A2S query time (most accurate)
            ping = int((time.time() - start_time) * 1000)
            
            # Cap ping at reasonable maximum
            if ping > 2000:
                ping = 999
            
            # Parse perspective from keywords
            keywords = info.keywords.lower() if hasattr(info, 'keywords') and info.keywords else ""
            if "1pp" in keywords and "3pp" not in keywords:
                perspective = "1PP"
            elif "3pp" in keywords and "1pp" not in keywords:
                perspective = "3PP"
            elif "1pp" in keywords and "3pp" in keywords:
                perspective = "1PP/3PP"
            else:
                perspective = "Unknown"
            
            return ServerInfo(
                name=info.server_name,
                map=info.map_name,
                perspective=perspective,
                players=info.player_count,
                max_players=info.max_players,
                ip=ip,
                qport=str(actual_qport),
                online=True,
                ping=ping
            )
            
        except Exception as e:
            print(f"Error querying {ip}:{qport} - {e}")
            return ServerInfo(
                name=f"Offline Server ({ip})",
                map="Unknown",
                ip=ip,
                qport=str(qport),
                online=False,
                ping=999
            )
    
    async def ping_server_icmp(self, ip: str) -> int:
        """Optimized fast ICMP ping"""
        try:
            import subprocess
            import time
            
            # Use system ping command with optimized settings for speed
            start_time = time.time()
            
            # Optimized ping: 1 packet, 1 second timeout, faster execution
            result = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: subprocess.run(
                    ['ping', '-c', '1', '-W', '1000', '-q', ip],  # -q for quiet (faster), 1s timeout
                    capture_output=True, 
                    text=True,
                    timeout=2  # Process timeout reduced to 2s
                )
            )
            
            if result.returncode == 0:
                # Try to extract actual ping time from output
                try:
                    # Parse ping output for actual RTT time
                    import re
                    ping_match = re.search(r'time=([0-9.]+)', result.stdout)
                    if ping_match:
                        return int(float(ping_match.group(1)))
                except:
                    pass
                
                # Fallback: calculate from execution time
                ping_time = int((time.time() - start_time) * 1000)
                return max(min(ping_time, 999), 10)  # Between 10ms and 999ms
            else:
                return -1  # Ping failed
                
        except Exception as e:
            # Silent failure for better performance
            return -1
    
    async def get_server_mods(self, ip: str, qport: int = 27016) -> List[str]:
        """Get server mod list using A2S rules query"""
        try:
            from a2s import dayzquery
            rules = await asyncio.get_event_loop().run_in_executor(
                None, lambda: dayzquery.dayz_rules((ip, qport))
            )
            
            if hasattr(rules, 'mods') and rules.mods:
                return [mod.workshop_id for mod in rules.mods]
            return []
            
        except Exception as e:
            print(f"Error getting mods for {ip}:{qport} - {e}")
            return []
    
    async def fetch_battlemetrics_servers(self, limit: int = None, filters: Dict[str, str] = None) -> List[ServerRecord]:
        """Fetch DayZ servers from BattleMetrics API (superior to Steam API)"""
        servers = []
        
        try:
            from battlemetrics_api import get_battlemetrics_api
            
            self.progressUpdate.emit(5, "Connecting to BattleMetrics API...")
            
            # Get BattleMetrics API instance
            bm_api = await get_battlemetrics_api()
            
            # Fetch servers (default limit: 2500, same as before but better data)
            fetch_limit = limit if limit else 2500
            self.progressUpdate.emit(20, f"Fetching {fetch_limit} popular servers from BattleMetrics...")
            
            # Get servers from BattleMetrics with filters
            bm_servers = await bm_api.get_dayz_servers(limit=fetch_limit, filters=filters)
            
            if bm_servers:
                self.progressUpdate.emit(60, f"Converting {len(bm_servers)} BattleMetrics servers...")
                
                # Convert BattleMetrics servers to our ServerRecord format
                for bm_server in bm_servers:
                    try:
                        server_record = bm_api.battlemetrics_to_server_record(bm_server)
                        servers.append(server_record)
                    except Exception as e:
                        print(f"Error converting BattleMetrics server: {e}")
                        continue
                
                print(f"✅ Successfully converted {len(servers)} servers from BattleMetrics")
                
                # 🗺️ Hybrid approach: Enrich with Steam API map data (fast batch method)
                self.progressUpdate.emit(75, f"Enriching {len(servers)} servers with Steam API map data...")
                servers = await self._enrich_servers_with_steam_maps(servers)
            else:
                print("❌ No servers returned from BattleMetrics")
                
        except Exception as e:
            print(f"❌ Error fetching from BattleMetrics API: {e}")
            # Fallback to Steam API if BattleMetrics fails
            return await self.fetch_steam_servers_fallback()
        
        return servers
    
    async def _enrich_servers_with_steam_maps_targeted(self, servers: List[ServerRecord]) -> List[ServerRecord]:
        """Enrich BattleMetrics servers by searching Steam API for each server specifically"""
        if not servers:
            return servers
            
        try:
            # Get Steam API key
            steam_api_key = self.get_steam_api_key()
            if not steam_api_key:
                print("⚠️ No Steam API key - keeping BattleMetrics map detection")
                return servers
            
            print(f"🗺️ Searching Steam API for {len(servers)} specific servers...")
            
            if HAS_AIOHTTP:
                async with aiohttp.ClientSession() as session:
                    enriched_count = 0
                    
                    # Search for each server individually in Steam API
                    for i, server in enumerate(servers):
                        if i % 20 == 0:  # Progress every 20 servers
                            self.progressUpdate.emit(75 + int(i/len(servers)*10), f"Searching Steam API: {i}/{len(servers)}")
                        
                        # Try both game port and query port
                        for port in [server.port, server.query_port]:
                            steam_map = await self._get_steam_map_for_server(session, steam_api_key, server.ip, port)
                            if steam_map and steam_map != 'Unknown':
                                old_map = server.map_name
                                server.map_name = steam_map
                                enriched_count += 1
                                print(f"🗺️ Found: {server.name[:35]}... {old_map} -> {steam_map}")
                                break  # Found it, no need to try other port
                    
                    print(f"🗺️ Successfully enriched {enriched_count}/{len(servers)} servers with targeted Steam search")
            
        except Exception as e:
            print(f"⚠️ Error in targeted Steam enrichment: {e}")
        
        return servers
    
    async def _get_steam_map_for_server(self, session, steam_api_key: str, ip: str, port: int) -> Optional[str]:
        """Get map for specific server from Steam API"""
        try:
            base_url = "https://api.steampowered.com/IGameServersService/GetServerList/v1/"
            
            # Search specifically for this server
            params = {
                'filter': f'\\addr\\{ip}:{port}',  # Search for specific server
                'key': steam_api_key,
                'format': 'json'
            }
            
            async with session.get(base_url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    steam_servers = data.get('response', {}).get('servers', [])
                    
                    if steam_servers:
                        return steam_servers[0].get('map', 'Unknown')
                
                return None
                        
        except Exception as e:
            # Silent fail for individual server lookups
            return None
    
    async def _enrich_servers_with_steam_maps(self, servers: List[ServerRecord]) -> List[ServerRecord]:
        """Enrich BattleMetrics servers with Steam API map information"""
        if not servers:
            return servers
            
        try:
            # Get Steam API key
            steam_api_key = self.get_steam_api_key()
            if not steam_api_key:
                print("⚠️ No Steam API key - keeping BattleMetrics map detection")
                return servers
            
            print(f"🗺️ Enriching with Steam API map data for {len(servers)} servers...")
            
            if HAS_AIOHTTP:
                async with aiohttp.ClientSession() as session:
                    # Get Steam servers (larger batch to find our servers)
                    steam_servers = await self._fetch_steam_servers_for_maps(session, steam_api_key)
                    
                    if steam_servers:
                        # Create mapping: IP -> map_name (ignore port differences between APIs)
                        steam_map_data = {}
                        for steam_server in steam_servers:
                            addr = steam_server.get('addr', '')
                            if ':' in addr:
                                ip, port_str = addr.split(':', 1)
                                steam_map_data[ip] = steam_server.get('map', 'Unknown')
                        
                        # Enrich our servers with Steam map data (match by IP only)
                        enriched_count = 0
                        for server in servers:
                            if server.ip in steam_map_data:
                                server.map_name = steam_map_data[server.ip]
                                enriched_count += 1
                        
                        print(f"🗺️ Successfully enriched {enriched_count}/{len(servers)} servers with Steam map data")
                    else:
                        print("⚠️ No Steam servers returned - keeping BattleMetrics map detection")
            
        except asyncio.TimeoutError:
            print(f"⚠️ Steam API timeout - continuing without map enrichment")
        except Exception as e:
            print(f"⚠️ Error enriching with Steam maps: {e}")
            import traceback
            traceback.print_exc()
        
        return servers
    
    async def _fetch_steam_servers_for_maps(self, session, steam_api_key: str) -> List[Dict]:
        """Fetch servers from Steam API specifically for map information"""
        try:
            base_url = "https://api.steampowered.com/IGameServersService/GetServerList/v1/"
            
            # Fetch larger batch from Steam to find our servers
            # Try different filter formats for DayZ servers
            params = {
                'filter': '\\appid\\221100',  # Correct filter format for DayZ
                'limit': '2000',  # Large batch to match our BattleMetrics servers
                'key': steam_api_key,
                'format': 'json'
            }
            
            async with session.get(base_url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    steam_servers = data.get('response', {}).get('servers', [])
                    print(f"🗺️ Retrieved {len(steam_servers)} servers from Steam API for map matching")
                    return steam_servers
                else:
                    print(f"❌ Steam API returned status {response.status}")
                    response_text = await response.text()
                    print(f"❌ Response content: {response_text[:200]}")
                    return []
                    
        except Exception as e:
            print(f"❌ Error fetching Steam servers for maps: {e}")
            return []
    
    async def fetch_filtered_servers(self, server_type: str = None, region: str = None, search_term: str = None, max_servers: int = 200) -> List[ServerRecord]:
        """Fetch servers using BattleMetrics API filters - much faster than client-side filtering"""
        try:
            # Build filters for BattleMetrics API
            filters = {}
            
            # Server type filters (map to BattleMetrics concepts)
            if server_type:
                if server_type == 'official':
                    # Official servers typically have no mods and specific naming patterns
                    filters['mods'] = ''  # No mods
                elif server_type == 'modded':
                    # We can't directly filter for "has mods" but we'll get all and filter later
                    pass
                elif server_type == 'private':
                    filters['private'] = 'true'
            
            # Region filtering
            if region:
                # Map common region names to country codes
                region_map = {
                    'europe': 'DE,FR,UK,NL,SE,NO,PL,IT,ES',
                    'north_america': 'US,CA', 
                    'oceania': 'AU,NZ',
                    'asia': 'JP,KR,CN,SG'
                }
                if region.lower() in region_map:
                    filters['countries[]'] = region_map[region.lower()]
                else:
                    filters['countries[]'] = region.upper()
            
            # Search term filtering
            if search_term:
                filters['search'] = search_term
            
            print(f"🎯 Smart filtering: {max_servers} servers with filters: {filters}")
            
            # Fetch filtered servers
            self.progressUpdate.emit(10, f"Fetching {max_servers} filtered servers...")
            return await self.fetch_battlemetrics_servers(limit=max_servers, filters=filters)
            
        except Exception as e:
            print(f"❌ Error in filtered fetch: {e}")
            # Fallback to regular fetch
            return await self.fetch_battlemetrics_servers(limit=max_servers)
    
    async def fetch_steam_servers_fallback(self) -> List[ServerRecord]:
        """Fallback Steam API method (kept for compatibility)"""
        print("🔄 Falling back to Steam API...")
        
        # Steam API configuration (fallback only)
        steam_api_key = self.get_steam_api_key()
        if not steam_api_key:
            print("No Steam API key found, returning empty list")
            return []
        
        servers = []
        base_url = "https://api.steampowered.com/IGameServersService/GetServerList/v1/"
        
        if HAS_AIOHTTP:
            try:
                async with aiohttp.ClientSession() as session:
                    params = {
                        'filter': '\\appid\\221100',
                        'limit': '1000',  # Reduced limit for fallback
                        'key': steam_api_key,
                        'format': 'json'
                    }
                    
                    async with session.get(base_url, params=params, timeout=15) as response:
                        if response.status == 200:
                            data = await response.json()
                            steam_servers = data.get('response', {}).get('servers', [])
                            
                            for server_data in steam_servers:
                                try:
                                    server_record = ServerRecord.from_steam_api(server_data)
                                    servers.append(server_record)
                                except Exception as e:
                                    continue
                                    
                            print(f"Steam fallback: {len(servers)} servers")
                        
            except Exception as e:
                print(f"Steam fallback failed: {e}")
        
        return servers
    
    async def measure_server_pings_batch(self, servers: List[ServerRecord], max_concurrent: int = 50) -> List[ServerRecord]:
        """Parallel ICMP ping measurement for maximum speed"""
        if not servers:
            return []
        
        # Sort servers by priority: players > 0, then by player count
        servers.sort(key=lambda s: (s.players > 0, s.players), reverse=True)
        
        print(f"⚡ Parallel ICMP ping for {len(servers)} servers (max {max_concurrent} concurrent)...")
        
        # Use higher concurrency for ICMP pings (much lighter than A2S)
        semaphore = asyncio.Semaphore(max_concurrent)
        total_servers = len(servers)
        completed = 0
        
        async def ping_server(server: ServerRecord) -> ServerRecord:
            nonlocal completed
            async with semaphore:
                # Smart ping strategy: Use fast ICMP ping instead of slow A2S
                try:
                    # Skip ping for servers with 0 players (likely actually offline)
                    if server.players == 0:
                        print(f"⏭️ {server.name[:40]}... - Skipping (0 players)")
                        server.ping = 500  # Assign medium ping, keep BattleMetrics data
                        server.online = True  # Trust BattleMetrics status
                    else:
                        # Use fast ICMP ping instead of A2S (much faster and more reliable)
                        try:
                            ping_result = await self.ping_server_icmp(server.ip)
                            if ping_result > 0:
                                server.ping = min(ping_result, 999)  # Cap at 999ms
                                server.online = True
                                print(f"🏓 {server.name[:40]}... - {server.ping}ms ICMP ({server.players}/{server.max_players})")
                            else:
                                # ICMP failed, use BattleMetrics data with estimated ping
                                server.ping = 350
                                server.online = True
                                print(f"📊 {server.name[:40]}... - ICMP failed, estimated ping ({server.players}/{server.max_players})")
                        except Exception as e:
                            # Fallback to estimated ping based on BattleMetrics data
                            server.ping = 300
                            server.online = True
                            print(f"📊 {server.name[:40]}... - Using BattleMetrics data ({server.players}/{server.max_players})")
                    
                    server.last_seen = time.time()
                    server.last_updated = time.time()
                    
                    # Update database with server info
                    self.database.update_server_ping(
                        server.ip, server.query_port, server.ping, 
                        server.players, server.max_players, emit_signal=True
                    )
                        
                except Exception as e:
                    # Even on exception, keep BattleMetrics data
                    server.ping = 400
                    server.online = True
                    print(f"📊 {server.name[:40]}... - Using BattleMetrics data only ({server.players}/{server.max_players})")
                
                completed += 1
                progress = int(80 + (completed / total_servers) * 15)  # 80-95% range
                
                # Early Display à 60% des serveurs pingés
                progress_ratio = completed / total_servers
                if progress_ratio >= 0.6 and not hasattr(self, '_early_display_triggered'):
                    self._early_display_triggered = True
                    self.progressUpdate.emit(90, f"Ready to play! Loading {total_servers - completed} more servers in background...")
                elif progress_ratio < 0.6:
                    self.progressUpdate.emit(progress, f"Pinging {completed}/{total_servers} servers...")
                else:
                    # Background loading - progress plus discret
                    self.progressUpdate.emit(progress, f"Background: {completed}/{total_servers} servers loaded")
                
                # DÉLAI entre pings pour éviter surcharge et faux pings
                # Plus agressif pour les premiers serveurs
                if progress_ratio < 0.6:
                    await asyncio.sleep(0.03)  # 30ms pour premiers serveurs
                else:
                    await asyncio.sleep(0.1)   # 100ms pour background servers
                    
                return server
        
        # Execute ALL pings in parallel for maximum speed
        print(f"🚀 Starting {total_servers} parallel ICMP pings...")
        start_time = time.time()
        
        # Create all ping tasks at once
        tasks = [ping_server(server) for server in servers]
        
        # Execute all pings in parallel with proper cancellation handling
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            print("⚠️ Ping tasks cancelled during shutdown")
            # Cancel all remaining tasks
            for task in tasks:
                if hasattr(task, 'cancel'):
                    task.cancel()
            return servers  # Return original servers without ping updates
        
        # Filter successful results
        updated_servers = []
        for result in results:
            if isinstance(result, ServerRecord):
                updated_servers.append(result)
            elif isinstance(result, Exception):
                print(f"❌ Ping task failed: {result}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⚡ Parallel ping complete! {len(updated_servers)} servers in {duration:.1f}s ({len(updated_servers)/duration:.1f} pings/sec)")
        return updated_servers
    
    async def measure_server_pings_realtime(self, servers: List[ServerRecord], max_concurrent: int = 50):
        """Measure pings with real-time UI updates as results come in"""
        if not servers:
            return
        
        print(f"🏓 Real-time ping measurement for {len(servers)} servers...")
        
        # Sort servers by priority for better user experience
        servers.sort(key=lambda s: (s.players > 0, s.players), reverse=True)
        
        # Use semaphore for controlled concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        total_servers = len(servers)
        completed = 0
        
        async def ping_and_update_server(server: ServerRecord):
            """Ping server and update UI immediately when result arrives"""
            nonlocal completed
            
            async with semaphore:
                try:
                    # Skip ping for empty servers (keep estimated ping)
                    if server.players == 0:
                        completed += 1
                        return
                    
                    # Measure ICMP ping
                    ping_result = await self.ping_server_icmp(server.ip)
                    
                    if ping_result > 0:
                        # Real ping successful
                        server.ping = min(ping_result, 999)
                        server.online = True
                        
                        # Update database immediately
                        self.database.update_server_ping(
                            server.ip, server.query_port, server.ping, 
                            server.players, server.max_players, emit_signal=True
                        )
                        
                        print(f"🏓 {server.name[:30]}... - {server.ping}ms (live update)")
                    else:
                        # ICMP failed - keep estimated ping but mark as less reliable
                        server.ping = min(server.ping + 50, 500)  # Slight penalty for failed ping
                        server.online = True
                        
                        # Still update database for consistency
                        self.database.update_server_ping(
                            server.ip, server.query_port, server.ping, 
                            server.players, server.max_players, emit_signal=True
                        )
                        
                        print(f"📊 {server.name[:30]}... - {server.ping}ms (estimated+)")
                
                except Exception as e:
                    # Keep estimated ping on error
                    print(f"❌ {server.name[:30]}... - Error: {e}")
                
                completed += 1
                
                # Progress update every 10 servers
                if completed % 10 == 0 or completed >= total_servers:
                    progress = 85 + int((completed / total_servers) * 10)  # 85-95% range
                    self.progressUpdate.emit(progress, f"Live pings: {completed}/{total_servers} updated")
        
        # 🚀 Launch all ping tasks in parallel
        print(f"🚀 Launching {total_servers} concurrent ping tasks...")
        tasks = [ping_and_update_server(server) for server in servers]
        
        # Wait for all pings to complete with proper cancellation handling
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            print("⚠️ Real-time ping tasks cancelled during shutdown")
            # Cancel all remaining tasks
            for task in tasks:
                if hasattr(task, 'cancel'):
                    task.cancel()
            return
        
        print(f"✅ Real-time ping measurement complete! All {total_servers} servers processed")
    
    def get_steam_api_key(self) -> Optional[str]:
        """Get Steam API key from config - OPTIONAL for privacy"""
        # Check environment variable first (most secure)
        import os
        key = os.getenv('STEAM_API_KEY')
        if key:
            print("✓ Found Steam API key from environment variable")
            return key
        
        # Check config files (user-provided)
        config_files = [
            self.config_path / "dzgui.conf",
            Path.home() / ".config" / "dztui" / "dztuirc",  # Original config location
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        for line in f:
                            if line.startswith('steam_api='):
                                key = line.split('=', 1)[1].strip().strip('"')
                                if key and key != '""':
                                    print(f"✓ Found Steam API key from {config_file}")
                                    return key
                except Exception as e:
                    print(f"Error reading config {config_file}: {e}")
        
        print("ℹ️  No Steam API key found - using fallback server list")
        print("   To get more servers, obtain a free API key from:")
        print("   https://steamcommunity.com/dev/apikey")
        return None
    
    def get_fallback_servers(self) -> List[ServerRecord]:
        """Fallback servers when Steam API is not available - Popular community servers"""
        # Well-known popular DayZ servers that don't require API key
        fallback_data = [
            {'name': 'DayZ Official - No API Key Required', 'addr': '127.0.0.1:2302', 'map': 'chernarusplus', 'players': 0, 'max_players': 60},
            {'name': '🔧 Add your favorite servers to favorites!', 'addr': '127.0.0.1:2402', 'map': 'livonia', 'players': 0, 'max_players': 60},
            {'name': 'ℹ️  Get Steam API key for 2500+ servers', 'addr': '127.0.0.1:2502', 'map': 'namalsk', 'players': 0, 'max_players': 60},
        ]
        
        return [ServerRecord.from_steam_api(data) for data in fallback_data]
    
    async def refresh_servers_async(self, server_type: str = None, region: str = None, search_term: str = None):
        """Ultra-Smart server refresh - Use BattleMetrics API filters to fetch only relevant servers (~200 max)"""
        try:
            self.progressUpdate.emit(5, "Starting BattleMetrics filtered refresh...")
            
            # 🎯 NEW APPROACH: Use BattleMetrics API filters to get ONLY relevant servers
            max_servers = 200  # Much smaller, faster set
            
            if server_type or region or search_term:
                self.progressUpdate.emit(10, f"Fetching filtered servers: {server_type}/{region}/{search_term}")
                server_records = await self.fetch_filtered_servers(
                    server_type=server_type, 
                    region=region, 
                    search_term=search_term, 
                    max_servers=max_servers
                )
            else:
                # Default: Get top popular servers (no specific filters)
                self.progressUpdate.emit(10, f"Fetching top {max_servers} popular servers...")
                server_records = await self.fetch_battlemetrics_servers(limit=max_servers)
            
            if not server_records:
                self.serverError.emit("Failed to fetch filtered servers from BattleMetrics API")
                return
            
            print(f"🎯 API-Filtered: Got {len(server_records)} servers (vs old 2500+)")
            self.progressUpdate.emit(40, f"Got {len(server_records)} filtered servers, saving...")
            
            # Save filtered servers to database (for search/stats only)
            self.database.upsert_servers_batch(server_records)
            
            # Convert to display format
            display_servers = [server.to_dict() for server in server_records]
            
            # 🚀 DISPLAY immediately - all servers are relevant
            self.progressUpdate.emit(60, f"Showing all {len(display_servers)} filtered servers...")
            self.serversUpdated.emit(display_servers)
            
            print(f"✅ API-Filtered Display: All {len(display_servers)} servers shown immediately")
            self.progressUpdate.emit(70, "Measuring pings for filtered servers...")
            
            # 🏓 Ping all filtered servers (small set, very fast)
            print(f"🏓 Pinging all {len(server_records)} filtered servers...")
            await self.measure_server_pings_batch(server_records, max_concurrent=50)
            
            self.progressUpdate.emit(95, "Finalizing...")
            self.database.cleanup_old_servers()
            
            self.progressUpdate.emit(100, f"✅ Ready! {len(server_records)} filtered servers loaded & pinged")
            
            # Print final stats
            print(f"📊 API-Filtered stats: {len(server_records)} servers (filtered by BattleMetrics API)")
            
        except Exception as e:
            self.serverError.emit(f"Error refreshing servers: {str(e)}")
            print(f"Refresh error: {e}")
    
    def _dict_to_server_record(self, server_dict: Dict) -> ServerRecord:
        """Convert server dict back to ServerRecord for ping measurement"""
        return ServerRecord(
            id=server_dict.get('id'),
            name=server_dict['name'],
            ip=server_dict['ip'],
            port=int(server_dict['qport']) - 1 if server_dict['qport'].isdigit() else 27016,
            query_port=int(server_dict['qport']) if server_dict['qport'].isdigit() else 27017,
            map_name=server_dict['map'],
            players=server_dict['players'],
            max_players=server_dict['max_players'],
            queue=server_dict.get('queue', 0),
            ping=server_dict['ping'],
            perspective=server_dict['perspective'],
            server_type=server_dict['server_type'],
            online=server_dict['online'],
            last_seen=server_dict.get('last_seen', 0)
        )
    
    def search_servers(self, query: str, server_type: Optional[str] = None) -> List[Dict]:
        """Search servers in database"""
        return self.database.search_servers(query, server_type)
    
    def get_servers_by_type(self, server_type: str) -> List[Dict]:
        """Get servers by type - directly fetch with filters instead of cache"""
        # With BattleMetrics filtering, we fetch fresh data instead of using cache
        asyncio.create_task(self.refresh_servers_async(server_type=server_type))
        return []  # Return empty, will be populated via signals
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        return self.database.get_database_stats()
    
    
    def refresh_servers(self, server_type: str = None, region: str = None, search_term: str = None):
        """Start server refresh in thread - no more cache checking needed"""
        # Show progress immediately 
        self.progressUpdate.emit(0, "Starting BattleMetrics filtered refresh...")
        
        # Start async refresh with filters
        self.refresh_thread = ServerRefreshThread(self, server_type, region, search_term)
        self.refresh_thread.start()


class ServerRefreshThread(QThread):
    """Thread for async server refresh"""
    
    def __init__(self, manager: DZServerManager, server_type: str = None, region: str = None, search_term: str = None):
        super().__init__()
        self.manager = manager
        self.server_type = server_type
        self.region = region
        self.search_term = search_term
    
    def run(self):
        """Run async server refresh"""
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async refresh with filters
            loop.run_until_complete(self.manager.refresh_servers_async(
                server_type=self.server_type,
                region=self.region, 
                search_term=self.search_term
            ))
        except Exception as e:
            print(f"Thread refresh error: {e}")
        finally:
            # Clean shutdown of event loop
            try:
                # Cancel all remaining tasks
                pending = asyncio.all_tasks(loop)
                if pending:
                    print(f"🔄 Cancelling {len(pending)} pending tasks...")
                    for task in pending:
                        task.cancel()
                    
                    # Wait for cancelled tasks to complete
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as e:
                print(f"Error cancelling tasks: {e}")
            finally:
                loop.close()
                print("🔄 Thread event loop closed")


# Singleton instance
_server_manager = None

def get_server_manager() -> DZServerManager:
    """Get singleton server manager instance"""
    global _server_manager
    if _server_manager is None:
        _server_manager = DZServerManager()
    return _server_manager