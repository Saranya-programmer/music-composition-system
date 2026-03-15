# frontend/app.py - Restored working version
import os
import sys
import time
import uuid
import json
import io
import zipfile
import base64
from datetime import datetime
from typing import List, Optional, Dict
import streamlit as st

# Performance optimizations
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_model_info():
    """Cache model information to avoid repeated calculations"""
    return {
        "Fast (Small)": {
            "params": "300M", "speed": "⚡⚡⚡ Very Fast", "quality": "⭐⭐⭐ Good",
            "time": "~30-45s", "use_case": "Quick drafts, long tracks", "memory": "Low",
            "status": "🚧 Coming Soon"
        },
        "Balanced (Medium)": {
            "params": "1.5B", "speed": "⚡⚡ Medium", "quality": "⭐⭐⭐⭐ Very Good", 
            "time": "~60-90s", "use_case": "Most situations", "memory": "Medium",
            "status": "✅ Available"
        },
        "Best (Large)": {
            "params": "3.3B", "speed": "⚡ Slower", "quality": "⭐⭐⭐⭐⭐ Excellent",
            "time": "~90-120s", "use_case": "High quality, short tracks", "memory": "High",
            "status": "🚧 Coming Soon"
        },
        "Melody (Medium)": {
            "params": "1.5B", "speed": "⚡⚡ Medium", "quality": "⭐⭐⭐⭐ Melody-focused",
            "time": "~60-90s", "use_case": "Melody conditioning", "memory": "Medium", 
            "status": "🚧 Coming Soon"
        }
    }

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_cached_examples():
    """Cache example prompts to improve performance"""
    return [
        "Calm ambient piano with soft pads",
        "Happy ukulele melody for children", 
        "Deep EDM bass with energetic beats",
        "Romantic acoustic guitar duet",
        "Epic orchestral trailer music",
        "Lo-fi chillhop with rainy mood",
        "Dark synthwave with heavy bass",
        "Peaceful flute meditation music",
        "Slow R&B groove with smooth vocals"
    ]

@st.cache_data
def get_background_media(media_name="video.mp4"):
    """Load and encode background media (image or video)"""
    try:
        media_path = os.path.join(os.path.dirname(__file__), "assets", media_name)
        if os.path.exists(media_path):
            # Check if it's a video file
            video_extensions = ['.mp4', '.webm', '.ogg', '.mov', '.avi']
            is_video = any(media_name.lower().endswith(ext) for ext in video_extensions)
            
            if is_video:
                # For videos, encode as base64 like images
                with open(media_path, "rb") as f:
                    media_bytes = f.read()
                encoded = base64.b64encode(media_bytes).decode()
                
                # Determine video MIME type
                if media_name.lower().endswith('.mp4'):
                    mime_type = "video/mp4"
                elif media_name.lower().endswith('.webm'):
                    mime_type = "video/webm"
                elif media_name.lower().endswith('.ogg'):
                    mime_type = "video/ogg"
                elif media_name.lower().endswith('.mov'):
                    mime_type = "video/mp4"  # MOV can be played as MP4
                else:
                    mime_type = "video/mp4"
                
                return {"type": "video", "data": f"data:{mime_type};base64,{encoded}", "name": media_name}
            else:
                # For images, encode as base64
                with open(media_path, "rb") as f:
                    media_bytes = f.read()
                encoded = base64.b64encode(media_bytes).decode()
                
                # Determine MIME type based on file extension
                if media_name.lower().endswith('.webp'):
                    mime_type = "image/webp"
                elif media_name.lower().endswith('.png'):
                    mime_type = "image/png"
                else:
                    mime_type = "image/jpeg"
                    
                return {"type": "image", "data": f"data:{mime_type};base64,{encoded}"}
        else:
            print(f"Background media not found at: {media_path}")
            return None
    except Exception as e:
        print(f"Error loading background media: {e}")
        return None

model_map = {
    "Fast (Small)": "facebook/musicgen-small",
    "Balanced (Medium)": "facebook/musicgen-medium", 
    "Best (Large)": "facebook/musicgen-large",
    "Melody (Medium)": "facebook/musicgen-melody"
}

PRESETS = {
    "Quick Draft": {"model": "Fast (Small)", "duration": 15, "energy": 4, "description": "Fast generation, good quality"},
    "Standard": {"model": "Balanced (Medium)", "duration": 30, "energy": 6, "description": "Balanced speed and quality"},
    "Professional": {"model": "Best (Large)", "duration": 60, "energy": 8, "description": "Best quality, slower generation"},
    "Custom": {"description": "User-defined settings"}
}

# Ensure project root importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

# Import MainService
try:
    from backend.main_service import MainService
except Exception as e:
    st.error("❌ Could not import backend.main_service. Fix backend/main_service.py")
    st.exception(e)
    raise

# ---------- Config ----------
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")
MAX_DISPLAY = 20
SAMPLE_OUTPUT_DIR = os.path.join(ROOT, "generated")
os.makedirs(SAMPLE_OUTPUT_DIR, exist_ok=True)

# ---------- Enhanced Page Setup ----------
st.set_page_config(page_title="MelodAI — Music Generator", page_icon="🎵", layout="wide")

# Check for animated GIF background
gif_path = os.path.join(os.path.dirname(__file__), "assets", "giffy1.gif")
if os.path.exists(gif_path):
    # Load and encode GIF
    with open(gif_path, "rb") as f:
        gif_bytes = f.read()
    gif_base64 = base64.b64encode(gif_bytes).decode()
    
    css_background = f"""
/* Animated GIF Background */
.stApp {{
    background-image: url('data:image/gif;base64,{gif_base64}');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
    min-height: 100vh;
}}

/* Add overlay for better text readability */
.stApp::before {{
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(255, 255, 255, 0.85);
    z-index: -1;
    pointer-events: none;
}}
"""
else:
    # Fallback to image background
    cl_path = os.path.join(os.path.dirname(__file__), "assets", "cl.jpg")
    if os.path.exists(cl_path):
        with open(cl_path, "rb") as f:
            img_bytes = f.read()
        img_base64 = base64.b64encode(img_bytes).decode()
        
        css_background = f"""
/* Image Background Fallback */
.stApp {{
    background-image: url('data:image/jpeg;base64,{img_base64}');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
    min-height: 100vh;
}}

/* Add overlay for better text readability */
.stApp::before {{
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(255, 255, 255, 0.65);
    z-index: -1;
    pointer-events: none;
}}
"""
    else:
        css_background = """
/* Pure White Theme Styles - Fallback */
.stApp {
    background-color: #ffffff !important;
}
"""

