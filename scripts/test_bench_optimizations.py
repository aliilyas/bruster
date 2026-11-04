import copy
import unittest

from bench_optimizations import summarize


class PairedSummaryTests(unittest.TestCase):
    def rows(self):
        rows = []
        for n, scale in enumerate([1, 10, 100], 1):
            for label, ratio in [('baseline', 1), ('candidate', .5)]:
                rows.append({'round': n, 'build': label, 'transport': 'mcp',
                             'timings': {'work_ms': [scale * ratio * x for x in [1, 2, 3, 100]]},
                             'correctness': {'result': 'identical'}})
        return rows[::-1]  # Arrival order must not determine pairing.

    def test_pair_ratios_use_session_medians(self):
        summary = summarize(self.rows())['mcp/work_ms']
        self.assertEqual(summary['baseline_median'], 25)
        self.assertEqual(summary['candidate_median'], 12.5)
        self.assertAlmostEqual(summary['paired_change_percent'], -50)
        for bound in summary['interval95_percent']:
            self.assertAlmostEqual(bound, -50)
        self.assertEqual(summary['baseline_p95'], 1000)

    def test_missing_pairs_and_changed_results_cannot_publish(self):
        rows = self.rows()
        with self.assertRaises(AssertionError):
            summarize(rows[1:])
        changed = copy.deepcopy(rows)
        changed[0]['correctness']['result'] = 'missing element'
        with self.assertRaises(AssertionError):
            summarize(changed)


if __name__ == '__main__':
    unittest.main()
