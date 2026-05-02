# 🗳️ DEMS — Digital Election Management System

**A production-ready Egyptian election platform secured by AI Face Biometrics.**

Built with Django · PostgreSQL · OpenCV · Face Recognition (Dlib) · Modern HTML/CSS/JS

---

## 🏗️ Project Structure
dems/
├── dems_project/           # Django project config
│   ├── settings.py         # DB, Face Auth configs
│   ├── urls.py             # Root routing
│   └── wsgi.py
│
├── voting/                 # Main application
│   ├── models.py           # Voter (with Faceprint field), Candidate, District, Vote
│   ├── views.py            # AI verification & Request handlers
│   ├── urls.py             # App URL patterns
│   ├── face_auth.py        # 👤 Face Recognition Engine (128-d Encodings)
│   │
│   ├── templates/voting/
│   │   ├── base.html
│   │   ├── login.html      # Live Camera Feed UI
│   │   ├── vote.html       # Voting page
│   │   ├── results.html    # Real-time analytics
│   │   └── admin_voters.html
│   │
│   ├── static/voting/
│   │   ├── css/main.css
│   │   └── js/
│   │       ├── main.js
│   │       └── face_auth.js # MediaDevices API + Base64 Image Capture
│   │
│   └── management/commands/
│       ├── seed_data.py            # Egyptian sample data (National IDs)
│       └── register_test_faces.py  # Mock data for testing
│
├── manage.py
├── requirements.txt
└── .env.example


---

## ⚙️ Setup Instructions

### Step 1 — Prerequisites
- **Python 3.11+**
- **CMake** (Required for dlib/face_recognition)
- **PostgreSQL 15+**
- **VS Code** (Recommended)

### Step 2 — Install Dependencies
```bash
# Ensure you have C++ Build Tools installed for dlib
pip install django opencv-python face_recognition numpy psycopg2-binary python-dotenv
Step 3 — Database Setup
SQL
-- In pgAdmin or psql:
CREATE DATABASE dems_db;
Step 4 — Environment Configuration
Create a .env file from .env.example:

Code snippet
SECRET_KEY=any-long-random-string-here
DEBUG=True
DB_NAME=dems_db
DB_USER=postgres
DB_PASSWORD=YOUR_POSTGRES_PASSWORD_HERE
FACE_MATCH_THRESHOLD=0.6  # Lower is stricter
Step 5 — Run Migrations & Seed
Bash
python manage.py makemigrations voting
python manage.py migrate
python manage.py seed_data
Step 6 — Run Server
Bash
python manage.py runserver
Access the app at: http://127.0.0.1:8000

👤 How Face Authentication Works
Capture: The browser accesses the webcam via navigator.mediaDevices.

Detection: OpenCV/Dlib locates the face in the frame.

Encoding: The system extracts 128 unique facial landmarks (the "Faceprint").

Comparison:

It calculates the Euclidean Distance between the live scan and the stored profile.

If Distance < FACE_MATCH_THRESHOLD (default 0.6) → Authenticated.

Security: No raw photos are stored; only the mathematical face encodings.

🧪 Testing
Go to /admin/ or the custom /panel/voters/.

Upload a Reference Photo for a voter (e.g., Ahmed Mohamed).

Navigate to /login/.

Enter the National ID (e.g., 29901011234561).

Look into the camera for the AI to verify your identity.

🔐 Security Features
CSRF Protection: Secure AJAX image transmission.

Biometric Privacy: Encodings are one-way vectors (cannot be reversed to photos).

Anti-Double Vote: DB-level constraints preventing multiple ballots.

National ID Logic: Validates age, district, and checksum for Egyptian IDs.

🛠️ Common Issues
Dlib Build Error: Ensure cmake is installed and added to PATH.

Camera Access: Browser requires localhost or HTTPS for camera permissions.

Lighting: Face recognition performs best in clear, front-lit environments.
