import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from quark.auth.models import User


# Mixins
class IDCodeMixin(object):
    id_code = models.CharField(max_length=20, db_index=True, unique=True)


# Models
class RandomTokenManager(models.Manager):
    def generate(self, **kwargs):
        kwargs['token'] = kwargs.get('token', uuid.uuid4())
        return self.create(**kwargs)


class RandomToken(models.Model):
    """
    Generates a random string linked to an email or user. It can be used for
    account registration
    """
    email = models.EmailField(unique=True)
    expiration_date = models.DateTimeField()
    token = models.CharField(unique=True, max_length=64)
    used = models.BooleanField(default=False)

    user = models.ForeignKey(User, blank=True, null=True)

    objects = RandomTokenManager()

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def is_expired(self):
        current_date = timezone.now()
        return self.expiration_date < current_date

    def __unicode__(self):
        return "%s for %s, %s, %s" % (
            self.token,
            self.email,
            self.expiration_date,
            self.used)


class University(models.Model):
    short_name = models.CharField(max_length=8, unique=True)
    long_name = models.CharField(max_length=64)
    website = models.URLField()

    def __unicode__(self):
        return self.long_name

    class Meta:
        ordering = ('long_name',)


class Major(models.Model):
    short_name = models.CharField(max_length=8)
    long_name = models.CharField(max_length=64)
    university = models.ForeignKey(University)
    website = models.URLField()

    def __unicode__(self):
        return self.long_name

    class Meta:
        ordering = ('long_name',)
        unique_together = ('university', 'short_name')


class TermManager(models.Manager):
    def get_current_term(self):
        try:
            return self.get(current=True)
        except Term.DoesNotExist:
            return None

    def get_terms(self, include_future=False, include_summer=False,
                  reverse=False):
        terms = self.all()

        if not include_summer:
            terms = terms.exclude(term=Term.SUMMER)

        # Semester systems do not have a winter quarter.
        if getattr(settings, 'TERM_TYPE', 'quarter') == 'semester':
            terms = terms.exclude(term=Term.WINTER)

        if not include_future:
            current_term = self.get_current_term()
            if current_term:
                terms = terms.filter(id__lte=current_term.id)

        if reverse:
            return terms.order_by('-id')

        return terms

    def get_by_url_name(self, name):
        """
        The url param is generated by the get_url_name function. It takes the
        form of "fa2012".
        """
        if not isinstance(name, basestring):
            return None

        try:
            return self.get(term=name[0:2], year=name[2:])
        except Term.DoesNotExist:
            return None
        except ValueError:
            return None

    def get_by_natural_key(self, term, year):
        try:
            return self.get(term=term, year=year)
        except Term.DoesNotExist:
            return None