st.markdown("""
<style>
""" + css_background + """

/* Performance & UX Enhancements */
.loading-spinner {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 3px solid #f3f3f3;
    border-top: 3px solid #4a90e2;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.smooth-transition {
    transition: all 0.3s ease-in-out;
}

.hover-lift:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(74,144,226,0.2);
}

/* Keyboard shortcuts info */
.keyboard-shortcuts {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: rgba(255,255,255,0.96);
    border: 2px solid rgba(50, 50, 50, 0.4);
    border-radius: 8px;
    padding: 12px;
    font-size: 0.8em;
    color: #1a1a1a !important;
    font-weight: 600;
    z-index: 1000;
    backdrop-filter: blur(2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    text-shadow: 1px 1px 2px rgba(255,255,255,0.8);
}

/* Enhanced loading states */
.generation-progress {
    background: linear-gradient(90deg, #4a90e2, #7b68ee);
    background-size: 200% 100%;
    animation: gradient-shift 2s ease-in-out infinite;
    color: white;
    padding: 10px;
    border-radius: 8px;
    text-align: center;
}

@keyframes gradient-shift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Accessibility improvements */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

/* Focus indicators for keyboard navigation */
button:focus, .stSelectbox:focus, .stSlider:focus {
    outline: 2px solid #4a90e2 !important;
    outline-offset: 2px !important;
}

/* Enhanced text visibility for all Streamlit elements */
.stMarkdown, .stText, p, span, div, h1, h2, h3, h4, h5, h6 {
    color: #000000 !important;
    text-shadow: 
        0 0 1px rgba(255,255,255,1),
        0 0 3px rgba(255,255,255,0.8),
        1px 1px 1px rgba(255,255,255,0.9);
    font-weight: 600 !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Sidebar text visibility */
.css-1d391kg, .css-1v0mbdj, .sidebar .sidebar-content {
    color: #000000 !important;
    background: rgba(255, 255, 255, 0.96) !important;
    text-shadow: 
        0 0 1px rgba(255,255,255,1),
        0 0 2px rgba(255,255,255,0.8);
    -webkit-font-smoothing: antialiased;
}

/* Metric labels and values */
.metric-container label, [data-testid="metric-container"] {
    color: #000000 !important;
    font-weight: 700 !important;
    text-shadow: 
        0 0 1px rgba(255,255,255,1),
        0 0 3px rgba(255,255,255,0.8),
        1px 1px 1px rgba(255,255,255,0.9);
    -webkit-font-smoothing: antialiased;
}

/* Form labels and inputs */
.stTextInput label, .stTextArea label, .stSelectbox label, .stSlider label {
    color: #000000 !important;
    font-weight: 700 !important;
    text-shadow: 
        0 0 1px rgba(255,255,255,1),
        0 0 3px rgba(255,255,255,0.8),
        1px 1px 1px rgba(255,255,255,0.9);
    -webkit-font-smoothing: antialiased;
}

/* Tab labels */
.stTabs [data-baseweb="tab-list"] button {
    color: #000000 !important;
    font-weight: 700 !important;
    background: rgba(255, 255, 255, 0.96) !important;
    border: 1px solid rgba(0, 0, 0, 0.2) !important;
    text-shadow: 
        0 0 1px rgba(255,255,255,1),
        0 0 2px rgba(255,255,255,0.8);
    -webkit-font-smoothing: antialiased;
}

/* Expander headers */
.streamlit-expanderHeader {
    color: #000000 !important;
    font-weight: 700 !important;
    text-shadow: 
        0 0 1px rgba(255,255,255,1),
        0 0 3px rgba(255,255,255,0.8),
        1px 1px 1px rgba(255,255,255,0.9);
    background: rgba(255, 255, 255, 0.96) !important;
    -webkit-font-smoothing: antialiased;
}

/* Info, warning, error messages */
.stAlert, .stSuccess, .stInfo, .stWarning, .stError {
    background: rgba(255, 255, 255, 0.97) !important;
    color: #000000 !important;
    border: 2px solid rgba(0, 0, 0, 0.2) !important;
    text-shadow: 
        0 0 1px rgba(255,255,255,1),
        0 0 2px rgba(255,255,255,0.8);
    -webkit-font-smoothing: antialiased;
}

/* All text elements */
* {
    color: #000000 !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
}

.app-header {
    text-align: center;
    margin-top: 8px;
    margin-bottom: 18px;
}

.app-title {
    font-size: 3.4rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: 1px;
    color: #000000 !important;
    text-shadow: 
        0 0 2px rgba(255,255,255,1),
        0 0 4px rgba(255,255,255,0.9),
        0 0 6px rgba(255,255,255,0.7),
        2px 2px 1px rgba(255,255,255,0.8);
    -webkit-font-smoothing: antialiased;
}

.app-subtitle {
    margin-top: 4px;
    font-size: 1.05rem;
    color: #000000 !important;
    letter-spacing: 0.3px;
    text-shadow: 
        0 0 1px rgba(255,255,255,1),
        0 0 3px rgba(255,255,255,0.8),
        1px 1px 1px rgba(255,255,255,0.9);
    font-weight: 600;
    -webkit-font-smoothing: antialiased;
}

.card {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(3px);
    border: 2px solid rgba(50, 50, 50, 0.3);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 6px 25px rgba(0,0,0,0.2);
    transition: all 0.35s ease;
}

.card:hover {
    background: rgba(255, 255, 255, 0.98);
    box-shadow: 0 10px 35px rgba(0,0,0,0.25);
    border-color: rgba(74, 144, 226, 0.8);
    transform: translateY(-2px);
}

.stButton > button {
    background: rgba(255, 255, 255, 0.98) !important;
    color: #000000 !important;
    border: 2px solid rgba(0, 0, 0, 0.4) !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    padding: 12px 26px !important;
    transition: all 0.3s ease;
    text-shadow: none !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.stButton > button:hover {
    background: #4a90e2 !important;
    color: white !important;
    border-color: #4a90e2 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(74, 144, 226, 0.4);
}

/* Thumbs Up/Down Button Styling - Remove White Background */
.stButton > button[data-testid*="thumbs_up"], 
.stButton > button[data-testid*="thumbs_down"],
button[kind="secondary"]:has-text("👍"),
button[kind="secondary"]:has-text("👎") {
    background: transparent !important;
    border: 2px solid rgba(0, 0, 0, 0.3) !important;
    border-radius: 50% !important;
    width: 60px !important;
    height: 60px !important;
    font-size: 24px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
}

/* Thumbs Up Specific Styling */
.stButton > button:has-text("👍") {
    background: transparent !important;
    border-color: rgba(40, 167, 69, 0.5) !important;
}

.stButton > button:has-text("👍"):hover {
    background: rgba(40, 167, 69, 0.1) !important;
    border-color: #28a745 !important;
    transform: translateY(-2px) scale(1.05) !important;
    box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3) !important;
}

/* Thumbs Down Specific Styling */
.stButton > button:has-text("👎") {
    background: transparent !important;
    border-color: rgba(220, 53, 69, 0.5) !important;
}

.stButton > button:has-text("👎"):hover {
    background: rgba(220, 53, 69, 0.1) !important;
    border-color: #dc3545 !important;
    transform: translateY(-2px) scale(1.05) !important;
    box-shadow: 0 4px 15px rgba(220, 53, 69, 0.3) !important;
}

/* Secondary Button Styling (for thumbs buttons) */
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 2px solid rgba(0, 0, 0, 0.3) !important;
    border-radius: 12px !important;
    color: #000000 !important;
    font-weight: 600 !important;
    padding: 8px 16px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
}

/* Thumbs buttons specific styling */
.stButton > button[kind="secondary"]:hover {
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
}

.examples-container {
    border: 2px solid rgba(50, 50, 50, 0.4);
    border-radius: 16px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(2px);
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

.examples-title {
    color: #000000 !important;
    font-weight: 700 !important;
    text-shadow: 
        0 0 1px rgba(255,255,255,1),
        0 0 3px rgba(255,255,255,0.8),
        1px 1px 1px rgba(255,255,255,0.9);
    -webkit-font-smoothing: antialiased;
}

.small-muted {
    color: #1a1a1a !important;
    font-size: 0.8em;
    font-weight: 600;
    text-shadow: 
        0 0 1px rgba(255,255,255,1),
        0 0 2px rgba(255,255,255,0.7);
    -webkit-font-smoothing: antialiased;
}

/* ========== FLOATING MUSIC NOTES ANIMATION ========== */
/* DELETE THIS ENTIRE SECTION TO REMOVE ANIMATION */
.floating-notes {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: -1;
    overflow: hidden;
}

.music-note {
    position: absolute;
    font-size: 24px;
    color: rgba(200, 200, 200, 0.3);
    animation: float-up 15s infinite linear;
}

.music-note:nth-child(1) { left: 10%; animation-delay: 0s; font-size: 20px; }
.music-note:nth-child(2) { left: 20%; animation-delay: 2s; font-size: 28px; }
.music-note:nth-child(3) { left: 30%; animation-delay: 4s; font-size: 22px; }
.music-note:nth-child(4) { left: 40%; animation-delay: 6s; font-size: 26px; }
.music-note:nth-child(5) { left: 50%; animation-delay: 8s; font-size: 24px; }
.music-note:nth-child(6) { left: 60%; animation-delay: 10s; font-size: 20px; }
.music-note:nth-child(7) { left: 70%; animation-delay: 12s; font-size: 30px; }
.music-note:nth-child(8) { left: 80%; animation-delay: 14s; font-size: 22px; }
.music-note:nth-child(9) { left: 90%; animation-delay: 16s; font-size: 26px; }

@keyframes float-up {
    0% {
        transform: translateY(100vh) rotate(0deg);
        opacity: 0;
    }
    10% {
        opacity: 1;
    }
    90% {
        opacity: 1;
    }
    100% {
        transform: translateY(-100px) rotate(360deg);
        opacity: 0;
    }
}
/* ========== END FLOATING NOTES ANIMATION ========== */
</style>

<!-- FLOATING MUSIC NOTES HTML -->
<!-- DELETE THIS ENTIRE SECTION TO REMOVE ANIMATION -->
<div class="floating-notes">
    <div class="music-note">♪</div>
    <div class="music-note">♫</div>
    <div class="music-note">♪</div>
    <div class="music-note">♬</div>
    <div class="music-note">♫</div>
    <div class="music-note">♪</div>
    <div class="music-note">♩</div>
    <div class="music-note">♫</div>
    <div class="music-note">♪</div>
</div>
<!-- END FLOATING NOTES HTML -->
""", unsafe_allow_html=True)

# Add keyboard shortcuts and enhanced UX
st.markdown("""
<!-- Keyboard Shortcuts Info -->
<div class="keyboard-shortcuts">
    <div style="font-weight: bold; margin-bottom: 5px;">⌨️ Quick Tips</div>
    <div>Ctrl+Enter: Generate</div>
    <div>Ctrl+D: Download</div>
    <div>Ctrl+R: Refresh</div>
</div>
""", unsafe_allow_html=True)

# ---------- Functions ----------
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                print(f"[INFO] Loaded {len(data)} items from history")
                return data
            else:
                print("[WARN] History file contains non-list data")
                return []
    except json.JSONDecodeError as e:
        print(f"[ERROR] History file is corrupted: {e}")
        st.error(f"History file is corrupted. Attempting to restore from backup...")
        
        # Try to restore from backup
        backup_files = [
            HISTORY_FILE.replace(".json", "_backup.json"),
            HISTORY_FILE.replace(".json", "_backup_20251220_192245.json"),
            HISTORY_FILE.replace(".json", "_backup_20251220_192235.json")
        ]
        
        for backup_file in backup_files:
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, "r", encoding="utf-8") as f:
                        backup_data = json.load(f)
                        if isinstance(backup_data, list):
                            print(f"[INFO] Restored {len(backup_data)} items from backup: {backup_file}")
                            # Save the restored data as the main history
                            with open(HISTORY_FILE, "w", encoding="utf-8") as main_f:
                                json.dump(backup_data, main_f, ensure_ascii=False, indent=2)
                            st.success(f"✅ History restored from backup ({len(backup_data)} items)")
                            return backup_data
                except Exception as backup_e:
                    print(f"[WARN] Backup file {backup_file} also corrupted: {backup_e}")
                    continue
        
        st.error("❌ Could not restore history from any backup file")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load history: {e}")
        st.error(f"History load failed: {e}")
        return []

def save_history(all_items: List[dict]):
    if not all_items:
        print("[WARN] Refusing to overwrite history with empty list")
        return
    
    try:
        # Create backup before saving
        if os.path.exists(HISTORY_FILE):
            backup_file = HISTORY_FILE.replace(".json", "_backup.json")
            import shutil
            shutil.copy2(HISTORY_FILE, backup_file)
        
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        print(f"[INFO] History saved successfully with {len(all_items)} items")
    except Exception as e:
        print(f"[ERROR] Failed to save history: {e}")
        st.error(f"Failed to save history: {e}")

