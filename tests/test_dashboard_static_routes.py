"""Every shipped dashboard asset must actually be served.

The dashboard serves its CSS and JS through a hand-maintained route per file
in ``backend/routes/static.py``. That means "the file is in ``dashboard/``"
and "the file is reachable over HTTP" are two independent facts, and only the
second one makes the page work.

The failure this pins: ``app-companions.js`` and ``companions.css`` were
committed, listed in ``index.html``, and 404'd. ``index.html`` loaded, every
other asset loaded, and the console showed a 404 that only surfaces as a
TypeError when a companion button is clicked. A test that imports the app and
calls it healthy would have passed the whole time -- the app *was* healthy.
Only comparing the served route list against the shipped file list catches it.

Run: python3 -m unittest discover -s tests -v
"""

import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DASHBOARD = os.path.join(REPO, "dashboard")
STATIC_ROUTES = os.path.join(DASHBOARD, "backend", "routes", "static.py")

# Not web assets: server-side Python, data files, images, and anything the
# browser does not fetch as a <link>/<script> from index.html.
ASSET_EXT = (".js", ".css")


def _shipped_assets():
    return {
        name
        for name in os.listdir(DASHBOARD)
        if name.endswith(ASSET_EXT) and os.path.isfile(os.path.join(DASHBOARD, name))
    }


def _routed_assets():
    with open(STATIC_ROUTES, encoding="utf-8") as fh:
        source = fh.read()
    return set(re.findall(r'@router\.get\("/([^"]+\.(?:js|css))"\)', source))


def _referenced_assets():
    with open(os.path.join(DASHBOARD, "index.html"), encoding="utf-8") as fh:
        html = fh.read()
    return set(
        re.findall(r'(?:src|href)="([^"]+\.(?:js|css))"', html)
    )


class TestStaticRouteCoverage(unittest.TestCase):

    def test_every_shipped_asset_has_a_route(self):
        missing = _shipped_assets() - _routed_assets()
        self.assertEqual(
            missing, set(),
            "asset(s) in dashboard/ with no route in static.py, so they 404 "
            "in the browser: %s" % sorted(missing),
        )

    def test_every_asset_index_html_references_is_served(self):
        """The direction that bit us: index.html asks for a file, HTTP 404s."""
        missing = _referenced_assets() - _routed_assets()
        self.assertEqual(
            missing, set(),
            "index.html references asset(s) with no route in static.py, so "
            "the browser 404s them: %s" % sorted(missing),
        )

    def test_routes_point_at_files_that_exist(self):
        """A route for a missing file is a 500 waiting to happen.

        ws-client.js is currently routed but absent. Its handler is written to
        degrade to a stub, so it is allowed explicitly rather than by the
        general rule -- a deliberate stub is fine, an accidental 500 is not.
        """
        allowed_stubs = {"ws-client.js"}
        dangling = {
            name
            for name in _routed_assets()
            if name not in allowed_stubs
            and not os.path.isfile(os.path.join(DASHBOARD, name))
        }
        self.assertEqual(
            dangling, set(),
            "route(s) in static.py whose file is missing: %s" % sorted(dangling),
        )

    def test_dashboard_dir_is_derived_not_hardcoded(self):
        """Routes must resolve files from config, not a literal home path.

        A hardcoded /home/<user> path here would 404 for anyone else and
        would not be caught by the coverage tests above, because the route
        exists -- only the file it points at is wrong.
        """
        with open(STATIC_ROUTES, encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn(
            "/home/", source,
            "static.py contains a hardcoded home path; use DASHBOARD_DIR",
        )
        self.assertIn("DASHBOARD_DIR", source)


if __name__ == "__main__":
    unittest.main()
