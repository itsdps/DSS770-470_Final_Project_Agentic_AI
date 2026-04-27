import unittest
import json
import tempfile
from pathlib import Path

from main import ConfigurationError, MarketDataRepository


class TestMarketDataRepository(unittest.TestCase):
	def _base_data(self):
		return {
			"financials": {
				"2024": {
					"q3": {
						"revenue_target": 1200000,
						"sales_ledger": [
							{"invoice": "INV-001", "amount": 500000, "status": "PAID"},
							{"invoice": "INV-002", "amount": 600000, "status": "PAID"},
							{"invoice": "INV-003", "amount": 100000, "status": "PENDING"},
						],
						"total_expenses": 800000,
					}
				}
			},
			"crm_customers": [
				{"id": "C-001", "name": "John Doe", "ltv": 15000},
				{"id": "C-002", "name": "Jane Smith", "ltv": 50000},
			],
		}

	def test_normalizes_financials_year_quarter(self):
		repo = MarketDataRepository(self._base_data())

		payload = repo.get_financials("q3", "2024")
		self.assertEqual(payload["revenue"], 1100000)
		self.assertEqual(payload["revenue_target"], 1200000)
		self.assertEqual(payload["total_expenses"], 800000)
		self.assertEqual(payload["quarter"], "2024-Q3")

	def test_infers_period_from_user_input(self):
		repo = MarketDataRepository(self._base_data())

		payload = repo.get_financials(user_input="show 2024 q3 revenue")
		self.assertEqual(payload["quarter"], "2024-Q3")
		self.assertEqual(payload["revenue"], 1100000)

	def test_returns_not_found_payload_for_missing_quarter(self):
		repo = MarketDataRepository(self._base_data())

		payload = repo.get_financials("q4", "2024")
		self.assertEqual(payload["error"], "Requested period not found in financial data.")
		self.assertIn("2024-Q3", payload["available_quarters"])

	def test_fuzzy_crm_lookup(self):
		repo = MarketDataRepository(self._base_data())

		customer = repo.get_crm_data("jane")
		self.assertIsNotNone(customer)
		self.assertEqual(customer["name"], "Jane Smith")

	def test_raises_when_crm_customers_missing(self):
		bad_data = {
			"financials": {
				"2024": {
					"q3": {
						"sales_ledger": [{"amount": 1, "status": "PAID"}],
					}
				}
			}
		}

		with self.assertRaises(ConfigurationError) as ctx:
			MarketDataRepository(bad_data)

		self.assertIn("crm_customers", str(ctx.exception))

	def test_raises_on_invalid_ledger_amount_type(self):
		bad_data = self._base_data()
		bad_data["financials"]["2024"]["q3"]["sales_ledger"][0]["amount"] = "500000"

		with self.assertRaises(ConfigurationError) as ctx:
			MarketDataRepository(bad_data)

		self.assertIn("sales_ledger", str(ctx.exception))

	def test_loads_data_from_database_file(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			db_path = Path(tmpdir) / "database.json"
			db_path.write_text(json.dumps(self._base_data()), encoding="utf-8")

			repo = MarketDataRepository.from_path(db_path)
			payload = repo.get_financials("q3", "2024")

			self.assertEqual(payload["quarter"], "2024-Q3")
			self.assertEqual(payload["revenue"], 1100000)

	def test_loads_actual_project_database_file(self):
		db_path = Path(__file__).parent / "database.json"
		repo = MarketDataRepository.from_path(db_path)

		payload = repo.get_financials("q3", "2024")
		self.assertEqual(payload["quarter"], "2024-Q3")
		self.assertEqual(payload["revenue"], 1100000)
		self.assertEqual(payload["revenue_target"], 1200000)

		customer = repo.get_crm_data("john")
		self.assertIsNotNone(customer)

	def test_aggregates_year_when_only_year_is_requested(self):
		repo = MarketDataRepository.from_path(Path(__file__).parent / "database.json")

		payload = repo.get_financials(year="2024")
		self.assertEqual(payload["period"], "2024")
		self.assertEqual(payload["revenue"], 2250000)
		self.assertEqual(payload["revenue_target"], 2600000)
		self.assertEqual(payload["total_expenses"], 1750000)
		self.assertIn("2024-Q3", payload["quarters"])
		self.assertIn("2024-Q4", payload["quarters"])

	def test_aggregates_year_inferred_from_user_input(self):
		repo = MarketDataRepository.from_path(Path(__file__).parent / "database.json")

		payload = repo.get_financials(user_input="what's the total rev in 2024?")
		self.assertEqual(payload["period"], "2024")
		self.assertEqual(payload["revenue"], 2250000)


if __name__ == "__main__":
	unittest.main(verbosity=2)