def create_zip_bytes(file_paths: List[str], arc_names: Optional[List[str]] = None) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i, p in enumerate(file_paths):
            if not os.path.exists(p):
                continue
            arcname = (arc_names[i] if arc_names and i < len(arc_names) else os.path.basename(p))
            zf.write(p, arcname=arcname)
    bio.seek(0)
    return bio.read()

def evaluate_quality_for_item(item: dict) -> Optional[Dict]:
    """Evaluate quality for a specific item and update it in history"""
    
    audio_path = item.get("audio_files", {}).get("wav")
    
    if not audio_path:
        st.error("❌ No audio file path found in item")
        return None
    
    if not os.path.exists(audio_path):
        st.error(f"❌ Audio file not found: {audio_path}")
        return None

    st.info(f"🔍 Evaluating quality for: {os.path.basename(audio_path)}")
    
    try:
        svc = st.session_state.service
        
        # Get expected parameters
        expected_params = item.get("parameters", {})
        if not expected_params:
            # Fallback defaults
            expected_params = {"duration": 30, "energy": 5}
        
        st.info(f"📊 Expected parameters: Duration={expected_params.get('duration', 30)}s, Energy={expected_params.get('energy', 5)}")
        
        # Evaluate quality
        quality_result = svc.score_audio(audio_path, expected_params)
        
        if not quality_result:
            st.error("❌ Quality evaluation returned no results")
            return None
        
        # Display results immediately
        overall_score = quality_result.get("overall", 0)
        status = quality_result.get("status", "UNKNOWN")
        
        st.success(f"✅ Quality Score: {overall_score:.1f}/100 ({status})")
        
        # Update the item in history
        updated = False
        for it in st.session_state.history_master:
            if it["id"] == item["id"]:
                it["quality"] = quality_result
                updated = True
                break
        
        if not updated:
            st.warning("⚠️ Could not find item in history to update")
            return quality_result
        
        # Save updated history
        save_history(st.session_state.history_master)
        
        # Update session state
        st.session_state.history = st.session_state.history_master[:MAX_DISPLAY]
        
        st.success("💾 Quality data saved to history")
        
        return quality_result

    except Exception as e:
        st.error(f"❌ Quality evaluation failed: {str(e)}")
        st.exception(e)
        return None

def display_quality_metrics(quality_data: dict):
    """Display comprehensive quality metrics with visual progress bars and color coding"""
    if not quality_data or not isinstance(quality_data, dict):
        st.warning("⚠️ No quality data available")
        return
    
    overall_score = quality_data.get("overall", 0)
    breakdown = quality_data.get("breakdown", {})
    analysis = quality_data.get("analysis", {})
    
    # Overall Quality Score with emoji
    quality_emoji = "🏆" if overall_score >= 90 else "🥇" if overall_score >= 80 else "🥈" if overall_score >= 70 else "🥉" if overall_score >= 60 else "⚠️"
    quality_level = analysis.get("quality_level", "Unknown")
    
    st.metric(
        label=f"{quality_emoji} Quality Score",
        value=f"{overall_score:.1f}/100",
        delta=quality_level
    )
    
    # Detailed Quality Breakdown with Progress Bars
    st.markdown("#### 📊 Quality Breakdown")
    
    quality_metrics = [
        ("🎵 Audio Quality", breakdown.get("audio_quality", 0), "Technical audio quality (clipping, noise, volume)"),
        ("⏱️ Duration Accuracy", breakdown.get("duration_accuracy", 0), "How well duration matches request"),
        ("🔇 Silence Detection", breakdown.get("silence_detection", 0), "Absence of unwanted silent sections"),
        ("📈 Dynamic Range", breakdown.get("dynamic_range", 0), "Musical variation and dynamics"),
        ("🎼 Frequency Balance", breakdown.get("frequency_balance", 0), "Balanced frequency distribution"),
        ("⚡ Energy Level", breakdown.get("energy_level", 0), "Energy matching request"),
        ("🥁 Tempo Detection", breakdown.get("tempo_detection", 0), "Tempo alignment with energy"),
        ("🌈 Spectral Quality", breakdown.get("spectral_characteristics", 0), "Spectral richness and stability")
    ]
    
    for metric_name, score, description in quality_metrics:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Color coding based on score
            if score >= 85:
                color = "#00C851"  # Green
                status_emoji = "✅"
            elif score >= 70:
                color = "#ffbb33"  # Yellow
                status_emoji = "⚠️"
            else:
                color = "#ff4444"  # Red
                status_emoji = "❌"
            
            # Progress bar
            progress_html = f"""
            <div style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                    <span style="font-weight: 500;">{metric_name}</span>
                    <span style="font-weight: bold; color: {color};">{status_emoji} {score:.1f}</span>
                </div>
                <div style="background-color: #f0f0f0; border-radius: 10px; height: 8px; overflow: hidden;">
                    <div style="background-color: {color}; height: 100%; width: {score}%; border-radius: 10px; transition: width 0.3s ease;"></div>
                </div>
                <div style="font-size: 0.8em; color: #666; margin-top: 2px;">{description}</div>
            </div>
            """
            st.markdown(progress_html, unsafe_allow_html=True)

def add_quality_evaluation_button(item: dict, context: str = "current"):
    """Add quality evaluation button for current generation only"""
    item_id = item.get("id")
    
    # Check if this item has been evaluated in this session
    if item_id in st.session_state.evaluated_items:
        quality_result = st.session_state.evaluated_items[item_id]
        overall_score = quality_result.get("overall", 0)
        status = quality_result.get("status", "UNKNOWN")
        quality_emoji = "🏆" if overall_score >= 90 else "🥇" if overall_score >= 80 else "🥈" if overall_score >= 70 else "🥉" if overall_score >= 60 else "⚠️"
        
        st.success(f"{quality_emoji} Quality Score: {overall_score:.1f}/100 ({status})")
        st.markdown("#### 📊 Quality Breakdown")
        display_quality_metrics(quality_result)
        return
    
    # Check if item already has quality data
    if item.get("quality"):
        quality_data = item.get("quality", {})
        if isinstance(quality_data, dict):
            overall_score = quality_data.get("overall", 0)
            quality_emoji = "🏆" if overall_score >= 90 else "🥇" if overall_score >= 80 else "🥈" if overall_score >= 70 else "🥉" if overall_score >= 60 else "⚠️"
            st.info(f"{quality_emoji} Quality: {overall_score:.1f}/100")
        return
    
    # Show evaluation button for current generation only
    if st.button(f"🔍 Evaluate Quality", key=f"eval_quality_{context}_{item_id}"):
        with st.spinner("Evaluating audio quality..."):
            quality_result = evaluate_quality_for_item(item)
            if quality_result:
                # Store in session state for immediate display
                st.session_state.evaluated_items[item_id] = quality_result
                
                # Show immediate results
                overall_score = quality_result.get("overall", 0)
                status = quality_result.get("status", "UNKNOWN")
                quality_emoji = "🏆" if overall_score >= 90 else "🥇" if overall_score >= 80 else "🥈" if overall_score >= 70 else "🥉" if overall_score >= 60 else "⚠️"
                
                st.success(f"{quality_emoji} Quality Score: {overall_score:.1f}/100 ({status})")
                
                # Display the quality metrics immediately
                st.markdown("#### 📊 Quality Breakdown")
                display_quality_metrics(quality_result)
                
                st.info("💾 Quality data has been saved to history.")
            else:
                st.error("❌ Quality evaluation failed. Please try again.")

def display_feedback_system(item_id: str, context: str = "fullwidth"):
    """Display user feedback system with star rating, thumbs, categories, and comments"""
    st.markdown("### 💬 User Feedback")
    
    # Check if feedback already exists for this item
    existing_feedback = []
    for item in st.session_state.history_master:
        if item["id"] == item_id:
            existing_feedback = item.get("feedback", [])
            break
    
    if existing_feedback:
        st.info(f"✅ You've already provided {len(existing_feedback)} feedback(s) for this track.")
        with st.expander("📝 View Previous Feedback"):
            for idx, fb in enumerate(existing_feedback, 1):
                st.markdown(f"**Feedback #{idx}** - {fb.get('timestamp', 'N/A')}")
                if fb.get('rating'):
                    st.write(f"⭐ Rating: {'★' * fb['rating']}{'☆' * (5 - fb['rating'])} ({fb['rating']}/5)")
                if fb.get('thumbs') is not None:
                    st.write(f"👍 Quick Feedback: {'👍 Thumbs Up' if fb['thumbs'] else '👎 Thumbs Down'}")
                if fb.get('category'):
                    st.write(f"🏷️ Category: {fb['category']}")
                if fb.get('comment'):
                    st.write(f"💭 Comment: {fb['comment']}")
                st.markdown("---")
    
    st.markdown("#### 🎯 Provide New Feedback")
    
    # Star Rating (1-5 stars) - Using radio buttons for better UX
    st.markdown("**⭐ Rate this music**")
    star_options = [
        "1 ★☆☆☆☆ - Poor",
        "2 ★★☆☆☆ - Fair", 
        "3 ★★★☆☆ - Good",
        "4 ★★★★☆ - Very Good",
        "5 ★★★★★ - Excellent"
    ]
    selected_rating_str = st.radio(
        "Select rating:",
        star_options,
        key=f"rating_{context}_{item_id}",
        index=None,
        label_visibility="collapsed"
    )
    selected_rating = None
    if selected_rating_str:
        selected_rating = int(selected_rating_str[0])
    
    # Thumbs Up/Down (below rating) - Improved styling
    st.markdown("**👍👎 Quick Feedback**")
    
    # Create centered columns for better spacing
    col_left, thumb_col1, thumb_col2, col_right = st.columns([1, 2, 2, 1])
    thumbs_feedback = None
    
    with thumb_col1:
        if st.button("👍 Like", key=f"thumbs_up_{context}_{item_id}", use_container_width=True, type="secondary"):
            thumbs_feedback = True
    
    with thumb_col2:
        if st.button("👎 Dislike", key=f"thumbs_down_{context}_{item_id}", use_container_width=True, type="secondary"):
            thumbs_feedback = False
    
    # Feedback Categories
    st.markdown("**🏷️ Feedback Category**")
    feedback_categories = [
        "Select a category...",
        "✨ Perfect!",
        "🎵 Great melody",
        "🥁 Good rhythm",
        "🎨 Creative composition",
        "❌ Doesn't match mood",
        "🔊 Poor audio quality",
        "🔁 Too repetitive",
        "⚡ Wrong energy level",
        "⏱️ Duration issue"
    ]
    
    selected_category = st.selectbox(
        "Choose what best describes this music:",
        feedback_categories,
        key=f"category_{context}_{item_id}",
        label_visibility="collapsed"
    )
    
    # Optional Comment Box
    st.markdown("**💭 Additional Comments (Optional)**")
    comment = st.text_area(
        "Share your detailed thoughts about this music...",
        key=f"comment_{context}_{item_id}",
        placeholder="What did you like or dislike? Any specific feedback?",
        height=80,
        label_visibility="collapsed"
    )
    
    # Submit Feedback Button
    if st.button("📝 Submit Feedback", key=f"submit_feedback_{context}_{item_id}", type="primary", use_container_width=True):
        if selected_rating or thumbs_feedback is not None or (selected_category != "Select a category...") or comment.strip():
            feedback_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "rating": selected_rating,
                "thumbs": thumbs_feedback,
                "category": selected_category if selected_category != "Select a category..." else None,
                "comment": comment.strip() if comment.strip() else None
            }
            
            # Save feedback to item
            for item in st.session_state.history_master:
                if item["id"] == item_id:
                    if "feedback" not in item:
                        item["feedback"] = []
                    item["feedback"].append(feedback_entry)
                    break
            
            save_history(st.session_state.history_master)
            st.success("🎉 Thank you for your feedback! Your input helps improve the music generation.")
            st.rerun()
        else:
            st.warning("⚠️ Please provide at least one type of feedback before submitting.")

