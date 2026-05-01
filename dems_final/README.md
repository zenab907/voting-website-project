# 🗳️ DEMS — Digital Election Management System

**A complete production-ready Egyptian election platform secured by AI voice biometrics.**

Built with Django · PostgreSQL · Librosa MFCC · Modern HTML/CSS/JS

---

## 🏗️ Project Structure

```
dems/
├── dems_project/           # Django project config
│   ├── settings.py         # All settings (DB, voice auth, etc.)
│   ├── urls.py             # Root URL routing
│   └── wsgi.py
│
├── voting/                 # Main application
│   ├── models.py           # Voter, Candidate, District, Vote, ElectionConfig
│   ├── views.py            # All request handlers
│   ├── urls.py             # App URL patterns
│   ├── forms.py            # Form validation
│   ├── admin.py            # Django admin customization
│   ├── voice_auth.py       # 🎙️ Librosa MFCC voice authentication engine
│   │
│   ├── templates/voting/   # HTML templates
│   │   ├── base.html
│   │   ├── home.html
│   │   ├── login.html      # Voice auth UI
│   │   ├── vote.html       # Voting page
│   │   ├── success.html
│   │   ├── results.html
│   │   └── admin_*.html
│   │
│   ├── static/voting/
│   │   ├── css/main.css    # Complete design system
│   │   └── js/
│   │       ├── main.js
│   │       └── voice_auth.js  # MediaRecorder + AJAX auth
│   │
│   └── management/commands/
│       ├── seed_data.py           # Egyptian sample data
│       └── register_test_voices.py # Synthetic voiceprints for testing
│
├── manage.py
├── requirements.txt
└── .env.example
```

---

## ⚙️ Setup Instructions

### Step 1 — Prerequisites

Install these on your system before starting:

