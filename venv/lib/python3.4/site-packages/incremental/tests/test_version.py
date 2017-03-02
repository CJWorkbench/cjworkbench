# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{incremental}.
"""

from __future__ import division, absolute_import

import sys
import operator

from tempfile import mkdtemp

from io import BytesIO

from incremental import getVersionString, IncomparableVersions
from incremental import Version, _inf

from twisted.python.filepath import FilePath
from twisted.trial.unittest import TestCase

VERSION_4_ENTRIES = b"""\
<?xml version="1.0" encoding="utf-8"?>
<wc-entries
   xmlns="svn:">
<entry
   committed-rev="18210"
   name=""
   committed-date="2006-09-21T04:43:09.542953Z"
   url="svn+ssh://svn.twistedmatrix.com/svn/Twisted/trunk/twisted"
   last-author="exarkun"
   kind="dir"
   uuid="bbbe8e31-12d6-0310-92fd-ac37d47ddeeb"
   repos="svn+ssh://svn.twistedmatrix.com/svn/Twisted"
   revision="18211"/>
</wc-entries>
"""

VERSION_8_ENTRIES = b"""\
8

dir
22715
svn+ssh://svn.twistedmatrix.com/svn/Twisted/trunk
"""

VERSION_9_ENTRIES = b"""\
9

dir
22715
svn+ssh://svn.twistedmatrix.com/svn/Twisted/trunk
"""

VERSION_10_ENTRIES = b"""\
10

