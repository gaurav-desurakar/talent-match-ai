import unicodedata

_PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00a0": " ",
    }
)


def normalize_for_verbatim_match(value: str) -> str:
    """Normalize presentation differences while preserving the exact word sequence."""
    normalized = unicodedata.normalize("NFKC", value).translate(_PUNCTUATION_TRANSLATION)
    return " ".join(normalized.split()).casefold()


def is_verbatim_excerpt(excerpt: str, document: str) -> bool:
    normalized_excerpt = normalize_for_verbatim_match(excerpt)
    return bool(normalized_excerpt) and normalized_excerpt in normalize_for_verbatim_match(document)
