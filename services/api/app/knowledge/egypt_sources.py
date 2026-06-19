from app.contracts.cases import EgyptSource


EGYPT_PESTICIDE_DATABASE_URL = "https://www1.apc.gov.eg/en/search.aspx"
EGYPT_FOOD_SAFETY_LAB_URL = "https://www.qcap-egypt.com/"


EGYPT_OFFICIAL_SOURCES = [
    EgyptSource(
        title="Plant Pathology Research Institute",
        organization="Egyptian Agricultural Research Center",
        url=(
            "https://www.arc.sci.eg/affiliate/23/"
            "%D9%85%D8%B9%D9%87%D8%AF-%D8%A8%D8%AD%D9%88%D8%AB-"
            "%D8%A3%D9%85%D8%B1%D8%A7%D8%B6-%D8%A7%D9%84%D9%86%D8%A8%D8%A7%D8%AA%D8%A7%D8%AA"
        ),
        purpose="Egyptian national plant-disease diagnosis, monitoring, and control expertise.",
        source_kind="diagnosis",
    ),
    EgyptSource(
        title="Vegetable Diseases Research Department",
        organization="Egyptian Agricultural Research Center",
        url=(
            "https://www.arc.sci.eg/affiliate/131/"
            "%D9%82%D8%B3%D9%85-%D8%A8%D8%AD%D9%88%D8%AB-%D8%A3%D9%85%D8%B1%D8%A7%D8%B6-"
            "%D8%A7%D9%84%D8%AE%D8%B6%D8%B1"
        ),
        purpose="Receives vegetable samples and performs examinations to identify disease causes.",
        source_kind="diagnosis",
    ),
    EgyptSource(
        title="Central Egyptian Pesticides Database",
        organization="Egyptian Agricultural Pesticides Committee",
        url=EGYPT_PESTICIDE_DATABASE_URL,
        purpose="Verify the current Egyptian registration by crop and pest before any pesticide use.",
        source_kind="pesticide_registration",
    ),
    EgyptSource(
        title="Pesticide Registration Rules",
        organization="Egyptian Agricultural Pesticides Committee",
        url="https://www.apc.gov.eg/EN/PesticidesRegistration.aspx",
        purpose="Official Egyptian pesticide registration and use requirements.",
        source_kind="pesticide_registration",
    ),
    EgyptSource(
        title="Central Laboratory of Residue Analysis of Pesticides and Heavy Metals in Food",
        organization="Egyptian Agricultural Research Center",
        url=EGYPT_FOOD_SAFETY_LAB_URL,
        purpose="Official Egyptian food-safety and pesticide-residue analysis route.",
        source_kind="food_safety",
    ),
]


def egypt_official_sources() -> list[EgyptSource]:
    return [source.model_copy(deep=True) for source in EGYPT_OFFICIAL_SOURCES]