dir
22715
svn+ssh://svn.twistedmatrix.com/svn/Twisted/trunk
"""


class VersionsTests(TestCase):

    def test_localIsShort(self):
        """
        The local version is the same as the short version.
        """
        va = Version("dummy", 1, 0, 0, release_candidate=1, dev=3)
        self.assertEqual(va.local(), va.short())

    def test_versionComparison(self):
        """
        Versions can be compared for equality and order.
        """
        va = Version("dummy", 1, 0, 0)
        vb = Version("dummy", 0, 1, 0)
        self.assertTrue(va > vb)
        self.assertTrue(vb < va)
        self.assertTrue(va >= vb)
        self.assertTrue(vb <= va)
        self.assertTrue(va != vb)
        self.assertTrue(vb == Version("dummy", 0, 1, 0))
        self.assertTrue(vb == vb)

    def test_versionComparisonCaseInsensitive(self):
        """
        Version package names are case insensitive.
        """
        va = Version("dummy", 1, 0, 0)
        vb = Version("DuMmY", 0, 1, 0)
        self.assertTrue(va > vb)
        self.assertTrue(vb < va)
        self.assertTrue(va >= vb)
        self.assertTrue(vb <= va)
        self.assertTrue(va != vb)
        self.assertTrue(vb == Version("dummy", 0, 1, 0))
        self.assertTrue(vb == vb)

    def test_comparingNEXTReleases(self):
        """
        NEXT releases are always larger than numbered releases.
        """
        va = Version("whatever", "NEXT", 0, 0)
        vb = Version("whatever", 1, 0, 0)
        self.assertTrue(va > vb)
        self.assertFalse(va < vb)
        self.assertNotEquals(vb, va)

    def test_NEXTMustBeAlone(self):
        """
        NEXT releases must always have the rest of the numbers set to 0.
        """
        with self.assertRaises(ValueError):
            Version("whatever", "NEXT", 1, 0, release_candidate=0, dev=0)

        with self.assertRaises(ValueError):
            Version("whatever", "NEXT", 0, 1, release_candidate=0, dev=0)

        with self.assertRaises(ValueError):
            Version("whatever", "NEXT", 0, 0, release_candidate=1, dev=0)

        with self.assertRaises(ValueError):
            Version("whatever", "NEXT", 0, 0, release_candidate=0, dev=1)

    def test_comparingNEXTReleasesEqual(self):
        """
        NEXT releases are equal to each other.
        """
        va = Version("whatever", "NEXT", 0, 0)
        vb = Version("whatever", "NEXT", 0, 0)
        self.assertEquals(vb, va)

    def test_comparingPrereleasesWithReleases(self):
        """
        Prereleases are always less than versions without prereleases.
        """
        va = Version("whatever", 1, 0, 0, prerelease=1)
        vb = Version("whatever", 1, 0, 0)
        self.assertTrue(va < vb)
        self.assertFalse(va > vb)
        self.assertNotEquals(vb, va)

    def test_prereleaseDeprecated(self):
        """
        Passing 'prerelease' to Version is deprecated.
        """
        Version("whatever", 1, 0, 0, prerelease=1)
        warnings = self.flushWarnings([self.test_prereleaseDeprecated])
        self.assertEqual(len(warnings), 1)
        self.assertEqual(
            warnings[0]['message'],
            ("Passing prerelease to incremental.Version was deprecated in "
             "Incremental 16.9.0. Please pass release_candidate instead."))

    def test_prereleaseAttributeDeprecated(self):
        """
        Accessing 'prerelease' on a Version is deprecated.
        """
        va = Version("whatever", 1, 0, 0, release_candidate=1)
        va.prerelease
        warnings = self.flushWarnings(
            [self.test_prereleaseAttributeDeprecated])
        self.assertEqual(len(warnings), 1)
        self.assertEqual(
            warnings[0]['message'],
            ("Accessing incremental.Version.prerelease was deprecated in "
             "Incremental 16.9.0. Use Version.release_candidate instead."))

    def test_comparingReleaseCandidatesWithReleases(self):
        """
        Release Candidates are always less than versions without release
        candidates.
        """
        va = Version("whatever", 1, 0, 0, release_candidate=1)
        vb = Version("whatever", 1, 0, 0)
        self.assertTrue(va < vb)
        self.assertFalse(va > vb)
        self.assertNotEquals(vb, va)

    def test_comparingDevReleasesWithReleases(self):
        """
        Dev releases are always less than versions without dev releases.
        """
        va = Version("whatever", 1, 0, 0, dev=1)
        vb = Version("whatever", 1, 0, 0)
        self.assertTrue(va < vb)
        self.assertFalse(va > vb)
        self.assertNotEquals(vb, va)

    def test_rcEqualspre(self):
        """
        Release Candidates are equal to prereleases.
        """
        va = Version("whatever", 1, 0, 0, release_candidate=1)
        vb = Version("whatever", 1, 0, 0, prerelease=1)
        self.assertTrue(va == vb)
        self.assertFalse(va != vb)

    def test_rcOrpreButNotBoth(self):
        """
        Release Candidate and prerelease can't both be given.
        """
        with self.assertRaises(ValueError):
            Version("whatever", 1, 0, 0,
                    prerelease=1, release_candidate=1)

    def test_comparingReleaseCandidates(self):
        """
        The value specified as the release candidate is used in version
        comparisons.
        """
        va = Version("whatever", 1, 0, 0, release_candidate=1)
        vb = Version("whatever", 1, 0, 0, release_candidate=2)
        self.assertTrue(va < vb)
        self.assertTrue(vb > va)
        self.assertTrue(va <= vb)
        self.assertTrue(vb >= va)
        self.assertTrue(va != vb)
        self.assertTrue(vb == Version("whatever", 1, 0, 0,
                                      release_candidate=2))
        self.assertTrue(va == va)

    def test_comparingDev(self):
        """
        The value specified as the dev release is used in version comparisons.
        """
        va = Version("whatever", 1, 0, 0, dev=1)
        vb = Version("whatever", 1, 0, 0, dev=2)
        self.assertTrue(va < vb)
        self.assertTrue(vb > va)
        self.assertTrue(va <= vb)
        self.assertTrue(vb >= va)
        self.assertTrue(va != vb)
        self.assertTrue(vb == Version("whatever", 1, 0, 0,
                                      dev=2))
        self.assertTrue(va == va)

    def test_comparingDevAndRC(self):
        """
        The value specified as the dev release and release candidate is used in
        version comparisons.
        """
        va = Version("whatever", 1, 0, 0, release_candidate=1, dev=1)
        vb = Version("whatever", 1, 0, 0, release_candidate=1, dev=2)
        self.assertTrue(va < vb)
        self.assertTrue(vb > va)
        self.assertTrue(va <= vb)
        self.assertTrue(vb >= va)
        self.assertTrue(va != vb)
        self.assertTrue(vb == Version("whatever", 1, 0, 0,
                                      release_candidate=1, dev=2))
        self.assertTrue(va == va)

    def test_comparingDevAndRCDifferent(self):
        """
        The value specified as the dev release and release candidate is used in
        version comparisons.
        """
        va = Version("whatever", 1, 0, 0, release_candidate=1, dev=1)
        vb = Version("whatever", 1, 0, 0, release_candidate=2, dev=1)
        self.assertTrue(va < vb)
        self.assertTrue(vb > va)
        self.assertTrue(va <= vb)
        self.assertTrue(vb >= va)
        self.assertTrue(va != vb)
        self.assertTrue(vb == Version("whatever", 1, 0, 0,
                                      release_candidate=2, dev=1))
        self.assertTrue(va == va)

    def test_infComparison(self):
        """
        L{_inf} is equal to L{_inf}.

        This is a regression test.
        """
        self.assertEqual(_inf, _inf)

    def test_disallowBuggyComparisons(self):
        """
        The package names of the Version objects need to be the same.
        """
        self.assertRaises(IncomparableVersions,
                          operator.eq,
                          Version("dummy", 1, 0, 0),
                          Version("dumym", 1, 0, 0))

    def test_notImplementedComparisons(self):
        """
        Comparing a L{Version} to some other object type results in
        C{NotImplemented}.
        """
        va = Version("dummy", 1, 0, 0)
        vb = ("dummy", 1, 0, 0)  # a tuple is not a Version object
        self.assertEqual(va.__cmp__(vb), NotImplemented)

    def test_repr(self):
        """
        Calling C{repr} on a version returns a human-readable string
        representation of the version.
        """
        self.assertEqual(repr(Version("dummy", 1, 2, 3)),
                         "Version('dummy', 1, 2, 3)")

    def test_reprWithPrerelease(self):
        """
        Calling C{repr} on a version with a prerelease returns a human-readable
        string representation of the version including the prerelease as a
        release candidate..
        """
        self.assertEqual(repr(Version("dummy", 1, 2, 3, prerelease=4)),
                         "Version('dummy', 1, 2, 3, release_candidate=4)")

    def test_reprWithReleaseCandidate(self):
        """
        Calling C{repr} on a version with a release candidate returns a
        human-readable string representation of the version including the rc.
        """
        self.assertEqual(repr(Version("dummy", 1, 2, 3, release_candidate=4)),
                         "Version('dummy', 1, 2, 3, release_candidate=4)")

    def test_devWithReleaseCandidate(self):
        """
        Calling C{repr} on a version with a dev release returns a
        human-readable string representation of the version including the dev
        release.
        """
        self.assertEqual(repr(Version("dummy", 1, 2, 3, dev=4)),
                         "Version('dummy', 1, 2, 3, dev=4)")

    def test_str(self):
        """
        Calling C{str} on a version returns a human-readable string
        representation of the version.
        """
        self.assertEqual(str(Version("dummy", 1, 2, 3)),
                         "[dummy, version 1.2.3]")

    def test_strWithPrerelease(self):
        """
        Calling C{str} on a version with a prerelease includes the prerelease
        as a release candidate.
        """
        self.assertEqual(str(Version("dummy", 1, 0, 0, prerelease=1)),
                         "[dummy, version 1.0.0rc1]")

    def test_strWithReleaseCandidate(self):
        """
        Calling C{str} on a version with a release candidate includes the
        release candidate.
        """
        self.assertEqual(str(Version("dummy", 1, 0, 0, release_candidate=1)),
                         "[dummy, version 1.0.0rc1]")

    def test_strWithDevAndReleaseCandidate(self):
        """
        Calling C{str} on a version with a release candidate and dev release
        includes the release candidate and the dev release.
        """
        self.assertEqual(str(Version("dummy", 1, 0, 0,
                                     release_candidate=1, dev=2)),
                         "[dummy, version 1.0.0rc1dev2]")

    def test_strWithDev(self):
        """
        Calling C{str} on a version with a dev release includes the dev
        release.
        """
        self.assertEqual(str(Version("dummy", 1, 0, 0, dev=1)),
                         "[dummy, version 1.0.0dev1]")

    def testShort(self):
        self.assertEqual(Version('dummy', 1, 2, 3).short(), '1.2.3')

    def test_goodSVNEntries_4(self):
        """
        Version should be able to parse an SVN format 4 entries file.
        """
        version = Version("dummy", 1, 0, 0)
        self.assertEqual(
            version._parseSVNEntries_4(BytesIO(VERSION_4_ENTRIES)), b'18211')

    def test_goodSVNEntries_8(self):
        """
        Version should be able to parse an SVN format 8 entries file.
        """
        version = Version("dummy", 1, 0, 0)
        self.assertEqual(
            version._parseSVNEntries_8(BytesIO(VERSION_8_ENTRIES)), b'22715')

    def test_goodSVNEntries_9(self):
        """
        Version should be able to parse an SVN format 9 entries file.
        """
        version = Version("dummy", 1, 0, 0)
        self.assertEqual(
            version._parseSVNEntries_9(BytesIO(VERSION_9_ENTRIES)), b'22715')

    def test_goodSVNEntriesTenPlus(self):
        """
        Version should be able to parse an SVN format 10 entries file.
        """
        version = Version("dummy", 1, 0, 0)
        self.assertEqual(
            version._parseSVNEntriesTenPlus(BytesIO(VERSION_10_ENTRIES)),
            b'22715')

    def test_getVersionString(self):
        """
        L{getVersionString} returns a string with the package name and the
        short version number.
        """
        self.assertEqual(
            'Twisted 8.0.0', getVersionString(Version('Twisted', 8, 0, 0)))

    def test_getVersionStringWithPrerelease(self):
        """
        L{getVersionString} includes the prerelease as a release candidate, if
        any.
        """
        self.assertEqual(
            getVersionString(Version("whatever", 8, 0, 0, prerelease=1)),
            "whatever 8.0.0rc1")

    def test_getVersionStringWithReleaseCandidate(self):
        """
        L{getVersionString} includes the release candidate, if any.
        """
        self.assertEqual(
            getVersionString(Version("whatever", 8, 0, 0,
                                     release_candidate=1)),
            "whatever 8.0.0rc1")

    def test_getVersionStringWithDev(self):
        """
        L{getVersionString} includes the dev release, if any.
        """
        self.assertEqual(
            getVersionString(Version("whatever", 8, 0, 0,
                                     dev=1)),
            "whatever 8.0.0dev1")

    def test_getVersionStringWithDevAndRC(self):
        """
        L{getVersionString} includes the dev release and release candidate, if
        any.
        """
        self.assertEqual(
            getVersionString(Version("whatever", 8, 0, 0,
                                     release_candidate=2, dev=1)),
            "whatever 8.0.0rc2dev1")

    def test_baseWithNEXT(self):
        """
        The C{base} method returns just "NEXT" when NEXT is the major version.
        """
        self.assertEqual(Version("foo", "NEXT", 0, 0).base(), "NEXT")

    def test_base(self):
        """
        The C{base} method returns a very simple representation of the version.
        """
        self.assertEqual(Version("foo", 1, 0, 0).base(), "1.0.0")

    def test_baseWithPrerelease(self):
        """
        The base version includes 'rcX' for versions with prereleases.
        """
        self.assertEqual(Version("foo", 1, 0, 0, prerelease=8).base(),
                         "1.0.0rc8")

    def test_baseWithDev(self):
        """
        The base version includes 'devX' for versions with dev releases.
        """
        self.assertEqual(Version("foo", 1, 0, 0, dev=8).base(),
                         "1.0.0dev8")

    def test_baseWithReleaseCandidate(self):
        """
        The base version includes 'rcX' for versions with prereleases.
        """
        self.assertEqual(Version("foo", 1, 0, 0, release_candidate=8).base(),
                         "1.0.0rc8")

    def test_baseWithDevAndRC(self):
        """
        The base version includes 'rcXdevX' for versions with dev releases and
        a release candidate.
        """
        self.assertEqual(Version("foo", 1, 0, 0,
                                 release_candidate=2, dev=8).base(),
                         "1.0.0rc2dev8")

    def test_git(self):

        gitDir = FilePath(self.mktemp())
        gitDir.makedirs()
        gitDir.child("HEAD").setContent(b"ref: refs/heads/master\n")

        heads = gitDir.child("refs").child("heads")
        heads.makedirs()
        heads.child("master").setContent(
            b"a96d61d94949c0dc097d6e1c3515792e99a724d5\n")

        version = Version("foo", 1, 0, 0)
        self.assertEqual(version._parseGitDir(gitDir.path),
                         "a96d61d94949c0dc097d6e1c3515792e99a724d5")


class FormatDiscoveryTests(TestCase):
    """
    Tests which discover the parsing method based on the imported module name.
    """
    def setUp(self):
        """
        Create a temporary directory with a package structure in it.
        """
        self.entry = FilePath(mkdtemp())
        self.addCleanup(self.entry.remove)

        self.preTestModules = sys.modules.copy()
        sys.path.append(self.entry.path)
        pkg = self.entry.child("incremental_test_package")
        pkg.makedirs()
        pkg.child("__init__.py").setContent(
            b"from incremental import Version\n"
            b"version = Version('incremental_test_package', 1, 0, 0)\n")
        self.svnEntries = pkg.child(".svn")
        self.svnEntries.makedirs()

    def tearDown(self):
        """
        Remove the imported modules and sys.path modifications.
        """
        sys.modules.clear()
        sys.modules.update(self.preTestModules)
        sys.path.remove(self.entry.path)

    def checkSVNFormat(self, formatVersion, entriesText, expectedRevision):
        """
        Check for the given revision being detected after setting the SVN
        entries text and format version of the test directory structure.
        """
        self.svnEntries.child("format").setContent(formatVersion + b"\n")
        self.svnEntries.child("entries").setContent(entriesText)
        self.assertEqual(self.getVersion()._getSVNVersion(), expectedRevision)

    def getVersion(self):
        """
        Import and retrieve the Version object from our dynamically created
        package.
        """
        import incremental_test_package
        return incremental_test_package.version

    def test_detectVersion4(self):
        """
        Verify that version 4 format file will be properly detected and parsed.
        """
        self.checkSVNFormat(b"4", VERSION_4_ENTRIES, b'18211')

    def test_detectVersion8(self):
        """
        Verify that version 8 format files will be properly detected and
        parsed.
        """
        self.checkSVNFormat(b"8", VERSION_8_ENTRIES, b'22715')

    def test_detectVersion9(self):
        """
        Verify that version 9 format files will be properly detected and
        parsed.
        """
        self.checkSVNFormat(b"9", VERSION_9_ENTRIES, b'22715')

    def test_unparseableEntries(self):
        """
        Verify that the result is C{b"Unknown"} for an apparently supported
        version for which parsing of the entries file fails.
        """
        self.checkSVNFormat(b"4", b"some unsupported stuff", b"Unknown")

    def test_detectVersion10(self):
        """
        Verify that version 10 format files will be properly detected and
        parsed.

        Differing from previous formats, the version 10 format lacks a
        I{format} file and B{only} has the version information on the first
        line of the I{entries} file.
        """
        self.svnEntries.child("entries").setContent(VERSION_10_ENTRIES)
        self.assertEqual(self.getVersion()._getSVNVersion(), b'22715')

    def test_detectUnknownVersion(self):
        """
        Verify that a new version of SVN will result in the revision 'Unknown'.
        """
        self.checkSVNFormat(b"some-random-new-version", b"ooga booga!",
                            b'Unknown')

    def test_getVersionStringWithRevision(self):
        """
        L{getVersionString} includes the discovered revision number.
        """
        self.svnEntries.child("format").setContent(b"9\n")
        self.svnEntries.child("entries").setContent(VERSION_10_ENTRIES)
        version = getVersionString(self.getVersion())
        self.assertEqual(
            "incremental_test_package 1.0.0+r22715",
            version)
        self.assertTrue(isinstance(version, type("")))
