""" test for app action functionality """
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory

from bookwyrm import models, views
from bookwyrm.tests.validate_html import validate_html


@patch("bookwyrm.activitystreams.add_book_statuses_task.delay")
@patch("bookwyrm.activitystreams.add_status_task.delay")
@patch("bookwyrm.activitystreams.populate_stream_task.delay")
@patch("bookwyrm.suggested_users.rerank_suggestions_task.delay")
@patch("bookwyrm.models.activitypub_mixin.broadcast_task.apply_async")
class ExportViews(TestCase):
    """viewing and creating statuses"""

    @classmethod
    def setUpTestData(self):  # pylint: disable=bad-classmethod-argument
        """we need basic test data and mocks"""
        with patch("bookwyrm.suggested_users.rerank_suggestions_task.delay"), patch(
            "bookwyrm.activitystreams.populate_stream_task.delay"
        ):
            self.local_user = models.User.objects.create_user(
                "mouse@local.com",
                "mouse@mouse.com",
                "mouseword",
                local=True,
                localname="mouse",
                remote_id="https://example.com/users/mouse",
            )
        self.work = models.Work.objects.create(title="Test Work")
        self.book = models.Edition.objects.create(
            title="Test Book",
            remote_id="https://example.com/book/1",
            parent_work=self.work,
            isbn_13="9781234567890",
            bnf_id="beep",
        )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()

    def tst_export_get(self, *_):
        """request export"""
        request = self.factory.get("")
        request.user = self.local_user
        result = views.Export.as_view()(request)
        validate_html(result.render())

    def test_export_file(self, *_):
        """simple export"""
        models.ShelfBook.objects.create(
            shelf=self.local_user.shelf_set.first(),
            user=self.local_user,
            book=self.book,
        )
        request = self.factory.post("")
        request.user = self.local_user
        export = views.Export.as_view()(request)
        self.assertIsInstance(export, HttpResponse)
        self.assertEqual(export.status_code, 200)
        # pylint: disable=line-too-long
        self.assertEqual(
            export.content,
            b"title,author_text,remote_id,openlibrary_key,inventaire_id,librarything_key,goodreads_key,bnf_id,viaf,wikidata,asin,aasin,isfdb,isbn_10,isbn_13,oclc_number,rating,review_name,review_cw,review_content\r\nTest Book,,"
            + self.book.remote_id.encode("utf-8")
            + b",,,,,beep,,,,,,123456789X,9781234567890,,,,,\r\n",
        )
