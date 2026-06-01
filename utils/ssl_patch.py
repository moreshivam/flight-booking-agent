"""
SSL certificate fix for Windows Python environments.
Call apply() once at the entry point (main.py, test_agent.py).
"""
import ssl
import os
import urllib3
import requests


def apply():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    ssl._create_default_https_context = ssl._create_unverified_context
    os.environ["PYTHONHTTPSVERIFY"]  = "0"
    os.environ["CURL_CA_BUNDLE"]     = ""
    os.environ["REQUESTS_CA_BUNDLE"] = ""

    # patch requests.Session so ALL requests calls (including SerpAPI internals)
    # skip SSL verification — no need to change individual tool files
    _original = requests.Session.request
    def _patched(self, method, url, **kwargs):
        kwargs.setdefault("verify", False)
        return _original(self, method, url, **kwargs)
    requests.Session.request = _patched
