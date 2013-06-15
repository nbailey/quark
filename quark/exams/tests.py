import os
import shutil

from django.conf import settings
from django.core.files import File
from django.test import TestCase

from quark.base.models import Term
from quark.courses.models import CourseInstance
from quark.exams.models import Exam
from quark.exams.models import ExamFlag


def make_test_exam(number):
    test_file = open('test.txt', 'w+')
    test_file.write('This is a test file.')
    test_exam = Exam(
        course_instance=CourseInstance.objects.get(pk=number),
        exam_number=Exam.MT1, exam_type=Exam.EXAM, verified=True,
        exam_file=File(test_file))
    test_exam.save()
    test_exam.course_instance.course.department.save()
    test_exam.course_instance.course.save()
    test_exam.course_instance.save()
    return test_exam


class ExamTest(TestCase):
    fixtures = ['test/course_instance.yaml']

    def setUp(self):
        self.test_exam = make_test_exam(10000)
        self.folder = self.test_exam.unique_id[0:2]

    def tearDown(self):
        folder = os.path.join(
            settings.MEDIA_ROOT, Exam.EXAM_FILES_LOCATION, self.folder)
        shutil.rmtree(folder, ignore_errors=True)
        os.remove('test.txt')

    def test_properites(self):
        self.assertEquals(self.test_exam.file_ext, '.txt')
        self.assertNotEqual(self.test_exam.unique_id, '')
        self.assertEquals(self.test_exam.get_term_display(), 'Spring')
        self.assertEquals(self.test_exam.get_term_name(), 'Spring 2013')
        self.assertEquals(
            unicode(self.test_exam),
            '{course}-{term}-{number}-{instructors}-{type}{ext}'.format(
                course='test100', term=Term.SPRING + '2013',
                number=Exam.MT1, instructors='Beta_Tau',
                type=Exam.EXAM, ext='.txt'))


class ExamFlagTest(TestCase):
    fixtures = ['test/course_instance.yaml']

    def setUp(self):
        self.test_exam = make_test_exam(10000)
        self.folder = self.test_exam.unique_id[0:2]

    def tearDown(self):
        folder = os.path.join(
            settings.MEDIA_ROOT, Exam.EXAM_FILES_LOCATION, self.folder)
        shutil.rmtree(folder, ignore_errors=True)
        os.remove('test.txt')

    def test_properites(self):
        exam_flag = ExamFlag(exam=self.test_exam)
        self.assertEquals(
            unicode(exam_flag), unicode(self.test_exam) + ' Flag')
        self.assertFalse(exam_flag.resolved)


class InstructorPermissionTest(TestCase):
    fixtures = ['test/course_instance.yaml']

    def setUp(self):
        self.test_exam = make_test_exam(10000)
        self.folder = self.test_exam.unique_id[0:2]

    def tearDown(self):
        folder = os.path.join(
            settings.MEDIA_ROOT, Exam.EXAM_FILES_LOCATION, self.folder)
        shutil.rmtree(folder, ignore_errors=True)
        os.remove('test.txt')

    def test_properites(self):
        permission = list(self.test_exam.get_permissions())[0]
        self.assertIsNone(permission.permission_allowed)


class DeleteFileTest(TestCase):
    fixtures = ['test/course_instance.yaml']

    def setUp(self):
        self.test_exam = make_test_exam(10000)
        self.folder = self.test_exam.unique_id[0:2]

    def tearDown(self):
        folder = os.path.join(
            settings.MEDIA_ROOT, Exam.EXAM_FILES_LOCATION, self.folder)
        shutil.rmtree(folder, ignore_errors=True)
        os.remove('test.txt')

    def test_delete_exam_with_file(self):
        file_name = self.test_exam.get_absolute_pathname()
        self.assertTrue(os.path.exists(file_name))
        self.test_exam.delete()
        self.assertFalse(os.path.exists(file_name))

    def test_delete_exam_without_file(self):
        self.test_exam.exam_file.delete()
        file_name = self.test_exam.get_absolute_pathname()
        self.test_exam.delete()
        self.assertFalse(os.path.exists(file_name))


