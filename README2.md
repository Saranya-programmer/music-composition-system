# 🎵 MelodAI - AI Music Generation Platform

MelodAI is a text-to-music generation platform that converts natural language descriptions into high-quality audio compositions using Meta's MusicGen AI model.

## � Hoiw It Works (Start to End)

```
1. User opens the Streamlit web app at http://localhost:8501

2. User types a music description
   Example: "calm piano music with soft ambient pads"

3. Frontend (app.py) sends the prompt to backend MainService

4. Backend checks the Cache first
   → If same prompt was generated before → returns instantly (< 1 second)
   → If new prompt → proceeds to generation

5. MainService sends the prompt to Kaggle GPU via ngrok API
   → Kaggle runs Meta's MusicGen Medium model (1.5B parameters)
   → Model generates audio based on the text description
   → Takes 60-90 seconds for new generation

6. Generated WAV audio file is saved to /generated folder

7. Result is cached for future identical requests

8. Audio is returned to frontend and played in the browser

9. User can optionally click "Evaluate Quality"
   → System analyzes audio across 8 metrics
   → Gives a quality score from 0-100

10. Generation is saved to History with all metadata
    → User can favorite, download, or delete tracks
```

## � uTech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit (Python) |
| Backend | Python REST API |
| AI Model | Meta MusicGen Medium (1.5B params) |
| Cloud GPU | Kaggle + ngrok tunnel |
| Audio Analysis | Librosa, SciPy, NumPy |
| Caching | Custom LRU Cache (Python) |
| Storage | Local filesystem + JSON |

## 📁 Project Structure

```
melodai/
├── backend/
│   ├── main_service.py     # Handles API calls to Kaggle GPU
│   ├── quality_scorer.py   # Analyzes audio quality (8 metrics)
│   ├── cache_manager.py    # Caches generated music (LRU + TTL)
│   ├── model_manager.py    # Manages MusicGen model selection
│   └── config.json         # API endpoint configuration
├── frontend/
│   ├── app.py              # Complete Streamlit web interface
│   └── assets/             # Background images
├── tests/                  # Test scripts
└── requirements.txt        # Python dependencies
```

## 🚀 Quick Start

```bash
pip install -r requirements.txt
cd frontend
streamlit run app.py
```

> **Note:** Requires Kaggle GPU running with MusicGen model and ngrok tunnel active.
> Update `backend/config.json` with your ngrok URL before running.

## 📊 Key Metrics

- New generation time: 60-90 seconds
- Cached response time: < 1 second
- Cache hit rate: 65%+
- Quality scoring: 8 metrics (0-100 scale)

---
**Stack:** Python · Streamlit · PyTorch · Meta MusicGen · Kaggle GPU · Librosa
