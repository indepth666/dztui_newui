#!/usr/bin/env python3
"""
DZGUI - Simple PySide6 Test
Test moderne interface with working components
"""

import sys
import os
import json
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QLabel, QPushButton, QScrollArea, QFrame,
                               QLineEdit, QCheckBox, QGroupBox, QProgressBar, QTabWidget, QSpinBox, QComboBox)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QPalette, QColor

# Import our native Python server manager and mod manager
from dzgui_server_manager import get_server_manager
from dzgui_mod_manager import get_mod_manager

class ModernDZGUI(QMainWindow):
    """Modern DZGUI with PySide6 Widgets"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DayZConnect - Modern Server Browser")
        self.setGeometry(100, 100, 1200, 800)
        
        # Favorites management
        self.favorites_file = Path.home() / ".config" / "dzgui" / "favorites.json"
        self.favorites_file.parent.mkdir(parents=True, exist_ok=True)
        self.favorites = self.load_favorites()
        
        # Server manager
        self.server_manager = get_server_manager()
        self.server_manager.serversUpdated.connect(self.on_servers_updated)
        self.server_manager.serverError.connect(self.on_server_error)
        self.server_manager.progressUpdate.connect(self.on_progress_update)
        self.server_manager.serverPingUpdated.connect(self.on_server_ping_updated)  # NEW: Real-time ping updates
        
        # Mod manager
        self.mod_manager = get_mod_manager()
        
        # Server data
        self.servers = []
        self.filtered_servers = []  # For search results
        
        # Server type selection
        self.selected_server_type = None  # No default selection - show all servers initially
        self.server_type_buttons = {}  # Store button references
        
        # Apply dark military theme
        self.setup_theme()
        
        # Create UI
        self.create_ui()
        
        # Set initial server type styling and load servers immediately
        QTimer.singleShot(50, self.update_server_type_styles)  # Apply styling after UI is ready
        QTimer.singleShot(100, self.load_servers_immediately)  # Load servers immediately
    
    def load_favorites(self):
        """Load favorites from JSON file"""
        try:
            if self.favorites_file.exists():
                with open(self.favorites_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading favorites: {e}")
            return []
    
    def save_favorites(self):
        """Save favorites to JSON file"""
        try:
            with open(self.favorites_file, 'w') as f:
                json.dump(self.favorites, f, indent=2)
        except Exception as e:
            print(f"Error saving favorites: {e}")
    
    def add_favorite(self, server_data):
        """Add server to favorites"""
        server_id = f"{server_data['name']}_{server_data.get('ip', 'unknown')}"
        
        # Check if already in favorites
        for fav in self.favorites:
            if fav.get('id') == server_id:
                return False  # Already favorite
        
        # Add to favorites
        favorite = {
            'id': server_id,
            'name': server_data['name'],
            'ip': server_data.get('ip', 'unknown'),
            'map': server_data.get('map', 'Unknown'),
            'added_date': str(Path().stat().st_ctime)
        }
        
        self.favorites.append(favorite)
        self.save_favorites()
        return True
    
    def remove_favorite(self, server_data):
        """Remove server from favorites"""
        server_id = f"{server_data['name']}_{server_data.get('ip', 'unknown')}"
        
        self.favorites = [fav for fav in self.favorites if fav.get('id') != server_id]
        self.save_favorites()
        return True
    
    def is_favorite(self, server_data):
        """Check if server is in favorites"""
        server_id = f"{server_data['name']}_{server_data.get('ip', 'unknown')}"
        return any(fav.get('id') == server_id for fav in self.favorites)
        
    def setup_theme(self):
        """Apply dark military theme"""
        palette = QPalette()
        
        # DayZ colors
        bg_color = QColor(15, 15, 15)        # #0f0f0f
        surface_color = QColor(26, 26, 26)   # #1a1a1a  
        card_color = QColor(42, 42, 42)      # #2a2a2a
        primary_color = QColor(74, 124, 89)  # #4a7c59
        text_color = QColor(232, 232, 232)   # #e8e8e8
        text_secondary = QColor(184, 184, 184) # #b8b8b8
        
        # Set palette colors
        palette.setColor(QPalette.Window, bg_color)
        palette.setColor(QPalette.WindowText, text_color)
        palette.setColor(QPalette.Base, surface_color)
        palette.setColor(QPalette.AlternateBase, card_color)
        palette.setColor(QPalette.ToolTipBase, card_color)
        palette.setColor(QPalette.ToolTipText, text_color)
        palette.setColor(QPalette.Text, text_color)
        palette.setColor(QPalette.Button, card_color)
        palette.setColor(QPalette.ButtonText, text_color)
        palette.setColor(QPalette.BrightText, text_color)
        palette.setColor(QPalette.Link, primary_color)
        palette.setColor(QPalette.Highlight, primary_color)
        palette.setColor(QPalette.HighlightedText, text_color)
        
        self.setPalette(palette)
        
        # Modern font
        font = QFont("Cantarell", 10)
        self.setFont(font)
        
        # Custom stylesheet for modern look
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f0f0f;
                color: #e8e8e8;
            }
            
            QWidget {
                background-color: #1a1a1a;
                color: #e8e8e8;
            }
            
            QPushButton {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                color: #e8e8e8;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 24px;
            }
            
            QPushButton:hover {
                background-color: #333333;
                border-color: #4a7c59;
            }
            
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
            
            QPushButton.primary {
                background-color: #4a7c59;
                color: white;
            }
            
            QPushButton.primary:hover {
                background-color: #5a8c69;
            }
            
            QLineEdit {
                background-color: #2a2a2a;
                border: 2px solid #404040;
                border-radius: 6px;
                padding: 8px;
                color: #e8e8e8;
            }
            
            QLineEdit:focus {
                border-color: #4a7c59;
            }
            
            QLabel {
                color: #e8e8e8;
                background-color: transparent;
            }
            
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 8px;
            }
            
            QScrollArea {
                border: none;
                background-color: #1a1a1a;
            }
            
            QCheckBox {
                color: #e8e8e8;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #404040;
                border-radius: 4px;
                background-color: #2a2a2a;
            }
            
            QCheckBox::indicator:checked {
                background-color: #4a7c59;
                border-color: #4a7c59;
            }
            
            QGroupBox {
                color: #b8b8b8;
                font-weight: bold;
                border: 2px solid #404040;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 8px 0 8px;
            }
            
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 6px;
                background-color: #2a2a2a;
                text-align: center;
            }
            
            QProgressBar::chunk {
                background-color: #4a7c59;
                border-radius: 4px;
            }
        """)
    
    def create_ui(self):
        """Create the main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sidebar
        self.create_sidebar(main_layout)
        
        # Main content
        self.create_main_content(main_layout)
    
    def create_sidebar(self, parent_layout):
        """Create sidebar with filters and actions"""
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setFrameStyle(QFrame.Box)
        
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Title
        title = QLabel("DayZConnect")
        title.setFont(QFont("Cantarell", 18, QFont.Bold))
        layout.addWidget(title)
        
        subtitle = QLabel("Modern Server Browser")
        subtitle.setStyleSheet("color: #b8b8b8; font-size: 11px;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(16)
        
        # Quick Actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        # Server limit selector removed - now loads all available servers
        refresh_btn = QPushButton("↻ Refresh Servers")
        refresh_btn.setObjectName("primary")
        refresh_btn.setStyleSheet("QPushButton { background-color: #4a7c59; color: white; }")
        refresh_btn.clicked.connect(self.manual_refresh_servers)
        actions_layout.addWidget(refresh_btn)
        
        self.quick_connect_btn = QPushButton("⚡ Quick Connect")
        self.quick_connect_btn.clicked.connect(self.quick_connect_favorite)
        actions_layout.addWidget(self.quick_connect_btn)
        
        # Add Server button for direct connect
        add_server_btn = QPushButton("➕ Add Server")
        add_server_btn.setStyleSheet("QPushButton { background-color: #5c7a89; color: white; }")
        add_server_btn.clicked.connect(self.show_add_server_dialog)
        actions_layout.addWidget(add_server_btn)
        
        lan_btn = QPushButton("📡 Scan LAN")
        actions_layout.addWidget(lan_btn)
        
        layout.addWidget(actions_group)
        
        # Favorites section
        self.favorites_group = QGroupBox("Mes Favoris")
        self.favorites_layout = QVBoxLayout(self.favorites_group)
        
        # Will be populated by update_favorites_display()
        self.update_favorites_display()
        
        layout.addWidget(self.favorites_group)
        
        # Filters
        filters_group = QGroupBox("Filters")
        filters_layout = QVBoxLayout(filters_group)
        
        self.filters = {}
        filter_options = [
            ("Show Empty", True),
            ("Show Full", True), 
            ("Show Modded", True),
            ("1PP Only", False),
            ("3PP Only", False)
        ]
        
        for name, checked in filter_options:
            cb = QCheckBox(name)
            cb.setChecked(checked)
            cb.stateChanged.connect(self.apply_filters)  # Connect to filter system
            self.filters[name] = cb
            filters_layout.addWidget(cb)
        
        layout.addWidget(filters_group)
        
        # Server Types
        types_group = QGroupBox("Server Types")
        types_layout = QVBoxLayout(types_group)
        
        # Create server type buttons with exclusive selection behavior
        server_types = [
            (None, "🌍 All Servers"),  # New option to show all servers
            ("official", "🏛️ Official Servers"),
            ("community", "👥 Community"), 
            ("private", "🔒 Private Hive")
        ]
        
        for type_key, type_label in server_types:
            btn = QPushButton(type_label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=type_key: self.select_server_type(t))
            types_layout.addWidget(btn)
            self.server_type_buttons[type_key] = btn
        
        # Set "All Servers" as default selection
        self.server_type_buttons[None].setChecked(True)
        self.update_server_type_styles()
        
        layout.addWidget(types_group)
        
        layout.addStretch()
        parent_layout.addWidget(sidebar)
    
    def create_main_content(self, parent_layout):
        """Create main content area with tabs"""
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #404040;
                background-color: #1a1a1a;
            }
            QTabBar::tab {
                background-color: #2a2a2a;
                color: #e8e8e8;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #404040;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #1a1a1a;
                border-bottom: 1px solid #1a1a1a;
            }
            QTabBar::tab:hover {
                background-color: #3a3a3a;
            }
        """)
        
        # Create server tab
        self.server_tab = QWidget()
        self.create_server_tab_content()
        self.tab_widget.addTab(self.server_tab, "🖥️ Servers")
        
        # Create mod tab
        self.mod_tab = QWidget()
        self.create_mod_tab_content()
        self.tab_widget.addTab(self.mod_tab, "🧩 Mods")
        
        layout.addWidget(self.tab_widget)
        
        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #b8b8b8; font-size: 11px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        connection_status = QLabel("Connected ●")
        connection_status.setStyleSheet("color: #4a7c59; font-size: 11px;")
        status_layout.addWidget(connection_status)
        
        layout.addLayout(status_layout)
        
        parent_layout.addWidget(main_widget)
    
    def create_server_tab_content(self):
        """Create server tab content"""
        layout = QVBoxLayout(self.server_tab)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header with search
        header_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search servers by name, map, or players...")
        self.search_input.setFixedHeight(40)
        self.search_input.textChanged.connect(self.filter_servers)
        header_layout.addWidget(self.search_input)
        
        layout.addLayout(header_layout)
        
        # Filter bar
        self.create_filter_bar(layout)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)
        
        # Server list
        self.server_scroll = QScrollArea()
        self.server_scroll.setWidgetResizable(True)
        self.server_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.server_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.server_list_widget = QWidget()
        self.server_list_layout = QVBoxLayout(self.server_list_widget)
        self.server_list_layout.setSpacing(8)
        
        self.server_scroll.setWidget(self.server_list_widget)
        layout.addWidget(self.server_scroll)
    
    def create_mod_tab_content(self):
        """Create mod management tab content"""
        layout = QVBoxLayout(self.mod_tab)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Mod header
        header_layout = QHBoxLayout()
        mod_title = QLabel("🧩 Mod Management")
        mod_title.setFont(QFont("Cantarell", 14, QFont.Bold))
        header_layout.addWidget(mod_title)
        
        header_layout.addStretch()
        
        # Refresh mods button
        refresh_mods_btn = QPushButton("↻ Scan Mods")
        refresh_mods_btn.setStyleSheet("QPushButton { background-color: #4a7c59; color: white; }")
        refresh_mods_btn.clicked.connect(self.refresh_mods)
        header_layout.addWidget(refresh_mods_btn)
        
        layout.addLayout(header_layout)
        
        # Mod statistics
        self.mod_stats_layout = QHBoxLayout()
        self.update_mod_stats()
        layout.addLayout(self.mod_stats_layout)
        
        # Mod list
        self.mod_scroll = QScrollArea()
        self.mod_scroll.setWidgetResizable(True)
        self.mod_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mod_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.mod_list_widget = QWidget()
        self.mod_list_layout = QVBoxLayout(self.mod_list_widget)
        self.mod_list_layout.setSpacing(8)
        
        self.mod_scroll.setWidget(self.mod_list_widget)
        layout.addWidget(self.mod_scroll)
        
        # Load mods initially
        self.refresh_mods()
    
    def create_server_card(self, server_data):
        """Create a server card widget"""
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setFixedHeight(100)
        
        # Store server data in widget for later reference
        card._server_data = server_data
        card.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 12px;
                padding: 8px;
            }
            QFrame:hover {
                border-color: #4a7c59;
                background-color: #333333;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        
        # Header
        header_layout = QHBoxLayout()
        
        name_label = QLabel(server_data["name"])
        name_label.setFont(QFont("Cantarell", 11, QFont.Bold))
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # Favorite button
        is_fav = self.is_favorite(server_data)
        fav_btn = QPushButton("★" if is_fav else "☆")
        fav_btn.setFixedSize(24, 24)
        fav_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {'#FFD700' if is_fav else '#666666'};
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: #FFD700;
                background-color: rgba(255, 215, 0, 0.1);
                border-radius: 12px;
            }}
        """)
        fav_btn.clicked.connect(lambda: self.toggle_favorite(server_data))
        header_layout.addWidget(fav_btn)
        
        # Status and players
        status_color = "#4CAF50" if server_data["online"] else "#F44336"
        players_label = QLabel(f"● {server_data['players']}/{server_data['max_players']}")
        players_label.setStyleSheet(f"color: {status_color};")
        header_layout.addWidget(players_label)
        
        # Connect button for this server
        connect_btn = QPushButton("⚡ Connect")
        connect_btn.setFixedSize(80, 24)
        connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a7c59;
                color: white;
                border: 1px solid #5a8c69;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #5a8c69;
                border-color: #6a9c79;
            }
            QPushButton:pressed {
                background-color: #3a6c49;
            }
        """)
        connect_btn.clicked.connect(lambda: self.connect_to_server(server_data))
        header_layout.addWidget(connect_btn)
        
        layout.addLayout(header_layout)
        
        # Info row
        info_layout = QHBoxLayout()
        
        map_label = QLabel(f"Map: {server_data['map']}")
        map_label.setStyleSheet("color: #b8b8b8; font-size: 10px;")
        info_layout.addWidget(map_label)
        
        # Mods information from BattleMetrics
        try:
            mods_str = server_data.get('mods', '[]')
            
            if isinstance(mods_str, str):
                import json
                mods_list = json.loads(mods_str) if mods_str != '[]' else []
            else:
                mods_list = mods_str if isinstance(mods_str, list) else []
            
            if mods_list:
                mod_count = len(mods_list)
                mod_label = QLabel(f"🔧 {mod_count} mod{'s' if mod_count != 1 else ''}")
                mod_label.setStyleSheet("color: #ff9800; font-size: 10px; font-weight: bold;")
                
                # Create tooltip with mod names if available
                tooltip_lines = [f"This server uses {mod_count} mods:"]
                for i, mod in enumerate(mods_list[:10]):  # Show first 10 mods
                    if isinstance(mod, dict):
                        mod_name = mod.get('name', f"Mod {mod.get('id', 'Unknown')}")
                        mod_id = mod.get('id', '')
                        tooltip_lines.append(f"• {mod_name} ({mod_id})")
                    else:
                        # Old format - just ID
                        tooltip_lines.append(f"• Mod {mod}")
                
                if len(mods_list) > 10:
                    tooltip_lines.append(f"... and {len(mods_list) - 10} more")
                
                mod_label.setToolTip('\n'.join(tooltip_lines))
                info_layout.addWidget(mod_label)
            else:
                # No mods - vanilla server
                vanilla_label = QLabel("✅ Vanilla")
                vanilla_label.setStyleSheet("color: #4CAF50; font-size: 10px; font-weight: bold;")
                vanilla_label.setToolTip("This server uses no mods (vanilla DayZ)")
                info_layout.addWidget(vanilla_label)
        except Exception as e:
            print(f"Error displaying mods for {server_data.get('name', 'Unknown')}: {e}")
            # Fallback - just show unknown
            unknown_label = QLabel("❓ Mods")
            unknown_label.setStyleSheet("color: #9E9E9E; font-size: 10px;")
            unknown_label.setToolTip("Mod information not available")
            info_layout.addWidget(unknown_label)
        
        # Ping with colors and status
        ping = server_data.get("ping", -1)
        if ping == -1:
            ping_text = "Pinging..."
            ping_color = "#b8b8b8"
        elif ping >= 999:
            ping_text = "Offline"
            ping_color = "#F44336"  # Red
        elif ping < 50:
            ping_text = f"{ping}ms"
            ping_color = "#4CAF50"  # Green - Excellent
        elif ping < 100:
            ping_text = f"{ping}ms"
            ping_color = "#8BC34A"  # Light Green - Good
        elif ping < 200:
            ping_text = f"{ping}ms"
            ping_color = "#FF9800"  # Orange - Acceptable
        else:
            ping_text = f"{ping}ms"
            ping_color = "#F44336"  # Red - Poor
        
        ping_label = QLabel(f"Ping: {ping_text}")
        ping_label.setStyleSheet(f"color: {ping_color}; font-size: 10px; font-weight: bold;")
        info_layout.addWidget(ping_label)
        
        layout.addLayout(info_layout)
        
        layout.addStretch()
        
        return card
    
    def on_servers_updated(self, servers):
        """Handle servers updated signal"""
        # Only update if we don't have servers already (avoid overriding real-time updates)
        if not self.servers or len(servers) > len(self.servers):
            self.servers = servers
            # Apply server type filter only if explicitly selected by user
            if hasattr(self, 'selected_server_type') and self.selected_server_type is not None:
                self.filter_by_server_type(self.selected_server_type)
            else:
                # Show all servers by default - no automatic filtering
                if self.server_list_layout.count() == 0:
                    self.populate_server_list()
    
    def on_server_error(self, error_msg):
        """Handle server error signal"""
        self.status_label.setText(f"Error: {error_msg}")
        self.progress.setVisible(False)
    
    def on_progress_update(self, percentage, message):
        """Handle progress update signal"""
        if percentage == 0:
            self.progress.setVisible(True)
            self.progress.setRange(0, 100)
            # Reset early display flag
            self._ui_ready_for_play = False
        
        self.progress.setValue(percentage)
        self.status_label.setText(message)
        
        # Early Display styling à 60%+ 
        if percentage >= 90 and "Ready to play" in message and not getattr(self, '_ui_ready_for_play', False):
            self._ui_ready_for_play = True
            # Change progress bar style - vert pour "ready"
            self.progress.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #4CAF50;
                    border-radius: 5px;
                    background-color: #2a2a2a;
                    text-align: center;
                    color: white;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;  /* Vert = Ready */
                    border-radius: 3px;
                }
            """)
            # Change status to green
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            print("🎉 UI Ready for play mode activated!")
            
        elif percentage < 90:
            # Normal progress style - bleu
            self.progress.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #4a7c59;
                    border-radius: 5px;
                    background-color: #2a2a2a;
                    text-align: center;
                    color: white;
                }
                QProgressBar::chunk {
                    background-color: #4a7c59;  /* Bleu = Loading */
                    border-radius: 3px;
                }
            """)
            self.status_label.setStyleSheet("color: #e8e8e8;")
        
        if percentage == 100:
            # Final completion - hide after delay and reset styling
            QTimer.singleShot(3000, lambda: (
                self.progress.setVisible(False),
                self.status_label.setStyleSheet("color: #e8e8e8;"),
                setattr(self, '_ui_ready_for_play', False)
            ))
    
    def on_server_ping_updated(self, server_data):
        """Handle real-time server ping updates - add server to UI immediately"""
        try:
            # NO SERVER TYPE FILTERING DURING LOADING - Show ALL servers that respond
            # Only apply server type filtering when user explicitly selects a type
            
            # Update existing server in list or add new one
            server_found = False
            for i, existing_server in enumerate(self.servers):
                if (existing_server.get('ip') == server_data.get('ip') and 
                    existing_server.get('qport') == server_data.get('qport')):
                    # Update existing server
                    self.servers[i] = server_data
                    server_found = True
                    break
            
            if not server_found:
                # Add new server to list
                self.servers.append(server_data)
            
            # Check if server type filtering is explicitly active
            server_type_filter_active = (hasattr(self, 'selected_server_type') and 
                                       self.selected_server_type is not None)
            
            if server_type_filter_active:
                # Server type filter is active - check if this server matches
                server_type = server_data.get('server_type', 'community')
                if server_type != self.selected_server_type:
                    return  # Skip display if doesn't match active filter
            
            # Update filtered list if we have other active filters (search, ping, etc.)
            if hasattr(self, '_filters_applied') and self._filters_applied:
                # Reapply current filters to include the new/updated server
                self.apply_filters()
            else:
                # No active filters, just add to main display
                if not server_found:
                    self.add_server_to_ui(server_data)
                else:
                    self.update_server_in_ui(server_data)
                    
        except Exception as e:
            print(f"Error in real-time ping update: {e}")
    
    def clear_server_list_ui(self):
        """Clear the server list UI display only"""
        try:
            # Clear existing servers properly
            while self.server_list_layout.count():
                item = self.server_list_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
            print("Server list UI cleared")
        except Exception as e:
            print(f"Error clearing server list UI: {e}")
    
    def add_server_to_ui(self, server_data):
        """Add a single server to the UI immediately"""
        try:
            # Only add if server has a valid ping (not -1 or 999)
            ping = server_data.get('ping', 999)
            if ping == -1 or ping >= 999:
                return
                
            # Create server card
            server_card = self.create_server_card(server_data)
            
            # Insert in the right position (sorted by ping)
            inserted = False
            for i in range(self.server_list_layout.count()):
                widget = self.server_list_layout.itemAt(i).widget()
                if widget and hasattr(widget, '_server_data'):
                    widget_ping = widget._server_data.get('ping', 999)
                    if ping < widget_ping:
                        self.server_list_layout.insertWidget(i, server_card)
                        inserted = True
                        break
            
            if not inserted:
                # Add at the end if not inserted elsewhere
                self.server_list_layout.addWidget(server_card)
                
            print(f"➕ Added to UI: {server_data.get('name', 'Unknown')[:40]}... - {ping}ms")
            
        except Exception as e:
            print(f"Error adding server to UI: {e}")
    
    def update_server_in_ui(self, server_data):
        """Update an existing server in the UI"""
        try:
            ip = server_data.get('ip')
            qport = server_data.get('qport')
            
            # Find and update existing server card
            for i in range(self.server_list_layout.count()):
                widget = self.server_list_layout.itemAt(i).widget()
                if (widget and hasattr(widget, '_server_data') and
                    widget._server_data.get('ip') == ip and 
                    widget._server_data.get('qport') == qport):
                    
                    # Update the widget's data and display
                    widget._server_data = server_data
                    self.update_server_card_display(widget, server_data)
                    print(f"🔄 Updated in UI: {server_data.get('name', 'Unknown')[:40]}... - {server_data.get('ping', 999)}ms")
                    break
                    
        except Exception as e:
            print(f"Error updating server in UI: {e}")
    
    def update_server_card_display(self, widget, server_data):
        """Update the display of an existing server card"""
        try:
            # Find and update ping label
            ping = server_data.get('ping', 999)
            players = server_data.get('players', 0)
            max_players = server_data.get('max_players', 0)
            
            # Update ping display
            ping_labels = widget.findChildren(QLabel)
            for label in ping_labels:
                if 'Ping:' in label.text():
                    if ping < 999:
                        label.setText(f"Ping: {ping}ms")
                        # Color code ping
                        if ping < 50:
                            label.setStyleSheet("color: #4CAF50; font-weight: bold;")  # Green
                        elif ping < 100:
                            label.setStyleSheet("color: #FF9800; font-weight: bold;")  # Orange
                        else:
                            label.setStyleSheet("color: #F44336; font-weight: bold;")  # Red
                    else:
                        label.setText("Ping: ---")
                        label.setStyleSheet("color: #9E9E9E;")
                elif 'Players:' in label.text():
                    label.setText(f"Players: {players}/{max_players}")
                    
        except Exception as e:
            print(f"Error updating server card display: {e}")
    
    def populate_server_list(self):
        """Populate the server list"""
        # Clear existing servers properly
        while self.server_list_layout.count():
            item = self.server_list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        
        # Use filtered servers if we have applied filters, even if the result is empty
        # This fixes the bug where empty filter results showed all servers
        if hasattr(self, 'filtered_servers') and hasattr(self, '_filters_applied') and self._filters_applied:
            servers_to_show = self.filtered_servers  # Even if empty!
        else:
            servers_to_show = self.servers
        
        # Add server cards
        for server in servers_to_show:
            card = self.create_server_card(server)
            self.server_list_layout.addWidget(card)
        
        # Add stretch at the end
        self.server_list_layout.addStretch()
        
        # Update status with better messaging
        if hasattr(self, '_filters_applied') and self._filters_applied:
            if len(servers_to_show) == 0:
                self.status_label.setText("No servers match the current filters")
            else:
                self.status_label.setText(f"{len(servers_to_show)} servers found (filtered from {len(self.servers)})")
        else:
            self.status_label.setText(f"{len(servers_to_show)} servers loaded")
    
    def load_servers_immediately(self):
        """Load servers immediately on startup using BattleMetrics filtering"""
        try:
            print("Loading servers with BattleMetrics filtering...")
            self.status_label.setText("Loading popular servers...")
            # Start fresh server load - no more cache checking
            self.server_manager.refresh_servers()
        except Exception as e:
            print(f"Error loading servers: {e}")
            self.status_label.setText(f"Error loading servers: {e}")
    
    def refresh_servers(self):
        """Refresh server list using BattleMetrics API filtering"""
        try:
            self.status_label.setText("Starting BattleMetrics server refresh...")
            print("Starting server refresh with BattleMetrics filtering...")
            
            # Clear the display for fresh load
            print("Clearing server list for fresh load")
            self.servers = []
            self.filtered_servers = []
            self.clear_server_list_ui()
            
            # Use BattleMetrics filtering
            self.server_manager.refresh_servers()
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            print(f"Error refreshing servers: {e}")
    
    def manual_refresh_servers(self):
        """Manual refresh triggered by user"""
        try:
            self.status_label.setText("Manual refresh starting...")
            print("Manual server refresh requested - clearing everything")
            
            # Always clear for manual refresh
            self.servers = []
            self.filtered_servers = []
            self.clear_server_list_ui()
            
            # Force refresh with BattleMetrics filtering
            self.server_manager.refresh_servers()
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            print(f"Error in manual refresh: {e}")
    
    
    def load_sample_servers(self):
        """Load sample server data"""
        self.servers = [
            {
                "name": "[SAMPLE] DayZ Official Server",
                "map": "Chernarus",
                "perspective": "1PP", 
                "time": "14:32",
                "players": 42,
                "max_players": 60,
                "queue": 0,
                "ping": 23,
                "online": True,
                "ip": "192.168.1.100",
                "qport": "27016"
            },
            {
                "name": "[SAMPLE] Community PvP Server",
                "map": "Livonia",
                "perspective": "3PP",
                "time": "18:45",
                "players": 15,
                "max_players": 80, 
                "queue": 2,
                "ping": 67,
                "online": True,
                "ip": "192.168.1.101",
                "qport": "27016"
            },
            {
                "name": "[SAMPLE] Vanilla Experience",
                "map": "Chernarus",
                "perspective": "1PP/3PP",
                "time": "09:15",
                "players": 28,
                "max_players": 60,
                "queue": 0,
                "ping": 12,
                "online": True,
                "ip": "192.168.1.102",
                "qport": "27016"
            },
            {
                "name": "[SAMPLE] Modded Survival",
                "map": "Deer Isle", 
                "perspective": "1PP",
                "time": "21:07",
                "players": 55,
                "max_players": 100,
                "queue": 5,
                "ping": 89,
                "online": True,
                "ip": "192.168.1.103",
                "qport": "27016"
            }
        ]
        
        self.populate_server_list()
    
    def update_favorites_display(self):
        """Update the favorites display in sidebar"""
        # Clear existing favorites display
        for i in reversed(range(self.favorites_layout.count())):
            child = self.favorites_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if not self.favorites:
            no_fav_label = QLabel("Aucun favori")
            no_fav_label.setStyleSheet("color: #b8b8b8; font-style: italic; font-size: 11px;")
            self.favorites_layout.addWidget(no_fav_label)
            self.quick_connect_btn.setEnabled(False)
            self.quick_connect_btn.setText("⚡ Quick Connect (aucun favori)")
        else:
            # Show up to 5 favorites
            for i, fav in enumerate(self.favorites[:5]):
                fav_btn = QPushButton(f"★ {fav['name'][:25]}{'...' if len(fav['name']) > 25 else ''}")
                fav_btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 6px;
                        background-color: #2a2a2a;
                        border: 1px solid #4a7c59;
                        color: #e8e8e8;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #4a7c59;
                        color: white;
                    }
                """)
                fav_btn.clicked.connect(lambda checked, f=fav: self.connect_to_favorite(f))
                self.favorites_layout.addWidget(fav_btn)
            
            # Update quick connect button
            primary_fav = self.favorites[0]  # First favorite is primary
            self.quick_connect_btn.setEnabled(True)
            self.quick_connect_btn.setText(f"⚡ Connect to {primary_fav['name'][:15]}{'...' if len(primary_fav['name']) > 15 else ''}")
    
    def quick_connect_favorite(self):
        """Quick connect to primary favorite"""
        if self.favorites:
            self.connect_to_favorite(self.favorites[0])
    
    def connect_to_favorite(self, favorite):
        """Connect to a favorite server"""
        print(f"Connecting to favorite: {favorite['name']} ({favorite['ip']})")
        self.status_label.setText(f"Connecting to {favorite['name']}...")
        # TODO: Implement actual connection logic
    
    def toggle_favorite(self, server_data):
        """Toggle favorite status of a server"""
        if self.is_favorite(server_data):
            self.remove_favorite(server_data)
            print(f"Removed from favorites: {server_data['name']}")
        else:
            self.add_favorite(server_data)
            print(f"Added to favorites: {server_data['name']}")
        
        # Update displays
        self.update_favorites_display()
        self.populate_server_list()  # Refresh server list to update star icons
    
    def filter_servers(self):
        """Filter servers based on search input (now integrated with apply_filters)"""
        # Just call the main filter function which handles search + all other filters
        self.apply_filters()
    
    def create_filter_bar(self, parent_layout):
        """Create the filter bar between search and server list"""
        filter_frame = QFrame()
        filter_frame.setFrameStyle(QFrame.Box)
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 1px solid #4a7c59;
                border-radius: 8px;
                padding: 8px;
                margin: 4px;
            }
        """)
        
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setSpacing(16)
        filter_layout.setContentsMargins(12, 8, 12, 8)
        
        # Ping Filter
        ping_label = QLabel("🏓 Ping:")
        ping_label.setStyleSheet("color: #e8e8e8; font-weight: bold; font-size: 11px;")
        filter_layout.addWidget(ping_label)
        
        self.ping_filter = QComboBox()
        self.ping_filter.addItems(["All", "< 50ms", "< 100ms", "< 200ms", "> 200ms", "Offline"])
        self.ping_filter.setStyleSheet(self.get_combobox_style())
        self.ping_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.ping_filter)
        
        # Map Filter
        map_label = QLabel("🗺️ Map:")
        map_label.setStyleSheet("color: #e8e8e8; font-weight: bold; font-size: 11px;")
        filter_layout.addWidget(map_label)
        
        self.map_filter = QComboBox()
        self.map_filter.addItems(["All", "Chernarus", "Livonia", "Namalsk", "Sakhal", "Other"])
        self.map_filter.setStyleSheet(self.get_combobox_style())
        self.map_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.map_filter)
        
        # Status Filter (Player count)
        status_label = QLabel("👥 Status:")
        status_label.setStyleSheet("color: #e8e8e8; font-weight: bold; font-size: 11px;")
        filter_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Empty", "Low (1-25%)", "Medium (25-75%)", "High (75-99%)", "Full"])
        self.status_filter.setStyleSheet(self.get_combobox_style())
        self.status_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.status_filter)
        
        # Sort Options
        sort_label = QLabel("📊 Sort:")
        sort_label.setStyleSheet("color: #e8e8e8; font-weight: bold; font-size: 11px;")
        filter_layout.addWidget(sort_label)
        
        self.sort_filter = QComboBox()
        self.sort_filter.addItems(["Name", "Players", "Ping", "Map"])
        self.sort_filter.setCurrentText("Ping")  # Default sort by ping
        self.sort_filter.setStyleSheet(self.get_combobox_style())
        self.sort_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.sort_filter)
        
        # Add stretch to push everything left
        filter_layout.addStretch()
        
        # Clear Filters button
        clear_btn = QPushButton("🔄 Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                border: 1px solid #555555;
                color: #e8e8e8;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #444444;
                border-color: #4a7c59;
            }
        """)
        clear_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(clear_btn)
        
        parent_layout.addWidget(filter_frame)
    
    def get_combobox_style(self):
        """Get consistent ComboBox style"""
        return """
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #4a7c59;
                color: #e8e8e8;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 80px;
                font-size: 11px;
            }
            QComboBox:hover {
                border-color: #5a8c69;
                background-color: #333333;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #e8e8e8;
                margin-right: 8px;
            }
        """
    
    def clear_filters(self):
        """Reset all filters to default"""
        self.ping_filter.setCurrentText("All")
        self.map_filter.setCurrentText("All")
        self.status_filter.setCurrentText("All")
        self.sort_filter.setCurrentText("Ping")
        self.search_input.clear()
        
        # Reset sidebar checkboxes to default
        if hasattr(self, 'filters'):
            self.filters["Show Empty"].setChecked(True)
            self.filters["Show Full"].setChecked(True)
            self.filters["Show Modded"].setChecked(True)
            self.filters["1PP Only"].setChecked(False)
            self.filters["3PP Only"].setChecked(False)
        
        # Apply filters after clearing (will show all servers, sorted by ping)
        self.apply_filters()
    
    def apply_filters(self):
        """Apply filters using BattleMetrics API or client-side for ping/sorting only"""
        # Get current filter values
        search_text = self.search_input.text().lower().strip()
        ping_filter = self.ping_filter.currentText() if hasattr(self, 'ping_filter') else "All"
        map_filter = self.map_filter.currentText() if hasattr(self, 'map_filter') else "All"
        status_filter = self.status_filter.currentText() if hasattr(self, 'status_filter') else "All"
        sort_option = self.sort_filter.currentText() if hasattr(self, 'sort_filter') else "Ping"
        
        # For some filters, we need to refetch from BattleMetrics API
        api_filters_needed = (search_text or map_filter != "All")
        
        if api_filters_needed:
            # Use BattleMetrics API filtering for search and map
            self.apply_battlemetrics_filters()
            return
        
        # For ping and player count filtering, we can filter client-side since we have the data
        if not self.servers:
            return
        
        # Check sidebar checkboxes
        sidebar_filters_active = False
        if hasattr(self, 'filters'):
            sidebar_filters_active = (
                not self.filters.get("Show Empty", QCheckBox()).isChecked() or
                not self.filters.get("Show Full", QCheckBox()).isChecked() or
                not self.filters.get("Show Modded", QCheckBox()).isChecked() or
                self.filters.get("1PP Only", QCheckBox()).isChecked() or
                self.filters.get("3PP Only", QCheckBox()).isChecked()
            )
        
        filters_active = (ping_filter != "All" or 
                         status_filter != "All" or
                         sidebar_filters_active)
        
        self._filters_applied = filters_active
        
        # Start with all servers
        filtered_servers = self.servers.copy()
        
        # Apply client-side filters (ping, player count, sidebar filters)
        filtered_servers = self.apply_client_side_filters(filtered_servers, ping_filter, status_filter)
        
        # Apply sorting
        filtered_servers = self.apply_sorting(filtered_servers, sort_option)
        
        # Store and display
        self.filtered_servers = filtered_servers
        self.display_servers(filtered_servers)
    
    def apply_battlemetrics_filters(self):
        """Apply filters using BattleMetrics API for search and map"""
        # Get current filter values
        search_text = self.search_input.text().lower().strip()
        map_filter = self.map_filter.currentText() if hasattr(self, 'map_filter') else "All"
        
        # Map UI filter names to BattleMetrics API concepts
        search_term = search_text if search_text else None
        
        # Convert map filter
        region = None
        if map_filter == "Chernarus":
            # BattleMetrics doesn't have map filters, but we can search for it
            search_term = "chernarus" if not search_term else f"{search_term} chernarus"
        elif map_filter == "Livonia":
            search_term = "livonia" if not search_term else f"{search_term} livonia"
        elif map_filter == "Namalsk":
            search_term = "namalsk" if not search_term else f"{search_term} namalsk"
        
        print(f"🎯 Applying BattleMetrics filters: search='{search_term}', region='{region}'")
        self.status_label.setText("Applying filters via BattleMetrics API...")
        
        # Trigger fresh server fetch with filters
        self.server_manager.refresh_servers(
            search_term=search_term,
            region=region
        )
    
    def apply_client_side_filters(self, servers, ping_filter, status_filter):
        """Apply client-side filters for ping and player count"""
        filtered = servers
        
        # Apply ping filter
        if ping_filter != "All":
            ping_filtered = []
            for server in filtered:
                ping = server.get('ping', -1)
                if ping_filter == "< 50ms" and 0 <= ping < 50:
                    ping_filtered.append(server)
                elif ping_filter == "< 100ms" and 0 <= ping < 100:
                    ping_filtered.append(server)
                elif ping_filter == "< 200ms" and 0 <= ping < 200:
                    ping_filtered.append(server)
                elif ping_filter == "> 200ms" and ping >= 200 and ping < 999:
                    ping_filtered.append(server)
                elif ping_filter == "Offline" and ping >= 999:
                    ping_filtered.append(server)
            filtered = ping_filtered
        
        # Apply status filter (player count)
        if status_filter != "All":
            status_filtered = []
            for server in filtered:
                players = server.get('players', 0)
                max_players = server.get('max_players', 1)
                percentage = (players / max_players * 100) if max_players > 0 else 0
                
                if status_filter == "Empty" and players == 0:
                    status_filtered.append(server)
                elif status_filter == "Low (1-25%)" and 0 < percentage <= 25:
                    status_filtered.append(server)
                elif status_filter == "Medium (25-75%)" and 25 < percentage <= 75:
                    status_filtered.append(server)
                elif status_filter == "High (75-99%)" and 75 < percentage < 100:
                    status_filtered.append(server)
                elif status_filter == "Full" and percentage >= 100:
                    status_filtered.append(server)
            filtered = status_filtered
        
        # Apply sidebar checkbox filters
        if hasattr(self, 'filters'):
            sidebar_filtered = []
            for server in filtered:
                # Show Empty filter
                if not self.filters["Show Empty"].isChecked() and server.get('players', 0) == 0:
                    continue
                
                # Show Full filter
                if not self.filters["Show Full"].isChecked():
                    players = server.get('players', 0)
                    max_players = server.get('max_players', 1)
                    if players >= max_players and max_players > 0:
                        continue
                
                # Show Modded filter (simplified heuristic)
                if not self.filters["Show Modded"].isChecked():
                    server_name = server.get('name', '').lower()
                    if any(keyword in server_name for keyword in ['mod', 'trader', 'loot+', 'custom']):
                        continue
                
                # 1PP Only filter
                if self.filters["1PP Only"].isChecked():
                    perspective = server.get('perspective', '').lower()
                    if '1pp' not in perspective or '3pp' in perspective:
                        continue
                
                # 3PP Only filter
                if self.filters["3PP Only"].isChecked():
                    perspective = server.get('perspective', '').lower()  
                    if '3pp' not in perspective:
                        continue
                
                sidebar_filtered.append(server)
            filtered = sidebar_filtered
        
        return filtered
    
    def apply_sorting(self, servers, sort_option):
        """Apply sorting to server list"""
        if sort_option == "Name":
            return sorted(servers, key=lambda s: s.get('name', '').lower())
        elif sort_option == "Players":
            return sorted(servers, key=lambda s: s.get('players', 0), reverse=True)
        elif sort_option == "Ping":
            return sorted(servers, key=lambda s: s.get('ping', 999))
        elif sort_option == "Map":
            return sorted(servers, key=lambda s: s.get('map', '').lower())
        else:
            return servers
    
    def display_servers(self, servers):
        """Display filtered servers in the UI"""
        # Clear existing servers
        self.clear_server_list_ui()
        
        # Add filtered servers
        for server in servers:
            self.add_server_to_ui(server)
        
        # Update status
        total_count = len(self.servers)
        filtered_count = len(servers)
        if filtered_count != total_count:
            self.status_label.setText(f"{filtered_count} servers (filtered from {total_count})")
        else:
            self.status_label.setText(f"{filtered_count} servers loaded")
            
        print(f"🎯 Displayed {filtered_count} servers after filtering")
    
    def closeEvent(self, event):
        """Handle application close event"""
        try:
            print("🔄 Application closing, cleaning up...")
            
            # Stop server refresh thread
            if hasattr(self.server_manager, 'refresh_thread') and self.server_manager.refresh_thread:
                if self.server_manager.refresh_thread.isRunning():
                    print("🛑 Stopping refresh thread...")
                    self.server_manager.refresh_thread.terminate()
                    if not self.server_manager.refresh_thread.wait(3000):  # Wait 3 seconds
                        print("⚠️ Thread did not stop gracefully, forcing...")
                        
            # Close BattleMetrics API session
            try:
                import asyncio
                from battlemetrics_api import close_battlemetrics_api
                
                # Try to close API session
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                    if loop and loop.is_running():
                        # Schedule cleanup task
                        asyncio.create_task(close_battlemetrics_api())
                except Exception:
                    # Create new loop if needed
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(close_battlemetrics_api())
                    loop.close()
            except Exception as e:
                print(f"Error closing API session: {e}")
            
            print("✅ Cleanup completed")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            # Always accept the close event
            event.accept()
    
    def filter_by_server_type(self, server_type):
        """Quick filter by server type"""
        if not self.servers:
            return
        
        # Filter servers based on type heuristics
        type_filtered = []
        
        for server in self.servers:
            server_name = server.get('name', '').lower()
            
            if server_type == "official":
                # Official servers: Look for servers that could be official
                # Since Steam API might not return true official servers, we'll be more flexible
                if (
                    # Classic official patterns
                    ('dayz' in server_name and any(pattern in server_name for pattern in [' de ', ' us ', ' eu ', ' uk ', ' fr ', ' au ', ' ca '])) or
                    ('dayz official' in server_name) or
                    ('official' in server_name and 'dayz' in server_name) or
                    # Simple names that could be official (without obvious community markers)
                    (server_name.startswith('dayz ') and len(server_name.split()) <= 4) or
                    # Servers with "official" in name
                    ('official' in server_name)
                ):
                    # Exclude servers with obvious community markers
                    if not any(char in server_name for char in ['[', ']', '|', '★', '♦', '●', '~', '!']):
                        # But allow some that might still be official-like
                        if not any(keyword in server_name for keyword in ['discord', 'www', 'http', 'x10', 'loot+', 'rp |', 'roleplay', 'clan']):
                            type_filtered.append(server)
                
                # If no official servers found, show some vanilla-like servers as fallback
                if not type_filtered:
                    for server in self.servers:
                        server_name = server.get('name', '').lower() 
                        # Show servers without obvious mod indicators as "official-like"
                        if (not any(char in server_name for char in ['[', ']', '|', '★', '♦', '●', '~', '!']) and
                            not any(keyword in server_name for keyword in ['mod', 'x10', 'loot+', 'trader', 'discord', 'www', 'http']) and
                            len(server_name.split()) <= 5):
                            type_filtered.append(server)
                            if len(type_filtered) >= 20:  # Limit to 20 servers
                                break
                    
            elif server_type == "community":
                # Community servers: creative names, often with brackets, special chars
                if (any(char in server_name for char in ['[', ']', '|', '★', '♦', '●']) or
                    any(keyword in server_name for keyword in ['community', 'clan', 'group', 'squad', 'team']) or
                    len(server_name.split()) >= 4):
                    # Exclude obvious official servers
                    if not any(keyword in server_name for keyword in ['official', 'dayz server']):
                        type_filtered.append(server)
                        
            elif server_type == "private":
                # Private servers: often mention "private", "whitelist", "closed"
                if any(keyword in server_name for keyword in ['private', 'whitelist', 'closed', 'invite', 'members']):
                    type_filtered.append(server)
        
        # Apply the filtered results
        self.filtered_servers = type_filtered
        self._filters_applied = True
        self.populate_server_list()
        
        # Clear other filters to show pure type filter
        self.search_input.clear()
        if hasattr(self, 'ping_filter'):
            self.ping_filter.setCurrentText("All")
            self.map_filter.setCurrentText("All") 
            self.status_filter.setCurrentText("All")
        
        print(f"Filtered by {server_type} servers: {len(type_filtered)} found")
    
    def show_all_servers(self):
        """Show all servers without server type filtering"""
        if not self.servers:
            return
        
        # Reset server type filtering - show all servers
        self.filtered_servers = self.servers.copy()
        self._filters_applied = False  # Reset other filters too
        
        # Clear other filter inputs to show pure "all servers" view
        self.search_input.clear()
        if hasattr(self, 'ping_filter'):
            self.ping_filter.setCurrentText("All")
            self.map_filter.setCurrentText("All") 
            self.status_filter.setCurrentText("All")
        
        # Refresh display
        self.populate_server_list()
        
        print(f"Showing all servers: {len(self.servers)} total")
    
    async def connect_to_server_async(self, server_data):
        """Connect to DayZ server with mod detection and management"""
        try:
            server_ip = server_data.get('ip', '')
            server_port = int(server_data.get('qport', '27016'))
            server_name = server_data.get('name', 'Unknown Server')
            
            if not server_ip or server_ip == '127.0.0.1':
                self.status_label.setText("Cannot connect to this server (invalid IP)")
                return
            
            # Step 1: Detect required mods
            self.status_label.setText("Detecting required mods...")
            self.status_label.setStyleSheet("color: #FFD700;")
            
            required_mod_ids = await self.mod_manager.get_server_mods(server_ip, server_port)
            
            if required_mod_ids:
                print(f"Server requires {len(required_mod_ids)} mods: {required_mod_ids}")
                
                # Step 2: Check missing mods
                missing_mods, available_mods = self.mod_manager.check_missing_mods(required_mod_ids)
                
                if missing_mods:
                    # Show mod installation dialog
                    await self.show_mod_installation_dialog(server_data, missing_mods, available_mods)
                    return
                else:
                    # All mods available, launch with mods
                    self.launch_dayz_with_mods(server_ip, server_port, server_name, required_mod_ids)
            else:
                # No mods required, launch normally
                print("No mods required by server")
                self.launch_dayz_with_mods(server_ip, server_port, server_name, [])
                
        except Exception as e:
            print(f"Error connecting to server: {e}")
            self.status_label.setText(f"Connection error: {str(e)}")
            self.status_label.setStyleSheet("color: #F44336;")
    
    def connect_to_server(self, server_data):
        """Connect to DayZ server (wrapper for async function)"""
        import asyncio
        
        # Create async task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.connect_to_server_async(server_data))
        finally:
            loop.close()
    
    def launch_dayz_with_mods(self, server_ip: str, server_port: str, server_name: str, mod_ids: list):
        """Launch DayZ with specified mods using Steam launch options"""
        try:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            from PySide6.QtWidgets import QApplication
            import subprocess
            import platform
            import shlex
            
            # Copy server IP to clipboard
            clipboard = QApplication.clipboard()
            server_address = f"{server_ip}:{server_port}"
            clipboard.setText(server_address)
            
            # Generate mod parameters
            mod_params = self.mod_manager.generate_mod_params(mod_ids) if mod_ids else ""
            
            print(f"🚀 Launching DayZ for server: {server_name}")
            print(f"📋 Server address: {server_address}")
            print(f"🧩 Mods: {len(mod_ids)} required")
            if mod_params:
                print(f"🔧 Mod params: {mod_params}")
            
            # Update status
            mod_status = f" with {len(mod_ids)} mods" if mod_ids else ""
            self.status_label.setText(f"Launching DayZ{mod_status}...")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            # Method 1: Direct Steam launch with parameters (Linux)
            success = False
            
            if platform.system() == "Linux":
                try:
                    # Build Steam launch command with mod parameters
                    steam_args = ['steam']
                    
                    if mod_params:
                        # Launch DayZ with mod parameters
                        launch_options = f"{mod_params}"
                        steam_args.extend(['-applaunch', '221100'] + shlex.split(launch_options))
                    else:
                        # Launch DayZ normally
                        steam_args.extend(['-applaunch', '221100'])
                    
                    print(f"Steam command: {' '.join(steam_args)}")
                    
                    # Launch Steam with parameters
                    subprocess.Popen(steam_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    success = True
                    
                except Exception as e:
                    print(f"Steam direct launch failed: {e}")
            
            # Method 2: Fallback to Steam URL protocol
            if not success:
                try:
                    if mod_params:
                        # Launch with mods via Steam URL (might not work reliably)
                        steam_url = f"steam://run/221100//{mod_params}"
                    else:
                        steam_url = "steam://rungameid/221100"
                    
                    print(f"Fallback Steam URL: {steam_url}")
                    success = QDesktopServices.openUrl(QUrl(steam_url))
                except Exception as e:
                    print(f"Steam URL launch failed: {e}")
            
            if success:
                # Show connection instructions with mod info
                self.show_connection_notification_with_mods(server_ip, server_port, server_name, mod_ids)
                
                # Update status after delay
                QTimer.singleShot(3000, lambda: (
                    self.status_label.setText(f"📋 {server_address} - ready to connect{mod_status}"),
                    self.status_label.setStyleSheet("color: #FFD700; font-weight: bold;")
                ))
            else:
                self.status_label.setText("Failed to launch DayZ - please start manually")
                self.status_label.setStyleSheet("color: #F44336;")
                # Still show instructions
                self.show_connection_notification_with_mods(server_ip, server_port, server_name, mod_ids)
                
        except Exception as e:
            print(f"Error launching DayZ with mods: {e}")
            self.status_label.setText(f"Launch error: {str(e)}")
            self.status_label.setStyleSheet("color: #F44336;")
    
    def launch_dayz_with_server_info(self, server_ip: str, server_port: str, server_name: str):
        """Launch DayZ using the 2024/2025 compatible method"""
        try:
            from PySide6.QtGui import QDesktopServices, QClipboard
            from PySide6.QtCore import QUrl
            from PySide6.QtWidgets import QApplication
            import subprocess
            import platform
            
            # Copy server IP to clipboard for easy pasting
            clipboard = QApplication.clipboard()
            server_address = f"{server_ip}:{server_port}"
            clipboard.setText(server_address)
            
            # Update status
            self.status_label.setText(f"Launching DayZ for {server_name[:30]}...")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            print(f"🚀 Launching DayZ for server: {server_name}")
            print(f"📋 Server address copied to clipboard: {server_address}")
            
            # Method 1: Try DayZ Launcher directly (2024+ method)
            success = False
            try:
                if platform.system() == "Linux":
                    # On Linux, try to launch DayZ directly via Steam
                    subprocess.Popen(['steam', 'steam://rungameid/221100'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    success = True
                elif platform.system() == "Windows":
                    # On Windows, try Steam protocol (might work)
                    success = QDesktopServices.openUrl(QUrl("steam://rungameid/221100"))
                else:
                    # Mac or other - use Steam protocol
                    success = QDesktopServices.openUrl(QUrl("steam://rungameid/221100"))
                    
            except Exception as e:
                print(f"Steam launch failed: {e}")
                
            # Method 2: Fallback to opening Steam itself
            if not success:
                try:
                    success = QDesktopServices.openUrl(QUrl("steam://open/main"))
                except Exception:
                    pass
            
            if success:
                # Show updated connection instructions for 2024
                self.show_connection_notification_2024(server_ip, server_port, server_name)
                
                # Update status after a delay
                QTimer.singleShot(3000, lambda: (
                    self.status_label.setText(f"📋 {server_address} - paste in DayZ Direct Connect"),
                    self.status_label.setStyleSheet("color: #FFD700; font-weight: bold;")
                ))
            else:
                self.status_label.setText("Failed to launch - please start DayZ manually")
                self.status_label.setStyleSheet("color: #F44336;")
                # Still show instructions even if launch failed
                self.show_connection_notification_2024(server_ip, server_port, server_name)
                
        except Exception as e:
            print(f"Error launching DayZ: {e}")
            self.status_label.setText(f"Launch error: {str(e)}")
            self.status_label.setStyleSheet("color: #F44336;")
    
    def show_connection_notification_2024(self, server_ip: str, server_port: str, server_name: str):
        """Show connection notification with 2024/2025 instructions"""
        from PySide6.QtWidgets import QMessageBox
        
        notification_msg = f"""
