from django.test import SimpleTestCase

from usuarios.geography import iter_official_regions_and_comunas, normalize_geography_name


class GeographySupplementTests(SimpleTestCase):
    def test_rm_supplement_is_included_when_source_is_missing_it(self):
        geojson = {
            "regiones": [
                {
                    "codigo": "01",
                    "nombre_largo": "Region de Tarapaca",
                    "provincias": [
                        {
                            "comunas": [
                                {"nombre": "Iquique"},
                            ]
                        }
                    ],
                }
            ]
        }

        pairs = list(iter_official_regions_and_comunas(geojson))
        normalized_pairs = {
            (normalize_geography_name(region), normalize_geography_name(comuna))
            for region, comuna in pairs
        }

        self.assertIn(
            (
                normalize_geography_name("Region Metropolitana de Santiago"),
                normalize_geography_name("Santiago"),
            ),
            normalized_pairs,
        )
        self.assertIn(
            (
                normalize_geography_name("Region Metropolitana de Santiago"),
                normalize_geography_name("Puente Alto"),
            ),
            normalized_pairs,
        )
