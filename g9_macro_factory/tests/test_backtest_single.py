import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.backtest_engine.backtest_runner import run_backtest_for_date

class TestBacktestSingle(unittest.TestCase):
    @patch('g9_macro_factory.backtest_engine.backtest_runner.retrieve_context')
    @patch('g9_macro_factory.backtest_engine.backtest_runner.generate_strategy')
    @patch('g9_macro_factory.backtest_engine.backtest_runner.evaluate_strategy')
    @patch('g9_macro_factory.backtest_engine.backtest_runner.store_success')
    def test_run_backtest_flow(self, mock_store, mock_eval, mock_gen, mock_retrieve):
        # Setup Mocks
        mock_retrieve.return_value = [{"title": "News"}]
        mock_gen.return_value = [{"ticker": "AAPL", "action": "BUY"}]
        mock_eval.return_value = {"return_pct": 5.0, "is_success": True, "entry_price": 100, "exit_price": 105}
        
        res = run_backtest_for_date("2023-01-01")
        
        self.assertIsNotNone(res)
        self.assertTrue(res['is_success'])
        mock_store.assert_called_once()

if __name__ == '__main__':
    unittest.main()
