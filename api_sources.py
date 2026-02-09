import re
import json
import urllib.request
import urllib.parse


def _extract_series_from_title(title, search_term):
    """Extract (series, raw_title, subtitle, orig_separator) from a book/comic title string.

    Returns:
        series: The clean series name (e.g. "Berserk")
        raw_title: The original unmodified title from the API (e.g. "Berserk Volume 1")
        subtitle: Subtitle text if present (e.g. "The Black Swordsman"), or None
        orig_sep: The separator used before the subtitle in the source (": " or " - ")
    """
    clean = re.split(r'[,:\-]?\s*(?:Vol\.?|Volume|v\.)\s*\d', title, maxsplit=1, flags=re.IGNORECASE)[0]
    clean = re.split(r'[,:\-]?\s*(?:Chapter|Ch\.?)\s*\d', clean, maxsplit=1, flags=re.IGNORECASE)[0]
    clean = re.sub(r'\s+\d+\s*$', '', clean)
    clean = clean.strip(' ,:-')
    if not clean:
        return None, None, None, None

    # Extract subtitle and original separator
    subtitle = None
    orig_sep = " - "
    sub_match = re.search(
        r'(?:Vol\.?|Volume|v\.)\s*\d+\s*([:\-\u2013\u2014])\s*(.+)',
        title, flags=re.IGNORECASE
    )
    if sub_match:
        raw_sep = sub_match.group(1)
        subtitle = sub_match.group(2).strip()
        orig_sep = ": " if raw_sep == ":" else " - "

    # Verify relevance
    search_norm = re.sub(r'[^a-z0-9]', '', search_term.lower())
    result_norm = re.sub(r'[^a-z0-9]', '', clean.lower())
    if search_norm in result_norm or result_norm in search_norm:
        return clean, title, subtitle, orig_sep

    return None, None, None, None


def fetch_google_books_name(search_term, cache):
    """Fetch series info from Google Books API.

    Returns (series_name, raw_title, subtitle, original_separator) or (None, None, None, None).

    Args:
        search_term: The series name guess to search for
        cache: A dict used for caching results across calls
    """
    if not search_term or not search_term.strip():
        return None, None, None, None
    if search_term in cache:
        return cache[search_term]

    words = search_term.strip().split()
    attempts = []
    attempts.append(f'intitle:"{search_term}"')
    attempts.append(f'"{search_term}"')
    for i in range(len(words) - 1, 0, -1):
        shorter = " ".join(words[:i])
        attempts.append(f'intitle:"{shorter}"')

    for query in attempts:
        try:
            params = {"q": query, "maxResults": 3}
            url = f"https://www.googleapis.com/books/v1/volumes?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'PythonRenamer/1.0'})
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode())
            if "items" in data and len(data["items"]) > 0:
                for item in data["items"]:
                    title = item["volumeInfo"].get("title", "")
                    if not title:
                        continue
                    result = _extract_series_from_title(title, search_term)
                    if result[0]:
                        cache[search_term] = result
                        return result
        except Exception as e:
            print(f"Google Books API error for '{query}': {e}")
            continue

    cache[search_term] = (None, None, None, None)
    return None, None, None, None


def fetch_comicvine_name(search_term, cache, api_key, vol_num=None, status_callback=None):
    """Fetch series info from ComicVine API by searching issues.

    Returns (series_name, raw_title, subtitle, original_separator) or (None, None, None, None).

    Searches for issues (not volumes) so we get:
    - volume.name  = series name (e.g. "Berserk")
    - issue_number = the issue/volume number
    - name         = issue title / subtitle (e.g. "The Black Swordsman")

    Args:
        search_term: The series name guess to search for
        cache: A dict used for caching results across calls
        api_key: ComicVine API key string
        vol_num: Optional volume/issue number string to match (e.g. "1")
        status_callback: Optional callable(text, color) for error status display
    """
    cache_key = f"{search_term}||{vol_num or ''}"
    if not search_term or not search_term.strip():
        return None, None, None, None
    if cache_key in cache:
        return cache[cache_key]

    if not api_key:
        return None, None, None, None

    words = search_term.strip().split()
    # Try full name, then progressively shorter
    queries = [search_term]
    for i in range(len(words) - 1, 0, -1):
        queries.append(" ".join(words[:i]))

    for query in queries:
        try:
            params = {
                "api_key": api_key,
                "format": "json",
                "resources": "issue",
                "query": query,
                "limit": 10,
                "field_list": "name,issue_number,volume"
            }
            url = f"https://comicvine.gamespot.com/api/search/?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={
                'User-Agent': 'CBZRenamer/1.0',
                'Accept': 'application/json'
            })
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            if data.get("error") == "OK" and data.get("results"):
                # First pass: find issue matching both series name and volume number
                # Second pass: match series name only (fallback)
                for match_num in (True, False):
                    for item in data["results"]:
                        vol_info = item.get("volume") or {}
                        series_name = (vol_info.get("name") or "").strip()
                        if not series_name:
                            continue

                        # Verify series name relevance
                        search_norm = re.sub(r'[^a-z0-9]', '', search_term.lower())
                        result_norm = re.sub(r'[^a-z0-9]', '', series_name.lower())
                        if not (search_norm in result_norm or result_norm in search_norm):
                            continue

                        issue_number = str(item.get("issue_number") or "").strip()
                        issue_name = (item.get("name") or "").strip() or None

                        # On first pass, require issue number match
                        if match_num:
                            if not vol_num or not issue_number:
                                continue
                            # Normalize numbers for comparison (strip leading zeros)
                            try:
                                if int(issue_number) != int(vol_num):
                                    continue
                            except ValueError:
                                if issue_number != vol_num:
                                    continue

                        # Build a raw_title from ComicVine's structured data
                        raw_title = None
                        if issue_number:
                            raw_title = f"{series_name} #{issue_number}"
                            if issue_name:
                                raw_title += f" - {issue_name}"

                        subtitle = issue_name
                        orig_sep = " - "

                        result = (series_name, raw_title, subtitle, orig_sep)
                        cache[cache_key] = result
                        return result

            elif data.get("error") == "Invalid API Key":
                print("ComicVine: Invalid API key")
                if status_callback:
                    status_callback("ComicVine: Invalid API key \u2014 check Settings", "#ef4444")
                cache[cache_key] = (None, None, None, None)
                return None, None, None, None
        except Exception as e:
            print(f"ComicVine API error for '{query}': {e}")
            continue

    cache[cache_key] = (None, None, None, None)
    return None, None, None, None