class ExamListTest(TestCase):
    fixtures = ['test/course_instance.yaml']

    def setUp(self):
        self.test_exam1 = make_test_exam(10000)
        self.test_exam2 = make_test_exam(20000)
        self.test_exam3 = make_test_exam(30000)
        self.folder1 = self.test_exam1.unique_id[0:2]
        self.folder2 = self.test_exam2.unique_id[0:2]
        self.folder3 = self.test_exam3.unique_id[0:2]

    def tearDown(self):
        folder1 = os.path.join(
            settings.MEDIA_ROOT, Exam.EXAM_FILES_LOCATION, self.folder1)
        folder2 = os.path.join(
            settings.MEDIA_ROOT, Exam.EXAM_FILES_LOCATION, self.folder2)
        folder3 = os.path.join(
            settings.MEDIA_ROOT, Exam.EXAM_FILES_LOCATION, self.folder3)
        shutil.rmtree(folder1, ignore_errors=True)
        shutil.rmtree(folder2, ignore_errors=True)
        shutil.rmtree(folder3, ignore_errors=True)
        os.remove('test.txt')

    def test_response(self):
        resp = self.client.get('/courses/Test/100/')
        # A successful HTTP GET request has status code 200
        self.assertEqual(resp.status_code, 200)

    def test_multiple_blacklists_and_exams(self):
        """Permission 1 affects only Exam 1.
        Permission 2 affects Exam 1 and Exam 2.
        Permission 3 affects Exam 2 and Exam 3.
        """
        # pylint: disable=W0612,R0915
        resp = self.client.get('/courses/Test/100/')
        permission1 = list(self.test_exam1.get_permissions())[0]
        permission2 = list(self.test_exam2.get_permissions())[0]
        permission3 = list(self.test_exam3.get_permissions())[0]
        # All exams with 0 blacklists
        self.assertEqual(resp.context['exams'].count(), 3)
        # Exam 1 with 1 blacklist, Exam 2 with 0, Exam 3 with 0
        permission1.permission_allowed = False
        permission1.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertTrue(self.test_exam1.blacklisted)
        self.assertFalse(self.test_exam2.blacklisted)
        self.assertFalse(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 2)
        # Exam 1 with 2 blacklists, Exam 2 with 1, Exam 3 with 0
        permission2.permission_allowed = False
        permission2.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertTrue(self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam2.blacklisted)
        self.assertFalse(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 1)
        # Exam 1 with 1 blacklists, Exam 2 with 0, Exam 3 with 0
        permission2.permission_allowed = True
        permission2.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertTrue(self.test_exam1.blacklisted)
        self.assertFalse(self.test_exam2.blacklisted)
        self.assertFalse(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 2)
        # Exam 1 with 1 blacklists, Exam 2 with 1, Exam 3 with 1
        permission3.permission_allowed = False
        permission3.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertTrue(self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam2.blacklisted)
        self.assertTrue(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 0)
        # Exam 1 with 2 blacklists, Exam 2 with 2, Exam 3 with 1
        permission2.permission_allowed = False
        permission2.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertTrue(self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam2.blacklisted)
        self.assertTrue(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 0)
        # Exam 1 with 2 blacklists, Exam 2 with 1, Exam 3 with 0
        permission3.permission_allowed = True
        permission3.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertTrue(self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam2.blacklisted)
        self.assertFalse(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 1)
        # Exam 1 with 1 blacklist, Exam 2 with 0, Exam 3 with 0
        permission2.permission_allowed = True
        permission2.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertTrue(self.test_exam1.blacklisted)
        self.assertFalse(self.test_exam2.blacklisted)
        self.assertFalse(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 2)
        # Exam 1 with 0 blacklists, Exam 2 with 0, Exam 3 with 0
        permission1.permission_allowed = True
        permission1.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertFalse(self.test_exam1.blacklisted)
        self.assertFalse(self.test_exam2.blacklisted)
        self.assertFalse(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 3)
        # Exam 1 with 0 blacklist, Exam 2 with 1, Exam 3 with 1
        permission3.permission_allowed = False
        permission3.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertFalse(self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam2.blacklisted)
        self.assertTrue(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 1)
        # Exam 1 with 1 blacklist, Exam 2 with 2, Exam 3 with 1
        permission2.permission_allowed = False
        permission2.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertTrue(self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam2.blacklisted)
        self.assertTrue(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 0)
        # Exam 1 with 0 blacklists, Exam 2 with 1, Exam 3 with 1
        permission2.permission_allowed = True
        permission2.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertFalse(self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam2.blacklisted)
        self.assertTrue(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 1)
        # Exam 1 with 0 blacklists, Exam 2 with 0, Exam 3 with 0
        permission3.permission_allowed = True
        permission3.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam2 = Exam.objects.get(pk=self.test_exam2.pk)
        self.test_exam3 = Exam.objects.get(pk=self.test_exam3.pk)
        self.assertFalse(self.test_exam1.blacklisted)
        self.assertFalse(self.test_exam2.blacklisted)
        self.assertFalse(self.test_exam3.blacklisted)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 3)

    def test_flags_verified_and_blacklist(self):
        """Tests all 8 combinations of flags, blacklisted, and verified."""
        # pylint: disable=W0612
        self.assertTrue(self.test_exam1.flags <= ExamFlag.LIMIT)
        self.assertTrue(not self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam1.verified)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 3)
        # Under flag limit, not blacklisted, verified
        exam_flag_list = []
        for i in range(0, ExamFlag.LIMIT):
            exam_flag = ExamFlag(exam=self.test_exam1)
            exam_flag.save()
            exam_flag_list.append(exam_flag)
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.assertTrue(self.test_exam1.flags <= ExamFlag.LIMIT)
        self.assertTrue(not self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam1.verified)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 3)
        # Over flag limit, not blacklisted, verified
        last_exam_flag = ExamFlag(exam=self.test_exam1)
        last_exam_flag.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.assertFalse(self.test_exam1.flags <= ExamFlag.LIMIT)
        self.assertTrue(not self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam1.verified)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 2)
        # Under flag limit, blacklisted, verified
        exam_flag_list[0].resolved = True
        exam_flag_list[0].save()
        permission1 = list(self.test_exam1.get_permissions())[0]
        permission1.permission_allowed = False
        permission1.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.assertTrue(self.test_exam1.flags <= ExamFlag.LIMIT)
        self.assertFalse(not self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam1.verified)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 2)
        # Under flag limit, not blacklisted, not verified
        permission1.permission_allowed = True
        permission1.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam1.verified = False
        self.test_exam1.save()
        self.assertTrue(self.test_exam1.flags <= ExamFlag.LIMIT)
        self.assertTrue(not self.test_exam1.blacklisted)
        self.assertFalse(self.test_exam1.verified)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 2)
        # Over flag limit, not blacklisted, not verified
        exam_flag_list[0].resolved = False
        exam_flag_list[0].save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.assertFalse(self.test_exam1.flags <= ExamFlag.LIMIT)
        self.assertTrue(not self.test_exam1.blacklisted)
        self.assertFalse(self.test_exam1.verified)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 2)
        # Over flag limit, blacklisted, verified
        self.test_exam1.verified = True
        self.test_exam1.save()
        permission1.permission_allowed = False
        permission1.save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.assertFalse(self.test_exam1.flags <= ExamFlag.LIMIT)
        self.assertFalse(not self.test_exam1.blacklisted)
        self.assertTrue(self.test_exam1.verified)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 2)
        # Under flag limit, blacklisted, not verified
        exam_flag_list[0].resolved = True
        exam_flag_list[0].save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.test_exam1.verified = False
        self.test_exam1.save()
        self.assertTrue(self.test_exam1.flags <= ExamFlag.LIMIT)
        self.assertFalse(not self.test_exam1.blacklisted)
        self.assertFalse(self.test_exam1.verified)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 2)
        # Over flag limit, blacklisted, not verified
        exam_flag_list[0].resolved = False
        exam_flag_list[0].save()
        self.test_exam1 = Exam.objects.get(pk=self.test_exam1.pk)
        self.assertFalse(self.test_exam1.flags <= ExamFlag.LIMIT)
        self.assertFalse(not self.test_exam1.blacklisted)
        self.assertFalse(self.test_exam1.verified)
        resp = self.client.get('/courses/Test/100/')
        self.assertEqual(resp.context['exams'].count(), 2)
