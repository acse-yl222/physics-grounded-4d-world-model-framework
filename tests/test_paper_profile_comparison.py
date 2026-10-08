"""Guard scientific comparison against duplicate ambiguity and extrapolation."""
import unittest

from urban_flow.paper_rotor.compare_paper_profiles import errors, ordered_profile


class ProfileComparisonTests(unittest.TestCase):
    def test_linear_interpolation_with_identical_parallel_duplicates(self):
        x, values = ordered_profile([2, 0, 1, 1], [4, 0, 2, 2])
        result = errors(x, values, [[0.5, 1], [1.5, 3]])
        self.assertEqual(result['rms'], 0)
        self.assertEqual(result['points'], 2)

    def test_conflicting_duplicates_are_not_silently_averaged(self):
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            ordered_profile([0, 1, 1], [0, 2, 3])

    def test_outside_support_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'extrapolate'):
            errors([0, 1], [0, 2], [[1.1, 2]])

    def test_signed_bias_and_rms_are_distinct(self):
        result = errors([0, 1], [1, -1], [[0, 0], [1, 0]])
        self.assertEqual(result['rms'], 1)
        self.assertEqual(result['mean_signed'], 0)


if __name__ == '__main__':
    unittest.main()
