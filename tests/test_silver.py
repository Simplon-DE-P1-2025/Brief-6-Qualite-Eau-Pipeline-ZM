from pyspark.sql import Row
from pyspark.sql import functions as F


def test_categorisation_microbiologie(spark):
    df = spark.createDataFrame(
        [
            Row(libelle_parametre="escherichia coli"),
            Row(libelle_parametre="bacteries coliformes"),
        ]
    )
    result = df.withColumn(
        "categorie",
        F.when(
            F.col("libelle_parametre").rlike(
                r"(bact[eé]ri|escherichia|enteroco|coliform)"
            ),
            "microbiologie",
        ).otherwise("autre"),
    ).collect()
    assert all(r.categorie == "microbiologie" for r in result)


def test_categorisation_chimie(spark):
    df = spark.createDataFrame(
        [
            Row(libelle_parametre="nitrates"),
            Row(libelle_parametre="plomb total"),
        ]
    )
    result = df.withColumn(
        "categorie",
        F.when(
            F.col("libelle_parametre").rlike(r"(nitrate|nitrite|plomb)"), "chimie"
        ).otherwise("autre"),
    ).collect()
    assert all(r.categorie == "chimie" for r in result)


def test_categorisation_autre(spark):
    df = spark.createDataFrame([Row(libelle_parametre="couleur")])
    result = df.withColumn(
        "categorie",
        F.when(
            F.col("libelle_parametre").rlike(
                r"(bact[eé]ri|escherichia|enteroco|coliform)"
            ),
            "microbiologie",
        ).otherwise("autre"),
    ).collect()
    assert result[0].categorie == "autre"
