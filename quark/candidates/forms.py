from django import forms
from django.contrib.auth import get_user_model

from quark.base.models import Term
from quark.candidates.models import Candidate
from quark.candidates.models import CandidateRequirement
from quark.candidates.models import CandidateRequirementProgress
from quark.candidates.models import Challenge
from quark.candidates.models import ChallengeType
from quark.candidates.models import ManualCandidateRequirement
from quark.events.models import EventType
from quark.user_profiles.fields import UserCommonNameChoiceField


class CandidatePhotoForm(forms.ModelForm):
    # Remove default hyperlink to image for the ImageField since the template
    # already shows the actual image
    photo = forms.ImageField(widget=forms.FileInput)

    class Meta(object):
        model = Candidate
        fields = ('photo',)


class ChallengeVerifyForm(forms.ModelForm):
    # TODO(ericdwang): NullBooleanFields show an extra blank field when using
    # custom choices. This field can be removed (so Challenge.VERIFIED_CHOICES
    # would be used instead) when Django fixes the bug.
    verified = forms.NullBooleanField()

    class Meta(object):
        model = Challenge
        fields = ('verified', 'reason')


class CandidateRequirementForm(forms.ModelForm):
    credits_needed = forms.IntegerField(
        label='', min_value=0,
        widget=forms.TextInput(attrs={'size': 2, 'maxlength': 2}))

    class Meta(object):
        model = CandidateRequirement
        exclude = ('requirement_type', 'term', 'created', 'updated')


class ManualCandidateRequirementForm(CandidateRequirementForm):
    class Meta(CandidateRequirementForm.Meta):
        model = ManualCandidateRequirement

    def __init__(self, *args, **kwargs):
        super(ManualCandidateRequirementForm, self).__init__(*args, **kwargs)
        self.fields['credits_needed'].label = 'Credits needed'


class CandidateRequirementProgressForm(forms.ModelForm):
    manually_recorded_credits = forms.IntegerField(
        min_value=0,
        widget=forms.TextInput(attrs={'size': 2, 'maxlength': 2}),
        required=False)
    alternate_credits_needed = forms.IntegerField(
        min_value=0,
        widget=forms.TextInput(attrs={'size': 2, 'maxlength': 2}))
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}), required=False)

    class Meta(object):
        model = CandidateRequirementProgress
        fields = ('manually_recorded_credits', 'alternate_credits_needed',
                  'comments')


class BaseCandidateRequirementFormset(forms.formsets.BaseFormSet):
    """Base formset used to create the formset for editing candidate
    requirements for the current term.
    """
    def total_form_count(self):
        """Sets the number of forms equal to the number of candidate
        requirements for the current term.
        """
        events = EventType.objects.count()
        challenges = ChallengeType.objects.count()
        manual = ManualCandidateRequirement.objects.filter(
            term=Term.objects.get_current_term()).count()
        # extra 2 forms are for exam files and resume
        return events + challenges + 2 + manual


class BaseCandidateProgressFormset(forms.formsets.BaseFormSet):
    """Base formset used to create the formset for editing candidate
    requirement progresses for a specific candidate.
    """
    candidate_term = None

    def __init__(self, *args, **kwargs):
        self.candidate_term = kwargs.pop('candidate_term', None)
        super(BaseCandidateProgressFormset, self).__init__(*args, **kwargs)

    def total_form_count(self):
        """Sets the number of forms equal to the number of candidate
        requirements for the candidate's term.
        """
        return CandidateRequirement.objects.filter(
            term=self.candidate_term).count()


class BaseChallengeVerifyFormset(forms.formsets.BaseFormSet):
    """Base formset used to create the formset for verifying challenges."""
    display_term = None
    user = None

    def __init__(self, *args, **kwargs):
        self.display_term = kwargs.pop('display_term', None)
        self.user = kwargs.pop('user', None)
        super(BaseChallengeVerifyFormset, self).__init__(*args, **kwargs)

    def total_form_count(self):
        """Sets the number of forms equal to the number of challenges
        requested from the user for the specified term.
        """
        return Challenge.objects.filter(
            verifying_user=self.user,
            candidate__term=self.display_term).count()


# pylint: disable=C0103
# Formset for editing candidate requirements for the current semester
CandidateRequirementFormSet = forms.formsets.formset_factory(
    CandidateRequirementForm, formset=BaseCandidateRequirementFormset)


# pylint: disable=C0103
# Formset for editing the progresses for a candidate
CandidateRequirementProgressFormSet = forms.formsets.formset_factory(
    CandidateRequirementProgressForm, formset=BaseCandidateProgressFormset)


# pylint: disable=C0103
# Formset for verifying challenges
ChallengeVerifyFormSet = forms.formsets.formset_factory(
    ChallengeVerifyForm, formset=BaseChallengeVerifyFormset)


class ChallengeForm(forms.ModelForm):
    class Meta(object):
        model = Challenge
        fields = ('challenge_type', 'description', 'verifying_user')

    def __init__(self, *args, **kwargs):
        super(ChallengeForm, self).__init__(*args, **kwargs)
        current_term = Term.objects.get_current_term()
        self.fields['verifying_user'] = UserCommonNameChoiceField(
            label='Verifying Officer',
            queryset=get_user_model().objects.filter(
                officer__term=current_term).distinct())
