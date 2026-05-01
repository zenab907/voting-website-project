"""
DEMS - Forms
Handles validation for National ID, voter registration, etc.
"""

import re
from django import forms
from .models import Voter, Candidate, District, ElectionConfig


class LoginForm(forms.Form):
    """
    Authentication form: enter National ID
    """
    national_id = forms.CharField(
        max_length=14,
        min_length=14,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your 14-digit National ID',
            'maxlength': '14',
            'pattern': '[0-9]{14}',
            'autocomplete': 'off',
            'inputmode': 'numeric',
        }),
        label='National ID'
    )

    def clean_national_id(self):
        nid = self.cleaned_data['national_id'].strip()

        # Must be exactly 14 digits
        if not re.match(r'^\d{14}$', nid):
            raise forms.ValidationError("National ID must be exactly 14 digits.")

        # First digit must be 2 or 3 (century code for Egyptian NID)
        if nid[0] not in ('2', '3'):
            raise forms.ValidationError("Invalid National ID format.")

        # Validate birth month (digits 3-4)
        month = int(nid[3:5])
        if month < 1 or month > 12:
            raise forms.ValidationError("Invalid National ID: invalid birth month.")

        # Validate birth day (digits 5-6)
        day = int(nid[5:7])
        if day < 1 or day > 31:
            raise forms.ValidationError("Invalid National ID: invalid birth day.")

        return nid


class VoterAdminForm(forms.ModelForm):
    """Form for adding/editing voters in admin"""
    class Meta:
        model = Voter
        fields = ['full_name', 'national_id', 'district', 'is_active']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-input'}),
            'national_id': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '14'}),
        }

    def clean_national_id(self):
        nid = self.cleaned_data['national_id']
        if not re.match(r'^\d{14}$', nid):
            raise forms.ValidationError("Must be exactly 14 digits.")
        return nid


class CandidateForm(forms.ModelForm):
    """Form for adding/editing candidates"""
    class Meta:
        model = Candidate
        fields = ['full_name', 'district', 'party', 'bio', 'photo', 'is_active']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }


class DistrictForm(forms.ModelForm):
    """Form for adding/editing districts"""
    class Meta:
        model = District
        fields = ['name', 'name_arabic', 'code', 'seats_available']


class ElectionConfigForm(forms.ModelForm):
    """Form for election timing configuration"""
    class Meta:
        model = ElectionConfig
        fields = ['election_name', 'start_time', 'end_time', 'is_active']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
