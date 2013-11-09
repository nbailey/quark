from dateutil import parser
from django.contrib.auth import get_user_model
from django.utils.timezone import get_current_timezone
from django.utils.timezone import make_aware

from quark.base.models import Term
from quark.user_profiles.models import CollegeStudentInfo
from quark.user_profiles.models import StudentOrgUserProfile
from quark.user_profiles.models import UserProfile

from scripts import get_json_data
from scripts.import_base_models import SEMESTER_TO_TERM


def delete_users():
    users = get_user_model().objects.all()
    for user in users:
        user.delete()


def import_users():
    models = get_json_data('auth.user.json')
    timezone = get_current_timezone()
    for model in models:
        fields = model['fields']
        user = get_user_model().objects.create_user(
            pk=model['pk'],
            username=fields['username'],
            email=fields['email'])
        user.first_name = fields['first_name']
        user.last_name = fields['last_name']
        user.is_active = fields['is_active']
        user.is_superuser = fields['is_superuser']
        user.is_staff = fields['is_staff']
        user.email = fields['email']

        # Convert the naive datetime into an aware datetime
        date_joined = parser.parse(fields['date_joined'])
        user.date_joined = make_aware(date_joined, timezone)

        user.save()


def import_user_profiles():
    models = get_json_data('user_profiles.userprofile.json')
    for model in models:
        fields = model['fields']

        # TODO(ericdwang): transfer pictures
        UserProfile.objects.get_or_create(
            pk=model['pk'],
            user=get_user_model().objects.get(pk=fields['user']),
            preferred_name=fields['preferred_name'],
            middle_name=fields['middle_name'],
            birthday=fields['birthday'],
            gender=fields['gender'],
            alt_email=fields['alt_email'],
            cell_phone=fields['cell_phone'],
            home_phone=fields['home_phone'],
            receive_text=fields['receive_text'],
            local_address1=fields['local_address1'],
            local_address2=fields['local_address2'],
            local_city=fields['local_city'],
            local_state=fields['local_state'],
            local_zip=fields['local_zip'],
            perm_address1=fields['perm_address1'],
            perm_address2=fields['perm_address2'],
            perm_city=fields['perm_city'],
            perm_state=fields['perm_state'],
            perm_zip=fields['perm_zip'],
            international_address=fields['international_address'])

        # TODO(ericdwang): convert ManyToManyField major field in noiro to
        # Foreignkey in quark
        student_info, _ = CollegeStudentInfo.objects.get_or_create(
            pk=model['pk'],
            user=get_user_model().objects.get(pk=fields['user']))
        if fields['start_semester'] is not None:
            student_info.start_term = Term.objects.get(
                pk=SEMESTER_TO_TERM[fields['start_semester']])
        if fields['grad_semester'] is not None:
            student_info.grad_term = Term.objects.get(
                pk=SEMESTER_TO_TERM[fields['grad_semester']])
        student_info.save()

        # TODO(ericdwang): handle strange bio encodings
        student_profile, _ = StudentOrgUserProfile.objects.get_or_create(
            pk=model['pk'],
            user=get_user_model().objects.get(pk=fields['user']))
        if fields['initiation_semester'] is not None:
            student_profile.initiation_term = Term.objects.get(
                pk=SEMESTER_TO_TERM[fields['initiation_semester']])
        student_profile.save()