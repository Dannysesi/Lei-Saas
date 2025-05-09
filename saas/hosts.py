from django_hosts import patterns, host

host_patterns = patterns('',
    host(r'www', 'public.urls', name='www'),
    host(r'(?P<tenant>[\w-]+)', 'staffs.urls', name='wildcard'),
)