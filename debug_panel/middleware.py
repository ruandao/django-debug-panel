"""
Debug Panel middleware
"""
import threading
import time

try:
    from django.urls import reverse, resolve, Resolver404
except ImportError: # django < 2.0
    from django.core.urlresolvers import reverse, resolve, Resolver404
from django.conf import settings
from debug_panel.cache import cache
import debug_toolbar.middleware

from django.utils.lru_cache import lru_cache
from debug_toolbar import settings as dt_settings
from django.utils import six
from django.utils.module_loading import import_string
from debug_toolbar.toolbar import DebugToolbar

# the urls patterns that concern only the debug_panel application
import debug_panel.urls

def show_toolbar(request):
    """
    Default function to determine whether to show the toolbar on a given page.
    """
    if request.META.get('REMOTE_ADDR', None) not in settings.INTERNAL_IPS:
        return False

    return bool(settings.DEBUG)


debug_toolbar.middleware.show_toolbar = show_toolbar


@lru_cache()
def get_show_toolbar():
    # If SHOW_TOOLBAR_CALLBACK is a string, which is the recommended
    # setup, resolve it to the corresponding callable.
    func_or_path = dt_settings.get_config()["SHOW_TOOLBAR_CALLBACK"]
    if isinstance(func_or_path, six.string_types):
        return import_string(func_or_path)
    else:
        return func_or_path

class SupportAjaxDebugToolbarMiddleware(debug_toolbar.middleware.DebugToolbarMiddleware):

    def process_request(self, request):
        # Decide whether the toolbar is active for this request.
        show_toolbar = get_show_toolbar()
        if not show_toolbar(request):
            return

        toolbar = DebugToolbar(request)
        self.__class__.debug_toolbars[threading.current_thread().ident] = toolbar

        # Activate instrumentation ie. monkey-patch.
        for panel in toolbar.enabled_panels:
            panel.enable_instrumentation()

        # Run process_request methods of panels like Django middleware.
        response = None
        for panel in toolbar.enabled_panels:
            response = panel.process_request(request)
            if response:
                break
        return response

class DebugPanelMiddleware(SupportAjaxDebugToolbarMiddleware):
    """
    Middleware to set up Debug Panel on incoming request and render toolbar
    on outgoing response.
    """

    def process_request(self, request):
        """
        Try to match the request with an URL from debug_panel application.

        If it matches, that means we are serving a view from debug_panel,
        and we can skip the debug_toolbar middleware.

        Otherwise we fallback to the default debug_toolbar middleware.
        """

        try:
            res = resolve(request.path, urlconf=debug_panel.urls)
        except Resolver404:
            return super(DebugPanelMiddleware, self).process_request(request)

        return res.func(request, *res.args, **res.kwargs)


    def process_response(self, request, response):
        """
        Store the DebugToolbarMiddleware rendered toolbar into a cache store.

        The data stored in the cache are then reachable from an URL that is appened
        to the HTTP response header under the 'X-debug-data-url' key.
        """
        toolbar = self.__class__.debug_toolbars.get(threading.current_thread().ident, None)

        response = super(DebugPanelMiddleware, self).process_response(request, response)

        if toolbar:
            # for django-debug-toolbar >= 1.4
            for panel in reversed(toolbar.enabled_panels):
                if hasattr(panel, 'generate_stats'):
                    panel.generate_stats(request, response)

            cache_key = "%f" % time.time()
            cache.set(cache_key, toolbar.render_toolbar())

            response['X-debug-data-url'] = request.build_absolute_uri(
                reverse('debug_data', urlconf=debug_panel.urls, kwargs={'cache_key': cache_key}))

        return response
