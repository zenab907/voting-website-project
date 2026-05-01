# DEMS — Upgrade v3 Documentation

## Overview of All Changes

This document covers every upgrade made to the DEMS (Digital Election Management System).

---

## 1. Chatbot — Multi-Intent NLP (Arabic + English)

**Files:** `voting/chatbot.py` · `voting/static/voting/js/chatbot.js`

### What changed

| Feature | Before | After |
|---------|--------|-------|
| Language support | English only | Arabic + English auto-detected |
| Intents per message | 1 | Multiple (unlimited) |
| Intents supported | ~4 | 11 (added: districts, improved keywords) |
| Fallback | Generic error | Optional GPT-4o via OpenAI API |

### How multi-intent works

```
Input: "ازاي اسجل واصوت؟"

Chatbot:
  1. Detects Arabic (≥2 Arabic chars heuristic)
  2. Scores all 11 intents against the message
  3. Matches: registration (score=2) + voting (score=1)
  4. Returns both answers separated by a visual divider
```

### OpenAI fallback (optional)

Set `OPENAI_API_KEY` in `.env` to enable GPT-4o answers for questions
not covered by keyword rules. The bot always tries keyword matching first.

### New intents added

- `districts` — Lists covered governorates (Qena, Sohag, Elbehira, Luxor, Assuit)

---

## 2. Central Database — All Data in DB

**File:** `voting/models.py`

### Voter model fields

```python
class Voter(models.Model):
    national_id    = CharField(max_length=14, unique=True)   # 14-digit Egyptian NID
    full_name      = CharField(max_length=200)
    district       = ForeignKey(District)
    face_descriptor = TextField(null=True)                   # 128-float JSON array
    has_voted      = BooleanField(default=False)
    is_active      = BooleanField(default=True)
    registered_at  = DateTimeField(auto_now_add=True)
    last_login     = DateTimeField(null=True)
```

Key point: `face_descriptor` is a JSON array in the database — **no images stored anywhere**.

---

## 3. Face Recognition — Cross-Device

**Files:** `voting/static/voting/js/face_recognition.js` · `voting/views.py`

### Architecture

```
Browser (any device)              Backend (central DB)
─────────────────────             ────────────────────
Camera stream                     Voter.face_descriptor
    ↓                                     ↓
face-api.js TinyFaceDetector      JSON.loads → [128 floats]
    ↓                                     ↓
Float32Array(128)                 Euclidean distance
    ↓         POST descriptor ──→ if dist < 0.45 → match
No image sent                     Sets Django session
```

### Threshold tuning

`FACE_MATCH_THRESHOLD = 0.45` in `views.py`

| Value | Effect |
|-------|--------|
| 0.6   | More permissive (face-api.js default) |
| 0.45  | Balanced (current setting) |
| 0.35  | Very strict — may reject valid users in poor lighting |

Adjust in `views.py` if users report false rejections.

---

## 4. Login Flow

```
1. User enters 14-digit National ID
2. Clicks "Start Camera" → face-api.js loads from CDN
3. Clicks "Capture Face" → 128-D descriptor extracted
4. Clicks "Verify Identity" → POST /api/face/check/
5a. First time → embedding saved to DB → POST /api/login/ → session created
5b. Returning  → Euclidean distance < 0.45 → session created → redirect to /vote/
```

---

## 5. Voter Search API

```http
GET /api/voter/<national_id>/
```

**Response:**
```json
{
  "success": true,
  "voter": {
    "full_name": "Zenab Gamal Thabet",
    "national_id": "30606012502907",
    "district": "Assuit",
    "district_arabic": "أسيوط",
    "has_voted": false,
    "has_face_registered": true
  }
}
```

**Errors:** `400` invalid NID format · `404` not found

---

## 6. Voting System

- `cast_vote` uses `SELECT FOR UPDATE` inside `transaction.atomic()` — prevents race conditions
- `Vote` model uses `OneToOneField` on `Voter` — database-level uniqueness guarantee
- `has_voted = True` is set atomically with the `Vote` insert

---

## 7. Seed Data

```bash
python manage.py seed_data
```

