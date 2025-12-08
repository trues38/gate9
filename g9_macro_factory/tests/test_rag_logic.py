import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.backtest_engine.rag_strategy import generate_strategy

class TestRagLogic(unittest.TestCase):
    @patch('g9_macro_factory.backtest_engine.rag_strategy.client')
    def test_generate_strategy(self, mock_client):
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"ticker": "AAPL", "action": "BUY", "reason": "Good earnings", "confidence": 0.9}'
        mock_client.chat.completions.create.return_value = mock_response
        
        news = [{"published_at": "2023-01-01", "ticker": "AAPL", "title": "Test", "summary": "Test"}]
        strategies = generate_strategy(news)
        
        self.assertEqual(len(strategies), 1)
        self.assertEqual(strategies[0]['ticker'], "AAPL")
        self.assertEqual(strategies[0]['action'], "BUY")

if __name__ == '__main__':
    unittest.main()
