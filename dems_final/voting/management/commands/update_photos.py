"""
DEMS - Update candidate photos without re-seeding
Usage: python manage.py update_photos
"""
from django.core.management.base import BaseCommand
from voting.models import Candidate

PHOTO_MAP = {
    'Dr. Mahmoud Mohamed Owis':    'candidates/mahmoud_owis.jpg',
    'Amr Ahmed Hassanein':         'candidates/amr_hassanein.jpg',
    'Dr. Mamdouh Farouk':          'candidates/mamdouh_farouk.jpg',
    'Dr. Shirin Khalaf':           'candidates/shirin_khalaf.jpg',
    'Dr. Safaa Sobh':              'candidates/safaa_sobh.jpg',
    'Dr. Islam Mohamed Al-Qabbani':'candidates/islam_qabbani.jpg',
    'Dr. Mohamed Hassan Al-Saie':  'candidates/mohamed_hassan_alsaie.jpg',
    'Dr. Alaa Abdul Hakim':        'candidates/alaa_abdulhakim.jpg',
}

class Command(BaseCommand):
    help = 'Update candidate photos without re-seeding'

    def handle(self, *args, **options):
        self.stdout.write('\n📸 Updating candidate photos...')
        updated = 0
        not_found = 0
        for name, photo_path in PHOTO_MAP.items():
            try:
                candidate = Candidate.objects.get(full_name=name)
                candidate.photo = photo_path
                candidate.save(update_fields=['photo'])
                self.stdout.write(self.style.SUCCESS(f'  ✓ {name}'))
                updated += 1
            except Candidate.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  ✗ Not found: {name}'))
                not_found += 1
        self.stdout.write(f'\n  → {updated} updated, {not_found} not found\n')
