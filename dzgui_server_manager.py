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
    
    async def fetch_steam_servers(self, limit: int = None) -> List[ServerRecord]:
        """Fetch ALL DayZ servers from Steam API and convert to ServerRecord"""
        servers = []
        
        # Steam API configuration (same as original script)
        steam_api_key = self.get_steam_api_key()
        if not steam_api_key:
            print("No Steam API key found, using fallback servers")
            return []
        
        # Simple filter to get top 2500 popular DayZ servers
        filters = [
            "\\appid\\221100"  # Just DayZ app ID - gets most popular servers
        ]
        
        base_url = "https://api.steampowered.com/IGameServersService/GetServerList/v1/"
        api_limit = 2500  # Get more servers per request
        
        if HAS_AIOHTTP:
            try:
                async with aiohttp.ClientSession() as session:
                    all_servers = []
                    
                    self.progressUpdate.emit(5, "Fetching popular servers from Steam API...")
                    
                    # Single request for popular DayZ servers
                    params = {
                        'filter': '\\appid\\221100',  # Just DayZ app ID
                        'limit': str(api_limit),
                        'key': steam_api_key,
                        'format': 'json'
                    }
                    
                    self.progressUpdate.emit(30, "Fetching 2500 most popular servers...")
                    
                    try:
                        async with session.get(base_url, params=params, timeout=15) as response:
                            if response.status == 200:
                                data = await response.json()
                                steam_servers = data.get('response', {}).get('servers', [])
                                
                                for server_data in steam_servers:
                                    # Convert to ServerRecord
                                    try:
                                        server_record = ServerRecord.from_steam_api(server_data)
                                        all_servers.append(server_record)
                                    except Exception as e:
                                        print(f"Error parsing server: {e}")
                                        continue
                                        
                                print(f"Found {len(steam_servers)} popular servers")
                                
                                # Apply limit if specified
                                if limit and len(all_servers) >= limit:
                                    all_servers = all_servers[:limit]
                                    
                    except Exception as e:
                        print(f"Error fetching popular servers: {e}")
                    
                    print(f"Total popular servers fetched: {len(all_servers)}")
                    return all_servers
                        
            except Exception as e:
                print(f"Error fetching from Steam API: {e}")
        
        return []
    
    async def measure_server_pings_batch(self, servers: List[ServerRecord], max_concurrent: int = 20) -> List[ServerRecord]:
        """Measure ping for servers using A2S queries in batches"""
        if not servers:
            return []
            
        print(f"Measuring pings for {len(servers)} servers...")
        
        # Limit concurrent pings to avoid overwhelming
        semaphore = asyncio.Semaphore(max_concurrent)
        total_servers = len(servers)
        completed = 0
        
        async def ping_server(server: ServerRecord) -> ServerRecord:
            nonlocal completed
            async with semaphore:
                try:
                    # Use our A2S query to get real ping (fast mode pour premiers 60%)
                    fast_mode = (completed / total_servers) < 0.6
                    server_info = await self.query_server_a2s(server.ip, server.query_port, fast_mode)
                    
                    if server_info and server_info.online:
                        server.ping = server_info.ping
                        server.players = server_info.players
                        server.max_players = server_info.max_players
                        server.map_name = server_info.map
                        server.perspective = server_info.perspective
                        server.online = True
                        server.last_seen = time.time()
                        server.last_updated = time.time()
                        
                        # Update database immediately for real-time updates (this will emit signal!)
                        self.database.update_server_ping(
                            server.ip, server.query_port, server.ping, 
                            server.players, server.max_players, emit_signal=True
                        )
                        
                        print(f"✓ {server.name[:40]}... - {server.ping}ms ({server.players}/{server.max_players})")
                    else:
                        server.ping = 999
                        server.online = False
                        self.database.mark_server_offline(server.ip, server.query_port)
                        print(f"✗ {server.name[:40]}... - Offline")
                        
                except Exception as e:
                    server.ping = 999
                    server.online = False
                    self.database.mark_server_offline(server.ip, server.query_port)
                    print(f"✗ {server.name[:40]}... - Error: {e}")
                
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
        
        # Process servers in batches to avoid timeouts
        batch_size = 50
        updated_servers = []
        
        for i in range(0, len(servers), batch_size):
            batch = servers[i:i + batch_size]
            batch_progress = int(80 + (i / len(servers)) * 15)
            self.progressUpdate.emit(batch_progress, f"Processing batch {i//batch_size + 1}...")
            
            # Ping batch concurrently
            tasks = [ping_server(server) for server in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful results
            for result in batch_results:
                if isinstance(result, ServerRecord):
                    updated_servers.append(result)
        
        print(f"Ping measurement complete! {len(updated_servers)} servers processed")
        return updated_servers
    
    def get_steam_api_key(self) -> Optional[str]:
        """Get Steam API key from config"""
        # Check environment variable first
        import os
        key = os.getenv('STEAM_API_KEY')
        if key:
            print(f"Found Steam API key from environment")
            return key
        
        # Check config files (same location as original)
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
                                    print(f"Found Steam API key from {config_file}")
                                    return key
                except Exception as e:
                    print(f"Error reading config {config_file}: {e}")
        
        return None
    
    def get_fallback_servers(self) -> List[ServerRecord]:
        """Fallback servers when Steam API is not available"""
        fallback_data = [
            {'name': '[FALLBACK] DayZ Test Server', 'addr': '127.0.0.1:2302', 'map': 'chernarusplus', 'players': 0, 'max_players': 60},
            {'name': '[FALLBACK] Local Test', 'addr': '127.0.0.1:2402', 'map': 'livonia', 'players': 0, 'max_players': 60},
        ]
        
        return [ServerRecord.from_steam_api(data) for data in fallback_data]
    
    async def refresh_servers_async(self):
        """Refresh server list asynchronously with SQLite caching"""
        try:
            self.progressUpdate.emit(5, "Starting server refresh...")
            
            # Step 1: Fetch ALL servers from Steam API
            self.progressUpdate.emit(10, "Connecting to Steam API...")
            server_records = await self.fetch_steam_servers()
            
            if not server_records:
                self.serverError.emit("Failed to fetch servers from Steam API")
                return
            
            self.progressUpdate.emit(70, f"Fetched {len(server_records)} servers, saving to database...")
            
            # Step 2: Batch insert to database
            self.database.upsert_servers_batch(server_records)
            
            self.progressUpdate.emit(75, "Starting ping measurement...")
            
            # Step 3: Measure pings (this also updates database in real-time)
            await self.measure_server_pings_batch(server_records)
            
            self.progressUpdate.emit(95, "Cleaning up old servers...")
            
            # Step 4: Cleanup old servers
            self.database.cleanup_old_servers()
            
            # Step 5: Update cache timestamp
            self.database.set_cache_timestamp()
            
            self.progressUpdate.emit(98, "Loading servers for display...")
            
            # Step 6: Get fresh servers from database and emit
            fresh_servers = self.database.get_cached_servers()
            
            self.progressUpdate.emit(100, f"Successfully loaded {len(fresh_servers)} servers")
            
            # Emit updated servers
            self.serversUpdated.emit(fresh_servers)
            
            # Print stats
            stats = self.database.get_database_stats()
            print(f"Database stats: {stats}")
            
        except Exception as e:
            self.serverError.emit(f"Error refreshing servers: {str(e)}")
            print(f"Refresh error: {e}")
    
    def search_servers(self, query: str, server_type: Optional[str] = None) -> List[Dict]:
        """Search servers in database"""
        return self.database.search_servers(query, server_type)
    
    def get_servers_by_type(self, server_type: str) -> List[Dict]:
        """Get servers by type from database"""
        return self.database.get_cached_servers(server_type)
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        return self.database.get_database_stats()
    
    def load_cached_servers(self) -> List[Dict]:
        """Load servers from SQLite cache immediately"""
        try:
            is_fresh, count = self.database.is_cache_fresh()
            
            if count > 0:
                servers = self.database.get_cached_servers()
                print(f"Loaded {len(servers)} cached servers (fresh: {is_fresh})")
                
                # Emit cached servers immediately
                self.serversUpdated.emit(servers)
                
                # If cache is stale, trigger background refresh
                if not is_fresh:
                    print("Cache is stale, triggering background refresh")
                    self.refresh_servers(force_refresh=True)
                
                return servers
            else:
                print("No cached servers found, triggering full refresh")
                self.refresh_servers(force_refresh=True)
                return []
                
        except Exception as e:
            print(f"Error loading cached servers: {e}")
            self.refresh_servers(force_refresh=True)
            return []
    
    def refresh_servers(self, force_refresh: bool = False):
        """Start server refresh in thread"""
        # Check if refresh needed (unless forced)
        if not force_refresh:
            is_fresh, count = self.database.is_cache_fresh()
            if is_fresh and count > 0:
                print("Cache is fresh, skipping refresh")
                servers = self.database.get_cached_servers()
                self.serversUpdated.emit(servers)
                return
        
        # Show progress immediately 
        self.progressUpdate.emit(0, "Starting server refresh...")
        
        # Start async refresh
        self.refresh_thread = ServerRefreshThread(self)
        self.refresh_thread.start()


class ServerRefreshThread(QThread):
    """Thread for async server refresh"""
    
    def __init__(self, manager: DZServerManager):
        super().__init__()
        self.manager = manager
    
    def run(self):
        """Run async server refresh"""
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async refresh
            loop.run_until_complete(self.manager.refresh_servers_async())
        finally:
            loop.close()


# Singleton instance
_server_manager = None

def get_server_manager() -> DZServerManager:
    """Get singleton server manager instance"""
    global _server_manager
    if _server_manager is None:
        _server_manager = DZServerManager()
    return _server_manager