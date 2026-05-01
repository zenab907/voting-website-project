"""
DEMS - Views (Upgraded v3)
- api_voter_search: GET /api/voter/<national_id>/
- api_chatbot: POST /api/chatbot/ — multi-intent NLP, Arabic + English
- api_face_check: cross-device face verification via DB embeddings
- cast_vote: one-vote enforcement with SELECT FOR UPDATE
- api_login: national_id only login
"""

import json
import logging
from django.shortcuts import render, redirect, get_object_or_404 #badl full code error
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods, require_GET # 3shan a2olak en el view da by accept POST requests bas  
from django.contrib import messages
from django.utils import timezone
from django.db import transaction #3shan el Atomicity 
from django.views.decorators.csrf import csrf_exempt

from .models import Voter, Candidate, District, Vote, ElectionConfig
from .forms import LoginForm
from .chatbot import get_bot_response

logger = logging.getLogger(__name__)

FACE_MATCH_THRESHOLD = 0.45  # Euclidean distance — lower = stricter


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_active_election():
    return ElectionConfig.objects.filter(is_active=True).first() # btt2ked en el system open to vote


def get_voter_from_session(request): #meen ely 3amel login
    voter_id = request.session.get('voter_id') #btdawar 3ala voter id 
    if voter_id:
        try:
            return Voter.objects.get(id=voter_id, is_active=True) #law mawgoud tegeeb el data
        except Voter.DoesNotExist:
            pass
    return None


def get_client_ip(request): #btdawar 3ala el ip address bta3 el device
    xff = request.META.get('HTTP_X_FORWARDED_FOR') #for proxies
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
#pervent the person from voting with face accounts from the same device

def _json_error(msg, status=400): #_private function
    return JsonResponse({'success': False, 'error': msg}, status=status)


def _parse_json_body(request): #betfoke el data encrypted mn el front
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, AttributeError): #law json data ghalat
        return None, 'Invalid JSON body.'


# ─── Public Pages ──────────────────────────────────────────────────────────────

def home(request):
    election = get_active_election()
    if get_voter_from_session(request):
        return redirect('voting_page')
    return render(request, 'voting/home.html', {'election': election})


def login_page(request):
    if get_voter_from_session(request):
        return redirect('voting_page')
    if request.method == 'POST':
        form = LoginForm(request.POST) #beyahkod el data ely el user katabha
        if form.is_valid():
            national_id = form.cleaned_data['national_id']
            try:
                voter = Voter.objects.get(national_id=national_id, is_active=True) #bydawar 3leh bl id
                request.session['voter_id'] = voter.id 
                voter.last_login = timezone.now()
                voter.save(update_fields=['last_login'])
                messages.success(request, f'Welcome back, {voter.full_name}!')
                return redirect('voting_page')
            except Voter.DoesNotExist:
                messages.error(request, 'National ID not found in the voter registry.')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = LoginForm() # for first login 
    return render(request, 'voting/login.html', {'form': form})


def logout_view(request):
    request.session.flush() # flush badaal delete 3ashan btemsa7 el session data, cookies 
    messages.success(request, 'You have been logged out.')
    return redirect('home')


# ─── API: Login (national_id → session) ──────────────────────────────────────

@require_POST  # post request bas
@csrf_exempt   # for API endpoint (token-based auth can be added later if needed)
def api_login(request):
    """
    POST /api/login/
    Body: { "national_id": "12345678901234" }
    Sets Django session and returns voter info.
    """
    data, err = _parse_json_body(request)
    if err:
        return _json_error(err)

    national_id = data.get('national_id', '').strip()
    if not national_id or len(national_id) != 14 or not national_id.isdigit():
        return _json_error('National ID must be exactly 14 digits.')

    try:
        voter = Voter.objects.get(national_id=national_id, is_active=True)
        request.session['voter_id'] = voter.id
        voter.last_login = timezone.now()
        voter.save(update_fields=['last_login'])
        return JsonResponse({
            'success': True,
            'voter': {
                'id': voter.id,
                'full_name': voter.full_name,
                'national_id': voter.national_id,
                'has_voted': voter.has_voted,
                'district': voter.district.name if voter.district else None,
                'has_face_registered': voter.has_face_registered,
            }
        })
    except Voter.DoesNotExist:
        return _json_error('Voter not found.', 404)


# ─── API: Voter Search by National ID ────────────────────────────────────────