<b style="color: #4CAF50; font-size: 16px;">🚀 DayZ Connection (2024 Method)</b><br><br>

<b>Server:</b> {server_name}<br>
<b>Address:</b> <code style="background: #2a2a2a; padding: 2px 4px; color: #FFD700;">{server_ip}:{server_port}</code><br><br>

<b style="color: #4CAF50;">Method 1: DayZ Launcher Direct Connect</b><br>
1. Open <b>DayZ Launcher</b> (not Steam!)<br>
2. Click <b>Servers</b> → <b>Direct Connect</b><br>
3. Paste IP address (Ctrl+V)<br>
4. Click <b>Connect</b><br><br>

<b style="color: #FFD700;">Method 2: Steam Favorites</b><br>
1. In Steam: <b>View</b> → <b>Game Servers</b><br>
2. Click <b>Favorites</b> tab → <b>+</b> button<br>
3. Paste server address<br>
4. Right-click server → <b>Connect</b><br><br>

<b style="color: #FFD700;">📋 Server address copied to clipboard!</b>
        """
        
        # Quick notification dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🎮 DayZ Connection (Updated 2024)")
        msg_box.setText(notification_msg)
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setIcon(QMessageBox.Information)
        
        # Make it smaller and less intrusive
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1a1a1a;
                color: #e8e8e8;
                font-size: 12px;
            }
            QMessageBox QLabel {
                color: #e8e8e8;
                background-color: transparent;
                padding: 15px;
                min-width: 350px;
            }
            QMessageBox QPushButton {
                background-color: #4a7c59;
                color: white;
                border: 1px solid #5a8c69;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #5a8c69;
            }
        """)
        
        msg_box.exec()
    
    def try_steam_connection_methods(self, server_ip: str, server_port: str, server_name: str) -> bool:
        """Try multiple Steam connection methods"""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        # Method 1: steam://run with DayZ App ID (most reliable)
        steam_url_1 = f"steam://run/221100//+connect {server_ip}:{server_port}"
        print(f"Trying method 1: {steam_url_1}")
        
        if QDesktopServices.openUrl(QUrl(steam_url_1)):
            return True
            
        # Method 2: Classic steam://connect (fallback)
        steam_url_2 = f"steam://connect/{server_ip}:{server_port}"
        print(f"Trying method 2: {steam_url_2}")
        
        if QDesktopServices.openUrl(QUrl(steam_url_2)):
            return True
            
        # Method 3: Steam console command (advanced)
        steam_url_3 = f"steam://run/221100//-connect={server_ip} -port={server_port}"
        print(f"Trying method 3: {steam_url_3}")
        
        if QDesktopServices.openUrl(QUrl(steam_url_3)):
            return True
            
        return False
    
    def show_modern_connection_help(self, server_ip: str, server_port: str, server_name: str):
        """Show modern connection methods (Steam protocols disabled in 2024)"""
        from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
        from PySide6.QtGui import QFont
        
        # Copy IP to clipboard
        from PySide6.QtGui import QClipboard
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(f"{server_ip}:{server_port}")
        
        help_msg = f"""
<b style="color: #4a7c59; font-size: 14px;">Connect to: {server_name[:50]}</b><br><br>

<b style="color: #FFD700;">⚠️ Steam Connection Disabled</b><br>
Bohemia/Steam disabled direct connection protocols in 2024.<br><br>

<b style="color: #4CAF50;">✅ Working Methods:</b><br><br>

<b>🚀 Method 1: DayZ In-Game Browser (Recommended)</b><br>
1. Launch DayZ → Servers → Direct Connect<br>
2. Enter IP: <code style="background: #2a2a2a; padding: 2px 4px;">{server_ip}:{server_port}</code><br>
3. Check "Add to Favorites" ✓<br><br>

<b>🎯 Method 2: Steam Server Browser</b><br>
1. Steam → View → Game Servers<br>
2. Favorites tab → "+" Add Server<br>
3. Enter: <code style="background: #2a2a2a; padding: 2px 4px;">{server_ip}:{server_port}</code><br><br>

<b>⚡ Method 3: DayZ Console</b><br>
1. In DayZ → Press F1 (console)<br>
2. Type: <code style="background: #2a2a2a; padding: 2px 4px;">connect {server_ip}:{server_port}</code><br><br>

<b style="color: #FFD700;">📋 Server IP copied to clipboard!</b>
        """
        
        # Show modern help dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🎮 Connect to DayZ Server")
        msg_box.setText(help_msg)
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setIcon(QMessageBox.Information)
        
        # Custom styling for the dialog
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1a1a1a;
                color: #e8e8e8;
                font-size: 12px;
            }
            QMessageBox QLabel {
                color: #e8e8e8;
                background-color: transparent;
                padding: 10px;
            }
            QMessageBox QPushButton {
                background-color: #4a7c59;
                color: white;
                border: 1px solid #5a8c69;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #5a8c69;
            }
        """)
        
        msg_box.exec()
        
        self.status_label.setText(f"📋 Server IP copied: {server_ip}:{server_port}")
        self.status_label.setStyleSheet("color: #FFD700; font-weight: bold;")
    
    def select_server_type(self, server_type):
        """Handle exclusive server type selection"""
        # Update the selected type
        self.selected_server_type = server_type
        
        # Update button states (exclusive selection)
        for type_key, button in self.server_type_buttons.items():
            button.setChecked(type_key == server_type)
        
        # Update button styling
        self.update_server_type_styles()
        
        # Apply the server type filter only if a specific type is selected
        if server_type is None:
            # "All Servers" selected - show all servers, reset filtering
            self.show_all_servers()
            print("Selected server type: All Servers")
        else:
            # Specific type selected - apply filter
            self.filter_by_server_type(server_type)
            print(f"Selected server type: {server_type}")
    
    def update_server_type_styles(self):
        """Update server type button styles based on selection"""
        for type_key, button in self.server_type_buttons.items():
            if button.isChecked():
                # Selected state - green background
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #4a7c59;
                        color: white;
                        border: 2px solid #5a8c69;
                        border-radius: 8px;
                        padding: 8px 16px;
                        font-weight: bold;
                        min-height: 24px;
                    }
                    QPushButton:hover {
                        background-color: #5a8c69;
                        border-color: #6a9c79;
                    }
                """)
            else:
                # Unselected state - normal styling
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;
                        border: 1px solid #404040;
                        color: #e8e8e8;
                        border-radius: 8px;
                        padding: 8px 16px;
                        font-weight: bold;
                        min-height: 24px;
                    }
                    QPushButton:hover {
                        background-color: #333333;
                        border-color: #4a7c59;
                    }
                """)

    def show_add_server_dialog(self):
        """Show dialog to add a server by IP address"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle("➕ Add Server by IP")
        dialog.setModal(True)
        dialog.resize(400, 200)
        
        # Apply dark theme to dialog
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: #e8e8e8;
            }
            QLabel {
                color: #e8e8e8;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px;
                color: #e8e8e8;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #4a7c59;
            }
            QPushButton {
                background-color: #4a7c59;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a8c69;
            }
            QPushButton:pressed {
                background-color: #3a6c49;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        instructions = QLabel("Enter the server IP address and port to connect to a non-popular server:")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # IP input
        ip_layout = QHBoxLayout()
        ip_label = QLabel("Server Address:")
        ip_input = QLineEdit()
        ip_input.setPlaceholderText("192.168.1.100:2302")
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(ip_input)
        layout.addLayout(ip_layout)
        
        # Optional: Server name
        name_layout = QHBoxLayout()
        name_label = QLabel("Server Name (optional):")
        name_input = QLineEdit()
        name_input.setPlaceholderText("My Custom Server")
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_input)
        layout.addLayout(name_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        connect_btn = QPushButton("🚀 Connect")
        connect_btn.clicked.connect(lambda: self.handle_add_server(dialog, ip_input.text(), name_input.text()))
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(connect_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def handle_add_server(self, dialog, server_address: str, server_name: str = ""):
        """Handle adding and connecting to a custom server"""
        if not server_address.strip():
            self.status_label.setText("Please enter a server address")
            self.status_label.setStyleSheet("color: #F44336;")
            return
        
        # Parse IP and port
        try:
            if ':' in server_address:
                ip, port = server_address.split(':', 1)
                port = port.strip()
            else:
                ip = server_address.strip()
                port = "2302"  # Default DayZ port
            
            # Validate IP (basic check)
            ip_parts = ip.split('.')
            if len(ip_parts) != 4 or not all(0 <= int(part) <= 255 for part in ip_parts):
                raise ValueError("Invalid IP format")
            
            # Validate port
            port_num = int(port)
            if not (1 <= port_num <= 65535):
                raise ValueError("Invalid port range")
            
            # Create server data for connection
            server_data = {
                'name': server_name if server_name.strip() else f"Custom Server ({ip}:{port})",
                'ip': ip,
                'qport': port,
                'players': 0,
                'max_players': 0,
                'ping': 0,
                'map': 'Unknown',
                'server_type': 'custom'
            }
            
            # Close dialog
            dialog.accept()
            
            # Connect to server
            self.connect_to_server(server_data)
            
            # Optionally add to favorites
            self.add_favorite(server_data)
            
        except ValueError as e:
            self.status_label.setText(f"Invalid server address: {e}")
            self.status_label.setStyleSheet("color: #F44336;")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")
            self.status_label.setStyleSheet("color: #F44336;")
    
    def refresh_mods(self):
        """Refresh the mod list"""
        try:
            # Clear existing mod list
            for i in reversed(range(self.mod_list_layout.count())):
                child = self.mod_list_layout.itemAt(i).widget()
                if child:
                    child.deleteLater()
            
            # Get installed mods
            installed_mods = self.mod_manager.get_installed_mods()
            
            if not installed_mods:
                no_mods_label = QLabel("No mods found. Subscribe to mods on Steam Workshop first.")
                no_mods_label.setStyleSheet("color: #b8b8b8; font-size: 12px; padding: 20px;")
                no_mods_label.setAlignment(Qt.AlignCenter)
                self.mod_list_layout.addWidget(no_mods_label)
            else:
                # Sort mods by name
                installed_mods.sort(key=lambda m: m.name.lower())
                
                for mod in installed_mods:
                    mod_card = self.create_mod_card(mod)
                    self.mod_list_layout.addWidget(mod_card)
            
            # Update statistics
            self.update_mod_stats()
            
        except Exception as e:
            print(f"Error refreshing mods: {e}")
    
    def update_mod_stats(self):
        """Update mod statistics display"""
        # Clear existing stats
        for i in reversed(range(self.mod_stats_layout.count())):
            child = self.mod_stats_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        try:
            installed_mods = self.mod_manager.get_installed_mods()
            
            # Calculate statistics
            total_mods = len(installed_mods)
            total_size_mb = sum(mod.size_mb for mod in installed_mods)
            total_size_gb = round(total_size_mb / 1024, 2)
            
            # Create stat labels
            stats = [
                ("Total Mods:", str(total_mods)),
                ("Total Size:", f"{total_size_gb} GB"),
                ("Workshop Path:", str(self.mod_manager.workshop_path.name))
            ]
            
            for label_text, value_text in stats:
                stat_widget = QWidget()
                stat_layout = QHBoxLayout(stat_widget)
                stat_layout.setContentsMargins(0, 0, 0, 0)
                
                label = QLabel(label_text)
                label.setStyleSheet("color: #b8b8b8; font-size: 11px;")
                
                value = QLabel(value_text)
                value.setStyleSheet("color: #e8e8e8; font-size: 11px; font-weight: bold;")
                
                stat_layout.addWidget(label)
                stat_layout.addWidget(value)
                stat_layout.addStretch()
                
                self.mod_stats_layout.addWidget(stat_widget)
        
        except Exception as e:
            print(f"Error updating mod stats: {e}")
    
    def create_mod_card(self, mod_info):
        """Create a mod card widget"""
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setFixedHeight(80)
        card.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 8px;
                margin: 2px;
            }
            QFrame:hover {
                background-color: #323232;
                border-color: #4a7c59;
            }
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Mod info
        info_layout = QVBoxLayout()
        
        # Mod name and ID
        name_layout = QHBoxLayout()
        name_label = QLabel(mod_info.name[:50] + ("..." if len(mod_info.name) > 50 else ""))
        name_label.setStyleSheet("color: #e8e8e8; font-weight: bold; font-size: 13px;")
        name_layout.addWidget(name_label)
        
        id_label = QLabel(f"ID: {mod_info.workshop_id}")
        id_label.setStyleSheet("color: #b8b8b8; font-size: 10px;")
        name_layout.addWidget(id_label)
        name_layout.addStretch()
        
        info_layout.addLayout(name_layout)
        
        # Mod details
        details_layout = QHBoxLayout()
        
        size_label = QLabel(f"{mod_info.size_mb} MB")
        size_label.setStyleSheet("color: #b8b8b8; font-size: 10px;")
        details_layout.addWidget(size_label)
        
        # Status
        status_label = QLabel("✓ Installed" if mod_info.installed else "✗ Missing")
        status_label.setStyleSheet("color: #4CAF50; font-size: 10px;" if mod_info.installed else "color: #F44336; font-size: 10px;")
        details_layout.addWidget(status_label)
        
        details_layout.addStretch()
        
        info_layout.addLayout(details_layout)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # Actions
        action_layout = QVBoxLayout()
        
        # Workshop button
        workshop_btn = QPushButton("Workshop")
        workshop_btn.setFixedSize(80, 25)
        workshop_btn.setStyleSheet("QPushButton { background-color: #5c7a89; color: white; font-size: 10px; }")
        workshop_btn.clicked.connect(lambda: self.open_workshop_page(mod_info.workshop_id))
        action_layout.addWidget(workshop_btn)
        
        # Delete button
        delete_btn = QPushButton("Remove")
        delete_btn.setFixedSize(80, 25)
        delete_btn.setStyleSheet("QPushButton { background-color: #8b4b47; color: white; font-size: 10px; }")
        delete_btn.clicked.connect(lambda: self.remove_mod(mod_info))
        action_layout.addWidget(delete_btn)
        
        layout.addLayout(action_layout)
        
        return card
    
    def open_workshop_page(self, mod_id: str):
        """Open Steam Workshop page for mod"""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        workshop_url = self.mod_manager.get_steam_workshop_url(mod_id)
        QDesktopServices.openUrl(QUrl(workshop_url))
    
    def remove_mod(self, mod_info):
        """Remove a mod with confirmation"""
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, 
            "Remove Mod",
            f"Are you sure you want to remove:\n{mod_info.name}?\n\nThis will delete the mod files from disk.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if mod_info.local_path and mod_info.local_path.exists():
                    import shutil
                    shutil.rmtree(mod_info.local_path)
                    self.status_label.setText(f"Removed mod: {mod_info.name}")
                    self.status_label.setStyleSheet("color: #4CAF50;")
                    
                    # Refresh mod list
                    self.refresh_mods()
                else:
                    self.status_label.setText("Mod directory not found")
                    self.status_label.setStyleSheet("color: #F44336;")
                    
            except Exception as e:
                self.status_label.setText(f"Error removing mod: {e}")
                self.status_label.setStyleSheet("color: #F44336;")
    
    async def show_mod_installation_dialog(self, server_data, missing_mod_ids: list, available_mod_ids: list):
        """Show dialog for installing missing mods"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
        
        dialog = QDialog(self)
        dialog.setWindowTitle("🧩 Mods Required")
        dialog.setModal(True)
        dialog.resize(500, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: #e8e8e8;
            }
            QLabel {
                color: #e8e8e8;
            }
            QPushButton {
                background-color: #4a7c59;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a8c69;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        server_name = server_data.get('name', 'Server')
        header_label = QLabel(f"🎮 Server: {server_name[:40]}...")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
        layout.addWidget(header_label)
        
        # Status summary
        status_text = f"🧩 {len(available_mod_ids)} mods available, {len(missing_mod_ids)} missing"
        status_label = QLabel(status_text)
        status_label.setStyleSheet("color: #FFD700; margin: 10px 0;")
        layout.addWidget(status_label)
        
        if missing_mod_ids:
            # Get mod info for missing mods
            mod_info = await self.mod_manager.get_mod_info_from_steam(missing_mod_ids)
            
            # Instructions
            instructions = QLabel("❗ Missing mods must be subscribed on Steam Workshop:")
            instructions.setStyleSheet("color: #F44336; font-weight: bold;")
            layout.addWidget(instructions)
            
            # Missing mods list
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(200)
            
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            
            for mod_id in missing_mod_ids:
                mod_name = mod_info.get(mod_id, {}).get('name', f'Mod {mod_id}')
                
                mod_widget = QWidget()
                mod_layout = QHBoxLayout(mod_widget)
                
                mod_label = QLabel(f"• {mod_name} (ID: {mod_id})")
                mod_layout.addWidget(mod_label)
                
                workshop_btn = QPushButton("Open Workshop")
                workshop_btn.setFixedWidth(120)
                workshop_btn.clicked.connect(lambda checked, mid=mod_id: self.open_workshop_page(mid))
                mod_layout.addWidget(workshop_btn)
                
                scroll_layout.addWidget(mod_widget)
            
            scroll.setWidget(scroll_widget)
            layout.addWidget(scroll)
        
        # Available mods summary
        if available_mod_ids:
            available_label = QLabel(f"✅ {len(available_mod_ids)} mods ready")
            available_label.setStyleSheet("color: #4CAF50; margin-top: 10px;")
            layout.addWidget(available_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        if missing_mod_ids:
            install_btn = QPushButton("Subscribe & Retry")
            install_btn.setStyleSheet("background-color: #FFD700; color: #1a1a1a;")
            install_btn.clicked.connect(lambda: self.handle_mod_subscription(dialog, server_data, missing_mod_ids))
        else:
            install_btn = QPushButton("Continue")
            install_btn.clicked.connect(lambda: self.proceed_with_connection(dialog, server_data, available_mod_ids))
        
        button_layout.addWidget(install_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def handle_mod_subscription(self, dialog, server_data, missing_mod_ids):
        """Handle mod subscription process"""
        dialog.accept()
        
        # Open all workshop pages
        for mod_id in missing_mod_ids:
            self.open_workshop_page(mod_id)
        
        # Show instructions
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Mod Subscription")
        msg.setText("""
<b>Steam Workshop pages opened!</b><br><br>
<b>Next steps:</b><br>
1. Subscribe to the required mods<br>
2. Wait for mods to download<br>
3. Click 'Connect' on the server again<br><br>
<i>DayZConnect will automatically detect the installed mods.</i>
        """)
        msg.setTextFormat(Qt.RichText)
        msg.exec()
    
    def proceed_with_connection(self, dialog, server_data, mod_ids):
        """Proceed with server connection using available mods"""
        dialog.accept()
        
        server_ip = server_data.get('ip', '')
        server_port = int(server_data.get('qport', '27016'))
        server_name = server_data.get('name', 'Server')
        
        self.launch_dayz_with_mods(server_ip, server_port, server_name, mod_ids)
    
    def show_connection_notification_with_mods(self, server_ip: str, server_port: str, server_name: str, mod_ids: list):
        """Show connection notification with mod information"""
        from PySide6.QtWidgets import QMessageBox
        
        mod_status = f" with {len(mod_ids)} mods" if mod_ids else ""
        mod_list = ""
        
        if mod_ids and len(mod_ids) <= 5:
            # Show mod list if not too many
            installed_mods = self.mod_manager.get_installed_mods()
            mod_dict = {mod.workshop_id: mod.name for mod in installed_mods}
            
            mod_list = "<br><b>Mods loaded:</b><br>"
            for mod_id in mod_ids[:5]:
                mod_name = mod_dict.get(mod_id, f"Mod {mod_id}")
                mod_list += f"• {mod_name}<br>"
        elif len(mod_ids) > 5:
            mod_list = f"<br><b>{len(mod_ids)} mods loaded</b><br>"
        
        notification_msg = f"""
<b style="color: #4CAF50; font-size: 16px;">🚀 DayZ Launching{mod_status}</b><br><br>

<b>Server:</b> {server_name}<br>
<b>Address:</b> <code style="background: #2a2a2a; padding: 2px 4px; color: #FFD700;">{server_ip}:{server_port}</code><br>
{mod_list}<br>

<b style="color: #4CAF50;">Connection Method:</b><br>
1. Wait for DayZ to load completely<br>
2. Go to <b>Servers → Direct Connect</b><br>
3. Paste the address (Ctrl+V)<br>
4. Click <b>Connect</b><br><br>

<b style="color: #FFD700;">📋 Server address copied to clipboard!</b>
        """
        
        # Quick notification dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"🎮 DayZ Connection{mod_status}")
        msg_box.setText(notification_msg)
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setIcon(QMessageBox.Information)
        
        # Apply dark theme
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1a1a1a;
                color: #e8e8e8;
                font-size: 12px;
            }
            QMessageBox QLabel {
                color: #e8e8e8;
                background-color: transparent;
                padding: 15px;
                min-width: 400px;
            }
            QMessageBox QPushButton {
                background-color: #4a7c59;
                color: white;
                border: 1px solid #5a8c69;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #5a8c69;
            }
        """)
        
        msg_box.exec()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    window = ModernDZGUI()
    window.show()
    
    # Ensure clean exit
    try:
        return app.exec()
    except KeyboardInterrupt:
        print("Interrupted by user")
        return 0
    finally:
        # Clean up any running threads
        try:
            if hasattr(window.server_manager, 'refresh_thread'):
                if window.server_manager.refresh_thread.isRunning():
                    window.server_manager.refresh_thread.terminate()
                    window.server_manager.refresh_thread.wait(1000)
        except:
            pass

if __name__ == "__main__":
    sys.exit(main())