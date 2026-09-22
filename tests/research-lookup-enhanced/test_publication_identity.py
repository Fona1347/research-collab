import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "research-lookup-enhanced" / "scripts"))
from manuscript_packet import build_manuscript_packet, classify_publication
from rle.models import PaperRecord


class PublicationIdentityTests(unittest.TestCase):
    def test_peer_review_metadata_is_not_a_literature_review(self):
        record = PaperRecord(title="Decision letter for a transistor study",
                             doi="10.1000/review-report", publication_types=["peer-review"])
        self.assertEqual(classify_publication(record, record.title), "peer-review-document")
        packet = build_manuscript_packet(query="transistors", records=[record],
                                         search_ledger=[], target_references=1)
        reference = packet["references"][0]
        self.assertEqual(reference["source_publication_types"], ["peer-review"])
        self.assertEqual(reference["publication_type"], "peer-review-document")
        self.assertTrue(any("peer-review" in warning for warning in packet["warnings"]))

    def test_actual_review_keeps_existing_classification(self):
        record = PaperRecord(title="Review of ferroelectric computing", publication_types=["review"])
        self.assertEqual(classify_publication(record, record.title), "review")

    def test_peer_reviewed_text_does_not_change_article_identity(self):
        record = PaperRecord(title="Ferroelectric devices", publication_types=["journal-article"])
        self.assertNotEqual(classify_publication(record, "This study was peer-reviewed."),
                            "peer-review-document")


if __name__ == "__main__":
    unittest.main()
