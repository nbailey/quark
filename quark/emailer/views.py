import random

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.core.mail import make_msgid
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView

# TODO(nitishp) uncomment things as functionality is added to quark
# from quark.base.decorators import officer_required
from quark.base.models import Officer
from quark.base.models import Term
from quark.emailer.forms import ContactCaptcha, ContactForm
# from quark.events.views import get_event
from quark.events.models import Event  # until get_event is added


class EmailerView(FormView):
    """EmailerView class for sending emails

    DO NOT USE THIS CLASS WITH as_view(). IT DOESN'T SET template_name
    OR EMAIL RECIPIENTS AND WILL PROBABLY NOT WORK. EXTEND IT

    See documentation on FormView:
    https://docs.djangoproject.com/en/1.5/ref/class-based-views/\
    generic-editing/#django.views.generic.edit.FormView

    Override dispatch for instance variables that require the use of
    variables from the url dispatcher (self.request, self.args
    and self.kwargs) to be calculated, or for views that require special
    permissions to view

    form_valid is called when the form is valid and the request is a POST.
    The original form_valid redirected to self.success_url, but this doesn't
    allow setting context variables in a confirmation message, since it gets
    handled by another view, so it has been overridden to render the template
    with render_to_response. It also now calls form.send_email() with kwargs
    to override form field data

    form_invalid has been overridden to simply set the success and
    result_message context variables (FormView already returns the form with
    error messages)

    get_context_data should be overridden to add any custom context variables.
    EmailerView already adds result_message and success
    """
    form_class = ContactForm
    result_messages = {True: 'Successfully sent!', False: 'Failure'}
    result_message = False
    success = False

    def form_valid(self, form, **kwargs):
        # called when valid data is posted, should return HttpResponse kwargs
        # can be to_email, cc_list, bcc_list, headers, and overrides for form
        # field data (see ContactForm). At least one of to, cc, or bcc must
        # be given or a BadHeaderError will be raised

        self.success = form.send_email(**kwargs)
        self.result_message = self.result_messages[self.success]
        # return empty form if success = False
        # pylint: disable=E1102
        new_form = self.form_class() if self.success else form
        # override default behavior of redirecting to success url in order to
        # pass context variables for successful submission
        return render_to_response(
            self.template_name,
            self.get_context_data(form=new_form),
            context_instance=RequestContext(self.request))

    def form_invalid(self, form):
        self.result_message = False
        self.success = False
        return super(EmailerView, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(EmailerView, self).get_context_data(**kwargs)
        context['result_message'] = self.result_message
        context['success'] = self.success
        return context


class EventEmailerView(EmailerView):
    template_name = 'events/contact.html'

    # to be set by dispatch using request variables
    event = None
    signedup_list = None
    cc_email = None

    # TODO(nitishp) restore when user access is sorted out
    # @method_decorator(officer_required)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.initial = {
            'name': request.user.get_full_name(),
            'email': request.user.email,
            'subject': u'[TBP] {}: Important announcement'.format(
                self.event.name),
            'message': ''}

        event_id = kwargs['event_id']
        # TODO(nitishp) restore when views are added for events
        # self.event = get_event(request, event_id)
        self.event = get_object_or_404(Event, pk=event_id)  # same as above
        self.signedup_list = self.event.eventsignup_set.order_by('name')
        self.cc_email = [self.event.committee.short_name + '@tbp.berkeley.edu']
        return super(EventEmailerView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form, **kwargs):
        bcc_list = []
        for signup in self.signedup_list:
            if signup.person:
                # check if person has an account or if they signed up with
                # their email address
                bcc_list.append(signup.person.email)
            else:
                bcc_list.append(signup.email)

        if len(bcc_list) == 0:
            # empty recipients list, most likely due to no participants
            return render_to_response(
                self.template_name,
                {'form': form,
                 'success': False,
                 'result_message': 'Nobody hears you.'},
                context_instance=RequestContext(self.request))

        ip_addr = unicode(
            self.request.META.get('HTTP_X_FORWARDED_FOR',
                                  self.request.META.get('REMOTE_ADDR',
                                                        'None provided')))
        useragent = unicode(self.request.META.get('HTTP_USER_AGENT',
                                                  'None provided'))
        headers = {'X-EC-IP-Address': ip_addr, 'X-EC-UserAgent': useragent}

        return super(EventEmailerView, self).form_valid(
            form,
            cc_list=self.cc_email,
            bcc_list=bcc_list,
            headers=headers,
            **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EventEmailerView, self).get_context_data(**kwargs)
        context['event'] = self.event
        context['signedup_list'] = self.signedup_list
        context['cc_list'] = self.cc_email
        return context