- **Python 3.11+** — [python.org](https://python.org)
- **PostgreSQL 15+** — [postgresql.org](https://postgresql.org)
- **Git** (optional)
- **VS Code** (recommended) + Python extension

> **Windows users:** Install PostgreSQL from the official installer. During setup, note your password for the `postgres` user.

---

### Step 2 — Create the Database

Open **pgAdmin** or the **psql** terminal:

```sql
-- In psql or pgAdmin Query Tool:
CREATE DATABASE dems_db;
```

Or via terminal:
```bash
# Windows (psql in PATH):
psql -U postgres -c "CREATE DATABASE dems_db;"

# macOS/Linux:
sudo -u postgres createdb dems_db
```

---

### Step 3 — Set Up Virtual Environment

Open a terminal in the `dems/` folder (the root with `manage.py`):

```bash
# Create virtual environment
python -m venv venv

# Activate it:
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# You should see (venv) in your terminal prompt
```

---

### Step 4 — Install Python Packages

```bash
pip install -r requirements.txt
```

> ⏳ This may take 2–3 minutes — Librosa installs audio processing dependencies.

---

### Step 5 — Configure Environment

```bash
# Copy the example env file
cp .env.example .env   # macOS/Linux
copy .env.example .env  # Windows
```

Open `.env` in VS Code and update:

```env
SECRET_KEY=any-long-random-string-here-abcdef123456
DEBUG=True
DB_NAME=dems_db
DB_USER=postgres
DB_PASSWORD=YOUR_POSTGRES_PASSWORD_HERE
DB_HOST=localhost
DB_PORT=5432
```

---

### Step 6 — Run Database Migrations

```bash
python manage.py makemigrations voting
python manage.py migrate
```

Expected output:
```
Applying voting.0001_initial... OK
```

---

### Step 7 — Create Admin User

```bash
python manage.py createsuperuser
```

Enter your desired username, email, and password.

---

### Step 8 — Seed the Database

```bash
python manage.py seed_data
```

This creates:
- 8 Egyptian districts (Cairo, Alexandria, Giza, etc.)
- 24 registered voters with valid 14-digit National IDs
- 19 candidates across all districts
- 1 active election (opens immediately, closes in 8 hours)

---

### Step 9 — Register Test Voiceprints

```bash
python manage.py register_test_voices
```

⚠️ This creates **synthetic** (fake) voiceprints for testing. Voice matching against synthetic voiceprints won't work with real audio — they are only for seeing the full system flow.

**For real voice testing → see Step 12 below.**

---

### Step 10 — Run the Server

```bash
python manage.py runserver
```

Open your browser: **http://127.0.0.1:8000**

---

## 🧪 Testing the System

### Testing via Admin Panel (Real Voice):

1. Go to **http://127.0.0.1:8000/admin/** → log in as superuser
2. Go to **http://127.0.0.1:8000/panel/voters/**
3. Click **"Upload Voice"** next to a voter (e.g., Ahmed Mohamed Mahmoud)
4. Select a `.wav` or `.mp3` audio file (3+ seconds of clear speech)
5. Go to **http://127.0.0.1:8000/login/**
6. Enter the voter's National ID: `29901011234561`
7. Hold the record button and speak the same phrase as the uploaded audio
8. Release — the AI will compare and authenticate you

### Test National IDs (from seed data):

| Name | National ID | District |
|---|---|---|
| Ahmed Mohamed Mahmoud | 29901011234561 | Cairo |
| Fatma Hassan Ali | 29803151234562 | Cairo |
| Hana Mostafa Kamal | 29905031234571 | Alexandria |
| Karim Adel Farouk | 30001171234572 | Alexandria |
| Youssef Ramadan Saber | 30003251234581 | Giza |
| Ahmed Ramzy Naguib | 30007161234592 | Dakahlia |

### Key URLs:

| URL | Description |
|---|---|
| `/` | Home page |
| `/login/` | Voice authentication |
| `/vote/` | Voting page (requires auth) |
| `/success/` | Vote confirmation |
| `/results/` | Live results |
| `/panel/` | Custom admin dashboard |
| `/panel/voters/` | Upload voiceprints |
| `/admin/` | Django admin (full CRUD) |

---

## 🎙️ How Voice Authentication Works

```
User speaks → Browser MediaRecorder captures audio (WebM/OGG)
                          ↓
              Audio blob sent to /api/authenticate/ (multipart POST)
                          ↓
              Django reads audio bytes
                          ↓
              Librosa: librosa.load() → extract waveform
                          ↓
              librosa.feature.mfcc() → 13 MFCC coefficients
              librosa.feature.delta() → velocity features
              librosa.feature.delta(order=2) → acceleration features
                          ↓
              Mean across time frames → 39-dimensional feature vector
              Normalize vector (L2 norm)
                          ↓
              scipy.spatial.distance.cosine() vs stored voiceprint
                          ↓
              Similarity ≥ 0.82 → AUTH SUCCESS → set session
              Similarity < 0.82 → AUTH FAILURE → show error + confidence %
```

### Tuning Voice Sensitivity:

In `.env`, adjust:
```env
VOICE_MATCH_THRESHOLD=0.82   # Lower = easier (more false positives)
                              # Higher = stricter (more false negatives)
```

Range: `0.70` (permissive) to `0.95` (very strict). Start at `0.82`.

---

## 🔐 Security Features

| Feature | Implementation |
|---|---|
| CSRF Protection | Django middleware + tokens on all forms |
| National ID Validation | Regex + birth date logic in `forms.py` |
| Replay Attack Prevention | Unix timestamp checked ± 30 seconds |
| Double Vote Prevention | Atomic DB transaction + `select_for_update()` |
| Session Security | `SESSION_COOKIE_HTTPONLY=True`, 1-hour expiry |
| File Size Limit | 5MB max audio upload |
| Voice Data | MFCC features only (no raw audio stored) |

---

## 🛠️ Common Issues

**"No module named 'librosa'"**
```bash
pip install librosa  # Make sure venv is activated
```

**"could not connect to server: Connection refused" (PostgreSQL)**
```bash
# Start PostgreSQL service:
# Windows: services.msc → find PostgreSQL → Start
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql
```

**"relation 'voting_voter' does not exist"**
```bash
python manage.py migrate  # Run migrations first
```

**Audio not recording in browser:**
- Use **Chrome** or **Firefox** (Safari has limited WebM support)
- Must be on `localhost` (HTTPS required on production for mic access)
- Allow microphone access when browser prompts

**Voice authentication always fails:**
- Lower the threshold: `VOICE_MATCH_THRESHOLD=0.70` in `.env`
- Upload voice sample via `/panel/voters/` first
- Use a WAV file (better quality than MP3) for enrollment

---

## 🚀 Production Deployment Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Set a strong `SECRET_KEY` (50+ random chars)
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Run `python manage.py collectstatic`
- [ ] Use **gunicorn** + **nginx** (or Heroku, Railway, etc.)
- [ ] Enable HTTPS (required for microphone access in browsers)
- [ ] Set `SESSION_COOKIE_SECURE=True` in settings
- [ ] Set `VOICE_MATCH_THRESHOLD=0.85` for stricter auth

---

## 📋 Django Admin Quick Reference

```bash
# Create superuser
python manage.py createsuperuser

# Reset all votes (for re-testing)
python manage.py shell -c "from voting.models import Voter; Voter.objects.update(has_voted=False)"

# Clear all votes
python manage.py shell -c "from voting.models import Vote; Vote.objects.all().delete()"

# Check registered voters
python manage.py shell -c "from voting.models import Voter; [print(v, '| VP:', bool(v.voiceprint)) for v in Voter.objects.all()]"
```
