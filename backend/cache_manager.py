# backend/cache_manager.py
import os
import json
import hashlib
import time
import shutil
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import threading
from collections import OrderedDict

class CacheManager:
    def __init__(self, cache_dir='backend/cache', max_files=50, max_size_mb=500, ttl_hours=1):
        """
        Initialize cache manager with intelligent caching capabilities
        
        Args:
            cache_dir: Directory to store cached files
            max_files: Maximum number of cached files
            max_size_mb: Maximum cache size in MB
            ttl_hours: Time to live for cache entries in hours
        """
        self.cache_dir = cache_dir
        self.max_files = max_files
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ttl_seconds = ttl_hours * 3600
        
        # Cache metadata storage
        self.metadata_file = os.path.join(cache_dir, "cache_metadata.json")
        self.stats_file = os.path.join(cache_dir, "cache_stats.json")
        
        # LRU cache for quick access
        self.lru_cache = OrderedDict()
        
        # Statistics tracking
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
            "cache_size_bytes": 0,
            "most_cached_prompts": {},
            "last_updated": datetime.now().isoformat()
        }
        
        # Thread lock for concurrent access
        self.lock = threading.Lock()
        
        # Initialize cache directory and load existing data
        self._initialize_cache()
        
        print(f"[CacheManager] Initialized with max {max_files} files, {max_size_mb}MB limit")
    
    def _initialize_cache(self):
        """Initialize cache directory and load existing metadata"""
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load existing metadata
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                    # Rebuild LRU cache from metadata
                    for key, data in metadata.items():
                        if self._is_valid_cache_entry(data):
                            self.lru_cache[key] = data
                print(f"[CacheManager] Loaded {len(self.lru_cache)} cached entries")
            except Exception as e:
                print(f"[CacheManager] Warning: Could not load metadata: {e}")
        
        # Load existing statistics
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    self.stats.update(json.load(f))
            except Exception as e:
                print(f"[CacheManager] Warning: Could not load stats: {e}")
        
        # Clean up expired entries
        self._cleanup_expired()
    
    def get_cache_key(self, prompt: str, params: Dict) -> str:
        """
        Generate cache key from prompt and parameters
        
        Args:
            prompt: User input prompt
            params: Generation parameters (duration, energy, model, etc.)
            
        Returns:
            MD5 hash string as cache key
        """
        # Normalize parameters for consistent caching
        normalized_params = {
            "duration": params.get("duration", 30),
            "energy": params.get("energy", 5),
            "model_choice": params.get("model_choice", "Balanced (Medium)")
        }
        
        # Create cache string
        cache_string = f"{prompt.strip().lower()}_{json.dumps(normalized_params, sort_keys=True)}"
        
        # Generate MD5 hash
        return hashlib.md5(cache_string.encode('utf-8')).hexdigest()
    
    def get(self, cache_key: str) -> Optional[Dict]:
        """
        Retrieve cached audio file and metadata
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Dictionary with audio file path and metadata, or None if not found
        """
        with self.lock:
            self.stats["total_requests"] += 1
            
            # Check if key exists in LRU cache
            if cache_key not in self.lru_cache:
                self.stats["misses"] += 1
                self._save_stats()
                return None
            
            # Get cache entry
            cache_entry = self.lru_cache[cache_key]
            
            # Check if entry is still valid
            if not self._is_valid_cache_entry(cache_entry):
                self._remove_cache_entry(cache_key)
                self.stats["misses"] += 1
                self._save_stats()
                return None
            
            # Check if audio file still exists
            audio_path = cache_entry.get("audio_path")
            if not audio_path or not os.path.exists(audio_path):
                self._remove_cache_entry(cache_key)
                self.stats["misses"] += 1
                self._save_stats()
                return None
            
            # Move to end (most recently used)
            self.lru_cache.move_to_end(cache_key)
            
            # Update statistics
            self.stats["hits"] += 1
            prompt = cache_entry.get("prompt", "unknown")
            self.stats["most_cached_prompts"][prompt] = self.stats["most_cached_prompts"].get(prompt, 0) + 1
            
            self._save_stats()
            
            print(f"[CacheManager] Cache HIT for key: {cache_key[:8]}...")
            return cache_entry
    
    def set(self, cache_key: str, audio_file: str, metadata: Dict):
        """
        Store audio file and metadata in cache
        
        Args:
            cache_key: Cache key
            audio_file: Path to audio file to cache
            metadata: Generation metadata (prompt, params, etc.)
        """
        with self.lock:
            try:
                # Create cache entry
                cache_entry = {
                    "audio_path": audio_file,
                    "cached_at": datetime.now().isoformat(),
                    "prompt": metadata.get("prompt", ""),
                    "parameters": metadata.get("parameters", {}),
                    "file_size": os.path.getsize(audio_file) if os.path.exists(audio_file) else 0,
                    "cache_key": cache_key
                }
                
                # Check cache limits before adding
                self._enforce_cache_limits()
                
                # Add to LRU cache
                self.lru_cache[cache_key] = cache_entry
                
                # Update cache size
                self._update_cache_size()
                
                # Save metadata
                self._save_metadata()
                
                print(f"[CacheManager] Cached audio for key: {cache_key[:8]}...")
                
            except Exception as e:
                print(f"[CacheManager] Error caching audio: {e}")
    
    def _is_valid_cache_entry(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid (not expired)"""
        try:
            cached_at = datetime.fromisoformat(cache_entry["cached_at"])
            return datetime.now() - cached_at < timedelta(seconds=self.ttl_seconds)
        except:
            return False
    
    def _remove_cache_entry(self, cache_key: str):
        """Remove cache entry and associated files"""
        if cache_key in self.lru_cache:
            cache_entry = self.lru_cache[cache_key]
            
            # Remove audio file if it exists
            audio_path = cache_entry.get("audio_path")
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception as e:
                    print(f"[CacheManager] Warning: Could not remove cached file {audio_path}: {e}")
            
            # Remove from LRU cache
            del self.lru_cache[cache_key]
    
    def _cleanup_expired(self):
        """Remove expired cache entries"""
        expired_keys = []
        for key, entry in self.lru_cache.items():
            if not self._is_valid_cache_entry(entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_cache_entry(key)
        
        if expired_keys:
            print(f"[CacheManager] Cleaned up {len(expired_keys)} expired entries")
    
    def _enforce_cache_limits(self):
        """Enforce cache size and file count limits using LRU eviction"""
        # Remove expired entries first
        self._cleanup_expired()
        
        # Enforce file count limit
        while len(self.lru_cache) >= self.max_files:
            # Remove least recently used entry
            oldest_key = next(iter(self.lru_cache))
            self._remove_cache_entry(oldest_key)
            print(f"[CacheManager] Evicted LRU entry: {oldest_key[:8]}...")
        
        # Enforce size limit
        self._update_cache_size()
        while self.stats["cache_size_bytes"] > self.max_size_bytes and self.lru_cache:
            # Remove least recently used entry
            oldest_key = next(iter(self.lru_cache))
            self._remove_cache_entry(oldest_key)
            self._update_cache_size()
            print(f"[CacheManager] Evicted for size limit: {oldest_key[:8]}...")
    
    def _update_cache_size(self):
        """Update cache size statistics"""
        total_size = 0
        for entry in self.lru_cache.values():
            total_size += entry.get("file_size", 0)
        self.stats["cache_size_bytes"] = total_size
    
    def _save_metadata(self):
        """Save cache metadata to disk"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(dict(self.lru_cache), f, indent=2)
        except Exception as e:
            print(f"[CacheManager] Warning: Could not save metadata: {e}")
    
    def _save_stats(self):
        """Save cache statistics to disk"""
        try:
            self.stats["last_updated"] = datetime.now().isoformat()
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"[CacheManager] Warning: Could not save stats: {e}")
    
    def get_statistics(self) -> Dict:
        """Get cache statistics"""
        hit_rate = 0
        if self.stats["total_requests"] > 0:
            hit_rate = (self.stats["hits"] / self.stats["total_requests"]) * 100
        
        return {
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": self.stats["total_requests"],
            "cache_hits": self.stats["hits"],
            "cache_misses": self.stats["misses"],
            "cached_files": len(self.lru_cache),
            "cache_size_mb": round(self.stats["cache_size_bytes"] / (1024 * 1024), 2),
            "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
            "most_cached_prompts": dict(sorted(
                self.stats["most_cached_prompts"].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5])  # Top 5 most cached prompts
        }
    
    def clear_cache(self):
        """Clear all cached files and metadata"""
        with self.lock:
            # Remove all cached files
            for cache_key in list(self.lru_cache.keys()):
                self._remove_cache_entry(cache_key)
            
            # Reset statistics
            self.stats = {
                "hits": 0,
                "misses": 0,
                "total_requests": 0,
                "cache_size_bytes": 0,
                "most_cached_prompts": {},
                "last_updated": datetime.now().isoformat()
            }
            
            # Save empty state
            self._save_metadata()
            self._save_stats()
            
            print("[CacheManager] Cache cleared successfully")
    
    def export_cache(self, export_dir: str) -> bool:
        """Export cache to specified directory"""
        try:
            os.makedirs(export_dir, exist_ok=True)
            
            # Copy cache directory
            if os.path.exists(self.cache_dir):
                shutil.copytree(self.cache_dir, os.path.join(export_dir, "cache"), dirs_exist_ok=True)
            
            # Export statistics
            stats_export = {
                "export_date": datetime.now().isoformat(),
                "statistics": self.get_statistics(),
                "cache_entries": len(self.lru_cache)
            }
            
            with open(os.path.join(export_dir, "cache_export_info.json"), 'w') as f:
                json.dump(stats_export, f, indent=2)
            
            print(f"[CacheManager] Cache exported to: {export_dir}")
            return True
            
        except Exception as e:
            print(f"[CacheManager] Export failed: {e}")
            return False
    
    def validate_cache(self) -> Dict:
        """Validate cache integrity and return report"""
        report = {
            "total_entries": len(self.lru_cache),
            "valid_entries": 0,
            "invalid_entries": 0,
            "missing_files": 0,
            "expired_entries": 0,
            "issues": []
        }
        
        for cache_key, entry in self.lru_cache.items():
            # Check if entry is valid
            if not self._is_valid_cache_entry(entry):
                report["expired_entries"] += 1
                report["issues"].append(f"Expired: {cache_key[:8]}...")
                continue
            
            # Check if file exists
            audio_path = entry.get("audio_path")
            if not audio_path or not os.path.exists(audio_path):
                report["missing_files"] += 1
                report["issues"].append(f"Missing file: {cache_key[:8]}...")
                continue
            
            report["valid_entries"] += 1
        
        report["invalid_entries"] = report["expired_entries"] + report["missing_files"]
        
        return report

    def warm_cache_popular_moods(self):
        """Pre-generate popular mood prompts (placeholder for future implementation)"""
        popular_prompts = [
            "calm ambient piano with soft pads",
            "upbeat electronic dance music",
            "relaxing acoustic guitar melody",
            "epic orchestral trailer music",
            "lo-fi chillhop beats"
        ]
        
        print(f"[CacheManager] Cache warming with {len(popular_prompts)} popular moods (placeholder)")
        # Note: Actual implementation would require integration with generation service
        # This is a placeholder for the cache warming feature