class HelpdeskEmailerView(EmailerView):
    template_name = 'helpdesk/base.html'
    form_class = ContactCaptcha
    result_messages = {True: 'Successfully sent!',
                       False: 'Your message could not be sent for an unknown '
                              'reason. Please try again later.'}

    def form_valid(self, form, **kwargs):
        email = form.cleaned_data['email']
        name = form.cleaned_data['name']

        from_email = '{} <{}>'.format(name, email)
        reply_to = from_email
        to_email = [settings.HELPDESK_ADDRESS]

        ip_addr = unicode(
            self.request.META.get('HTTP_X_FORWARDED_FOR',
                                  self.request.META.get('REMOTE_ADDR',
                                                        'None provided')))
        useragent = unicode(self.request.META.get('HTTP_USER_AGENT',
                                                  'None provided'))
        headers = {'Reply-To': reply_to,
                   'Message-Id': make_msgid(),
                   'X-Helpdesk-IP-Address': ip_addr,
                   'X-Helpdesk-UserAgent': useragent}

        # do spam checks, assignment email, cc_asker
        if form.cleaned_data['author']:
            return self.handle_spam(form, from_email, headers)
        if settings.ENABLE_HELPDESKQ:
            self.handle_assignment(form,
                                   headers=headers,
                                   message_id=headers.get('Message-Id', None))
        if settings.HELPDESK_CC_ASKER:
            self.handle_confirmation(form, from_email)

        return super(HelpdeskEmailerView, self).form_valid(
            form,
            from_email=from_email,
            to_email=to_email,
            headers=headers,
            **kwargs)

    def handle_spam(self, form, from_email, headers):
        to_email = [settings.HELPDESK_SPAM_TO]
        headers['X-Helpdesk-WasSpam'] = 'Yes'
        headers['X-Helpdesk-Author'] = form.cleaned_data['author']

        if settings.HELPDESK_SEND_SPAM_NOTICE:
            spamnotice = EmailMessage(
                subject='[Helpdesk spam] ' + form.cleaned_data['subject'],
                body=('Help! We have been spammed by \"{email}\" from '
                      '{ip_addr}!\n\n------------\n\n{message}'.format(
                          email=from_email,
                          ip_addr=headers['X-Helpdesk-IP-Address'],
                          message=form.cleaned_data['message'])),
                from_email='root@tbp.berkeley.edu',
                to=[settings.HELPDESK_NOTICE_TO],
                headers=headers)
            # server will return 500 error if spamnotice cannot be sent.
            spamnotice.send()

        if settings.HELPDESK_SEND_SPAM:
            if settings.ENABLE_HELPDESKQ:
                self.handle_assignment(
                    form,
                    headers=headers,
                    message_id=headers.get('Message-Id', None))
            return super(HelpdeskEmailerView, self).form_valid(
                form,
                from_email=from_email,
                to_email=to_email,
                headers=headers)
        else:
            return render_to_response(
                self.template_name,
                {'result_message': self.result_messages[True],  # feign success
                 'form': self.form_class(),
                 'success': True},
                context_instance=RequestContext(self.request))

    def handle_assignment(self, form, headers, message_id):
        headers['References'] = message_id
        headers['In-Reply-To'] = message_id

        # only assign to stars members
        officers = Officer.objects.filter(
            term=Term.objects.get_current_term(),
            position__short_name="stars")

        if officers:  # if officers non-empty
            # select a random officer. we have enough that double assignments
            # shouldn't happen very often.
            assignee = random.choice(officers)
            assigning_to = ['{}@tbp.berkeley.edu'.format(
                assignee.user.username)]
            assigning_body = (
                'HelpdeskQ has automatically assigned {officer} as the point '
                'person for the helpdesk question with subject \"{subject}\". '
                'Please compile a response for this question within 48 '
                'hours. This is a random assignment among STARS committee '
                'members. Other officers should continue to contribute '
                'knowledge about this question, but you are responsible for '
                'sending the final answer. The body of the question is '
                'below for reference.\n\n'.format(
                    officer=assignee.user.get_common_name(),
                    subject=form.cleaned_data['subject']))
        else:
            assigning_to = [settings.IT_ADDRESS, settings.STARS_ADDRESS]
            assigning_body = (
                'Automatic-assignment for HelpdeskQ has failed. There are '
                'no STARS officers listed for the current semester, so '
                'auto-assignment to a STARS officer could not be completed. '
                'This is most likely a problem that needs to be fixed. '
                'The Helpdesk question (the body of which is copied below) '
                'was still sent to all officers.')

        assigning_body += form.cleaned_data['message']
        assigning_message = EmailMessage(
            subject=form.cleaned_data['subject'],
            body=assigning_body,
            from_email='helpdeskq@tbp.berkeley.edu',
            to=assigning_to,
            cc=[settings.HELPDESK_ADDRESS],
            headers=headers)

        assigning_message.send(fail_silently=True)

    def handle_confirmation(self, form, from_email):
        # cc address might be an innocent bystander's if it's spam
        ccmessage = EmailMessage(
            subject='[Helpdesk] ' + form.cleaned_data['subject'],
            body=('Hi {name},\n\nYour question has been submitted.\n\nSomeone'
                  'will get back to you as soon as possible!'
                  '\n\n------------\n\n{question}'.format(
                      name=form.cleaned_data['name'],
                      question=form.cleaned_data['message'])),
            from_email='TBP Helpdesk <{}>'.format(settings.HELPDESK_ADDRESS),
            to=[from_email],)
        # sending is nonessential due to confirmation page
        ccmessage.send(fail_silently=True)