Creates:
- 5 districts (Qena, Sohag, Elbehira, Luxor, Assuit)
- 8 voters (all linked to correct districts)
- 10 candidates (2 per district)
- 1 ElectionConfig (active, ends 8 hours from seeding)

Safe to re-run — uses `get_or_create` throughout.

---

## Setup Instructions

### Prerequisites

```
Python 3.10+
pip
```

### 1. Install dependencies

```bash
cd dems_upgraded
pip install django pillow python-dotenv
```

For PostgreSQL (production):
```bash
pip install dj-database-url psycopg2-binary
```

For OpenAI chatbot (optional):
```bash
pip install openai
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY at minimum
```

### 3. Database setup

```bash
python manage.py migrate
python manage.py seed_data
python manage.py createsuperuser
```

### 4. Run development server

```bash
python manage.py runserver
```

Visit: http://localhost:8000

### 5. Test the system

1. Go to http://localhost:8000/login/
2. Enter one of the seeded National IDs (e.g. `30606012502907`)
3. Click "Start Camera" → allow camera access
4. Click "Capture Face"
5. Click "Verify Identity"
   - First login → face is registered in DB
   - Subsequent logins → face is verified against stored embedding
6. Select a candidate and vote

---

## Production Deployment (Cloud)

### Switch to PostgreSQL

In `.env`:
```
DATABASE_URL=postgres://user:password@host:5432/dems_db
```

`settings.py` automatically detects `DATABASE_URL` and uses `dj_database_url`.

### Recommended platforms

| Platform | Notes |
|----------|-------|
| Render.com | Free PostgreSQL, one-click deploy |
| Railway | Simple, generous free tier |
| Supabase | PostgreSQL + free SSL |
| PythonAnywhere | Easiest for Django beginners |

### Security checklist for production

- [ ] `DEBUG=False` in `.env`
- [ ] Long random `SECRET_KEY`
- [ ] `ALLOWED_HOSTS` set to your domain
- [ ] `CSRF_TRUSTED_ORIGINS` set to your domain
- [ ] HTTPS enabled (all major platforms provide this free)
- [ ] `python manage.py collectstatic` run

---

## API Reference

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| GET    | `/api/voter/<nid>/` | None | Search voter by National ID |
| POST   | `/api/login/` | None | NID-only login → sets session |
| POST   | `/api/face/check/` | None | Face embedding verify/register |
| POST   | `/api/face/reset/` | Staff | Reset voter's face embedding |
| GET    | `/api/candidates/` | Session | Candidates for voter's district |
| POST   | `/api/cast-vote/` | Session | Cast vote (once only) |
| POST   | `/api/chatbot/` | None | NLP chatbot — Arabic + English |

---

## Security Architecture

| Concern | Solution |
|---------|----------|
| Biometric storage | 128-float JSON vector only — no images ever stored |
| Cross-device auth | All embeddings in central DB, queried per login |
| Double voting | `OneToOneField` + `SELECT FOR UPDATE` in transaction |
| Session hijacking | `SESSION_COOKIE_HTTPONLY=True`, 1-hour expiry |
| CSRF | All state-changing views protected; AJAX sends no CSRF for /api/ (csrf_exempt with input validation) |
| Vote anonymity | Vote record links voter→candidate but UI/admin never exposes individual choices |
| SQL injection | Django ORM — parameterised queries throughout |

---

## Troubleshooting

**Face not detected**
- Ensure good lighting (avoid backlight)
- Look directly at camera
- Remove glasses if first registration was without them
- Try increasing `scoreThreshold` in `face_recognition.js` from `0.5` to `0.4`

**Face mismatch on returning login**
- Increase threshold: change `FACE_MATCH_THRESHOLD = 0.45` to `0.55` in `views.py`
- Reset embedding via admin: `POST /api/face/reset/ { "national_id": "..." }`

**Chatbot not answering**
- Check the keyword lists in `chatbot.py` — add domain-specific terms
- Set `OPENAI_API_KEY` in `.env` for free-form question handling

**PostgreSQL connection error**
- Verify `DATABASE_URL` format: `postgres://user:pass@host:port/db`
- Install: `pip install dj-database-url psycopg2-binary`
- Check DB is accessible from your server