def display_aggregate_feedback():
    """Display aggregate feedback statistics"""
    if not st.session_state.history_master:
        return
    
    st.markdown("### 📊 Aggregate Feedback Summary")
    
    # Collect all feedback
    all_ratings = []
    thumbs_up = 0
    thumbs_total = 0
    category_counts = {}
    total_feedback_count = 0
    
    for item in st.session_state.history_master:
        for feedback in item.get("feedback", []):
            total_feedback_count += 1
            if feedback.get("rating"):
                all_ratings.append(feedback["rating"])
            
            if feedback.get("thumbs") is not None:
                thumbs_total += 1
                if feedback["thumbs"]:
                    thumbs_up += 1
            
            if feedback.get("category"):
                category = feedback["category"]
                category_counts[category] = category_counts.get(category, 0) + 1
    
    if total_feedback_count == 0:
        st.info("📝 No feedback collected yet. Generate music and provide feedback to see statistics here!")
        return
    
    # Display aggregate stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if all_ratings:
            avg_rating = sum(all_ratings) / len(all_ratings)
            rating_emoji = "🏆" if avg_rating >= 4.5 else "🥇" if avg_rating >= 4.0 else "🥈" if avg_rating >= 3.5 else "🥉" if avg_rating >= 3.0 else "📊"
            st.metric(f"{rating_emoji} Average Rating", f"{avg_rating:.1f}/5", f"({len(all_ratings)} ratings)")
        else:
            st.metric("⭐ Average Rating", "No ratings yet")
    
    with col2:
        if thumbs_total > 0:
            approval_rate = (thumbs_up / thumbs_total) * 100
            approval_emoji = "🎉" if approval_rate >= 80 else "👍" if approval_rate >= 60 else "👎"
            st.metric(f"{approval_emoji} Approval Rate", f"{approval_rate:.0f}%", f"({thumbs_up}/{thumbs_total})")
        else:
            st.metric("👍 Approval Rate", "No votes yet")
    
    with col3:
        st.metric("💬 Total Feedback", total_feedback_count)
    
    with col4:
        songs_with_feedback = sum(1 for item in st.session_state.history_master if item.get("feedback"))
        st.metric("🎵 Songs Rated", f"{songs_with_feedback}/{len(st.session_state.history_master)}")
    
    # Most common feedback themes
    if category_counts:
        st.markdown("#### 🏆 Most Common Feedback Themes")
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Create columns for better display
        theme_cols = st.columns(min(3, len(sorted_categories)))
        for idx, (category, count) in enumerate(sorted_categories[:3]):  # Top 3
            with theme_cols[idx % 3]:
                percentage = (count / total_feedback_count) * 100
                st.metric(f"{category}", f"{count} mentions", f"{percentage:.0f}% of feedback")
        
        # Show remaining themes in a compact format
        if len(sorted_categories) > 3:
            with st.expander("📋 View All Feedback Themes"):
                for category, count in sorted_categories:
                    percentage = (count / total_feedback_count) * 100
                    st.write(f"• **{category}**: {count} mentions ({percentage:.0f}%)")
    
    # Recent feedback highlights
    recent_feedback = []
    for item in st.session_state.history_master:
        for feedback in item.get("feedback", []):
            if feedback.get("comment"):
                recent_feedback.append({
                    "comment": feedback["comment"],
                    "timestamp": feedback.get("timestamp", "Unknown"),
                    "rating": feedback.get("rating"),
                    "prompt": item.get("prompt", "Unknown")[:50]
                })
    
    if recent_feedback:
        recent_feedback.sort(key=lambda x: x["timestamp"], reverse=True)
        with st.expander("💭 Recent Comments"):
            for fb in recent_feedback[:5]:  # Show last 5 comments
                rating_display = f"({'★' * fb['rating']}{'☆' * (5 - fb['rating'])})" if fb['rating'] else ""
                st.write(f"**\"{fb['prompt']}...\"** {rating_display}")
                st.write(f"💬 \"{fb['comment']}\"")
                st.write(f"🕒 {fb['timestamp']}")
                st.markdown("---")

# Initialize backend & session state with performance optimizations
if "service" not in st.session_state:
    with st.spinner("🚀 Initializing MelodAI services..."):
        st.session_state.service = MainService()

# Performance optimization: Cache service reference
service = st.session_state.service

# Performance optimization: Reduce unnecessary service reloads
if not hasattr(service, 'cache_manager') or service.cache_manager is None:
    print("[Frontend] Cache manager missing, reloading service...")
    with st.spinner("🔄 Optimizing cache system..."):
        st.session_state.service = MainService()
        service = st.session_state.service

# Update sidebar with detailed model info now that service is available
if (hasattr(st.session_state, 'current_model_choice') and 
    hasattr(service, 'model_manager') and 
    service.model_manager is not None):
    with st.sidebar:
        try:
            model_info = service.model_manager.get_model_info(st.session_state.current_model_choice)
            st.markdown("---")
            st.markdown("### 📊 Model Details")
            st.write(f"**Parameters:** {model_info['params']}")
            st.write(f"**Speed:** {model_info['speed']}")
            st.write(f"**Quality:** {model_info['quality']}")
            
            # Model recommendation for custom preset
            if (hasattr(st.session_state, 'current_preset') and 
                st.session_state.current_preset == "Custom" and 
                hasattr(st.session_state, 'current_duration')):
                recommended = service.model_manager.get_recommended_model(st.session_state.current_duration, "balanced")
                if recommended != st.session_state.current_model_choice:
                    st.info(f"💡 **Tip:** For {st.session_state.current_duration}s duration, we recommend **{recommended}** for optimal balance")
        except Exception as e:
            # Fallback if model_manager methods fail
            st.sidebar.info("📊 Model details loading...")

# Initialize history with proper persistence and auto-refresh
if "history_master" not in st.session_state:
    st.session_state.history_master = load_history()

if "history" not in st.session_state:
    st.session_state.history = st.session_state.history_master[:MAX_DISPLAY]

# Always refresh history from file on each run to show new samples immediately
current_history = load_history()
st.session_state.history_master = current_history
st.session_state.history = st.session_state.history_master[:MAX_DISPLAY]
# Update favorites set
st.session_state.favorites = set([item.get("id") for item in st.session_state.history_master if item.get("favorite")])

if "favorites" not in st.session_state:
    st.session_state.favorites = set([item.get("id") for item in st.session_state.history_master if item.get("favorite")])

if "current_generation" not in st.session_state:
    st.session_state.current_generation = None

if "user_input" not in st.session_state:
    st.session_state.user_input = ""

if "last_variations" not in st.session_state:
    st.session_state.last_variations = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if "history_limit" not in st.session_state:
    st.session_state.history_limit = 5

if "history_page" not in st.session_state:
    st.session_state.history_page = 1

if "keyboard_generate_trigger" not in st.session_state:
    st.session_state.keyboard_generate_trigger = False

if "evaluated_items" not in st.session_state:
    st.session_state.evaluated_items = {}  # Track items that have been evaluated in this session

def safe_generate(prompt: str, duration: int, energy: int, model_choice: str):
    svc = st.session_state.service
    return svc.generate_music_pipeline(
        user_input=prompt,
        duration=duration,
        energy=energy,
        model_choice=model_choice
    )