@require_GET
def api_voter_search(request, national_id):
    """
    GET /api/voter/<national_id>/
    Public endpoint — returns voter info (no sensitive data).
    Response: { full_name, district, district_arabic, has_voted, has_face_registered }
    """
    national_id = national_id.strip()
    if not national_id or len(national_id) != 14 or not national_id.isdigit():
        return _json_error('Invalid National ID format.')

    try:
        voter = Voter.objects.select_related('district').get(
            national_id=national_id, is_active=True
        )
        return JsonResponse({
            'success': True,
            'voter': {
                'full_name': voter.full_name,
                'national_id': voter.national_id,
                'district': voter.district.name if voter.district else None,
                'district_arabic': voter.district.name_arabic if voter.district else None,
                'has_voted': voter.has_voted,
                'has_face_registered': voter.has_face_registered,
            }
        })
    except Voter.DoesNotExist:
        return _json_error('Voter not found.', 404)


# ─── API: Candidates ──────────────────────────────────────────────────────────

@require_GET #beta2bal get bas , read only , mafeesh edit or add 
def api_candidates(request):
    voter = get_voter_from_session(request)
    if not voter:
        return _json_error('Not authenticated.', 401)
    candidates = Candidate.objects.filter(
        district=voter.district, is_active=True
    ).order_by('full_name')
    return JsonResponse({
        'success': True,
        'candidates': [
            {
                'id': c.id,
                'full_name': c.full_name,
                'party': c.get_party_display(),
                'bio': c.bio,
                'photo_url': c.photo.url if c.photo else None,
            }
            for c in candidates
        ]
    })


# ─── API: Face Biometric (cross-device) ──────────────────────────────────────

@require_POST
@csrf_exempt
def api_face_check(request):
    """
    POST /api/face/check/
    Body: { "national_id": "...", "descriptor": [128 floats] }

    Flow:
    - No face stored yet  → register embedding in DB → return "registered"
    - Face stored          → Euclidean distance compare
      - distance < threshold  → "verified" + creates session
      - distance >= threshold → "mismatch"

    IMPORTANT: Only 128-float embeddings are stored — NO images.
    Works from ANY device because embeddings live in the central database.
    """
    data, err = _parse_json_body(request)
    if err:
        return _json_error(err)

    national_id = data.get('national_id', '').strip()
    descriptor = data.get('descriptor')

    if not national_id or len(national_id) != 14 or not national_id.isdigit():
        return _json_error('Invalid National ID.')

    if not descriptor or not isinstance(descriptor, list) or len(descriptor) != 128:
        return _json_error('Descriptor must be a list of exactly 128 floats.')

    try:
        descriptor = [float(v) for v in descriptor]
    except (TypeError, ValueError):
        return _json_error('Descriptor must contain numeric values.')

    try:
        voter = Voter.objects.select_related('district').get(
            national_id=national_id, is_active=True
        )
    except Voter.DoesNotExist:
        return _json_error('Voter not found.', 404)

    # ── First time: register embedding ────────────────────────────────────────
    if not voter.has_face_registered:
        voter.set_face_embedding(descriptor)
        voter.save(update_fields=['face_descriptor'])
        logger.info(f"Face registered for voter {national_id}")
        return JsonResponse({
            'success': True,
            'status': 'registered',
            'message': 'تم تسجيل بصمة وجهك بنجاح ✓',
            'message_en': 'Face biometric registered successfully ✓',
        })

    # ── Compare against stored embedding ──────────────────────────────────────
    matched, distance = voter.verify_face(descriptor, threshold=FACE_MATCH_THRESHOLD)

    if matched:
        request.session['voter_id'] = voter.id
        voter.last_login = timezone.now()
        voter.save(update_fields=['last_login'])
        logger.info(f"Face verified for voter {national_id} (distance={distance})")
        return JsonResponse({
            'success': True,
            'status': 'verified',
            'distance': distance,
            'message': 'تم التحقق من هويتك بنجاح ✓',
            'message_en': 'Identity verified successfully ✓',
            'voter': {
                'id': voter.id,
                'full_name': voter.full_name,
                'has_voted': voter.has_voted,
                'district': voter.district.name if voter.district else None,
            }
        })
    else:
        logger.warning(f"Face mismatch for voter {national_id} (distance={distance})")
        return JsonResponse({
            'success': False,
            'status': 'mismatch',
            'distance': distance,
            'message': 'فشل التحقق — الوجه لا يطابق السجل ✗',
            'message_en': 'Verification failed — face does not match stored record ✗',
        }, status=403)


@require_POST
@csrf_exempt
def api_face_reset(request):
    """POST /api/face/reset/ — staff only. Clears a voter's face embedding."""
    if not request.user.is_staff:
        return _json_error('Forbidden.', 403)
    data, err = _parse_json_body(request)
    if err:
        return _json_error(err)
    national_id = data.get('national_id', '').strip()
    try:
        voter = Voter.objects.get(national_id=national_id)
        voter.face_descriptor = None
        voter.save(update_fields=['face_descriptor'])
        return JsonResponse({'success': True, 'message': 'Face biometric reset.'})
    except Voter.DoesNotExist:
        return _json_error('Voter not found.', 404)
    except Exception as e:
        logger.error(f"Face reset error: {e}")
        return _json_error(str(e), 500)


