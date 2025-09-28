# File: ingest/scripts/enrich.py
"""Post-ingest enrichment helpers.

Adds normalized address components, derived ZIP centroids, and search-friendly
strings so the front-end can filter markets without additional services.
"""
from __future__ import annotations

import re
from typing import Iterable, Tuple, Dict

import pandas as pd

STATE_MAP = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
    'district of columbia': 'DC', 'washington dc': 'DC', 'dc': 'DC',
    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM',
    'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND',
    'ohio': 'OH', 'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA',
    'rhode island': 'RI', 'south carolina': 'SC', 'south dakota': 'SD',
    'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
    'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
    'wisconsin': 'WI', 'wyoming': 'WY', 'puerto rico': 'PR'
}

ZIP_RE = re.compile(r"(\d{5})(?:-\d{4})?$")


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = str(value).lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _maybe(value: str | float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_state(token: str | None) -> str | None:
    if not token:
        return None
    cleaned = token.replace('.', '').strip().lower()
    if len(cleaned) == 2 and cleaned.isalpha():
        return cleaned.upper()
    return STATE_MAP.get(cleaned)


def _parse_address(raw: str | None) -> Tuple[str | None, str | None, str | None, str | None]:
    """Best-effort split of "street, City, ST 12345" into components."""
    text = _maybe(raw)
    if not text:
        return None, None, None, None

    cleaned = text.replace(';', ',').strip()

    zipcode = None
    zip_match = ZIP_RE.search(cleaned)
    if zip_match:
        zipcode = zip_match.group(1)
        cleaned = cleaned[:zip_match.start()].rstrip(', ')

    state = None
    if cleaned:
        lowered = cleaned.lower()
        tokens = sorted({**STATE_MAP, **{abbr.lower(): abbr for abbr in STATE_MAP.values()}}.items(), key=lambda kv: -len(kv[0]))
        for token, normalized in tokens:
            if lowered.endswith(token):
                state = normalized if len(normalized) == 2 else STATE_MAP.get(normalized, normalized)
                cleaned = cleaned[: -len(token)].rstrip(', ')
                break

    city = None
    street = None
    if cleaned and (state is not None or zipcode is not None):
        words = cleaned.split()
        if len(words) <= 2:
            return text, None, state, zipcode
        if ',' in cleaned:
            street, city = [part.strip() or None for part in cleaned.rsplit(',', 1)]
        else:
            parts = cleaned.rsplit(' ', 2)
            if len(parts) >= 2:
                city = parts[-1]
                street = ' '.join(parts[:-1]).strip() or None
            else:
                city = cleaned
                street = None

    if state is None and zipcode is None:
        return text, None, None, None

    if city is None and street is None:
        street = cleaned or text

    return street, city, state, zipcode


def _join_address(street: str | None, city: str | None, state: str | None, zipcode: str | None) -> str:
    pieces: Iterable[str] = [p for p in (street, city, state, zipcode) if p]
    return ', '.join(pieces)


def _zip_means(df: pd.DataFrame) -> pd.DataFrame:
    coords = df[['zip', 'latitude', 'longitude']].copy()
    coords['latitude'] = pd.to_numeric(coords['latitude'], errors='coerce')
    coords['longitude'] = pd.to_numeric(coords['longitude'], errors='coerce')
    coords = coords.dropna(subset=['zip', 'latitude', 'longitude'])
    if coords.empty:
        return pd.DataFrame(columns=['zip_lat', 'zip_lon'])
    means = coords.groupby('zip')[['latitude', 'longitude']].mean()
    means.columns = ['zip_lat', 'zip_lon']
    return means


def enrich_markets(df: pd.DataFrame) -> pd.DataFrame:
    """Add normalized address, search helpers, and per-ZIP centroids."""
    df = df.copy()

    parsed = df['location_address'].apply(_parse_address)
    df[['street', 'city', 'state', 'zip']] = pd.DataFrame(parsed.tolist(), index=df.index)

    zip_series = df['zip'].fillna('').astype(str)
    zip_series = zip_series.str.extract(r'(\d{5})')[0].fillna('')
    df['zip'] = zip_series

    df['full_address'] = df.apply(
        lambda r: _join_address(r.get('street'), r.get('city'), r.get('state'), r.get('zip'))
        or _maybe(r.get('location_address')),
        axis=1,
    )

    df['search_city'] = df['city'].fillna('').str.lower()
    df['search_state'] = df['state'].fillna('').str.upper()
    df['search_zip'] = df['zip'].fillna('').str.strip()
    df['search_city_norm'] = df['search_city'].apply(_normalize_text)
    df['search_state_norm'] = df['search_state'].apply(lambda s: s.strip().upper())

    means = _zip_means(df)
    df = df.join(means, on='zip')

    haystack_sources = pd.concat(
        [
            df['listing_name'],
            df['organization'],
            df['street'],
            df['city'],
            df['state'],
            df['zip'],
            df['location_desc'],
            df['listing_desc'],
        ],
        axis=1,
    ).fillna('').astype(str)

    df['search_haystack'] = haystack_sources.apply(lambda parts: ' '.join(p for p in parts if p), axis=1)
    df['search_haystack'] = df['search_haystack'].str.lower().str.replace(r'\s+', ' ', regex=True).str.strip()

    return df


def generate_zip_centroids(df: pd.DataFrame) -> dict[str, list[float]]:
    """Generate zip and zip-prefix centroids from a validated markets DataFrame."""
    centroids: dict[str, list[float]] = {}
    coords = df[['zip', 'zip_lat', 'zip_lon']].dropna(subset=['zip_lat', 'zip_lon'])
    for zip_code, group in coords.groupby('zip'):
        try:
            lat = float(group['zip_lat'].mean())
            lon = float(group['zip_lon'].mean())
        except Exception:
            continue
        if not zip_code:
            continue
        zip_str = str(zip_code).strip()
        if zip_str:
            centroids[zip_str] = [lat, lon]

    if not centroids:
        return centroids

    # Prefix centroids (3-digit) provide fallbacks for ZIPs not present in the dataset
    prefix_frame = coords.copy()
    prefix_frame['prefix'] = prefix_frame['zip'].astype(str).str[:3]
    prefix_means = prefix_frame.groupby('prefix')[['zip_lat', 'zip_lon']].mean()
    for prefix, row in prefix_means.iterrows():
        if not prefix:
            continue
        if prefix not in centroids:
            centroids[prefix] = [float(row['zip_lat']), float(row['zip_lon'])]

    return centroids


def generate_city_centroids(df: pd.DataFrame) -> Dict[str, list[float]]:
    """Average market coordinates per normalized city/state grouping."""
    city_data = df[['search_city_norm', 'search_state_norm', 'latitude', 'longitude']].copy()
    city_data['latitude'] = pd.to_numeric(city_data['latitude'], errors='coerce')
    city_data['longitude'] = pd.to_numeric(city_data['longitude'], errors='coerce')
    city_data = city_data.dropna(subset=['search_city_norm', 'latitude', 'longitude'])
    if city_data.empty:
        return {}

    grouped = city_data.groupby(['search_city_norm', 'search_state_norm'])[['latitude', 'longitude']].mean()
    counts = city_data.groupby(['search_city_norm', 'search_state_norm']).size()

    centroids: Dict[str, list[float]] = {}
    city_totals: Dict[str, tuple[float, float, int]] = {}
    city_states: Dict[str, set[str]] = {}

    for (city_norm, state_norm), row in grouped.iterrows():
        lat = float(row['latitude'])
        lon = float(row['longitude'])
        state_key = state_norm or ''
        if city_norm:
            city_states.setdefault(city_norm, set()).add(state_key or '')
            key = f"{city_norm}|{state_key}" if state_key else city_norm
            centroids[key] = [lat, lon]

            # Track overall city fallback keyed without state
            total_lat, total_lon, total_count = city_totals.get(city_norm, (0.0, 0.0, 0))
            count = int(counts.loc[(city_norm, state_norm)])
            city_totals[city_norm] = (total_lat + lat * count, total_lon + lon * count, total_count + count)

    for city_norm, (lat_sum, lon_sum, total_count) in city_totals.items():
        if total_count <= 0:
            continue
        avg_lat = lat_sum / total_count
        avg_lon = lon_sum / total_count
        state_variants = city_states.get(city_norm, set()) or {''}
        # Only provide a fallback centroid when the city appears in a single state
        non_empty_states = {s for s in state_variants if s}
        allow_fallback = len(non_empty_states) <= 1
        if allow_fallback:
            centroids.setdefault(city_norm, [avg_lat, avg_lon])

    return centroids


__all__ = ['enrich_markets', 'generate_zip_centroids', 'generate_city_centroids']
