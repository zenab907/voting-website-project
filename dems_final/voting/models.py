"""
DEMS - Models (Upgraded v3)
- face_descriptor stored as JSON array (128 floats) — no images stored
- Central DB (cloud-ready): all biometric data in DB, not localStorage
- Works from ANY device because embeddings are in the central database
"""
# بخزن التمثيل الرقمي للوش
import json
import math
from django.db import models
from django.utils import timezone


class District(models.Model):
    name = models.CharField(max_length=100, unique=True)
    name_arabic = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=10, unique=True)
    seats_available = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def candidate_count(self):
        return self.candidates.count()


class Voter(models.Model):
    """
    Registered voter.
    national_id   = 14-digit Egyptian National ID (primary lookup key)
    face_descriptor = 128-float JSON array — stored in DB, NEVER in localStorage
    """
    full_name = models.CharField(max_length=200)
    national_id = models.CharField(
        max_length=14,
        unique=True,  #btkhaly el person may3mlsh vote aktr mn marra
        db_index=True, #law 3ayza a search 3ala el national_id bsr3a
        help_text="Egyptian National ID — 14 digits"
    )
    district = models.ForeignKey( #btkhaly every voter related to one district only 
        District,
        on_delete=models.SET_NULL,  #law el district etms7, el voter yeb2a ma3ndosh district bas ma yetms7sh
        null=True,
        related_name='voters'
    )
    # Biometric: 128-float embedding from face-api.js — NO raw images stored
    face_descriptor = models.TextField( #3shan its txt field
        null=True, blank=True,
        help_text="128-float face-api.js descriptor as JSON array — no raw images stored"
    )
    has_voted = models.BooleanField(default=False) #double voting prevention
    is_active = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True) #3han a3raf el process done emta

    # ── Biometric helpers ────────────────────────────────────────────────────

    @property
    def has_face_registered(self): #el voter sagel 2bl keda wala la2
        return bool(self.face_descriptor) 

    def get_face_embedding(self): #bt7awel json stored in db to py list
        """Return stored embedding as list of floats, or None."""
        if self.face_descriptor:
            try:
                return json.loads(self.face_descriptor)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def set_face_embedding(self, embedding: list):
        """Persist a 128-float embedding to the DB field (no image stored)."""
        self.face_descriptor = json.dumps(embedding) #bt7awel list to string

    @staticmethod
    def euclidean_distance(a: list, b: list) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))) #the less distance the more similar the faces ya3ny the same person

    def verify_face(self, embedding: list, threshold: float = 0.45):
        """
        Compare incoming embedding against stored one.
        Returns (matched: bool, distance: float | None)
        threshold=0.45 is stricter than the default 0.6 recommended by face-api.
        """
        stored = self.get_face_embedding()
        if not stored or len(stored) != 128 or len(embedding) != 128:
            return False, None
        dist = self.euclidean_distance(embedding, stored)
        return dist <= threshold, round(dist, 4) #law el distance <=0.45 yeb2a matched

    # ── Convenience ──────────────────────────────────────────────────────────

    def get_national_id_birth_year(self):
        """Decode birth year from Egyptian NID format."""
        if len(self.national_id) == 14:
            c = self.national_id[0] #1st digit
            yy = self.national_id[1:3] # =2 1900 to 1999 or 3 2000 to 2099
            return f"19{yy}" if c == '2' else f"20{yy}" if c == '3' else "Unknown"
        return "Unknown"

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.national_id})"


class Candidate(models.Model):
    PARTY_CHOICES = [  # الاحزاب  
        ('ndp', 'National Democratic Party'),
        ('wafd', 'Al-Wafd Party'),
        ('tagammu', 'National Progressive Unionist Party'),
        ('independent', 'Independent'),
        ('free_egyptians', 'Free Egyptians Party'),
        ('future', "Nation's Future Party"),
        ('republican_peoples', "Republican People's Party"),
    ]

    full_name = models.CharField(max_length=200)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='candidates')
    party = models.CharField(max_length=50, choices=PARTY_CHOICES, default='independent')
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='candidates/', blank=True, null=True)
    vote_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['district', 'full_name']

    def __str__(self):
        return f"{self.full_name} — {self.district.name}"


class Vote(models.Model): #immutable 3shan adman en el voter may3mlsh vote aktr mn marra, OneToOneField 3shan kol voter yeb2a 3ando vote wa7ed bas, on_delete=models.PROTECT 3shan amna3 the deletion of any voter aw candidate aw district law fe vote related beihom, 
    """Immutable vote record — OneToOne on Voter enforces one-vote-per-person."""
    voter = models.OneToOneField(Voter, on_delete=models.PROTECT, related_name='vote_cast') #protect 3shan amna3 the deletion of any voter
    candidate = models.ForeignKey(Candidate, on_delete=models.PROTECT, related_name='votes') #related_name 3shan a3raf a2olak el votes elly related beihom
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name='votes')
    cast_at = models.DateTimeField(default=timezone.now)
    voter_ip = models.GenericIPAddressField(null=True, blank=True) #ip of device

    class Meta:
        ordering = ['-cast_at']

    def __str__(self):
        return f"{self.voter.full_name} → {self.candidate.full_name}"


class ElectionConfig(models.Model):
    election_name = models.CharField(max_length=200, default="Egyptian Parliamentary Elections 2024")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Election Configuration"

    def __str__(self):
        return self.election_name

    @property
    def is_open(self):
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time
