#!/usr/bin/env python3
"""
DZGUI Database Manager - SQLite cache and persistence
Handles server data storage, caching, and cleanup
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Signal

@dataclass
class ServerRecord:
    """Server record structure"""
    id: Optional[int] = None
    name: str = ""
    ip: str = ""
    port: int = 27016
    query_port: int = 27017
    map_name: str = "Unknown"
    players: int = 0
    max_players: int = 0
    queue: int = 0
    ping: int = 999
    perspective: str = "Unknown"
    time_of_day: str = "Unknown"
    server_type: str = "community"  # official, community, private
    online: bool = False
    last_seen: float = 0.0  # Unix timestamp
    last_updated: float = 0.0
    mods: str = "[]"  # JSON array as string
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for UI"""
        return {
            'id': self.id,
            'name': self.name,
            'ip': self.ip,
            'qport': str(self.query_port),
            'map': self.map_name,
            'players': self.players,
            'max_players': self.max_players,
            'queue': self.queue,
            'ping': self.ping,
            'perspective': self.perspective,
            'time': self.time_of_day,
            'server_type': self.server_type,
            'online': self.online,
            'last_seen': self.last_seen,
            'mods': self.mods  # Include mods data for UI
        }
    
    @classmethod
    def from_steam_api(cls, steam_data: Dict) -> 'ServerRecord':
        """Create from Steam API data"""
        addr = steam_data.get('addr', '127.0.0.1:27016')
        ip, port_str = addr.split(':', 1) if ':' in addr else (addr, '27016')
        port = int(port_str)
        query_port = port + 1 if port < 27000 else port
        
        # Parse gametype for perspective
        gametype = steam_data.get('gametype', '').lower()
        if '1pp' in gametype and '3pp' not in gametype:
            perspective = "1PP"
        elif '3pp' in gametype and '1pp' not in gametype:
            perspective = "3PP"  
        elif '1pp' in gametype and '3pp' in gametype:
            perspective = "1PP/3PP"
        else:
            perspective = "Unknown"
        
        # Determine server type based on name
        name = steam_data.get('name', '').lower()
        server_type = cls._determine_server_type(name)
        
        return cls(
            name=steam_data.get('name', 'Unknown Server'),
            ip=ip,
            port=port,
            query_port=query_port,
            map_name=steam_data.get('map', 'Unknown'),
            players=steam_data.get('players', 0),
            max_players=steam_data.get('max_players', 0),
            perspective=perspective,
            server_type=server_type,
            online=True,
            last_seen=time.time(),
            last_updated=time.time(),
            ping=-1  # Will be measured later
        )
    
    @staticmethod
    def _determine_server_type(name: str) -> str:
        """Determine server type from name"""
        name = name.lower()
        
        # Official servers
        if (('dayz' in name and any(pattern in name for pattern in [' de ', ' us ', ' eu ', ' uk ', ' fr ', ' au ', ' ca '])) or
            ('dayz official' in name) or
            ('official' in name and 'dayz' in name)):
            # Exclude obvious community servers
            if not any(char in name for char in ['[', ']', '|', '★', '♦', '●', '~', '!']):
                if not any(keyword in name for keyword in ['discord', 'www', 'http', 'x10', 'loot+', 'rp |', 'roleplay', 'clan']):
                    return 'official'
        
        # Private servers
        if any(keyword in name for keyword in ['private', 'whitelist', 'closed', 'invite', 'members']):
            return 'private'
            
        # Default to community
        return 'community'


