import unittest
from babel.messages.catalog import Catalog, Message
from cjworkbench.i18n.catalogs.util import find_corresponding_message


def assert_catalogs_deeply_equal(
    catalog: Catalog, other_catalog: Catalog, msg: str = ""
):
    """Assert that the two catalogs contain the same messages, where message equality is deep.

    Ignores header message.
    """
    msg = f"{msg}: " if msg else ""
    assert_catalog_deeply_contains_catalog(
        catalog,
        other_catalog,
        msg=f"{msg}The first catalog is not included in the second",
    )
    assert_catalog_deeply_contains_catalog(
        other_catalog,
        catalog,
        msg=f"{msg}The second catalog is not included in the first",
    )


def assert_catalog_deeply_contains_catalog(
    catalog: Catalog, other_catalog: Catalog, msg: str = ""
):
    """Assert that `other_catalog` contains all the messages of `catalog`, where message equality is deep.

    Ignores header message.
    """
    tc = unittest.TestCase()
    msg = f"{msg}: " if msg else ""
    tc.assertEqual(
        catalog.locale,
        other_catalog.locale,
        msg=f"{msg}The two catalogs have different locales",
    )
    for message in catalog:
        if message.id:  # ignore header
            other_message = find_corresponding_message(other_catalog, message)
            tc.assertTrue(
                other_message, msg=f"{msg}Message {message} not found in catalog"
            )
            assert_messages_deeply_equal(
                message,
                other_message,
                msg=f"{msg}The two catalogs have different properties in a message",
            )


def assert_messages_deeply_equal(
    message: Message, other_message: Message, msg: str = ""
):
    tc = unittest.TestCase()
    msg = f"{msg}: " if msg else ""
    tc.assertEqual(
        message,
        other_message,
        msg=f"{msg}The two messages have different ID and/or context: {message} (with context {message.context}), {other_message} (with context {other_message.context})",
    )  # this compares id and context
    tc.assertEqual(
        message.string,
        other_message.string,
        msg=f"{msg}The two messages have different string: {message} has {message.string}, {other_message} has {other_message.string}",
    )
    tc.assertEqual(
        message.flags,
        other_message.flags,
        msg=f"{msg}The two messages have different flags: {message} has {message.flags}, {other_message} has {other_message.flags}",
    )
    tc.assertEqual(
        message.auto_comments,
        other_message.auto_comments,
        msg=f"{msg}The two messages have different auto_comments: {message} has {message.auto_comments}, {other_message} has {other_message.auto_comments}",
    )
    tc.assertEqual(
        message.user_comments,
        other_message.user_comments,
        msg=f"{msg}The two messages have different user_comments: {message} has user_comments {message.user_comments}, {other_message} has {other_message.user_comments}",
    )
    tc.assertEqual(
        message.locations,
        other_message.locations,
        msg=f"{msg}The two messages have different locations: {message} has {message.locations}, {other_message} has {other_message.locations}",
    )
