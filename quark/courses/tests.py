from django.test import TestCase

from quark.auth.models import User
from quark.base.models import Term
from quark.courses.models import Course
from quark.courses.models import CourseInstance
from quark.courses.models import Department
from quark.courses.models import Instructor
from quark.course_surveys.models import Survey
from quark.exam_files.models import Exam


def make_test_department():
    test_department = Department(
        long_name='Test Department 1',
        short_name='Tst Dep 1',
        abbreviation='TEST DEPT 1')
    test_department.save()
    return test_department


def make_test_db(testcase):
    testcase.dept_cs = Department(
        long_name='Computer Science',
        short_name='CS',
        abbreviation='COMPSCI')
    testcase.dept_cs.save()
    testcase.dept_ee = Department(
        long_name='Electrical Engineering',
        short_name='EE',
        abbreviation='EL ENG')
    testcase.dept_ee.save()
    testcase.course_cs_1 = Course(department=testcase.dept_cs, number='1')
    testcase.course_cs_1.save()
    testcase.course_ee_1 = Course(department=testcase.dept_ee, number='1')
    testcase.course_ee_1.save()
    testcase.instructor_cs = Instructor(first_name='Tau', last_name='Bate',
                                        department=testcase.dept_cs)
    testcase.instructor_cs.save()
    testcase.instructor_ee = Instructor(first_name='Pi', last_name='Bent',
                                        department=testcase.dept_ee)
    testcase.instructor_ee.save()
    testcase.term = Term(term='sp', year=2013, current=True)
    testcase.term.save()
    testcase.courseInstance_cs_1 = CourseInstance(
        term=testcase.term,
        course=testcase.course_cs_1)
    testcase.courseInstance_cs_1.save()
    testcase.courseInstance_cs_1.instructors.add(testcase.instructor_cs)
    testcase.courseInstance_cs_1.save()
    testcase.courseInstance_ee_1 = CourseInstance(
        term=testcase.term,
        course=testcase.course_ee_1)
    testcase.courseInstance_ee_1.save()
    testcase.courseInstance_ee_1.instructors.add(testcase.instructor_ee)
    testcase.courseInstance_ee_1.save()
    testcase.user = User(
        username='tbpUser',
        email='tbp.berkeley.edu',
        first_name='tbp',
        last_name='user')
    testcase.user.save()
    testcase.survey_cs_1 = Survey(
        course=testcase.course_cs_1,
        term=testcase.term,
        instructor=testcase.instructor_cs,
        prof_rating=5,
        course_rating=5,
        time_commitment=5,
        comments='Test comments',
        submitter=testcase.user,
        published=True)
    testcase.survey_cs_1.save()
    testcase.exam_ee_1 = Exam(
        course_instance=testcase.courseInstance_ee_1,
        submitter=testcase.user,
        exam='final',
        exam_type='exam',
        unique_id='abcdefg',
        file_ext='.pdf',
        approved=True)
    testcase.exam_ee_1.save()
    return


class DepartmentTest(TestCase):
    def test_save(self):
        test_department = Department(
            long_name='Test Department 2',
            short_name='Tst Dep 2',
            abbreviation='test dept 2')
        self.assertFalse(test_department.slug)
        test_department.save()
        self.assertEquals(test_department.abbreviation, 'TEST DEPT 2')
        self.assertEquals(test_department.slug, 'tst-dep-2')
        test_department.short_name = 'Tst Dep 2 New'
        self.assertEquals(test_department.slug, 'tst-dep-2')
        test_department.save()
        self.assertEquals(test_department.slug, 'tst-dep-2-new')
        test_department.full_clean()


