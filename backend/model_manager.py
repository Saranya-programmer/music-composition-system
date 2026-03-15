# backend/model_manager.py

class ModelManager:
    def __init__(self):
        self.models = {
            "Fast (Small)": "facebook/musicgen-small",
            "Balanced (Medium)": "facebook/musicgen-medium", 
            "Best (Large)": "facebook/musicgen-large",
            "Melody": "facebook/musicgen-melody"
        }
        self.current_model = None
        
    def load_model(self, model_name):
        """Load model (handled by Kaggle backend)"""
        if model_name not in self.models:
            # Default to medium if unknown model
            model_name = "Balanced (Medium)"
        self.current_model = self.models[model_name]
        return self.current_model
    
    def get_recommended_model(self, duration, quality_preference="balanced"):
        """Get recommended model based on duration and quality preference"""
        if quality_preference == "speed":
            return "Fast (Small)"
        elif quality_preference == "quality":
            return "Best (Large)"
        elif duration > 45:
            # For long durations, use smaller model for speed
            return "Fast (Small)"
        elif duration < 15:
            # For short durations, can afford larger model
            return "Best (Large)"
        else:
            # Default balanced choice
            return "Balanced (Medium)"
    
    def get_model_info(self, model_name):
        """Get model information"""
        info = {
            "Fast (Small)": {"params": "300M", "speed": "Fast", "quality": "Good"},
            "Balanced (Medium)": {"params": "1.5B", "speed": "Medium", "quality": "Very Good"},
            "Best (Large)": {"params": "3.3B", "speed": "Slow", "quality": "Excellent"},
            "Melody": {"params": "1.5B", "speed": "Medium", "quality": "Melody-focused"}
        }
        return info.get(model_name, {"params": "Unknown", "speed": "Unknown", "quality": "Unknown"})
    
    def generate(self, prompt, params):
        """Generate music using current model (delegated to Kaggle API)"""
        # This is handled by the main service's Kaggle API call
        return self.current_model
