# DayZConnect

**Modern cross-platform DayZ server browser with real-time updates and smart caching**

DayZConnect is a fast, intuitive server browser for DayZ that displays the most popular servers with real-time ping updates and smart SQLite caching. Built with Python and PySide6 for a modern, responsive experience.


## ✨ Features

### 🚀 **Performance First**
- **Lightning fast loading** - Only fetches 2500 most popular servers (vs 13k+ others)
- **Real-time server updates** - Servers appear instantly as they respond
- **Smart 15-minute caching** - Preserves servers if cache is fresh
- **Early display at 60%** - "Ready to play" mode while background loading continues

### 🎯 **Smart Server Management**
- **All server types** - Official, Community, and Private servers displayed together
- **Filter on demand** - Choose server type only when you want to filter
- **Advanced filtering** - Search by name, map, ping, player count, perspective
- **Favorites system** - Save your preferred servers with one click

### 💎 **Modern Interface**
- **Dark military theme** - Easy on the eyes during long gaming sessions  
- **Responsive design** - Smooth scrolling with real-time updates
- **Server cards** - Clean, informative display with color-coded ping
- **Progress tracking** - Visual feedback during loading

### 🔧 **Technical Excellence**
- **A2S protocol** - Accurate ping measurements and server info
- **SQLite caching** - Persistent storage with automatic cleanup
- **Cross-platform** - Works on Linux, Windows, and macOS
- **Background processing** - Non-blocking UI with threaded operations

## 📋 Requirements

- Python 3.8+
- Steam API key (free from [Steam Developer](https://steamcommunity.com/dev/apikey))

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/yourusername/dayzconnect.git
cd dayzconnect
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

### 2. Install Dependencies
```bash
pip install PySide6 aiohttp python-a2s
```

### 3. Configure Steam API Key
Create `~/.config/dztui/dztuirc` and add:
```
steam_api=YOUR_STEAM_API_KEY_HERE
```

Or set environment variable:
```bash
export STEAM_API_KEY=your_key_here
```

### 4. Run DayZConnect
```bash
python dzgui_pyside_simple.py
```

Or use the launch script:
```bash
./run_dzgui.sh
```

## 🎮 Usage

### Server Browsing
- **All Servers** - Default view showing all server types
- **Official/Community/Private** - Click to filter by server type
- **Search** - Find servers by name, map, or other criteria
- **Sort** - By ping, players, name, or map

### Advanced Filtering
- **Ping ranges** - <50ms, <100ms, <200ms, etc.
- **Map selection** - Chernarus, Livonia, Sakhal, Namalsk, etc.
- **Player status** - Empty, Low, Medium, High, Full
- **Perspective** - 1PP Only, 3PP Only options

### Favorites Management
- **Star servers** - Click the ⭐ to add/remove favorites
- **Quick connect** - Fast access to your most-played server
- **Persistent storage** - Favorites saved between sessions

## 🔧 Configuration

### Database Location
Servers are cached in: `~/.cache/dzgui/servers.db`

### Config File
Settings stored in: `~/.config/dztui/dztuirc`

### Cache Settings
- **15-minute expiry** - Cache refreshes automatically when stale
- **Smart loading** - Preserves servers when cache is fresh
- **Automatic cleanup** - Removes offline servers after 2 hours

## 🏗️ Architecture

### Core Components
- **dzgui_pyside_simple.py** - Main GUI application (1400+ lines)
- **dzgui_server_manager.py** - Server fetching and ping management (500+ lines)  
- **dzgui_database.py** - SQLite caching and persistence (500+ lines)

### Key Technologies
- **PySide6/Qt6** - Modern cross-platform GUI framework
- **A2S Protocol** - Direct server querying for accurate data
- **Steam API** - Server discovery and metadata
- **SQLite** - Fast local caching with automatic management
- **AsyncIO** - Non-blocking server operations

### Real-time Architecture
1. **Steam API fetch** - Get 2500 most popular servers
2. **Batch database insert** - Store servers in SQLite  
3. **Concurrent pinging** - A2S queries with smart timeouts
4. **Real-time UI updates** - Servers appear as they respond
5. **Smart caching** - 15-minute expiry with background refresh

## 🤝 Contributing

DayZConnect is open source and welcomes contributions!

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run with development flags
python dzgui_pyside_simple.py --dev
```

### Code Style
- **Black formatting** - `black .`
- **Type hints** - Use Python type annotations
- **Docstrings** - Document all public methods
- **Error handling** - Graceful degradation

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **DayZ Community** - For inspiration and feedback
- **Steam API** - For server data access
- **A2S Protocol** - For accurate server information
- **PySide6/Qt** - For excellent cross-platform GUI framework

---

**Made with ❤️ for the DayZ community**

*DayZConnect - Your gateway to the best DayZ servers*