class CourseTest(TestCase):
    def setUp(self):
        self.test_department = make_test_department()
        self.test_department_2 = Department(
            long_name='Test Department 2',
            short_name='Tst Dep 2',
            abbreviation='TEST DEPT 2')
        self.test_department_2.save()
        self.test_course_1 = Course(
            department=self.test_department,
            number='61a',
            title='TestDept1 61a')
        self.test_course_1.save()
        self.test_course_2 = Course(
            department=self.test_department,
            number='h61a',
            title='Honors TestDept1 61a')
        self.test_course_2.save()
        self.test_course_3 = Course(
            department=self.test_department,
            number='61b',
            title='TestDept1 61b')
        self.test_course_3.save()
        self.test_course_4 = Course(
            department=self.test_department,
            number='70',
            title='TestDept1 70')
        self.test_course_4.save()
        self.test_course_5 = Course(
            department=self.test_department_2,
            number='C30',
            title='TestDept2 C30')
        self.test_course_5.save()
        self.test_course_6 = Course(
            department=self.test_department_2,
            number='70',
            title='TestDept2 70')
        self.test_course_6.save()
        self.test_course_7 = Course(
            department=self.test_department_2,
            number='130AC',
            title='TestDept2 130AC')
        self.test_course_7.save()
        self.test_course_8 = Course(
            department=self.test_department_2,
            number='C130AC',
            title='TestDept2 C130AC')
        self.test_course_8.save()
        self.test_course_9 = Course(
            department=self.test_department_2,
            number='H130AC',
            title='TestDept2 Honors 130AC')
        self.test_course_9.save()

    def tearDown(self):
        self.test_department.full_clean()

    def test_save(self):
        self.assertEquals(self.test_course_2.number, 'H61A')

    def test_abbreviation(self):
        self.assertEquals(self.test_course_2.abbreviation(), 'Tst Dep 1 H61A')

    def test_lessthan(self):
        self.assertFalse(self.test_course_1 < self.test_course_1)
        self.assertTrue(self.test_course_1 < self.test_course_2)
        self.assertTrue(self.test_course_1 < self.test_course_3)
        self.assertTrue(self.test_course_1 < self.test_course_4)
        self.assertTrue(self.test_course_1 < self.test_course_5)
        self.assertTrue(self.test_course_1 < self.test_course_6)
        self.assertTrue(self.test_course_2 < self.test_course_3)
        self.assertTrue(self.test_course_2 < self.test_course_4)
        self.assertTrue(self.test_course_4 < self.test_course_5)
        self.assertTrue(self.test_course_4 < self.test_course_6)
        self.assertTrue(self.test_course_4 < self.test_course_7)
        self.assertTrue(self.test_course_4 < self.test_course_8)
        self.assertTrue(self.test_course_7 < self.test_course_8)
        self.assertTrue(self.test_course_7 < self.test_course_9)
        self.assertTrue(self.test_course_8 < self.test_course_9)
        self.assertFalse(self.test_course_1 < self.test_department)

    def test_equals(self):
        self.assertTrue(self.test_course_1 == self.test_course_1)
        self.assertFalse(self.test_course_4 == self.test_course_6)
        self.assertFalse(self.test_course_7 == self.test_course_8)
        self.assertFalse(self.test_course_8 == self.test_course_9)
        self.assertFalse(self.test_course_1 == self.test_department)

    def test_other_comparison_methods(self):
        self.assertTrue(self.test_course_2 <= self.test_course_2)
        self.assertTrue(self.test_course_2 <= self.test_course_3)
        self.assertTrue(self.test_course_2 != self.test_course_3)
        self.assertTrue(self.test_course_4 > self.test_course_1)
        self.assertTrue(self.test_course_4 >= self.test_course_4)
        self.assertTrue(self.test_course_4 >= self.test_course_3)
        self.assertFalse(self.test_course_1 <= self.test_department)
        self.assertFalse(self.test_course_1 > self.test_department)
        self.assertFalse(self.test_course_1 >= self.test_department)
        self.assertTrue(self.test_course_1 != self.test_department)

    def test_sort(self):
        sorted_list = [self.test_course_1, self.test_course_2,
                       self.test_course_3, self.test_course_4,
                       self.test_course_5, self.test_course_6,
                       self.test_course_7, self.test_course_8,
                       self.test_course_9]
        test_list = [self.test_course_1, self.test_course_3,
                     self.test_course_5, self.test_course_7,
                     self.test_course_9, self.test_course_4,
                     self.test_course_6, self.test_course_8,
                     self.test_course_2]
        self.assertNotEqual(test_list, sorted_list)
        test_list.sort()
        # Correct ordering:
        # TD1 61A, TD1 H61A, TD1 61B, TD1 70, TD2 C30,
        # TD2 70, TD2 130AC, TD2 C130AC, TD2 H130AC
        self.assertEquals(test_list, sorted_list)


class InstructorTest(TestCase):
    def setUp(self):
        self.test_department = make_test_department()
        self.test_instructor = Instructor(
            first_name='Tau',
            last_name='Betapi',
            department=self.test_department)
        self.test_instructor.save()

    def tearDown(self):
        self.test_department.full_clean()

    def test_full_name(self):
        self.assertEquals(self.test_instructor.full_name(), 'Tau Betapi')


class DepartmentListViewTest(TestCase):
    def setUp(self):
        make_test_db(self)

    def test_response(self):
        resp = self.client.get('/courses/')
        # A successful HTTP GET request has status code 200
        self.assertEqual(resp.status_code, 200)

    def test_dept_filter(self):
        resp = self.client.get('/courses/')
        self.assertEqual(resp.context['department_list'].count(), 2)
        self.exam_ee_1.approved = False
        self.exam_ee_1.save()
        self.survey_cs_1.published = False
        self.survey_cs_1.save()
        resp = self.client.get('/courses/')
        # Filters out departments that don't have exams/surveys
        self.assertEqual(resp.context['department_list'].count(), 0)


class CourseListViewTest(TestCase):
    def setUp(self):
        make_test_db(self)

    def test_response(self):
        resp = self.client.get('/courses/cs/')
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get('/courses/bad-dept/')
        self.assertEqual(resp.status_code, 404)

    def test_course_filter(self):
        resp = self.client.get('/courses/cs/')
        self.assertEqual(resp.context['course_list'].count(), 1)
        self.survey_cs_1.published = False
        self.survey_cs_1.save()
        # Filters out courses that don't have exams/surveys
        self.assertEqual(resp.context['course_list'].count(), 0)
        resp = self.client.get('/courses/ee/')
        self.assertEqual(resp.context['course_list'].count(), 1)
        self.exam_ee_1.approved = False
        self.exam_ee_1.save()
        self.assertEqual(resp.context['course_list'].count(), 0)


class CourseDetailViewTest(TestCase):
    def setUp(self):
        make_test_db(self)

    def test_response(self):
        resp = self.client.get('/courses/cs/1/')
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get('/courses/bad-dept/1/')
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get('/courses/cs/9999/')
        self.assertEqual(resp.status_code, 404)

    def test_course_details(self):
        resp = self.client.get('/courses/cs/1/')
        self.assertEqual(resp.context['course'].pk,
                         self.course_cs_1.pk)
        self.assertEqual(resp.context['course_instances'].count(), 1)
        self.assertEqual(resp.context['exams'].count(), 0)
        self.assertEqual(resp.context['surveys'].count(), 1)
