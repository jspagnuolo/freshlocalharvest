# File: ingest/scripts/enrich.py
"""Post-ingest enrichment helpers.

Adds normalized address components and search-friendly tokens so that the
front-end can support richer filtering without additional services.
"""
from __future__ import annotations

import re
from typing import Iterable, Tuple

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

    text = text.rstrip(';')
    parts = [p.strip() for p in text.split(',') if p.strip()]
    if len(parts) >= 3:
        street = ', '.join(parts[:-2]) or None
        city = parts[-2] or None
        state_chunk = parts[-1]
    else:
        street = text or None
        city = None
        state_chunk = ""

    tokens = [tok for tok in state_chunk.replace(';', ' ').split() if tok]
    state_token = None
    zipcode = None
    if tokens:
        maybe_zip = tokens[-1]
        match = ZIP_RE.match(maybe_zip)
        if match:
            zipcode = match.group(1)
            tokens = tokens[:-1]
        state_token = ' '.join(tokens) if tokens else None

    state = _normalize_state(state_token)
    if zipcode and len(zipcode) == 5:
        zipcode = zipcode
    elif zipcode:
        zipcode = zipcode[:5]

    return street, city, state, zipcode


def _join_address(street: str | None, city: str | None, state: str | None, zipcode: str | None) -> str:
    pieces: Iterable[str] = [p for p in (street, city, state, zipcode) if p]
    return ', '.join(pieces)


def enrich_markets(df: pd.DataFrame) -> pd.DataFrame:
    """Add normalized address + search helper columns.

    Returns a copy so callers do not rely on mutation semantics.
    """
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


__all__ = ['enrich_markets']