# ─── API: Chatbot ─────────────────────────────────────────────────────────────

@require_POST
@csrf_exempt
def api_chatbot(request):
    """
    POST /api/chatbot/
    Body: { "message": "ازاي اسجل واصوت؟" }
    Returns: { "reply": "<html answer>" }

    Features:
    - Multi-intent: one message → multiple answers
    - Arabic + English detection
    - Optional OpenAI GPT-4o fallback (set OPENAI_API_KEY in .env)
    """
    data, err = _parse_json_body(request)
    if err:
        return _json_error(err)

    message = data.get('message', '').strip()
    if not message:
        return _json_error('Empty message.')
    if len(message) > 1000:
        return _json_error('Message too long (max 1000 chars).')

    reply = get_bot_response(message)
    return JsonResponse({'success': True, 'reply': reply})


# ─── Voting Pages ──────────────────────────────────────────────────────────────

def voting_page(request):
    voter = get_voter_from_session(request)
    if not voter:
        messages.error(request, 'Please login first.')
        return redirect('login')
    if voter.has_voted:
        return redirect('already_voted')
    election = get_active_election()
    if not election or not election.is_open:
        return render(request, 'voting/election_closed.html', {'election': election})
    candidates = Candidate.objects.filter(
        district=voter.district, is_active=True
    ).order_by('full_name')
    seconds_remaining = 0
    if election and election.is_open:
        delta = election.end_time - timezone.now()
        seconds_remaining = max(0, int(delta.total_seconds()))
    context = {
        'voter': voter,
        'candidates': candidates,
        'district': voter.district,
        'election': election,
        'seconds_remaining': seconds_remaining,
    }
    return render(request, 'voting/vote.html', context)


@require_POST
def cast_vote(request):
    """
    Cast a vote. Enforces one-vote-per-person using SELECT FOR UPDATE
    to prevent race conditions under concurrent requests.
    """
    voter = get_voter_from_session(request)
    if not voter:
        return _json_error('Not authenticated.', 401)
    if voter.has_voted:
        return _json_error('You have already voted.', 400)

    election = get_active_election()
    if not election or not election.is_open:
        return _json_error('Election is not currently open.', 400)

    data, err = _parse_json_body(request)
    if err:
        return _json_error(err)

    try:
        candidate_id = int(data.get('candidate_id'))
        candidate = get_object_or_404(
            Candidate, id=candidate_id, district=voter.district, is_active=True
        )
        with transaction.atomic():
            # Re-fetch with lock to prevent race condition double votes
            voter = Voter.objects.select_for_update().get(id=voter.id)
            if voter.has_voted:
                return _json_error('You have already voted.', 400)
            Vote.objects.create(
                voter=voter,
                candidate=candidate,
                district=voter.district,
                voter_ip=get_client_ip(request)
            )
            voter.has_voted = True
            voter.save(update_fields=['has_voted'])
            candidate.vote_count += 1
            candidate.save(update_fields=['vote_count'])
            request.session['voted_for'] = candidate.full_name
        return JsonResponse({'success': True, 'redirect': '/success/'})
    except (TypeError, ValueError):
        return _json_error('Invalid candidate ID.')
    except Exception as e:
        logger.error(f"Vote error: {e}")
        return _json_error('Server error during voting.', 500)


def vote_success(request):
    voter = get_voter_from_session(request)
    voted_for = request.session.get('voted_for')
    return render(request, 'voting/success.html', {'voter': voter, 'voted_for': voted_for})


def already_voted(request):
    voter = get_voter_from_session(request)
    return render(request, 'voting/already_voted.html', {'voter': voter})


# ─── Admin ─────────────────────────────────────────────────────────────────────

def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('/admin/')
    total_voters = Voter.objects.count()
    voted_count = Voter.objects.filter(has_voted=True).count()
    context = {
        'total_voters': total_voters,
        'voted_count': voted_count,
        'pending_count': total_voters - voted_count,
        'total_candidates': Candidate.objects.filter(is_active=True).count(),
        'face_registered': Voter.objects.exclude(
            face_descriptor__isnull=True
        ).exclude(face_descriptor='').count(),
        'election': get_active_election(),
        'districts': District.objects.prefetch_related('voters', 'votes', 'candidates').all(),
    }
    return render(request, 'voting/admin_dashboard.html', context)


def admin_voters(request):
    if not request.user.is_staff:
        return redirect('/admin/')
    voters = Voter.objects.select_related('district').all().order_by('full_name')
    return render(request, 'voting/admin_voters.html', {'voters': voters})


def results_page(request):
    districts = District.objects.prefetch_related('candidates').all()
    return render(request, 'voting/results.html', {'districts': districts})
