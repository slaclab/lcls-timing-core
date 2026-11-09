Release flow
============

A release is a tag. Pushing the tag runs the whole regression, and only when
every gate is green does the release job publish a GitHub release. This page
describes the tags the repository uses, what gates the release, what the
release job produces, how to generate release notes by hand, the conda package,
and how the documentation site is published.

Tags
----

Release tags follow ``vMAJOR.MINOR.PATCH``, for example ``v3.12.0``, then
``v3.11.1`` and ``v3.11.0`` before it. The release job accepts only a tag that
matches ``v?<digits>.<digits>.<digits>`` and stops with "Not a release version"
for any other tag. Create an annotated tag on the commit to release and push
it:

.. code-block:: bash

   git tag -a v3.13.0 -m "v3.13.0"
   git push --tags

Pull requests target ``pre-release``; merge ``pre-release`` into ``main``
before tagging. (The comment at the top of ``releaseNotes.py`` still names
``master``; the default branch is ``main``.)

What gates the release
----------------------

A push of any ref, tags included, runs ``timing_ci.yml``. The release job,
``gen_release``, runs only for a push event on a tag ref, so a pull request, a
branch push, and a manual run never publish a release. It waits for these jobs,
and a skipped or failed prerequisite stops it:

- ``Linting`` (``lint``): the text, flake8, vsg, and compliance audit checks.
- ``RTL test: <leg>`` (``test``): every leg of the matrix, ``common``,
  ``lcls1_evr``, ``lcls2_core``, and ``lcls2_evr``.
- ``Rogue Regression Tests`` (``rogue_test``).
- ``Production Guard`` (``production_guard``).
- ``Documentation`` (``docs``): the strict Sphinx build.

The manual ``Known issues`` jobs are not prerequisites. None of these jobs has
a job-level condition, because a skipped prerequisite would also skip the
release.

What the release job produces
-----------------------------

``gen_release`` is the reusable workflow ``slaclab/ruckus/.github/workflows/gen_release.yml``
at ``main``; it is not pinned, so a change to ruckus changes the release job.
It checks out the full history, runs ``git describe --tags``, clones ruckus,
and runs ``ruckus/scripts/releaseGen.py`` with the repository slug, the tag,
and the ``GH_TOKEN`` secret. That script finds the previous tag, collects the
merged pull requests between the two tags into release notes, appends a compare
link, and creates a GitHub release named ``Major Release``, ``Minor Release``,
or ``Patch Release`` followed by the tag. When a release for the tag already
exists it prints so and creates nothing. The ``version`` input that
``timing_ci.yml`` passes is required by the reusable workflow but never read.

Release notes by hand
---------------------

``releaseNotes.py`` at the repository root generates the same kind of notes
locally. Run it inside an up to date clone with the proper branch checked out.
It needs the ``PyGithub``, ``GitPython``, and ``pyperclip`` packages and prompts
for a GitHub token on standard input; type the token at the prompt and do not
put it in a command line or a file.

.. code-block:: bash

   python releaseNotes.py v3.12.0
   python releaseNotes.py v3.11.1..v3.12.0 --copy true

The first form covers the tag up to ``HEAD``; the second covers a range.
``--nosort true`` keeps the pull requests in log order instead of sorting by
size of change. The script has two reproduced defects: it crashes on a pull
request that has no description, and it derives the repository name from an
https remote incorrectly. Both are listed on the known-issues reference page.

The conda package
-----------------

``conda-recipe/`` builds a noarch Python package named ``lcls_timing_core``.
The version comes from the git tag (``GIT_DESCRIBE_TAG``) and the build number
from the commits since it. The recipe builds with ``conda-recipe/build.sh``,
which calls ``setup.py``; that file imports ``distutils``, which Python 3.12
removed, so the build needs an older Python or a setuptools shim. This is also
listed on the known-issues reference page. The documented build and upload
commands are in :repo:`conda-recipe/README.md`:

.. code-block:: bash

   conda build --debug conda-recipe --output-folder bld-dir -c tidair-packages -c tidair-tag -c conda-forge

Do not run ``setup.py`` or install the working tree to try the package: it
appends a ``__version__`` line to ``python/LclsTimingCore/__init__.py``, a
tracked file.

The documentation site
----------------------

The site is built by ``docs.yml``. It builds on every push, and it deploys only
for a push to ``main``; a tag push builds the site (and the ``docs`` job of
``timing_ci.yml`` builds it again) but never deploys it. The deploy uses the
GitHub Pages artifact actions and the repository's OIDC token, with no stored
secret.

Two one-time settings are needed before the first deploy, and both need a
repository admin:

1. In Settings, Pages, set Source to GitHub Actions. Until then the legacy
   branch-based site keeps serving.
2. In Settings, Environments, ``github-pages``, allow the ``main`` branch to
   deploy.

After that, merging a documentation change into ``main`` publishes it at
https://slaclab.github.io/lcls-timing-core/.