def handle_backend_result(prompt_text: str, result: dict) -> Optional[dict]:
    if not result or not isinstance(result, dict):
        st.error("Backend returned invalid response.")
        st.write("Response:", result)
        return None
        
    if result.get("status") == "error":
        st.error(f"Backend error: {result.get('error', 'Unknown error')}")
        return None
        
    if result.get("status") != "success":
        st.error("Backend returned an error.")
        st.write("Response:", result)
        return None
        
    audio_files = result.get("audio_files", {})
    if not audio_files.get("wav"):
        st.error("No audio file generated")
        return None
        
    item = {
        "id": str(uuid.uuid4()),
        "prompt": prompt_text,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "parameters": result.get("parameters", {}),
        "enhanced_prompt": result.get("enhanced_prompt", ""),
        "audio_files": audio_files,
        "favorite": False,
        "votes": 0,
        "feedback": [],
        "quality": result.get("quality", None)
    }
    
    # Prevent duplicate insert on rerun
    if not any(h["id"] == item["id"] for h in st.session_state.history_master):
        st.session_state.history_master.insert(0, item)
        save_history(st.session_state.history_master)
        st.session_state.history = st.session_state.history_master[:MAX_DISPLAY]
        st.session_state.current_generation = item
        
    return item

def toggle_favorite(item_id: str):
    for it in st.session_state.history_master:
        if it["id"] == item_id:
            it["favorite"] = not it.get("favorite", False)
            if it["favorite"]:
                st.session_state.favorites.add(item_id)
            else:
                st.session_state.favorites.discard(item_id)
            break
    save_history(st.session_state.history_master)
    st.session_state.history = st.session_state.history_master[:MAX_DISPLAY]

def delete_history_item(item_id: str):
    st.session_state.history_master = [h for h in st.session_state.history_master if h["id"] != item_id]
    st.session_state.history = st.session_state.history_master[:MAX_DISPLAY]
    st.session_state.favorites.discard(item_id)
    if st.session_state.current_generation and st.session_state.current_generation.get("id") == item_id:
        st.session_state.current_generation = None
    save_history(st.session_state.history_master)

# ---------- Header ----------
st.markdown("""
<div class="app-header">
    <h1 class="app-title">🎵 MelodAI</h1>
    <p class="app-subtitle">Professional Music Generator with AI</p>
</div>
""", unsafe_allow_html=True)

