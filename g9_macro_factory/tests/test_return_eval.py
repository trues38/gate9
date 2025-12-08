import unittest
from unittest.mock import patch
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.backtest_engine.evaluator import evaluate_strategy

class TestReturnEval(unittest.TestCase):
    @patch('g9_macro_factory.backtest_engine.evaluator.get_supabase_client')
    def test_evaluate_buy_success(self, mock_get_client):
        # Mock DB response
        mock_supabase = MagicMock()
        mock_get_client.return_value = mock_supabase
        
        # Mock prices: Entry 100, Exit 110 (+10%)
        mock_supabase.table().select().eq().gte().lte().order().execute.return_value.data = [
            {"date": "2023-01-01", "close": 100},
            {"date": "2023-01-08", "close": 110}
        ]
        
        result = evaluate_strategy("2023-01-01", "AAPL", "BUY")
        
        self.assertEqual(result['return_pct'], 10.0)
        self.assertTrue(result['is_success'])

from unittest.mock import MagicMock
if __name__ == '__main__':
    unittest.main()
