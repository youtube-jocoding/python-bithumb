import unittest
from unittest.mock import patch, MagicMock
import json

# Adjust the import path if necessary based on your project structure
from .private_api import Bithumb
from .public_api import BithumbAPIException

class TestPrivateApiOrderCreation(unittest.TestCase):

    def setUp(self):
        self.access_key = "dummy_access_key"
        self.secret_key = "dummy_secret_key"
        self.bithumb = Bithumb(self.access_key, self.secret_key)

    @patch('requests.request')
    def test_place_order_success_201(self, mock_requests_request):
        # 1. Prepare mock response
        mock_order_response_data = {
            "uuid": "c0000000-0000-0000-0000-000000000000",
            "side": "bid",
            "ord_type": "limit",
            "price": "100000.0",
            "state": "wait", # Or whatever is appropriate for a newly created order
            "market": "KRW-BTC",
            "created_at": "2023-01-01T00:00:00.000Z",
            "volume": "0.001",
            "remaining_volume": "0.001",
            "reserved_fee": "0.0000025",
            "remaining_fee": "0.0000025",
            "paid_fee": "0.0",
            "locked": "100.025",
            "executed_volume": "0.0",
            "trades_count": 0
        }

        # 2. Configure the mock response object
        mock_response = MagicMock()
        mock_response.status_code = 201
        # Ensure .content is bytes if _handle_response checks it
        # and .json() returns the dict
        mock_response.content = json.dumps(mock_order_response_data).encode('utf-8')
        mock_response.json.return_value = mock_order_response_data

        # 3. Configure the mock requests.request to return the mock_response
        mock_requests_request.return_value = mock_response

        # 4. Call an order function (e.g., buy_limit_order)
        # Parameters for buy_limit_order: ticker, price, volume
        order_result = None # Initialize to ensure it's in scope
        try:
            order_result = self.bithumb.buy_limit_order(
                ticker="KRW-BTC",
                price=100000.0,
                volume=0.001
            )
        except BithumbAPIException as e:
            self.fail(f"BithumbAPIException was raised unexpectedly: {e}")

        # 5. Assert that the returned data matches the mock response data
        self.assertEqual(order_result, mock_order_response_data)

        # 6. Assert that requests.request was called correctly (optional but good practice)
        # This requires knowing the exact URL and how data is prepared by _request method
        # For example, check if it was a POST to /v1/orders
        args, kwargs = mock_requests_request.call_args
        self.assertEqual(args[0], "POST") # method
        self.assertTrue(args[1].endswith("/v1/orders")) # url
        # Further checks on kwargs['data'] could be added if needed
        # For example, making sure json.dumps was called on the data
        # self.assertEqual(kwargs['data'], json.dumps(expected_data_sent_to_request))

if __name__ == '__main__':
    unittest.main()
