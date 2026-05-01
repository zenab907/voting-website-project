"""
DEMS - Admin Panel Registration
Customizes how models appear in Django Admin
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Voter, Candidate, District, Vote, ElectionConfig


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_arabic', 'code', 'candidate_count', 'seats_available']
    search_fields = ['name', 'code']
    list_per_page = 30


@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'national_id', 'district', 'has_voted', 'is_active', 'registered_at']
    list_filter = ['has_voted', 'is_active', 'district']
    search_fields = ['full_name', 'national_id']
    readonly_fields = ['registered_at', 'last_login', 'has_voted']
    list_per_page = 50
    actions = ['reset_votes']

    def reset_votes(self, request, queryset):
        queryset.update(has_voted=False)
        self.message_user(request, f"Reset votes for {queryset.count()} voters.")
    reset_votes.short_description = "Reset vote status"


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'district', 'party', 'vote_count', 'is_active']
    list_filter = ['district', 'party', 'is_active']
    search_fields = ['full_name']
    list_per_page = 50


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['voter', 'candidate', 'district', 'cast_at', 'voter_ip']
    list_filter = ['district', 'cast_at']
    readonly_fields = ['voter', 'candidate', 'district', 'cast_at', 'voter_ip']
    search_fields = ['voter__full_name', 'candidate__full_name']
    list_per_page = 50

    def has_add_permission(self, request):
        return False  # Votes cannot be added manually

    def has_delete_permission(self, request, obj=None):
        return False  # Votes cannot be deleted


@admin.register(ElectionConfig)
class ElectionConfigAdmin(admin.ModelAdmin):
    list_display = ['election_name', 'start_time', 'end_time', 'is_active', 'is_open_now']

    def is_open_now(self, obj):
        if obj.is_open:
            return format_html('<span style="color:green;font-weight:bold">● OPEN</span>')
        return format_html('<span style="color:red">● Closed</span>')
    is_open_now.short_description = 'Status'
