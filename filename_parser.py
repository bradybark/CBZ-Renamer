import re


def normalize(s):
    """Normalize a filename for comparison (lowercase, strip extension, non-alphanumeric, vol/chapter)."""
    s = s.lower()
    s = re.sub(r'\.cbz$', '', s)
    s = re.sub(r'[^a-z0-9]', '', s)
    s = re.sub(r'(volume|vol|chapter)', '', s)
    return s


def sanitize_filename(name):
    """Remove characters that are illegal in Windows filenames."""
    # Replace colon with ' -' for readability (e.g. "Title: Subtitle" -> "Title - Subtitle")
    name = name.replace(': ', ' - ').replace(':', '-')
    # Strip remaining illegal chars: * ? " < > |
    name = re.sub(r'[*?"<>|]', '', name)
    return name


def parse_filename(filename):
    """Parse a CBZ filename into (series_guess, volume_number_str, type_str).

    Returns:
        series: The guessed series name (e.g. "Berserk")
        num_str: The volume/chapter number as a string (e.g. "1")
        type_str: Either "Volume" or "Chapter"
    """
    base = re.sub(r'\.cbz$', '', filename, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\(\[][^\]\)]*[\)\]]', '', base).strip()

    vol_match = re.search(r'(?:v|vol\.?|volume)\s*(\d+)', cleaned, re.IGNORECASE)
    chap_match = re.search(r'(?:c|ch\.?|chapter|#)\s*(\d+)', cleaned, re.IGNORECASE)

    if vol_match:
        num_str = vol_match.group(1)
        type_str = "Volume"
        orig_match = re.search(r'(?:v|vol\.?|volume)\s*\d+', base, re.IGNORECASE)
        series = base[:orig_match.start()] if orig_match else cleaned[:vol_match.start()]
    elif chap_match:
        num_str = chap_match.group(1)
        type_str = "Chapter"
        orig_match = re.search(r'(?:c|ch\.?|chapter|#)\s*\d+', base, re.IGNORECASE)
        series = base[:orig_match.start()] if orig_match else cleaned[:chap_match.start()]
    else:
        num_fallback = re.search(r'(\d+)', cleaned)
        if num_fallback:
            num_str = num_fallback.group(1)
            type_str = "Chapter"
            series = cleaned[:num_fallback.start()]
        else:
            num_str = "0"
            type_str = "Volume"
            series = cleaned

    series = re.sub(r'[\(\[][^\]\)]*[\)\]]', '', series)
    series = series.strip()
    series = re.sub(r'[\s_-]+$', '', series)
    series = re.sub(r'^[\s_-]+', '', series)
    series = re.sub(r'[_]+', ' ', series)
    series = re.sub(r'\s{2,}', ' ', series)
    series = series.strip(' ,.-')

    if not series:
        series = re.sub(r'\.cbz$', '', filename, flags=re.IGNORECASE)

    return series, num_str, type_str
