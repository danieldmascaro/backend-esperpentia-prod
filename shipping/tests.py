from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from shipping.chilexpress import ChilexpressApiError
from usuarios.models import Comuna, Region


class ChilexpressStreetBatchCommandTests(TestCase):
    def setUp(self):
        self.region = Region.objects.create(nombre="Region Metropolitana")
        self.comuna_1 = Comuna.objects.create(region=self.region, nombre="Santiago")
        self.comuna_2 = Comuna.objects.create(region=self.region, nombre="Providencia")

    @patch("shipping.management.commands.test_chilexpress_streets_all_counties.search_chilexpress_streets")
    def test_command_queries_all_registered_counties(self, mocked_search):
        mocked_search.side_effect = [
            {"streets": [{"streetId": 1, "streetName": "SAN DIEGO"}]},
            {"streets": []},
        ]

        out = StringIO()
        call_command(
            "test_chilexpress_streets_all_counties",
            street_name="san",
            limit=1,
            stdout=out,
        )

        self.assertEqual(mocked_search.call_count, 2)
        first_kwargs = mocked_search.call_args_list[0].kwargs
        second_kwargs = mocked_search.call_args_list[1].kwargs

        self.assertEqual(first_kwargs["county_name"], self.comuna_2.nombre.upper())
        self.assertEqual(second_kwargs["county_name"], self.comuna_1.nombre.upper())
        self.assertEqual(first_kwargs["street_name"], "SAN")
        self.assertEqual(second_kwargs["street_name"], "SAN")

        output = out.getvalue()
        self.assertIn("Comunas probadas: 2", output)
        self.assertIn("Respuesta OK: 2", output)
        self.assertIn("OK con al menos una calle: 1", output)
        self.assertIn("Errores: 0", output)

    @patch("shipping.management.commands.test_chilexpress_streets_all_counties.search_chilexpress_streets")
    def test_command_fails_when_requested_and_errors_exist(self, mocked_search):
        mocked_search.side_effect = ChilexpressApiError("fallo forzado")

        with self.assertRaises(CommandError):
            call_command(
                "test_chilexpress_streets_all_counties",
                street_name="SAN",
                fail_on_error=True,
            )

    def test_command_validates_street_name_length(self):
        with self.assertRaises(CommandError):
            call_command("test_chilexpress_streets_all_counties", street_name="AB")
