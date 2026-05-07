"""
Validation Great Expectations sur un échantillon local des données Silver.
"""

import great_expectations as gx
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
REPORT_DIR = Path(__file__).resolve().parents[2] / "docs" / "quality_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_sample() -> pd.DataFrame:
    """Charge un échantillon des données brutes pour validation."""
    dfs = []
    for json_file in DATA_DIR.glob("**/*.json"):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data[:1000])  # 1000 lignes par fichier
        df["_source"] = json_file.name
        dfs.append(df)
    result = pd.concat(dfs, ignore_index=True)
    print(f"Echantillon chargé : {len(result):,} lignes")
    return result


def run_validation():
    """Lance la validation Great Expectations."""
    df = load_sample()

    context = gx.get_context()
    ds = context.sources.add_or_update_pandas(name="qualite_eau_local")
    asset = ds.add_dataframe_asset(name="silver_sample")
    batch_request = asset.build_batch_request(dataframe=df)

    suite = context.add_or_update_expectation_suite("silver_suite")
    validator = context.get_validator(
        batch_request=batch_request, expectation_suite=suite
    )

    # Règles
    validator.expect_column_to_exist("code_commune")
    validator.expect_column_to_exist("date_prelevement")
    validator.expect_column_to_exist("libelle_parametre")
    validator.expect_column_values_to_not_be_null("code_commune")
    validator.expect_column_values_to_not_be_null("date_prelevement")
    validator.expect_column_values_to_match_regex(
        "code_commune", r"^\d{5}$", mostly=0.99
    )
    validator.expect_column_values_to_be_in_set(
        "conclusion_conformite_prelevement",
        list(df["conclusion_conformite_prelevement"].dropna().unique()),
        mostly=0.95,
    )

    validator.save_expectation_suite()

    # Validation
    results = validator.validate()

    # Rapport
    print(f"\n{'='*50}")
    print(f"Résultat : {'✅ SUCCÈS' if results.success else '❌ ÉCHEC'}")
    print(f"{'='*50}")
    print(f"Règles OK : {results.statistics['successful_expectations']}")
    print(f"Règles KO : {results.statistics['unsuccessful_expectations']}")
    print(f"Total     : {results.statistics['evaluated_expectations']}")

    print("\nDétail :")
    for r in results.results:
        status = "✅" if r.success else "❌"
        col = r.expectation_config.kwargs.get("column", "")
        print(f"  {status} {r.expectation_config.expectation_type} {col}")

    # Sauvegarde rapport JSON
    report_path = (
        REPORT_DIR / f"rapport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "date": datetime.now().isoformat(),
                "succes": results.success,
                "nb_regles_ok": results.statistics["successful_expectations"],
                "nb_regles_ko": results.statistics["unsuccessful_expectations"],
                "nb_regles_total": results.statistics["evaluated_expectations"],
            },
            f,
            indent=2,
        )
    print(f"\n✅ Rapport sauvegardé : {report_path}")

    return results.success


if __name__ == "__main__":
    run_validation()
