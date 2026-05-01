"""
DEMS - URL Configuration (Upgraded v2)
New: /api/voter/<national_id>/, /api/chatbot/
"""
from django.urls import path
from . import views

urlpatterns = [
    # ── Public pages ──────────────────────────────────────────────────────────
    path('', views.home, name='home'),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('results/', views.results_page, name='results'),

    # ── Voting ────────────────────────────────────────────────────────────────
    path('vote/', views.voting_page, name='voting_page'),
    path('api/cast-vote/', views.cast_vote, name='cast_vote'),
    path('success/', views.vote_success, name='vote_success'),
    path('already-voted/', views.already_voted, name='already_voted'),

    # ── JSON APIs ─────────────────────────────────────────────────────────────
    path('api/login/', views.api_login, name='api_login'),
    path('api/candidates/', views.api_candidates, name='api_candidates'),
    path('api/face/check/', views.api_face_check, name='api_face_check'),
    path('api/face/reset/', views.api_face_reset, name='api_face_reset'),

    # ── NEW: Voter Search by National ID ──────────────────────────────────────
    path('api/voter/<str:national_id>/', views.api_voter_search, name='api_voter_search'),

    # ── NEW: Chatbot (NLP, multi-intent, Arabic+English) ──────────────────────
    path('api/chatbot/', views.api_chatbot, name='api_chatbot'),

    # ── Custom Admin Panel ────────────────────────────────────────────────────
    path('panel/', views.admin_dashboard, name='admin_dashboard'),
    path('panel/voters/', views.admin_voters, name='admin_voters'),
]