class Term(models.Model):
    """
    Refers to a school's quarter or semester system.
    Almost all models refer to this for the current term in the school year.
    """
    # Constants
    UNKNOWN = 'un'
    WINTER = 'wi'
    SPRING = 'sp'
    SUMMER = 'su'
    FALL = 'fa'

    TERM_CHOICES = (
        (UNKNOWN, 'Unknown'),
        (WINTER, 'Winter'),
        (SPRING, 'Spring'),
        (SUMMER, 'Summer'),
        (FALL, 'Fall'),
    )

    TERM_MAPPING = {
        UNKNOWN: 0,
        WINTER: 1,
        SPRING: 2,
        SUMMER: 3,
        FALL: 4
    }

    # pylint: disable=C0103
    id = models.IntegerField(primary_key=True)
    term = models.CharField(max_length=2, choices=TERM_CHOICES)
    year = models.PositiveSmallIntegerField()
    current = models.BooleanField()

    objects = TermManager()

    def save(self, *args, **kwargs):
        """
        We need to only have one current term. We'll do this by setting all
        other term's current bit to false, and then update our own. We can
        allow a case where there is NO current term. Infinite recursion cannot
        happen since updates only happen for objects with current=True.
        TODO(wli): Is this threadsafe? Do we need transactions?
        """
        if self.term == Term.UNKNOWN and self.year == 0:
            return

        # Make sure the term and year always map to the correct id.
        if (self.id is not None and
            (self.year != self.id // 10 or
             self.__term_as_int() != self.id % 10)):
            raise ValueError('You cannot update the year or term without '
                             'also updating the primary key value.')

        # Set the ID for a new object.
        # pylint: disable=C0103
        # pylint: disable=W0201
        self.id = self.year * 10 + self.__term_as_int()

        if self.current:
            Term.objects.filter(current=True).exclude(id=self.id).update(
                current=False)
        super(Term, self).save(*args, **kwargs)

    def verbose_name(self):
        """Returns the verbose name of this object in this form: Fall 2012."""
        # pylint: disable=E1101
        return '%s %d' % (self.get_term_display(), self.year)

    def get_url_name(self):
        """Returns the serialized version for use in URL params."""
        return self.term + str(self.year)

    def natural_key(self):
        return (self.term, self.year)

    def __unicode__(self):
        name = self.verbose_name()
        if self.current:
            name += ' (Current)'
        return name

    def __term_as_int(self):
        """Converts the term to a numeric mapping for the primary key."""
        return Term.TERM_MAPPING[self.term]

    def __lt__(self, other):
        if not isinstance(other, Term):
            other = Term(year=timezone.now().year,
                         term=Term.UNKNOWN)
        if self.year < other.year:
            return True
        elif self.year > other.year:
            return False
        else:
            return self.__term_as_int() < other.__term_as_int()

    def __le__(self, other):
        if not isinstance(other, Term):
            other = Term(year=timezone.now().year,
                         term=Term.UNKNOWN)
        return not other.__lt__(self)

    def __eq__(self, other):
        if not isinstance(other, Term):
            other = Term(year=timezone.now().year,
                         term=Term.UNKNOWN)
        return self.term == other.term and self.year == other.year

    def __ne__(self, other):
        if not isinstance(other, Term):
            other = Term(year=timezone.now().year,
                         term=Term.UNKNOWN)
        return not self.__eq__(other)

    def __gt__(self, other):
        if not isinstance(other, Term):
            other = Term(year=timezone.now().year,
                         term=Term.UNKNOWN)
        return other.__lt__(self)

    def __ge__(self, other):
        if not isinstance(other, Term):
            other = Term(year=timezone.now().year,
                         term=Term.UNKNOWN)
        return not self.__lt__(other)

    class Meta:
        ordering = ('id',)
        unique_together = ('term', 'year')


class OfficerPosition(models.Model):
    """
    Available officer position in any of the quark-supported organizations.
    An Officer object would reference an instance of OfficerPosition to link a
    user to an officer position.
    """
    # constants
    TBP_OFFICER = 0
    PIE_COORD = 1
    PIE_STAFF = 2

    OFFICER_TYPE_CHOICES = (
        (TBP_OFFICER, 'TBP Officer'),
        (PIE_COORD, 'PiE Coordinator'),
        (PIE_STAFF, 'PiE Staff'),
    )

    position_type = models.PositiveSmallIntegerField(
        choices=OFFICER_TYPE_CHOICES)
    short_name = models.CharField(max_length=16, unique=True)
    long_name = models.CharField(max_length=64, unique=True)
    rank = models.DecimalField(max_digits=5, decimal_places=2)
    mailing_list = models.CharField(max_length=16, blank=True)

    def __unicode__(self):
        return self.long_name

    def natural_key(self):
        return (self.short_name,)


class Officer(models.Model):
    user = models.ForeignKey(User)
    position = models.ForeignKey(OfficerPosition)
    term = models.ForeignKey(Term)

    is_chair = models.BooleanField(default=False)

    def __unicode__(self):
        # pylint: disable=E1101
        return '%s - %s (%s %d)' % (
            self.user.username, self.position.short_name,
            self.term.get_display_term(), self.term.year)

    def position_name(self):
        # pylint: disable=E1101
        name = self.position.long_name
        if self.is_chair:
            name += ' Chair'
        return name

    class Meta:
        unique_together = ('user', 'position', 'term')


class CollegeStudentInfo(models.Model, IDCodeMixin):
    user = models.ForeignKey(User)
    major = models.ForeignKey(Major)

    start_term = models.ForeignKey(Term, related_name='+')
    grad_term = models.ForeignKey(Term, related_name='+')

    def __unicode__(self):
        # pylint: disable=E1101
        return '%s - %s (%s - %s) id: %s' % (
            self.user.username, self.major, self.start_term, self.grad_term,
            self.id_code)