# ---------- Sidebar: Model & Presets ----------
with st.sidebar:
    st.header("🎛 Model & Presets")
    
    # Preset Selection
    preset = st.selectbox("Preset Configuration", list(PRESETS.keys()))
    
    if preset != "Custom":
        p = PRESETS[preset]
        model_choice = p["model"]
        duration = p["duration"]
        energy = p["energy"]
        st.info(f"📋 **{preset}**: {p['description']}")
    else:
        st.info(f"📋 **Custom**: {PRESETS['Custom']['description']}")
        
        # Model Selection with detailed info
        model_choice = st.selectbox(
            "Model Quality",
            list(model_map.keys()),
            help="Higher quality = slower generation. Currently only Medium is fully supported."
        )
        
        # Model Information Display (cached for performance)
        model_info = load_model_info()
        info = model_info[model_choice]
        
        # Model information display with enhanced accessibility
        with st.expander(f"📊 {model_choice} Details", expanded=False):
            st.markdown(f"""
            <div role="region" aria-label="Model {model_choice} specifications">
                <p><strong>Parameters:</strong> {info['params']}</p>
                <p><strong>Speed:</strong> {info['speed']}</p>
                <p><strong>Quality:</strong> {info['quality']}</p>
                <p><strong>Est. Time:</strong> {info['time']}</p>
                <p><strong>Best for:</strong> {info['use_case']}</p>
                <p><strong>Memory:</strong> {info['memory']}</p>
                <p><strong>Status:</strong> {info['status']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        duration = st.slider("Duration (sec)", 5, 60, 30, step=5)
        energy = st.slider("Energy", 1, 10, 6)
        
        # Estimated Generation Time
        base_time = {"Fast (Small)": 35, "Balanced (Medium)": 70, "Best (Large)": 100, "Melody (Medium)": 70}
        est_time = base_time[model_choice] + (duration * 0.8)
        st.info(f"⏱️ **Estimated Time:** ~{est_time:.0f} seconds")

    # Store in session state for later use
    st.session_state.current_model_choice = model_choice
    st.session_state.current_duration = duration
    st.session_state.current_energy = energy
    st.session_state.current_preset = preset

    # Settings Management
    st.markdown("---")
    st.subheader("⚙️ Settings Management")
    
    # Save Current Settings as Preset
    with st.expander("💾 Save Custom Preset"):
        preset_name = st.text_input("Preset Name", placeholder="My Custom Preset")
        if st.button("Save Preset") and preset_name:
            if "custom_presets" not in st.session_state:
                st.session_state.custom_presets = {}
            
            # Get current settings from session state
            current_model = st.session_state.get('current_model_choice', 'Balanced (Medium)')
            current_duration = st.session_state.get('current_duration', 30)
            current_energy = st.session_state.get('current_energy', 6)
            
            st.session_state.custom_presets[preset_name] = {
                "model": current_model,
                "duration": current_duration, 
                "energy": current_energy,
                "description": f"Custom: {current_model}, {current_duration}s, Energy {current_energy}"
            }
            st.success(f"✅ Saved preset: {preset_name}")
            st.rerun()
    
    # Load Saved Presets
    if hasattr(st.session_state, 'custom_presets') and st.session_state.custom_presets:
        with st.expander("📂 Load Custom Preset"):
            custom_preset = st.selectbox("Select Custom Preset", list(st.session_state.custom_presets.keys()))
            if st.button("Load Preset"):
                cp = st.session_state.custom_presets[custom_preset]
                st.session_state.current_model_choice = cp["model"]
                st.session_state.current_duration = cp["duration"]
                st.session_state.current_energy = cp["energy"]
                st.success(f"✅ Loaded preset: {custom_preset}")
                st.rerun()
    
    # Reset to Defaults
    if st.button("🔄 Reset to Standard"):
        st.session_state.current_model_choice = "Balanced (Medium)"
        st.session_state.current_duration = 30
        st.session_state.current_energy = 6
        st.success("✅ Reset to Standard preset")
        st.rerun()

    # Backend Status
    st.markdown("---")
    st.markdown("### 🔧 Backend Status")
    st.success("✅ **Kaggle GPU**: Connected")
    st.info("✅ **Medium Model**: Available")
    st.warning("⚠️ **Other Models**: Coming Soon")
    st.info("💡 **Tip**: Check Analytics tab for cache performance details")

# ---------- Layout: 3-Tab Structure ----------
tab_generate, tab_collection, tab_analytics = st.tabs(["🎵 Generate", "📚 Collection", "📊 Analytics"])

# ---------- 🎵 GENERATE TAB ----------
with tab_generate:
    left_col, mid_col, right_col = st.columns([1, 2, 1])

    # LEFT: Controls
    with left_col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("⚙️ Controls")
        duration = st.slider("Duration (seconds)", 5, 60, 30, step=5, help="Output length in seconds")
        energy = st.slider("Energy (1-10)", 1, 10, 5, help="Higher → more energetic/creative")
        
        with st.expander("Advanced parameters"):
            top_k = st.slider("Top-K (0=disabled)", 0, 500, 0)
            top_p = st.slider("Top-P (0.0 - 1.0)", 0.0, 1.0, 1.0, step=0.01)
            cfg = st.slider("CFG (guidance scale)", 0.0, 10.0, 3.0, step=0.1)
            expert_mode = st.checkbox("Expert mode")
        st.markdown("</div>", unsafe_allow_html=True)

    # MIDDLE: Original Layout
    with mid_col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        
        # 1. Main prompt box with form for Enter key support
        st.markdown("### Describe your Music ")
        
        # Use form to enable Enter key submission
        with st.form(key="music_generation_form", clear_on_submit=False):
            prompt_val = st.session_state.get("user_input", "")
            # Sync example click into text area
            if st.session_state.pending_prompt is not None:
                 st.session_state.user_input = st.session_state.pending_prompt
                 st.session_state.pending_prompt = None

            user_prompt = st.text_area("Describe your music", value=prompt_val, key="user_input", 
                                       height=120, placeholder="E.g., calm ambient piano with soft pads")
            
            char_count = len((user_prompt or "").strip())
            st.markdown(f"<div class='small-muted'>Characters: {char_count} | Press Ctrl+Enter in text area to generate</div>", unsafe_allow_html=True)
            
            # Form submit button (this will work with Enter key)
            form_submitted = st.form_submit_button("🎵 Generate Music", 
                                                 type="primary",
                                                 help="🎵 Create your unique track\n⌨️ Ctrl+Enter in text area works!\n⚡ Uses intelligent caching",
                                                 use_container_width=True)

        # 2. Examples in 3x3 grid
        st.markdown("""
        <div class="examples-container">
            <div class="examples-title">🎯 Click an Example to Get Started</div>
        """, unsafe_allow_html=True)
        
        EXAMPLES = get_cached_examples()
        
        # Create 3x3 grid using columns
        for row in range(3):
            cols = st.columns(3)
            for col in range(3):
                idx = row * 3 + col
                if idx < len(EXAMPLES):
                    with cols[col]:
                        if st.button(EXAMPLES[idx], key=f"example_{idx}", 
                                   help=f"Use: {EXAMPLES[idx]}"):
                            st.session_state.pending_prompt = EXAMPLES[idx]
                            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

        # 4. Batch prompts section
        with st.expander("📦 Batch Generation", expanded=False):
            batch_prompts = st.text_area("Batch prompts (one per line)", value="", height=80, 
                                        key="batch_prompts",
                                        placeholder="Enter multiple prompts, each on a separate line")

        # 3. Additional generation options (outside form)
        st.markdown("### 🎯 Additional Options")
        col_var, col_batch = st.columns([1, 1])
        with col_var:
            gen_variations = st.button("♻️ Generate 3 Variations", 
                                     help="♻️ Create 3 different versions of your prompt\n🎯 Automatically adjusts energy levels\n⚡ Each variation cached separately",
                                     use_container_width=True)
        with col_batch:
            gen_batch = st.button("🧾 Batch Generate", help="📦 Process multiple prompts at once\n📝 One prompt per line\n⚡ Efficient batch processing",
                                use_container_width=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    # Quality Evaluation Section - Full Width (moved outside columns)
    if st.session_state.current_generation:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 📊 Quality Evaluation")
        cg = st.session_state.current_generation
        quality_data = cg.get("quality")
        if quality_data:
            display_quality_metrics(quality_data)
        else:
            add_quality_evaluation_button(cg, context="fullwidth")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Feedback System Section - Full Width (below quality evaluation)
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        display_feedback_system(cg["id"], context="fullwidth")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Aggregate Feedback Summary - Full Width
        if st.session_state.history_master:
            display_aggregate_feedback()

    # RIGHT: Current Generation (simplified)
    with right_col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📌 Current Generation")
        
        if st.session_state.current_generation:
            cg = st.session_state.current_generation
            st.markdown(f"**{cg['prompt'][:60]}**")
            st.markdown(f"<div class='small-muted'>{cg['timestamp']}</div>", unsafe_allow_html=True)
            
            audio_path = cg.get("audio_files", {}).get("wav")
            if audio_path and os.path.exists(audio_path):
                st.audio(audio_path)
                
                # Download button
                with open(audio_path, "rb") as f:
                    st.download_button("⬇️ Download WAV", f, file_name=f"{cg['id']}.wav", 
                                     key=f"dl_current_{cg['id']}")
            
            if st.button("➕ Extend current"):
                st.session_state._extend_target = cg["id"]
                st.rerun()
        else:
            st.write("No current generation selected.")
        
        st.markdown("</div>", unsafe_allow_html=True)

# ---------- 📚 COLLECTION TAB ----------
with tab_collection:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    
    # Enhanced Collection Header
    col_title, col_refresh = st.columns([3, 1])
    with col_title:
        st.subheader("📚 Music Collection")
        st.markdown("*Manage your generated music library*")
    with col_refresh:
        if st.button("🔄 Refresh", help="Refresh collection from file"):
            st.session_state.history_master = load_history()
            st.session_state.history = st.session_state.history_master[:MAX_DISPLAY]
            st.session_state.favorites = set([item.get("id") for item in st.session_state.history_master if item.get("favorite")])
            st.rerun()

    total_songs = len(st.session_state.history_master)
    
    # Collection Statistics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎵 Total Songs", total_songs)
    col2.metric("⭐ Favorites", len(st.session_state.favorites))
    
    # Calculate additional stats
    rated_songs = sum(1 for item in st.session_state.history_master if item.get("feedback"))
    avg_quality = 0
    if st.session_state.history_master:
        quality_scores = [item.get("quality", {}).get("overall", 0) for item in st.session_state.history_master if item.get("quality")]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    col3.metric("💬 Rated Songs", rated_songs)
    col4.metric("📊 Avg Quality", f"{avg_quality:.1f}/100" if avg_quality > 0 else "N/A")

    st.markdown("---")

    # Enhanced Download Section
    st.markdown("### 📦 Download Music Collection")
    
    col_zip1, col_zip2, col_zip3 = st.columns(3)

    with col_zip1:
        if st.button("⬇ Download ALL Songs", key="zip_all_collection"):
           all_paths = []
           all_names = []

           for it in st.session_state.history_master:
              ap = it.get("audio_files", {}).get("wav")
              if ap and os.path.exists(ap):
                all_paths.append(ap)
                all_names.append(f"{it['id']}.wav")

           if not all_paths:
              st.warning("No audio files found.")
           else:
              zip_bytes = create_zip_bytes(all_paths, arc_names=all_names)
              st.download_button(
                "📥 Download Complete Collection",
                zip_bytes,
                file_name="melodai_complete_collection.zip",
                mime="application/zip",
                key="zip_all_download_collection"
              )

    with col_zip2:
        if st.button("⭐ Download FAVORITES", key="zip_fav_collection"):
           fav_paths = []
           fav_names = []

           for it in st.session_state.history_master:
             if it["id"] in st.session_state.favorites:
                ap = it.get("audio_files", {}).get("wav")
                if ap and os.path.exists(ap):
                    fav_paths.append(ap)
                    fav_names.append(f"{it['id']}.wav")

           if not fav_paths:
            st.warning("No favorite audio files found.")
           else:
            zip_bytes = create_zip_bytes(fav_paths, arc_names=fav_names)
            st.download_button(
                "📥 Download Favorites Collection",
                zip_bytes,
                file_name="melodai_favorites_collection.zip",
                mime="application/zip",
                key="zip_fav_download_collection"
            )
    
    with col_zip3:
        # High Quality Downloads (quality > 80)
        if st.button("🏆 Download High Quality", key="zip_quality_collection"):
           quality_paths = []
           quality_names = []

           for it in st.session_state.history_master:
             quality_score = it.get("quality", {}).get("overall", 0) if isinstance(it.get("quality"), dict) else 0
             if quality_score >= 80:
                ap = it.get("audio_files", {}).get("wav")
                if ap and os.path.exists(ap):
                    quality_paths.append(ap)
                    quality_names.append(f"{it['id']}_q{quality_score:.0f}.wav")

           if not quality_paths:
            st.warning("No high quality audio files found (80+ score).")
           else:
            zip_bytes = create_zip_bytes(quality_paths, arc_names=quality_names)
            st.download_button(
                "📥 Download High Quality Collection",
                zip_bytes,
                file_name="melodai_high_quality_collection.zip",
                mime="application/zip",
                key="zip_quality_download_collection"
            )

    st.markdown("---")

    # Enhanced Filtering and Sorting
    st.markdown("### 🔍 Filter & Sort Collection")
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        sort_option = st.selectbox(
            "Sort by",
            ["Latest First", "Oldest First", "Favorites First", "Highest Quality", "Most Feedback"],
            index=0
        )
    
    with filter_col2:
        filter_option = st.selectbox(
            "Filter by",
            ["All Songs", "Favorites Only", "High Quality (80+)", "With Feedback", "Recent (Last 7 days)"],
            index=0
        )
    
    with filter_col3:
        # Restore the slider for controlling number of songs displayed
        st.session_state.history_limit = st.slider(
            "Songs to display",
            min_value=1,
            max_value=50,
            value=st.session_state.history_limit,
            help="Adjust number of songs shown in grid"
        )

    # Apply filtering and sorting
    items = st.session_state.history_master.copy()
    
    # Apply filters
    if filter_option == "Favorites Only":
        items = [item for item in items if item.get("favorite")]
    elif filter_option == "High Quality (80+)":
        items = [item for item in items if isinstance(item.get("quality"), dict) and item.get("quality", {}).get("overall", 0) >= 80]
    elif filter_option == "With Feedback":
        items = [item for item in items if item.get("feedback")]
    elif filter_option == "Recent (Last 7 days)":
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        items = [item for item in items if datetime.strptime(item.get("timestamp", "1970-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S") > week_ago]
    
    # Apply sorting
    if sort_option == "Oldest First":
        items.reverse()
    elif sort_option == "Favorites First":
        items.sort(key=lambda x: x.get("favorite", False), reverse=True)
    elif sort_option == "Highest Quality":
        items.sort(
            key=lambda x: (
                x.get("quality", {}).get("overall", 0)
                if isinstance(x.get("quality"), dict) else 0
            ),
            reverse=True
        )
    elif sort_option == "Most Feedback":
        items.sort(key=lambda x: len(x.get("feedback", [])), reverse=True)

    # Display filtered results info
    if len(items) != len(st.session_state.history_master):
        st.info(f"📋 Showing {len(items)} of {len(st.session_state.history_master)} songs (filtered by: {filter_option})")

    # Show items based on user's slider selection
    shown = items[:st.session_state.history_limit]

    if not shown:
        if len(items) == 0:
            st.info(f"🔍 No songs match the filter '{filter_option}'. Try a different filter.")
        else:
            st.info("📋 No songs to display. Adjust the display limit.")
    else:
        st.markdown("### 🎵 Your Music Collection")
        st.markdown("*Click on any album to play • Use ⋮ menu for actions*")
        
        # Create album grid layout - 4 albums per row
        albums_per_row = 4
        
        # Add CSS for album grid with clickable albums and three-dots menu
        st.markdown("""
        <style>
        .album-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: flex-start;
            margin: 20px 0;
        }
        
        .album-card {
            width: 200px;
            background: rgba(255, 255, 255, 0.95);
            border: 2px solid rgba(0, 0, 0, 0.1);
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            cursor: pointer;
            text-align: center;
            position: relative;
        }
        
        .album-card:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .album-art {
            width: 120px;
            height: 120px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
            margin: 0 auto 15px auto;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            position: relative;
        }
        
        .album-art:hover::after {
            content: '▶️';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 24px;
            background: rgba(0,0,0,0.7);
            color: white;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0% { transform: translate(-50%, -50%) scale(1); }
            50% { transform: translate(-50%, -50%) scale(1.1); }
            100% { transform: translate(-50%, -50%) scale(1); }
        }
        
        .album-title {
            font-weight: 700;
            color: #2c3e50;
            font-size: 14px;
            margin-bottom: 8px;
            line-height: 1.3;
            height: 36px;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        
        .album-info {
            color: #7f8c8d;
            font-size: 11px;
            margin-bottom: 15px;
        }
        
        /* Album card that contains both content and buttons */
        .album-card-with-buttons {
            width: 200px;
            background: rgba(255, 255, 255, 0.95);
            border: 2px solid rgba(0, 0, 0, 0.1);
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            text-align: center;
            position: relative;
            margin-bottom: 20px;
        }
        
        .album-card-with-buttons:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        /* AGGRESSIVE: Make ALL buttons inside this card transparent */
        .album-card-with-buttons .stButton > button,
        .album-card-with-buttons .stDownloadButton > button,
        .album-card-with-buttons button,
        .album-card-with-buttons [data-testid*="button"],
        .album-card-with-buttons [role="button"] {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 18px !important;
            padding: 8px 4px !important;
            margin: 2px !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
            min-height: 40px !important;
            color: #2c3e50 !important;
        }
        
        .album-card-with-buttons .stButton > button:hover,
        .album-card-with-buttons .stDownloadButton > button:hover,
        .album-card-with-buttons button:hover,
        .album-card-with-buttons [data-testid*="button"]:hover,
        .album-card-with-buttons [role="button"]:hover {
            background: rgba(74, 144, 226, 0.25) !important;
            background-color: rgba(74, 144, 226, 0.25) !important;
            transform: translateY(-2px) scale(1.1) !important;
            border-radius: 50% !important;
            box-shadow: 0 4px 12px rgba(74, 144, 226, 0.4) !important;
        }
        
        /* Remove default Streamlit column gaps inside album cards */
        .album-card-with-buttons .stColumns {
            gap: 0.2rem !important;
        }
        
        .album-card-with-buttons [data-testid="column"] {
            padding: 0.2rem !important;
        }
        
        /* Override any remaining Streamlit button defaults */
        .album-card-with-buttons * {
            box-shadow: none !important;
        }
        
        .album-card-with-buttons .stButton,
        .album-card-with-buttons .stDownloadButton {
            background: transparent !important;
        }
        
        /* Additional override for stubborn Streamlit button styling */
        div[data-testid="column"] .stButton button,
        div[data-testid="column"] .stDownloadButton button {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        
        /* Force transparent background on all button states */
        .action-buttons button:not(:hover) {
            background: transparent !important;
            background-color: transparent !important;
        }
        
        /* SUPER AGGRESSIVE: Target play buttons specifically */
        button[key*="play_"],
        [data-testid*="button"][key*="play_"],
        .stButton button[key*="play_"],
        .album-card-with-buttons button[key*="play_"] {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 18px !important;
            padding: 8px 4px !important;
            margin: 2px !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
            min-height: 40px !important;
            color: #2c3e50 !important;
        }
        
        /* Play button hover effects */
        button[key*="play_"]:hover,
        [data-testid*="button"][key*="play_"]:hover,
        .stButton button[key*="play_"]:hover,
        .album-card-with-buttons button[key*="play_"]:hover {
            background: rgba(74, 144, 226, 0.25) !important;
            background-color: rgba(74, 144, 226, 0.25) !important;
            transform: translateY(-2px) scale(1.1) !important;
            border-radius: 50% !important;
            box-shadow: 0 4px 12px rgba(74, 144, 226, 0.4) !important;
        }
        
        /* Ultimate override for any remaining white backgrounds */
        .stButton > button:not(:hover) {
            background: transparent !important;
            background-color: transparent !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Process songs in groups of albums_per_row
        for i in range(0, len(shown), albums_per_row):
            row_items = shown[i:i + albums_per_row]
            cols = st.columns(albums_per_row)
            
            for idx, it in enumerate(row_items):
                with cols[idx]:
                    # Generate album art based on song characteristics
                    quality_data = it.get("quality")
                    overall_score = quality_data.get("overall", 0) if quality_data and isinstance(quality_data, dict) else 0
                    
                    # Choose album art emoji and colors based on prompt content
                    prompt_lower = it['prompt'].lower()
                    if any(word in prompt_lower for word in ['piano', 'classical', 'elegant']):
                        album_emoji = "🎹"
                        bg_color = "linear-gradient(45deg, #667eea 0%, #764ba2 100%)"
                    elif any(word in prompt_lower for word in ['guitar', 'acoustic', 'folk']):
                        album_emoji = "🎸"
                        bg_color = "linear-gradient(45deg, #f093fb 0%, #f5576c 100%)"
                    elif any(word in prompt_lower for word in ['electronic', 'edm', 'synth', 'techno']):
                        album_emoji = "🎛️"
                        bg_color = "linear-gradient(45deg, #4facfe 0%, #00f2fe 100%)"
                    elif any(word in prompt_lower for word in ['drums', 'beat', 'rhythm']):
                        album_emoji = "🥁"
                        bg_color = "linear-gradient(45deg, #fa709a 0%, #fee140 100%)"
                    elif any(word in prompt_lower for word in ['orchestral', 'epic', 'cinematic']):
                        album_emoji = "🎼"
                        bg_color = "linear-gradient(45deg, #a8edea 0%, #fed6e3 100%)"
                    elif any(word in prompt_lower for word in ['jazz', 'blues', 'smooth']):
                        album_emoji = "🎺"
                        bg_color = "linear-gradient(45deg, #ffecd2 0%, #fcb69f 100%)"
                    elif any(word in prompt_lower for word in ['ambient', 'chill', 'calm', 'peaceful']):
                        album_emoji = "🌙"
                        bg_color = "linear-gradient(45deg, #a8caba 0%, #5d4e75 100%)"
                    else:
                        album_emoji = "🎵"
                        bg_color = "linear-gradient(45deg, #ffecd2 0%, #fcb69f 100%)"
                    
                    # Quality-based border color
                    if overall_score >= 90:
                        border_color = "#FFD700"  # Gold
                    elif overall_score >= 80:
                        border_color = "#C0C0C0"  # Silver
                    elif overall_score >= 70:
                        border_color = "#CD7F32"  # Bronze
                    else:
                        border_color = "#ddd"
                    
                    # Create clickable album card with three-dots menu
                    audio_path = it.get("audio_files", {}).get("wav")
                    
                    # Album card with play button below and actions menu
                    st.markdown(f"""
                    <div class="album-card-with-buttons">
                        <div class="album-content">
                            <div class="album-art" style="background: {bg_color}; border: 3px solid {border_color};">
                                {album_emoji}
                            </div>
                            <div class="album-title">
                                {'⭐ ' if it["id"] in st.session_state.favorites else ''}{it['prompt'][:40]}{'...' if len(it['prompt']) > 40 else ''}
                            </div>
                            <div class="album-info">
                                {it['timestamp'].split()[0]} • {it.get("parameters", {}).get("duration", "30")}s
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Play button directly below album (centered) - inside the album card
                    if audio_path and os.path.exists(audio_path):
                        if st.button("▶️", key=f"play_{it['id']}", help="Play", use_container_width=True):
                            st.audio(audio_path, format="audio/wav", autoplay=True)
                    
                    # Actions menu with the other three options
                    with st.expander("⚙️", expanded=False):
                        action_col1, action_col2, action_col3 = st.columns(3)
                        
                        with action_col1:
                            # Favorite button
                            fav_icon = "⭐" if it["id"] in st.session_state.favorites else "☆"
                            if st.button(fav_icon, key=f"fav_{it['id']}", help="Toggle favorite", use_container_width=True):
                                toggle_favorite(it["id"])
                                st.rerun()
                        
                        with action_col2:
                            # Download button
                            if audio_path and os.path.exists(audio_path):
                                with open(audio_path, "rb") as f:
                                    st.download_button(
                                        "⬇️",
                                        f,
                                        file_name=f"{it['prompt'][:15].replace(' ', '_')}_{it['id'][:8]}.wav",
                                        key=f"dl_{it['id']}",
                                        help="Download audio file",
                                        use_container_width=True
                                    )
                        
                        with action_col3:
                            # Delete button
                            if st.button("🗑️", key=f"del_{it['id']}", help="Delete this song", use_container_width=True):
                                delete_history_item(it["id"])
                                st.rerun()
                    
                    st.markdown("</div>", unsafe_allow_html=True)  # Close album card
                    
                    st.markdown("---")  # Separator between albums

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- 📊 ANALYTICS TAB ----------
with tab_analytics:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📊 Analytics Dashboard")
    st.markdown("*Comprehensive insights into your music generation*")
    
    if not st.session_state.history_master:
        st.info("📈 Generate some music first to see analytics!")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        # Overall Statistics
        st.markdown("### 📈 Overall Statistics")
        
        total_songs = len(st.session_state.history_master)
        total_favorites = len(st.session_state.favorites)
        
        # Calculate quality statistics
        quality_scores = []
        for item in st.session_state.history_master:
            if isinstance(item.get("quality"), dict):
                score = item.get("quality", {}).get("overall", 0)
                if score > 0:
                    quality_scores.append(score)
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Calculate feedback statistics
        total_feedback = sum(len(item.get("feedback", [])) for item in st.session_state.history_master)
        rated_songs = sum(1 for item in st.session_state.history_master if item.get("feedback"))
        
        # Display key metrics
        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
        
        metric_col1.metric("🎵 Total Songs", total_songs)
        metric_col2.metric("⭐ Favorites", f"{total_favorites} ({(total_favorites/total_songs*100):.1f}%)" if total_songs > 0 else "0")
        metric_col3.metric("📊 Avg Quality", f"{avg_quality:.1f}/100" if avg_quality > 0 else "N/A")
        metric_col4.metric("💬 Total Feedback", total_feedback)
        metric_col5.metric("📝 Rated Songs", f"{rated_songs}/{total_songs}")
        
        st.markdown("---")
        
        # Cache Analytics Section
        st.markdown("### 💾 Cache Performance Analytics")
        
        cache_available = hasattr(service, 'cache_manager') and service.cache_manager is not None
        
        if cache_available:
            try:
                cache_stats = service.get_cache_statistics()
                
                cache_col1, cache_col2, cache_col3, cache_col4 = st.columns(4)
                
                with cache_col1:
                    hit_rate = cache_stats.get('hit_rate_percent', 0)
                    hit_emoji = "🎯" if hit_rate >= 50 else "📊" if hit_rate >= 25 else "📉"
                    st.metric(f"{hit_emoji} Cache Hit Rate", f"{hit_rate:.1f}%")
                
                with cache_col2:
                    cached_files = cache_stats.get('cached_files', 0)
                    st.metric("📁 Cached Files", f"{cached_files}/50")
                
                with cache_col3:
                    cache_size = cache_stats.get('cache_size_mb', 0)
                    size_emoji = "💽" if cache_size < 400 else "⚠️"
                    st.metric(f"{size_emoji} Cache Size", f"{cache_size:.1f}/500 MB")
                
                with cache_col4:
                    total_requests = cache_stats.get('total_requests', 0)
                    st.metric("📊 Total Requests", total_requests)
                
                # Cache efficiency insights
                if hit_rate >= 50:
                    st.success("🎯 **Excellent Cache Performance!** Your cache is saving significant generation time.")
                elif hit_rate >= 25:
                    st.info("📊 **Good Cache Performance.** Consider generating variations of popular prompts.")
                else:
                    st.warning("📉 **Low Cache Hit Rate.** Try reusing successful prompts to improve efficiency.")
                
                # Popular prompts analytics
                popular = cache_stats.get('most_cached_prompts', {})
                if popular:
                    st.markdown("#### 🔥 Most Popular Prompts")
                    pop_col1, pop_col2 = st.columns(2)
                    
                    with pop_col1:
                        st.markdown("**🏆 Top Cached Prompts:**")
                        for i, (prompt, count) in enumerate(list(popular.items())[:5], 1):
                            st.write(f"{i}. **{prompt}** ({count} times)")
                    
                    with pop_col2:
                        # Cache management actions
                        st.markdown("**🛠️ Cache Management:**")
                        
                        if st.button("🗑️ Clear All Cache", help="Remove all cached files"):
                            result = service.clear_cache()
                            if result.get("status") == "success":
                                st.success("✅ Cache cleared successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to clear cache")
                        
                        if st.button("🔍 Validate Cache", help="Check cache integrity"):
                            validation = service.validate_cache()
                            if validation.get('invalid_entries', 0) == 0:
                                st.success(f"✅ Cache is healthy ({validation.get('valid_entries', 0)} files)")
                            else:
                                st.warning(f"⚠️ Found {validation.get('invalid_entries', 0)} invalid entries")
                
            except Exception as e:
                st.error(f"❌ Cache analytics error: {str(e)}")
        else:
            st.warning("⚠️ Cache system not available for analytics")
        
        st.markdown("---")
        
        # Feedback Analytics (moved from Generate tab)
        display_aggregate_feedback()
        
        st.markdown("---")
        
        # Quality Analytics
        if quality_scores:
            st.markdown("### 🎯 Quality Analytics")
            
            qual_col1, qual_col2 = st.columns(2)
            
            with qual_col1:
                # Quality distribution
                excellent = sum(1 for score in quality_scores if score >= 90)
                good = sum(1 for score in quality_scores if 70 <= score < 90)
                fair = sum(1 for score in quality_scores if 50 <= score < 70)
                poor = sum(1 for score in quality_scores if score < 50)
                
                st.markdown("**🏆 Quality Distribution:**")
                total_evaluated = len(quality_scores)
                st.write(f"🏆 Excellent (90+): {excellent} ({excellent/total_evaluated*100:.1f}%)")
                st.write(f"🥇 Good (70-89): {good} ({good/total_evaluated*100:.1f}%)")
                st.write(f"🥈 Fair (50-69): {fair} ({fair/total_evaluated*100:.1f}%)")
                st.write(f"🥉 Poor (<50): {poor} ({poor/total_evaluated*100:.1f}%)")
            
            with qual_col2:
                # Quality insights
                st.markdown("**📊 Quality Insights:**")
                max_quality = max(quality_scores)
                min_quality = min(quality_scores)
                
                st.write(f"🎯 **Best Quality**: {max_quality:.1f}/100")
                st.write(f"📉 **Lowest Quality**: {min_quality:.1f}/100")
                st.write(f"📊 **Quality Range**: {max_quality - min_quality:.1f} points")
                st.write(f"🔍 **Evaluated Songs**: {len(quality_scores)}/{total_songs}")
                
                if avg_quality >= 80:
                    st.success("🏆 **Excellent overall quality!**")
                elif avg_quality >= 70:
                    st.info("🥇 **Good overall quality.**")
                else:
                    st.warning("📈 **Room for quality improvement.**")
        
        # Current Generation Analysis (if available)
        if st.session_state.current_generation:
            st.markdown("---")
            st.markdown("### 🔍 Current Generation Analysis")
            
            cg = st.session_state.current_generation
            
            analysis_col1, analysis_col2 = st.columns(2)
            
            with analysis_col1:
                st.markdown("**📋 Generation Details:**")
                st.write(f"**Prompt**: {cg['prompt']}")
                st.write(f"**Timestamp**: {cg['timestamp']}")
                
                params = cg.get("parameters", {})
                if params:
                    st.write(f"**Duration**: {params.get('duration', 'N/A')}s")
                    st.write(f"**Energy**: {params.get('energy', 'N/A')}/10")
                    st.write(f"**Model**: {params.get('actual_model', 'N/A')}")
            
            with analysis_col2:
                # Quality evaluation for current generation
                quality_data = cg.get("quality")
                if quality_data:
                    st.markdown("**📊 Quality Analysis:**")
                    display_quality_metrics(quality_data)
                else:
                    st.markdown("**🔍 Quality Evaluation:**")
                    add_quality_evaluation_button(cg, context="analytics")
            
            # Feedback for current generation
            st.markdown("---")
            display_feedback_system(cg["id"], context="analytics")
    
    st.markdown("</div>", unsafe_allow_html=True)
# ---------- Generation Logic ----------
# Get current settings from session state
current_duration = st.session_state.get('current_duration', 30)
current_energy = energy if 'energy' in locals() else st.session_state.get('current_energy', 6)
current_model = st.session_state.get('current_model_choice', 'Balanced (Medium)')

# Model compatibility check - removed warning display
# Backend will handle model fallback automatically

try:
    # Handle form submission (main generation)
    if form_submitted:
        prompt_text = (st.session_state.get("user_input") or "").strip()
        if not prompt_text:
            st.warning("Please enter a prompt.")
        else:
            with st.spinner("🔍 Processing prompt and checking cache..."):
                time.sleep(0.3)
            with st.spinner("🎵 Generating music (this may take 60-90 seconds)..."):
                # Add progress indicator
                progress_placeholder = st.empty()
                progress_placeholder.markdown("""
                <div class="generation-progress">
                    🎵 Generating your music... Please wait while AI creates your track
                </div>
                """, unsafe_allow_html=True)
                try:
                    res = safe_generate(prompt_text, current_duration, current_energy, current_model)
                    progress_placeholder.empty()  # Clear progress indicator
                except Exception as e:
                    progress_placeholder.empty()  # Clear progress indicator
                    st.error("Generation failed (backend).")
                    st.exception(e)
                    res = None
            new_item = handle_backend_result(prompt_text, res)
            if new_item:
                # Show cache status in success message
                if res and res.get("cached"):
                    st.success(f"⚡ **INSTANT** - Used cached result! (Key: {res.get('cache_key', 'N/A')})")
                else:
                    actual_model = new_item.get("parameters", {}).get("actual_model", "Unknown")
                    cache_key = res.get('cache_key') if res else None
                    cache_msg = f" (Cached: {cache_key})" if cache_key else ""
                    st.success(f"✅ Generation finished using **{actual_model}**{cache_msg} & saved to History.")
                st.session_state.last_variations = []
                st.rerun()
except Exception:
    pass

try:
    if gen_variations:
        base = (st.session_state.get("user_input") or "").strip()
        if not base:
            st.warning("Enter a base prompt.")
        else:
            st.info("🎯 Generating 3 variations with different energy levels...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            st.session_state.last_variations = []
            for i in range(3):
                progress_bar.progress((i) / 3)
                tweak_prompt = f"{base} (variation {i+1})"
                tweak_energy = max(1, min(10, current_energy + (i - 1)))
                status_text.text(f"🎵 Creating variation {i+1}/3 (Energy: {tweak_energy})")
                with st.spinner(f"♻️ Generating variation {i+1} with energy {tweak_energy}..."):
                    try:
                        res = safe_generate(tweak_prompt, current_duration, tweak_energy, current_model)
                    except Exception as e:
                        st.error(f"Variation {i+1} failed.")
                        st.exception(e)
                        res = None
                item = handle_backend_result(tweak_prompt, res)
                if item:
                    st.session_state.last_variations.append(item)
            progress_bar.progress(1.0)
            status_text.text("✅ All variations completed!")
            if st.session_state.last_variations:
                st.success("Variations generated & saved to History.")
                st.session_state.current_generation = st.session_state.last_variations[0]
                st.rerun()
except Exception:
    pass

try:
    if gen_batch:
        batch_text = (st.session_state.get("batch_prompts") or "").strip()
        if not batch_text:
            st.warning("Enter batch prompts.")
        else:
            prompts = [p.strip() for p in batch_text.split('\n') if p.strip()]
            if not prompts:
                st.warning("No valid prompts found.")
            else:
                st.info(f"📦 Processing {len(prompts)} prompts in batch mode...")
                batch_progress = st.progress(0)
                batch_status = st.empty()
                batch_results = []
                for i, prompt in enumerate(prompts):
                    batch_progress.progress(i / len(prompts))
                    batch_status.text(f"🎵 Processing {i+1}/{len(prompts)}: {prompt[:40]}...")
                    with st.spinner(f"🧾 Generating track {i+1}/{len(prompts)}: {prompt[:30]}..."):
                        try:
                            res = safe_generate(prompt, current_duration, current_energy, current_model)
                        except Exception as e:
                            st.error(f"Batch item {i+1} failed: {prompt}")
                            st.exception(e)
                            res = None
                    item = handle_backend_result(prompt, res)
                    if item:
                        batch_results.append(item)
                batch_progress.progress(1.0)
                batch_status.text(f"✅ Batch complete: {len(batch_results)} tracks generated!")
                if batch_results:
                    st.success(f"Batch complete: {len(batch_results)} tracks generated.")
                    st.session_state.current_generation = batch_results[0]
                    st.rerun()
except Exception:
    pass