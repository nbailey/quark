from django.conf.urls import patterns
from django.conf.urls import url

from quark.project_reports.views import ProjectReportListAllView
from quark.project_reports.views import ProjectReportListView


urlpatterns = patterns(
    '',
    url(r'^$', ProjectReportListView.as_view(), name='list-current'),
    url(r'^(?P<term>\w{2}\d{4})/$', ProjectReportListView.as_view(),
        name='term'),
    url(r'^all/$', ProjectReportListAllView.as_view(), name='list-all'),
)
