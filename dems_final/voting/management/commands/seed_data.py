"""
DEMS - Database Seed Command (Upgraded v4)

Changes in v4:
- Removed all dummy/fake candidates
- Added real candidates from Sphinx University, Faculty of Computers & AI
- Candidates grouped by governorate and linked to existing District objects
- Candidate table is fully cleared before re-seeding (idempotent)
- Districts and Voters are NOT touched — only Candidates are replaced

Usage:
    python manage.py seed_data           # full seed (districts + voters + candidates + election)
    python manage.py seed_data --candidates-only  # replace candidates only, keep everything else
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from voting.models import District, Voter, Candidate, ElectionConfig

# ── Districts ──────────────────────────────────────────────────────────────────
DISTRICTS_DATA = [
    {'name': 'Qena',     'name_arabic': 'قنا',     'code': 'qen', 'seats': 1},
    {'name': 'Sohag',    'name_arabic': 'سوهاج',   'code': 'Soh', 'seats': 1},
    {'name': 'Elbehira', 'name_arabic': 'البحيرة', 'code': 'Beh', 'seats': 1},
    {'name': 'Assuit',   'name_arabic': 'أسيوط',   'code': 'ASS', 'seats': 1},
]

# ── Voters ─────────────────────────────────────────────────────────────────────
VOTERS_DATA = [
    ('Zenab Gamal Thabet',          '30606012502907', 'Assuit'),
    ('Dalia Ahmed Mohamed',         '30605062502421', 'Assuit'),
    ('Abdelrahman Mohamed Ali',     '30609192502135', 'Assuit'),
    ('Wael Magdy Obaid',            '30512111301951', 'Assuit'),
    ('alaa ahmed farghaly',         '30601252502465', 'Assuit'),
    ('Mohamed Hassan Elsaie',       '27802042601331', 'Qena'),
    ('Mariam Yasser Mahmoud',       '30608051803968', 'Elbehira'),
    ('Abdallah Mahmoud Abdelkarim', '30601102602879', 'Sohag'),
]

# ── Real Candidates — Sphinx University, Faculty of Computers & AI ─────────────
# Format: (full_name, district_name, party, bio)
# district_name must exactly match District.name in the database
CANDIDATES_DATA = [
    # === Sohag ===
    (
        'Dr. Mahmoud Mohamed Owis',
        'Sohag',
        'independent',
        'Doctor at Sphinx University, Faculty of Computers and Artificial Intelligence',
        'candidates/mahmoud_owis.jpg',
    ),
    (
        'Amr Ahmed Hassanein',
        'Sohag',
        'independent',
        'Doctor at Sphinx University, Faculty of Computers and Artificial Intelligence',
        'candidates/amr_hassanein.jpg',
    ),

    # === Assuit ===
    (
        'Dr. Mamdouh Farouk',
        'Assuit',
        'independent',
        'Doctor at Sphinx University, Faculty of Computers and Artificial Intelligence',
        'candidates/mamdouh_farouk.jpg',
    ),
    (
        'Dr. Shirin Khalaf',
        'Assuit',
        'independent',
        'Doctor at Sphinx University, Faculty of Computers and Artificial Intelligence',
        'candidates/shirin_khalaf.jpg',
    ),

    # === Elbehira (Beheira) ===
    (
        'Dr. Safaa Sobh',
        'Elbehira',
        'independent',
        'Doctor at Sphinx University, Faculty of Computers and Artificial Intelligence',
        'candidates/safaa_sobh.jpg',
    ),
    (
        'Dr. Islam Mohamed Al-Qabbani',
        'Elbehira',
        'independent',
        'Doctor at the Faculty of Computers and Artificial Intelligence',
        'candidates/islam_qabbani.jpg',
    ),

    # === Qena ===
    (
        'Dr. Mohamed Hassan Al-Saie',
        'Qena',
        'independent',
        'Doctor at Sphinx University, Faculty of Computers and Artificial Intelligence',
        'candidates/mohamed_hassan_alsaie.jpg',
    ),
    (
        'Dr. Alaa Abdul Hakim',
        'Qena',
        'independent',
        'Doctor at Sphinx University, Faculty of Computers and Artificial Intelligence',
        'candidates/alaa_abdulhakim.jpg',
    ),
]


class Command(BaseCommand):
    help = 'Seed the DEMS database. Use --candidates-only to replace candidates only.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--candidates-only',
            action='store_true',
            help='Clear and re-seed candidates only. Districts, voters, and election config are not touched.',
        )

    def handle(self, *args, **options):
        candidates_only = options['candidates_only']

        self.stdout.write(self.style.WARNING('\n🗳️  DEMS Database Seed'))
        self.stdout.write('─' * 45)

        if candidates_only:
            self.stdout.write('Mode: candidates only\n')
            district_map = {d.name: d for d in District.objects.all()}
            if not district_map:
                self.stdout.write(self.style.ERROR(
                    '✗ No districts found. Run without --candidates-only first.'
                ))
                return
            self._seed_candidates(district_map)
        else:
            district_map = self._seed_districts()
            self._seed_voters(district_map)
            self._seed_candidates(district_map)
            self._seed_election()

        self._print_summary()

    # ── Step 1: Districts ──────────────────────────────────────────────────────
    def _seed_districts(self):
        self.stdout.write('\n📍 Districts:')
        district_map = {}
        for d in DISTRICTS_DATA:
            obj, created = District.objects.get_or_create(
                code=d['code'],
                defaults={
                    'name': d['name'],
                    'name_arabic': d['name_arabic'],
                    'seats_available': d['seats'],
                }
            )
            district_map[obj.name] = obj
            tag = '✓ created' if created else '  exists '
            self.stdout.write(f'  [{tag}] {obj.name} ({obj.name_arabic})')
        return district_map

    # ── Step 2: Voters ─────────────────────────────────────────────────────────
    def _seed_voters(self, district_map):
        self.stdout.write('\n👤 Voters:')
        for full_name, national_id, district_name in VOTERS_DATA:
            district = district_map.get(district_name)
            if not district:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ District "{district_name}" not found — skipping {full_name}')
                )
                continue
            obj, created = Voter.objects.get_or_create(
                national_id=national_id,
                defaults={'full_name': full_name, 'district': district, 'is_active': True}
            )
            tag = '✓ created' if created else '  exists '
            self.stdout.write(f'  [{tag}] {obj.full_name} ({national_id}) — {district_name}')

    # ── Step 3: Candidates — CLEAR FIRST, then insert ─────────────────────────
    def _seed_candidates(self, district_map):
        self.stdout.write('\n🗳️  Candidates:')

        # Delete ALL existing candidates (fake + real) before inserting
        deleted_count, _ = Candidate.objects.all().delete()
        if deleted_count:
            self.stdout.write(
                self.style.WARNING(f'  🗑  Removed {deleted_count} existing candidate(s)')
            )

        inserted = 0
        errors   = 0
        for entry in CANDIDATES_DATA:
            full_name, district_name, party, bio = entry[0], entry[1], entry[2], entry[3]
            photo_path = entry[4] if len(entry) > 4 else None
            district = district_map.get(district_name)
            if not district:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ District "{district_name}" not found — skipping {full_name}')
                )
                errors += 1
                continue

            defaults = {'party': party, 'bio': bio, 'is_active': True}
            if photo_path:
                defaults['photo'] = photo_path

            # get_or_create as a safety net (shouldn't be needed after the delete above)
            obj, created = Candidate.objects.get_or_create(
                full_name=full_name,
                district=district,
                defaults=defaults
            )
            # Update photo if candidate already existed but photo changed
            if not created and photo_path and obj.photo.name != photo_path:
                obj.photo = photo_path
                obj.save(update_fields=['photo'])
            tag = '✓ added  ' if created else '  exists '
            photo_tag = f' [photo: {photo_path}]' if photo_path else ''
            self.stdout.write(f'  [{tag}] {obj.full_name} — {district_name}{photo_tag}')
            if created:
                inserted += 1

        self.stdout.write(
            self.style.SUCCESS(f'\n  → {inserted} candidate(s) inserted, {errors} error(s)')
        )

    # ── Step 4: Election Config ────────────────────────────────────────────────
    def _seed_election(self):
        self.stdout.write('\n📅 Election Config:')
        now = timezone.now()
        obj, created = ElectionConfig.objects.get_or_create(
            election_name='Egyptian Parliamentary Elections 2024',
            defaults={
                'start_time': now - timedelta(hours=1),
                'end_time': now + timedelta(weeks=1),
                'is_active': True,
            }
        )
        if not created:
            obj.start_time = now - timedelta(hours=1)
            obj.end_time = now + timedelta(weeks=1)
            obj.is_active = True
            obj.save(update_fields=['start_time', 'end_time', 'is_active'])
        tag = '✓ created' if created else '✓ updated '
        self.stdout.write(f'  [{tag}] {obj.election_name} (open for 1 week)')

    # ── Summary ────────────────────────────────────────────────────────────────
    def _print_summary(self):
        self.stdout.write('\n' + '─' * 45)
        self.stdout.write(self.style.SUCCESS('✅  Seed complete!'))
        self.stdout.write(f'  Districts:  {District.objects.count()}')
        self.stdout.write(f'  Voters:     {Voter.objects.count()}')
        self.stdout.write(f'  Candidates: {Candidate.objects.count()}')

        self.stdout.write('\n  Candidates per district:')
        for d in District.objects.order_by('name'):
            count = d.candidates.filter(is_active=True).count()
            self.stdout.write(f'    {d.name:12} → {count} candidate(s)')
        self.stdout.write('')
