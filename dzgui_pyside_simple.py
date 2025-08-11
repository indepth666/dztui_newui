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

# Import our native Python server manager
from dzgui_server_manager import get_server_manager

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
        
        # Set initial server type styling and load cached servers immediately
        QTimer.singleShot(50, self.update_server_type_styles)  # Apply styling after UI is ready
        QTimer.singleShot(100, self.load_cached_servers_immediately)  # Load cached servers first
    
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
        """Create main content area"""
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header with search
        header_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search servers by name, map, or players...")
        self.search_input.setFixedHeight(40)
        self.search_input.textChanged.connect(self.filter_servers)  # Connect search function
        header_layout.addWidget(self.search_input)
        
        connect_btn = QPushButton("Connect")
        connect_btn.setStyleSheet("QPushButton { background-color: #4a7c59; color: white; }")
        connect_btn.setFixedWidth(100)
        header_layout.addWidget(connect_btn)
        
        layout.addLayout(header_layout)
        
        # Filter bar
        self.create_filter_bar(layout)
        
        # Progress bar (for loading)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 0)  # Indeterminate
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
        
        layout.addLayout(header_layout)
        
        # Info row
        info_layout = QHBoxLayout()
        
        map_label = QLabel(f"Map: {server_data['map']}")
        map_label.setStyleSheet("color: #b8b8b8; font-size: 10px;")
        info_layout.addWidget(map_label)
        
        mode_label = QLabel(f"Mode: {server_data['perspective']}")
        mode_label.setStyleSheet("color: #b8b8b8; font-size: 10px;")
        info_layout.addWidget(mode_label)
        
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
    
    def load_cached_servers_immediately(self):
        """Load cached servers immediately on startup"""
        try:
            cached_servers = self.server_manager.load_cached_servers()
            if cached_servers:
                print(f"Loaded {len(cached_servers)} servers from cache")
            else:
                print("No cached servers available")
        except Exception as e:
            print(f"Error loading cached servers: {e}")
    
    def refresh_servers(self):
        """Refresh server list using Steam API with SQLite caching"""
        try:
            self.status_label.setText("Starting server refresh...")
            print("Starting server refresh with smart caching...")
            
            # Check if we should clear the display based on cache age
            is_fresh, count = self.server_manager.database.is_cache_fresh()
            if not is_fresh or count == 0:
                # Cache is stale or empty - clear the server list
                print("Cache is stale or empty, clearing server list")
                self.servers = []
                self.filtered_servers = []
                self.clear_server_list_ui()
            else:
                print(f"Cache is fresh with {count} servers, keeping existing display")
            
            # Use smart refresh (respects 15-minute cache)
            self.server_manager.refresh_servers(force_refresh=False)
            
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
            
            # Force refresh regardless of cache state
            self.server_manager.refresh_servers(force_refresh=True)
            
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
        """Apply all active filters and sorting"""
        if not self.servers:
            return
        
        # Check if any filters are actually active
        search_text = self.search_input.text().lower().strip()
        ping_filter = self.ping_filter.currentText() if hasattr(self, 'ping_filter') else "All"
        map_filter = self.map_filter.currentText() if hasattr(self, 'map_filter') else "All"
        status_filter = self.status_filter.currentText() if hasattr(self, 'status_filter') else "All"
        
        # Check sidebar checkboxes
        sidebar_filters_active = False
        if hasattr(self, 'filters'):
            # Check if any sidebar filter is unchecked (meaning it's filtering)
            sidebar_filters_active = (
                not self.filters.get("Show Empty", QCheckBox()).isChecked() or
                not self.filters.get("Show Full", QCheckBox()).isChecked() or
                not self.filters.get("Show Modded", QCheckBox()).isChecked() or
                self.filters.get("1PP Only", QCheckBox()).isChecked() or
                self.filters.get("3PP Only", QCheckBox()).isChecked()
            )
        
        filters_active = (search_text or 
                         ping_filter != "All" or 
                         map_filter != "All" or 
                         status_filter != "All" or
                         sidebar_filters_active)
        
        self._filters_applied = filters_active
        
        # Start with all servers
        filtered_servers = self.servers.copy()
        
        # Apply search filter first (from search input)
        search_text = self.search_input.text().lower().strip()
        if search_text:
            search_filtered = []
            for server in filtered_servers:
                if (search_text in server.get('name', '').lower() or
                    search_text in server.get('map', '').lower() or
                    search_text in server.get('perspective', '').lower() or
                    search_text in server.get('ip', '') or
                    (search_text == 'empty' and server.get('players', 0) == 0) or
                    (search_text == 'full' and server.get('players', 0) >= server.get('max_players', 1)) or
                    (search_text.isdigit() and str(server.get('players', 0)) == search_text)):
                    search_filtered.append(server)
            filtered_servers = search_filtered
        
        # Apply ping filter
        ping_filter = self.ping_filter.currentText()
        if ping_filter != "All":
            ping_filtered = []
            for server in filtered_servers:
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
            filtered_servers = ping_filtered
        
        # Apply map filter
        map_filter = self.map_filter.currentText()
        if map_filter != "All":
            map_filtered = []
            for server in filtered_servers:
                server_map = server.get('map', '').lower()
                if map_filter == "Chernarus" and 'chernarus' in server_map:
                    map_filtered.append(server)
                elif map_filter == "Livonia" and 'livonia' in server_map:
                    map_filtered.append(server)
                elif map_filter == "Namalsk" and 'namalsk' in server_map:
                    map_filtered.append(server)
                elif map_filter == "Sakhal" and 'sakhal' in server_map:
                    map_filtered.append(server)
                elif map_filter == "Other" and not any(map_name in server_map for map_name in ['chernarus', 'livonia', 'namalsk', 'sakhal']):
                    map_filtered.append(server)
            filtered_servers = map_filtered
        
        # Apply status filter (player count)
        status_filter = self.status_filter.currentText()
        if status_filter != "All":
            status_filtered = []
            for server in filtered_servers:
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
            filtered_servers = status_filtered
        
        # Apply sidebar checkbox filters
        if hasattr(self, 'filters'):
            sidebar_filtered = []
            
            for server in filtered_servers:
                # Show Empty filter - if unchecked, DON'T show empty servers
                if not self.filters["Show Empty"].isChecked() and server.get('players', 0) == 0:
                    continue  # Skip empty servers when "Show Empty" is OFF
                
                # Show Full filter - if unchecked, DON'T show full servers
                if not self.filters["Show Full"].isChecked():
                    players = server.get('players', 0)
                    max_players = server.get('max_players', 1)
                    if players >= max_players and max_players > 0:
                        continue  # Skip full servers when "Show Full" is OFF
                
                # Show Modded filter (check if server has mods - simplified)
                if not self.filters["Show Modded"].isChecked():
                    server_name = server.get('name', '').lower()
                    # Simple heuristic: if name contains mod-related keywords
                    if any(keyword in server_name for keyword in ['mod', 'trader', 'loot', 'car', 'heli', 'base']):
                        continue  # Skip modded servers
                
                # 1PP Only filter
                if self.filters["1PP Only"].isChecked():
                    perspective = server.get('perspective', '').lower()
                    if '1pp' not in perspective or '3pp' in perspective:
                        continue  # Skip non-1PP servers
                
                # 3PP Only filter
                if self.filters["3PP Only"].isChecked():
                    perspective = server.get('perspective', '').lower()  
                    if '3pp' not in perspective or ('1pp' in perspective and '3pp' in perspective):
                        continue  # Skip non-3PP servers
                
                sidebar_filtered.append(server)
            
            filtered_servers = sidebar_filtered
        
        # Apply sorting
        sort_by = self.sort_filter.currentText()
        if sort_by == "Name":
            filtered_servers.sort(key=lambda s: s.get('name', '').lower())
        elif sort_by == "Players":
            filtered_servers.sort(key=lambda s: s.get('players', 0), reverse=True)
        elif sort_by == "Ping":
            # Sort by ping, offline servers (999ms) go to the end
            filtered_servers.sort(key=lambda s: s.get('ping', 999) if s.get('ping', 999) < 999 else 9999)
        elif sort_by == "Map":
            filtered_servers.sort(key=lambda s: s.get('map', '').lower())
        
        # Update filtered_servers and refresh display
        self.filtered_servers = filtered_servers
        self.populate_server_list()
        
        print(f"Applied filters: {len(filtered_servers)} servers from {len(self.servers)} total")
    
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