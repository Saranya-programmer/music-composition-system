# backend/main_service.py
import os
import json
import requests
from backend.quality_scorer import QualityScorer
from backend.model_manager import ModelManager
from backend.cache_manager import CacheManager

# Load configuration
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}

KAGGLE_API_URL = CONFIG.get("kaggle_api_url", "https://unbartered-milan-sisterlike.ngrok-free.dev/generate")
MODEL_MAP = CONFIG.get("models", {
    "Fast (Small)": "facebook/musicgen-small",
    "Balanced (Medium)": "facebook/musicgen-medium",
    "Best (Large)": "facebook/musicgen-large",
    "Melody": "facebook/musicgen-melody"
})
class MainService:
    def __init__(self):
        print("[MainService] Ready")
        try:
            self.model_manager = ModelManager()
            print(f"[MainService] Multi-model support enabled")
            print(f"[MainService] Available models: {list(self.model_manager.models.keys())}")
        except Exception as e:
            print(f"[MainService] Warning: ModelManager initialization failed: {e}")
            self.model_manager = None
            
        self.quality_scorer = QualityScorer(min_score=CONFIG.get("quality_scoring", {}).get("min_score", 65))
        
        # Initialize cache manager with better error handling
        try:
            print("[MainService] Attempting to initialize CacheManager...")
            cache_config = CONFIG.get("caching", {})
            self.cache_manager = CacheManager(
                cache_dir=cache_config.get("cache_dir", "backend/cache"),
                max_files=cache_config.get("max_files", 50),
                max_size_mb=cache_config.get("max_size_mb", 500),
                ttl_hours=cache_config.get("ttl_hours", 1)
            )
            print("[MainService] ✅ Cache manager initialized successfully")
        except ImportError as e:
            print(f"[MainService] ❌ CacheManager import failed: {e}")
            self.cache_manager = None
        except Exception as e:
            print(f"[MainService] ❌ CacheManager initialization failed: {e}")
            import traceback
            traceback.print_exc()
            self.cache_manager = None
            
        self.use_local_fallback = False  # Disabled - only use Kaggle GPU
        print(f"[MainService] Kaggle API: {KAGGLE_API_URL}")
    
    def generate_music_local_fallback(self, user_input, duration=30, energy=5, model_choice=None):
        """Fallback method using local MusicGen when Kaggle API is unavailable"""
        try:
            from transformers import MusicgenForConditionalGeneration, AutoProcessor
            import torch
            import scipy.io.wavfile as wav
            import numpy as np
            import time
            
            # Map model choice to actual model names
            model_name = MODEL_MAP.get(model_choice, "facebook/musicgen-small")
            
            print(f"[MainService] Using local fallback with {model_name}")
            
            # Load model and processor
            processor = AutoProcessor.from_pretrained(model_name)
            model = MusicgenForConditionalGeneration.from_pretrained(model_name)
            
            # Generate music
            inputs = processor(
                text=[user_input],
                padding=True,
                return_tensors="pt",
            )
            
            # Calculate tokens for duration (approximately 50 tokens per second)
            max_new_tokens = int(duration * 50)
            
            audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)
            
            # Convert to numpy and save
            sampling_rate = model.config.audio_encoder.sampling_rate
            audio_data = audio_values[0, 0].cpu().numpy()
            
            # Ensure output directory exists
            os.makedirs("generated", exist_ok=True)
            
            # Generate unique filename
            timestamp = int(time.time())
            out_path = f"generated/music_{timestamp}.wav"
            
            # Save as WAV file
            wav.write(out_path, sampling_rate, audio_data)
            
            return {
                "status": "success",
                "parameters": {
                    "duration": duration,
                    "energy": energy,
                    "model_choice": model_choice
                },
                "enhanced_prompt": user_input,
                "audio_files": {"wav": out_path}
            }
            
        except Exception as e:
            print(f"[MainService] Local fallback failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    # ===============================
    # MUSIC GENERATION
    # ===============================
    def generate_music_pipeline(self, user_input, duration=30, energy=5, model_choice=None):
        # Auto-select model if not specified
        if not model_choice:
            model_choice = "Balanced (Medium)"  # Default to working model
            print(f"[MainService] Auto-selected model: {model_choice}")
        
        # Check cache first if cache manager is available
        cache_key = None
        if self.cache_manager:
            cache_params = {
                "duration": duration,
                "energy": energy,
                "model_choice": model_choice
            }
            cache_key = self.cache_manager.get_cache_key(user_input, cache_params)
            print(f"[MainService] Cache key: {cache_key[:8]}...")
            
            # Try to get from cache
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                print(f"[MainService] 🎯 CACHE HIT! Using cached result for: {user_input[:50]}...")
                return {
                    "status": "success",
                    "parameters": cached_result.get("parameters", cache_params),
                    "enhanced_prompt": user_input,
                    "audio_files": {"wav": cached_result["audio_path"]},
                    "cached": True,
                    "cache_key": cache_key[:8]
                }
            else:
                print(f"[MainService] Cache MISS - will generate and cache")
        
        # Check if model is supported
        supported_models = ["Balanced (Medium)"]
        if model_choice not in supported_models:
            print(f"[MainService] ⚠️ Model {model_choice} not supported, falling back to Medium")
            model_choice = "Balanced (Medium)"
        
        # Load the model
        selected_model = self.model_manager.load_model(model_choice) if self.model_manager else "facebook/musicgen-medium"
        
        # Only use Kaggle API - no local fallback
        payload = {
            "prompt": user_input,
            "duration": int(duration),
            "model": selected_model
        }
        
        print(f"[MainService] Using Kaggle API: {KAGGLE_API_URL}")
        print(f"[MainService] Model: {selected_model}")
        print(f"[MainService] Prompt: {user_input}")
        print(f"[MainService] Duration: {duration}s")
        
        try:
            # Adjust timeout based on model size
            if "small" in selected_model.lower():
                timeout = 45 if duration <= 15 else 60
            elif "large" in selected_model.lower():
                timeout = 90 if duration <= 15 else 120
            else:  # medium
                timeout = 60 if duration <= 15 else 90
                
            print(f"[MainService] Using timeout: {timeout}s for {model_choice}")
            
            response = requests.post(KAGGLE_API_URL, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                os.makedirs("generated", exist_ok=True)
                # Create unique filename with timestamp
                import time
                timestamp = int(time.time())
                out_path = f"generated/music_{timestamp}.wav"
                
                with open(out_path, "wb") as f:
                    f.write(response.content)
                
                print(f"[MainService] ✅ Music generated successfully: {out_path}")
                
                # Cache the result if cache manager is available
                if self.cache_manager and cache_key:
                    cache_metadata = {
                        "prompt": user_input,
                        "parameters": {
                            "duration": duration,
                            "energy": energy,
                            "model_choice": model_choice,
                            "actual_model": selected_model,
                            "model_supported": model_choice in supported_models
                        }
                    }
                    self.cache_manager.set(cache_key, out_path, cache_metadata)
                    print(f"[MainService] 💾 Result cached with key: {cache_key[:8]}...")
                
                return {
                    "status": "success",
                    "parameters": {
                        "duration": duration,
                        "energy": energy,
                        "model_choice": model_choice,
                        "actual_model": selected_model,
                        "model_supported": model_choice in supported_models
                    },
                    "enhanced_prompt": user_input,
                    "audio_files": {"wav": out_path},
                    "cached": False,
                    "cache_key": cache_key[:8] if cache_key else None
                    # Note: Quality evaluation removed - now manual only
                }
            else:
                error_msg = f"Kaggle API failed: {response.status_code} - {response.text[:200]}"
                print(f"[MainService] ❌ {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg
                }
                
        except requests.exceptions.Timeout:
            error_msg = f"Kaggle API timeout after {timeout}s - Your Kaggle session may have expired"
            print(f"[MainService] ❌ {error_msg}")
            return {
                "status": "error", 
                "error": error_msg
            }
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to Kaggle API - Check if your ngrok tunnel is running"
            print(f"[MainService] ❌ {error_msg}")
            return {
                "status": "error",
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Kaggle API connection error: {str(e)}"
            print(f"[MainService] ❌ {error_msg}")
            return {
                "status": "error",
                "error": error_msg
            }

    # ===============================
    # 🔑 QUALITY SCORING (THIS WAS MISSING)
    # ===============================
    def score_audio(self, audio_path, expected_params):
        return self.quality_scorer.score_audio(audio_path, expected_params)
    # ===============================
    # 🔑 CACHE MANAGEMENT METHODS
    # ===============================
    def get_cache_statistics(self):
        """Get cache statistics"""
        if self.cache_manager:
            return self.cache_manager.get_statistics()
        return {"error": "Cache manager not available"}
    
    def clear_cache(self):
        """Clear all cached files"""
        if self.cache_manager:
            self.cache_manager.clear_cache()
            return {"status": "success", "message": "Cache cleared successfully"}
        return {"status": "error", "message": "Cache manager not available"}
    
    def validate_cache(self):
        """Validate cache integrity"""
        if self.cache_manager:
            return self.cache_manager.validate_cache()
        return {"error": "Cache manager not available"}
    
    def export_cache(self, export_dir):
        """Export cache to directory"""
        if self.cache_manager:
            success = self.cache_manager.export_cache(export_dir)
            return {"status": "success" if success else "error"}
        return {"status": "error", "message": "Cache manager not available"}