class DZServerDatabase(QObject):
    """SQLite database manager for DayZ servers"""
    
    # Signals
    progressUpdate = Signal(int, str)  # percentage, message
    serversLoaded = Signal(list)       # list of server dicts
    serverPingUpdated = Signal(dict)   # single server dict with fresh ping
    
    def __init__(self, db_path: Optional[Path] = None):
        super().__init__()
        
        # Database path
        if db_path is None:
            self.db_path = Path.home() / ".cache" / "dzgui" / "servers.db"
        else:
            self.db_path = db_path
            
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Cleanup settings (no more cache)
        self.offline_cleanup_hours = 2
        self.delete_cleanup_hours = 24
        
        # Initialize database
        self._init_database()
        
        print(f"Database initialized: {self.db_path}")
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    query_port INTEGER NOT NULL,
                    map_name TEXT,
                    players INTEGER DEFAULT 0,
                    max_players INTEGER DEFAULT 0,
                    queue INTEGER DEFAULT 0,
                    ping INTEGER DEFAULT 999,
                    perspective TEXT DEFAULT 'Unknown',
                    time_of_day TEXT DEFAULT 'Unknown',
                    server_type TEXT DEFAULT 'community',
                    online BOOLEAN DEFAULT 0,
                    last_seen REAL NOT NULL,
                    last_updated REAL NOT NULL,
                    mods TEXT DEFAULT '[]',
                    UNIQUE(ip, query_port)
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_online ON servers(online)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_type ON servers(server_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_last_seen ON servers(last_seen)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_name ON servers(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_map ON servers(map_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_ping ON servers(ping)")
            
            # No more cache metadata table needed with BattleMetrics filtering
            
            conn.commit()
    
    
    
    def upsert_server(self, server: ServerRecord) -> int:
        """Insert or update a server record"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO servers (
                    name, ip, port, query_port, map_name, players, max_players,
                    queue, ping, perspective, time_of_day, server_type, online,
                    last_seen, last_updated, mods
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                server.name, server.ip, server.port, server.query_port,
                server.map_name, server.players, server.max_players,
                server.queue, server.ping, server.perspective, server.time_of_day,
                server.server_type, server.online, server.last_seen,
                server.last_updated, server.mods
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def upsert_servers_batch(self, servers: List[ServerRecord]):
        """Batch insert/update servers"""
        if not servers:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            data = []
            for server in servers:
                data.append((
                    server.name, server.ip, server.port, server.query_port,
                    server.map_name, server.players, server.max_players,
                    server.queue, server.ping, server.perspective, server.time_of_day,
                    server.server_type, server.online, server.last_seen,
                    server.last_updated, server.mods
                ))
            
            conn.executemany("""
                INSERT OR REPLACE INTO servers (
                    name, ip, port, query_port, map_name, players, max_players,
                    queue, ping, perspective, time_of_day, server_type, online,
                    last_seen, last_updated, mods
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            
            conn.commit()
            print(f"Batch updated {len(servers)} servers")
    
    def update_server_ping(self, ip: str, query_port: int, ping: int, players: int = None, max_players: int = None, emit_signal: bool = True):
        """Update server ping and player count"""
        with sqlite3.connect(self.db_path) as conn:
            if players is not None and max_players is not None:
                conn.execute("""
                    UPDATE servers 
                    SET ping = ?, players = ?, max_players = ?, last_updated = ?, online = 1
                    WHERE ip = ? AND query_port = ?
                """, (ping, players, max_players, time.time(), ip, query_port))
            else:
                conn.execute("""
                    UPDATE servers 
                    SET ping = ?, last_updated = ?, online = 1
                    WHERE ip = ? AND query_port = ?
                """, (ping, time.time(), ip, query_port))
            
            conn.commit()
            
            # Emit real-time signal with updated server data
            if emit_signal:
                # Get the updated server data
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM servers WHERE ip = ? AND query_port = ?
                """, (ip, query_port))
                
                row = cursor.fetchone()
                if row:
                    server_record = ServerRecord(
                        id=row['id'],
                        name=row['name'],
                        ip=row['ip'],
                        port=row['port'],
                        query_port=row['query_port'],
                        map_name=row['map_name'],
                        players=row['players'],
                        max_players=row['max_players'],
                        queue=row['queue'],
                        ping=row['ping'],
                        perspective=row['perspective'],
                        time_of_day=row['time_of_day'],
                        server_type=row['server_type'],
                        online=bool(row['online']),
                        last_seen=row['last_seen'],
                        last_updated=row['last_updated'],
                        mods=row['mods']
                    )
                    
                    # Emit signal for real-time UI update
                    self.serverPingUpdated.emit(server_record.to_dict())
    
    def mark_server_offline(self, ip: str, query_port: int):
        """Mark server as offline"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE servers 
                SET online = 0, last_updated = ?
                WHERE ip = ? AND query_port = ?
            """, (time.time(), ip, query_port))
            
            conn.commit()
    
    def cleanup_old_servers(self):
        """Clean up old/offline servers"""
        current_time = time.time()
        offline_cutoff = current_time - (self.offline_cleanup_hours * 3600)
        delete_cutoff = current_time - (self.delete_cleanup_hours * 3600)
        
        with sqlite3.connect(self.db_path) as conn:
            # Mark servers as offline if not seen recently
            cursor = conn.execute("""
                UPDATE servers 
                SET online = 0 
                WHERE last_seen < ? AND online = 1
            """, (offline_cutoff,))
            offline_count = cursor.rowcount
            
            # Delete servers not seen for 24 hours
            cursor = conn.execute("""
                DELETE FROM servers 
                WHERE last_seen < ?
            """, (delete_cutoff,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            
            if offline_count > 0 or deleted_count > 0:
                print(f"Cleanup: {offline_count} marked offline, {deleted_count} deleted")
    
    
    def get_server_counts(self) -> Dict[str, int]:
        """Get server counts by type"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT server_type, COUNT(*) 
                FROM servers 
                WHERE online = 1 
                GROUP BY server_type
            """)
            
            counts = {'official': 0, 'community': 0, 'private': 0}
            for server_type, count in cursor.fetchall():
                counts[server_type] = count
                
            return counts
    
    def search_servers(self, query: str, server_type: Optional[str] = None) -> List[Dict]:
        """Search servers by name, map, or other criteria"""
        query_lower = f"%{query.lower()}%"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if server_type:
                cursor = conn.execute("""
                    SELECT * FROM servers 
                    WHERE online = 1 AND server_type = ?
                    AND (LOWER(name) LIKE ? OR LOWER(map_name) LIKE ?)
                    ORDER BY ping ASC, name ASC
                """, (server_type, query_lower, query_lower))
            else:
                cursor = conn.execute("""
                    SELECT * FROM servers 
                    WHERE online = 1
                    AND (LOWER(name) LIKE ? OR LOWER(map_name) LIKE ?)
                    ORDER BY ping ASC, name ASC
                """, (query_lower, query_lower))
            
            servers = []
            for row in cursor:
                record = ServerRecord(
                    id=row['id'],
                    name=row['name'],
                    ip=row['ip'],
                    port=row['port'],
                    query_port=row['query_port'],
                    map_name=row['map_name'],
                    players=row['players'],
                    max_players=row['max_players'],
                    queue=row['queue'],
                    ping=row['ping'],
                    perspective=row['perspective'],
                    time_of_day=row['time_of_day'],
                    server_type=row['server_type'],
                    online=bool(row['online']),
                    last_seen=row['last_seen'],
                    last_updated=row['last_updated'],
                    mods=row['mods']
                )
                servers.append(record.to_dict())
            
            return servers
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total servers
            cursor = conn.execute("SELECT COUNT(*) FROM servers")
            stats['total'] = cursor.fetchone()[0]
            
            # Online servers
            cursor = conn.execute("SELECT COUNT(*) FROM servers WHERE online = 1")
            stats['online'] = cursor.fetchone()[0]
            
            # By type
            cursor = conn.execute("""
                SELECT server_type, COUNT(*) 
                FROM servers 
                WHERE online = 1 
                GROUP BY server_type
            """)
            stats['by_type'] = dict(cursor.fetchall())
            
            # No more cache age - using real-time BattleMetrics filtering
            stats['filtering_method'] = 'BattleMetrics API (real-time)'
                
            return stats
    
    def get_top_servers(self, limit: int = 150) -> List[Dict]:
        """Get top servers by player count"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT * FROM servers 
                WHERE online = 1
                ORDER BY players DESC, ping ASC, name ASC
                LIMIT ?
            """, (limit,))
            
            servers = []
            for row in cursor:
                record = ServerRecord(
                    id=row['id'],
                    name=row['name'],
                    ip=row['ip'],
                    port=row['port'],
                    query_port=row['query_port'],
                    map_name=row['map_name'],
                    players=row['players'],
                    max_players=row['max_players'],
                    queue=row['queue'],
                    ping=row['ping'],
                    perspective=row['perspective'],
                    time_of_day=row['time_of_day'],
                    server_type=row['server_type'],
                    online=bool(row['online']),
                    last_seen=row['last_seen'],
                    last_updated=row['last_updated'],
                    mods=row['mods']
                )
                servers.append(record.to_dict())
            
            return servers


# Singleton instance
_database = None

def get_database() -> DZServerDatabase:
    """Get singleton database instance"""
    global _database
    if _database is None:
        _database = DZServerDatabase()
    return _database