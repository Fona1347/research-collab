from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'skills' / 'research-lookup-enhanced' / 'scripts'))
from manuscript_packet import build_manuscript_packet
from rle.providers import OpenAlexProvider, CrossrefProvider, SemanticScholarProvider, EuropePmcProvider, SearchFilters
from rle.query_plan import build_query_plan
from rle.source_router import SourceRouter


class SearchBatchTests(unittest.TestCase):
    def make_provider(self, cls, payload):
        client = Mock()
        client.get_json.return_value = (payload, None)
        provider = cls(cache_dir=tempfile.gettempdir(), client=client)
        if hasattr(provider, 'api_key'):
            provider.api_key = 'fixture-only'
        return provider

    def test_oa_optional_null_preserves_location(self):
        row = {'id': 'https://openalex.org/W1', 'title': 'Paper', 'authorships': [{'author': None}],
               'best_oa_location': {'source': None, 'pdf_url': 'https://example.org/paper.pdf'}}
        record = OpenAlexProvider.normalize(row)
        self.assertEqual(record.fulltext_locations[0].url, 'https://example.org/paper.pdf')
        self.assertEqual(record.fulltext_locations[0].host_type, '')

    def test_malformed_record_isolated_and_search_list_compatible(self):
        provider = self.make_provider(OpenAlexProvider, {'results': [{'id': 'https://openalex.org/W1', 'title': 'Good'}, None,
            {'id': 'https://openalex.org/W2', 'title': 'Bad', 'topics': ['not-an-object']}], 'meta': {'count': 20}})
        batch = provider.search_batch('topic')
        self.assertEqual(len(batch.records), 1)
        self.assertEqual(batch.diagnostics['received_count'], 3)
        self.assertEqual(batch.diagnostics['normalized_count'], 1)
        self.assertEqual(batch.diagnostics['discarded_count'], 2)
        self.assertTrue(batch.diagnostics['has_more'])
        self.assertEqual(batch.diagnostics['stop_reason'], 'single-page-limit')
        self.assertEqual(batch.diagnostics['status'], 'partial')
        self.assertEqual(batch.diagnostics['row_errors'][1]['record_id'], 'https://openalex.org/W2')
        self.assertIsInstance(provider.search('topic'), list)

    def test_other_discovery_adapters_isolate_bad_rows(self):
        fixtures = [
            (CrossrefProvider, {'message': {'items': [{'DOI': '10.1000/good', 'title': ['Good']}, None], 'total-results': 2}}),
            (SemanticScholarProvider, {'data': [{'paperId': '1', 'title': 'Good'}, None], 'total': 2}),
            (EuropePmcProvider, {'resultList': {'result': [{'id': '1', 'title': 'Good'}, None]}, 'hitCount': 2}),
        ]
        for cls, payload in fixtures:
            with self.subTest(provider=cls.name):
                batch = self.make_provider(cls, payload).search_batch('topic')
                self.assertEqual(len(batch.records), 1)
                self.assertEqual(batch.diagnostics['discarded_count'], 1)
                self.assertFalse(batch.diagnostics['has_more'])

    def test_partial_provider_not_suppressed_and_packet_is_honest(self):
        provider = self.make_provider(OpenAlexProvider, {'results': [{'id': 'https://openalex.org/W1', 'title': 'Good'}, None], 'meta': {'count': 50}})
        plan = build_query_plan('ferroelectric temporal computing')
        ledger = []
        result = SourceRouter([provider], query_plan=plan, filters=SearchFilters(),
            max_results_per_request=10, fallback_threshold=20).run(ledger)
        self.assertNotIn('openalex', result.failed_providers)
        requests = [item for item in ledger if item.get('search_batch')]
        self.assertTrue(requests)
        self.assertTrue(all(item['status'] == 'partial' for item in requests))
        packet = build_manuscript_packet(query=plan.original_query, records=result.records, search_ledger=ledger, target_references=1)
        self.assertTrue(packet['coverage']['target_count_met'])
        self.assertEqual(packet['coverage']['retrieval_completeness']['status'], 'partial')
        self.assertEqual(packet['coverage']['relevance_assessment']['status'], 'not-assessed')

    def test_total_unavailable_not_invented(self):
        provider = self.make_provider(OpenAlexProvider, {'results': [{'id': 'W1', 'title': 'Good'}]})
        batch = provider.search_batch('topic')
        self.assertIsNone(batch.diagnostics['provider_total'])
        self.assertIsNone(batch.diagnostics['has_more'])
        self.assertEqual(batch.diagnostics['stop_reason'], 'pagination-unknown')

    def test_overflowing_optional_metrics_do_not_abort_a_batch(self):
        provider = self.make_provider(OpenAlexProvider, {'results': [
            {'id': 'W1', 'title': 'Good'},
            {'id': 'W2', 'title': 'Missing citation metric', 'cited_by_count': float('inf')},
        ], 'meta': {'count': float('inf')}})
        batch = provider.search_batch('topic')
        self.assertEqual(len(batch.records), 2)
        self.assertIsNone(batch.records[1].citation_count)
        self.assertIsNone(batch.diagnostics['provider_total'])
        self.assertIsNone(batch.diagnostics['has_more'])

    def test_row_overflow_is_isolated_when_normalization_cannot_recover(self):
        provider = self.make_provider(OpenAlexProvider, {})
        good = OpenAlexProvider.normalize({'id': 'W1', 'title': 'Good'})
        normalize = Mock(side_effect=[good, OverflowError()])
        result = provider._normalize_search_page([{'id': 'W1'}, {'id': 'W2'}], normalize)
        self.assertEqual(result, [good])
        self.assertEqual(provider._last_search_batch.diagnostics['status'], 'partial')
        self.assertEqual(provider._last_search_batch.diagnostics['row_errors'][0]['error_type'], 'OverflowError')

    def test_malformed_empty_collections_are_not_successful_zero_results(self):
        fixtures = [
            (OpenAlexProvider, {'results': {}, 'meta': {'count': 0}}),
            (CrossrefProvider, {'message': {'items': {}, 'total-results': 0}}),
            (SemanticScholarProvider, {'data': {}, 'total': 0}),
            (EuropePmcProvider, {'resultList': {'result': {}}, 'hitCount': 0}),
        ]
        for cls, payload in fixtures:
            with self.subTest(provider=cls.name):
                with self.assertRaisesRegex(ValueError, 'not a list'):
                    self.make_provider(cls, payload).search_batch('topic')

    def test_empty_row_does_not_become_a_phantom_paper(self):
        provider = self.make_provider(OpenAlexProvider, {'results': [{}, {'id': 'W1', 'title': 'Good'}]})
        batch = provider.search_batch('topic')
        self.assertEqual(len(batch.records), 1)
        self.assertEqual(batch.diagnostics['discarded_count'], 1)

    def test_crossref_uses_checked_english_and_keeps_identifier_route(self):
        provider = self.make_provider(CrossrefProvider, {'message': {'items': [], 'total-results': 0}})
        plan = build_query_plan('铁电器件用于时序计算', english_query='ferroelectric devices temporal computing')
        router = SourceRouter([provider], query_plan=plan, filters=SearchFilters(), max_results_per_request=10, fallback_threshold=1)
        self.assertEqual(router._targeted_variant('crossref').query, 'ferroelectric devices temporal computing')
        plan = build_query_plan('10.1000/example', english_query='irrelevant topic')
        router = SourceRouter([provider], query_plan=plan, filters=SearchFilters(), max_results_per_request=10, fallback_threshold=1)
        self.assertEqual(router._targeted_variant('crossref').query, '10.1000/example')

    def test_crossref_executes_faithful_supplied_queries_across_domains(self):
        questions = [
            ('铁电器件用于时序计算', 'ferroelectric devices temporal computing'),
            ('二维半导体接触电阻提取方法', 'two dimensional semiconductor contact resistance extraction'),
            ('稀疏图上的谱聚类稳定性', 'spectral clustering stability sparse graphs'),
        ]
        for original, english in questions:
            with self.subTest(original=original):
                provider = self.make_provider(CrossrefProvider, {'message': {'items': [{'title': [english], 'DOI': '10.1000/fixture'}], 'total-results': 1}})
                plan = build_query_plan(original, english_query=english)
                router = SourceRouter([provider], query_plan=plan, filters=SearchFilters(), max_results_per_request=10, fallback_threshold=1)
                router.run([])
                first = provider.client.get_json.call_args_list[0]
                self.assertEqual(first.kwargs['params']['query.bibliographic'], english)
                self.assertEqual(plan.original_query, original)


if __name__ == '__main__':
    unittest.main()
