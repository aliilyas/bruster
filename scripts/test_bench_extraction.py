"""Protect the public workload's timing/order and result-validation contract."""
import copy
import json
import unittest
from unittest.mock import patch

import bench_compare as compare
import bench_extraction as extraction


class FixtureClient:
    def __init__(self):
        self.events, self.elapsed, self.page = [], 0, 'tiny'
        self.corrupt_json = False
        self.large = {'title': 'large', 'elements': [element for i in range(1000) for element in (
            {'tag': 'a', 'name': f'link {i}', 'href': f'/item/{i}', 'value': None},
            {'tag': 'input', 'name': f'input {i}', 'href': None, 'value': ''})]}

    def navigate(self, url):
        self.events.append(('navigate', url))
        self.page = 'large' if '/large' in url else 'tiny'
        return 250

    def call(self, method, params):
        assert method == 'eval'
        expression = params['expression']
        if expression not in (compare.EXTRACT, f'JSON.stringify({compare.EXTRACT})'):
            assert 'document.readyState' in expression
            return 1, {'width': 1280, 'height': 800, 'state': 'complete'}, 64
        format_ = 'object' if expression == compare.EXTRACT else 'json'
        self.elapsed += 1
        self.events.append(('extract', self.page, format_, self.elapsed))
        value = self.large if self.page == 'large' else {'title': 'bench', 'elements': [{}] * 5}
        if format_ == 'json':
            value = copy.deepcopy(value)
            if self.corrupt_json:
                value['elements'][0]['href'] = '/wrong'
            value = json.dumps(value)
        return self.elapsed, value, 128


class SharedExtractionTests(unittest.TestCase):
    @staticmethod
    def row():
        return {'timings': {}, 'correctness': {}, 'order': []}

    def test_public_navigation_sequence_and_warmups_are_kept_separate(self):
        client, row = FixtureClient(), self.row()
        with patch.object(extraction.time, 'sleep'), patch.object(compare, 'native_snapshot'):
            extraction.workload(client, 'http://fixture', 1, 4, row, lambda: None)
        self.assertEqual(len(row['timings']['tiny_extract_ms']), 10)
        for key in ('large_extract_ms', 'large_extract_json_ms', 'large_extract_pair_ms'):
            self.assertEqual(len(row['timings'][key]), 5)
        for key in ('tiny_extract_warm_ms', 'large_extract_warm_ms', 'large_extract_json_warm_ms'):
            self.assertEqual(len(row['timings'][key]), 4)
        first_warm = next(i for i, event in enumerate(client.events)
                          if event[0] == 'navigate' and '?warm=1' in event[1])
        cold = client.events[:first_warm]
        for i, event in enumerate(cold):
            if event[0] == 'navigate' and '?tool=bruster' in event[1]:
                self.assertEqual(cold[i + 1][0], 'extract')
        # All ten tiny and ten large calls precede the warmed diagnostics.
        self.assertEqual(sum(event[0] == 'extract' for event in cold), 20)
        self.assertEqual(row['timings']['tiny_extract_warm_ms'], [23, 24, 25, 26])
        cold_order = [item for item in row['order'] if item['phase'] == 'post_navigation']
        self.assertEqual([item['format'] for item in cold_order[:4]], ['json', 'object', 'object', 'json'])
        for i, total in enumerate(row['timings']['large_extract_pair_ms']):
            self.assertEqual(total, cold_order[2 * i]['ms'] + cold_order[2 * i + 1]['ms'])

    def test_both_formats_are_balanced_across_adjacent_sessions(self):
        first = []
        for round_ in (1, 2):
            client, row = FixtureClient(), self.row()
            client.page = 'large'
            for i in range(5):
                extraction.large_pair(client, round_, i, row)
            first.extend(item['format'] for item in row['order'] if item['position'] == 0)
        self.assertEqual(first.count('object'), 5)
        self.assertEqual(first.count('json'), 5)

    def test_corrupt_results_are_rejected_in_measured_and_warmup_calls(self):
        for record in (False, True):
            client = FixtureClient()
            client.page, client.corrupt_json = 'large', True
            with self.subTest(record=record), self.assertRaisesRegex(AssertionError, 'results differ'):
                extraction.large_pair(client, 1, 0, self.row(), warm=not record, record=record)


if __name__ == '__main__':
    unittest.main()
