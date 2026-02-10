import re
import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error


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
    def _norm(s):
        s = s.lower().strip()
        # Remove leading "the ", "a ", "an "
        s = re.sub(r'^(the|a|an)\s+', '', s)
        # Remove special chars
        return re.sub(r'[^a-z0-9]', '', s)

    search_norm = _norm(search_term)
    result_norm = _norm(clean)

    # STRICT MATCHING: The search term must be contained in the result.
    # We do NOT allow the result to be a substring of the search term (e.g. "Solo Leveling" in "Solo Leveling Ragnarok").
    # This matches "Berserk" -> "Berserk Deluxe" (OK), but rejects "Fullmetal Alchemist: Brotherhood" -> "Fullmetal Alchemist" (Maybe OK? but usually we want strict)
    # Actually, for "Solo Leveling Ragnarok", we searched specific words. If result misses "Ragnarok", it's wrong.
    if search_norm in result_norm:
        return clean, title, subtitle, orig_sep

    return None, None, None, None


# ─── Persistent Disk Cache ───────────────────────────────────────────────────

def load_disk_cache(cache_path):
    """Load the persistent API result cache from disk.

    Returns a dict mapping search terms to (series, raw_title, subtitle, sep) tuples.
    """
    try:
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Convert lists back to tuples
            return {k: tuple(v) for k, v in raw.items()}
    except Exception as e:
        print(f"Cache load error: {e}")
    return {}


def save_disk_cache(cache, cache_path):
    """Save the API result cache to disk."""
    try:
        # Convert tuples to lists for JSON serialization
        serializable = {k: list(v) for k, v in cache.items()}
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Cache save error: {e}")


# ─── Google Books ─────────────────────────────────────────────────────────────

# Module-level cooldown: timestamp of when we can next call Google Books
_google_books_next_allowed = 0.0


_google_books_quota_exceeded = False

def reset_google_books_quota():
    """Reset the daily quota exceeded flag. Call this when starting a new scan."""
    global _google_books_quota_exceeded
    _google_books_quota_exceeded = False

def fetch_google_books_name(search_term, cache, api_key=None, status_callback=None, vol_num=None):
    """Fetch series info from Google Books API.

    Returns (series_name, raw_title, subtitle, original_separator) or (None, None, None, None).

    Args:
        search_term: The series name guess to search for
        cache: A dict used for caching results across calls
        api_key: Optional Google Books API key for higher quota (1000/day vs ~100/day)
        status_callback: Optional callable(text, color) for status display
        vol_num: Optional volume number string (e.g. "1") to refine search for unique subtitles.
                 If provided, API calls increase (1 per volume). If None, 1 call per series.
    """
    global _google_books_next_allowed, _google_books_quota_exceeded

    if _google_books_quota_exceeded:
        if status_callback:
             # Calculate roughly time until midnight PT (UTC-8)
             # Just a static message is safer than complex timezone math without pytz
             status_callback("Daily Quota Exceeded. Resets ~Midnight PT.", "#ef4444")
        return None, None, None, None

    # Cache key depends on whether we are searching for specific volume
    if vol_num:
         cache_key = f"GB::{search_term}||{vol_num}"
    else:
         cache_key = search_term

    if not search_term or not search_term.strip():
        return None, None, None, None
    if cache_key in cache:
        return cache[cache_key]

    words = search_term.strip().split()

    # Smart query strategy
    # If looking for specific volume, combine Series + Vol
    # e.g. intitle:"Berserk" intitle:"1"
    if vol_num:
        attempts = [f'intitle:"{search_term}" intitle:"{vol_num}"']
        # Fallback to just series if strict volume search fails (optional, but maybe better to fail fast?)
        # Actually, if user wants subtitle, getting just series name without subtitle is better than nothing.
        # But we must not cache series-only result as volume-specific result.
        pass 
    else:
        # Series-only search
        attempts = [f'intitle:"{search_term}"']
        if len(words) > 1:
            attempts.append(f'"{search_term}"')
            for i in range(len(words) - 1, 0, -1):
                shorter = " ".join(words[:i])
                attempts.append(f'intitle:"{shorter}"')

    for query in attempts:
        # Respect cooldown from previous 429 errors
        now = time.time()
        if now < _google_books_next_allowed:
            wait = _google_books_next_allowed - now
            msg = f"Google Books rate limit: waiting {wait:.1f}s..."
            print(msg)
            if status_callback:
                status_callback(msg, "#eab308")  # Yellow/Warning color
            time.sleep(wait)

        time.sleep(0.5)  # Base delay between requests

        # Try up to 3 times with exponential backoff on 429
        for retry in range(3):
            try:
                params = {"q": query, "maxResults": 5}
                if api_key:
                    params["key"] = api_key
                url = f"https://www.googleapis.com/books/v1/volumes?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers={'User-Agent': 'PythonRenamer/1.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                if "items" in data and len(data["items"]) > 0:
                    for item in data["items"]:
                        vol_info = item["volumeInfo"]
                        title = vol_info.get("title", "")
                        subtitle = vol_info.get("subtitle", "")
                        if not title:
                            continue
                        
                        # Check volume match if requested
                        # Google Books isn't perfect with issue numbers, so we rely on checks
                        # But typically if we searched intitle:"1", the result likely contains it.
                        
                        full_title = f"{title}: {subtitle}" if subtitle else title
                        result = _extract_series_from_title(full_title, search_term)
                        if result[0]:
                            cache[cache_key] = result
                            return result
                break  # Request succeeded (even if no match), try next query
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    backoff = 2 ** (retry + 1)  # 2s, 4s, 8s
                    if retry < 2:
                        msg = f"Google Books: 429 rate limited, retrying in {backoff}s..."
                        print(msg)
                        if status_callback:
                            status_callback(msg, "#eab308")
                        _google_books_next_allowed = time.time() + backoff
                        time.sleep(backoff)
                        continue
                    else:
                        # Retries failed, assume Quota Limit
                        _google_books_quota_exceeded = True
                        msg = "Daily Quota Exceeded. Stopping API calls."
                        print(msg)
                        if status_callback:
                            status_callback(msg, "#ef4444")
                        return None, None, None, None
                print(f"Google Books API error for '{query}': {e}")
                break
            except Exception as e:
                print(f"Google Books API error for '{query}': {e}")
                break

    cache[cache_key] = (None, None, None, None)
    return None, None, None, None


# ─── ComicVine ────────────────────────────────────────────────────────────────

def fetch_comicvine_name(search_term, cache, api_key, vol_num=None, vol_prefix="#", status_callback=None):
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
        vol_prefix: String to use before the volume number (e.g. "#", "Vol. ", "Volume ")
        status_callback: Optional callable(text, color) for error status display
    """
    cache_key = f"{search_term}||{vol_num or ''}||{vol_prefix}"
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

                        # Verify series name relevance via token matching
                        search_tokens = set(re.sub(r'[^a-z0-9\s]', '', search_term.lower()).split())
                        result_tokens = set(re.sub(r'[^a-z0-9\s]', '', series_name.lower()).split())
                        
                        common = search_tokens.intersection(result_tokens)
                        if not common:
                             continue
                        
                        if len(search_tokens) > 1 and len(common) < len(search_tokens) * 0.5:
                             continue

                        issue_number = str(item.get("issue_number") or "").strip()
                        issue_name = (item.get("name") or "").strip() or None

                        # On first pass, require issue number match
                        if match_num:
                            if not vol_num or not issue_number:
                                continue
                            try:
                                if int(issue_number) != int(vol_num):
                                    continue
                            except ValueError:
                                if issue_number != vol_num:
                                    continue

                        # Build a raw_title from ComicVine's structured data
                        raw_title = None
                        if issue_number:
                            prefix = vol_prefix
                            raw_title = f"{series_name} {prefix}{issue_number}"
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
