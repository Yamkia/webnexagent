import datetime

from langchain_core.tools import tool

import config
import requests
from email_tools import send_email


def _format_date(dt: datetime.date) -> str:
    return dt.isoformat()


@tool
def fetch_cipc_new_businesses(since_date: str = None, max_results: int = 20) -> list:
    """Fetch recently registered businesses from the CIPC.

    This tool expects the following environment variables to be set in your .env file:
      - CIPC_API_BASE_URL (required): Base URL for the CIPC endpoint that returns new registrations.
      - CIPC_API_KEY (optional): API key / token if the CIPC endpoint is protected.

    The exact JSON schema returned by the CIPC endpoint is unknown here, so this tool will attempt to
    return a list of company records. If the endpoint returns a different structure, you can customize
    this function to match your API.

    Args:
        since_date (str): ISO date (YYYY-MM-DD) to fetch records created since that date.
                          Defaults to 7 days ago if not provided.
        max_results (int): Maximum number of records to return.

    Returns:
        A list of dicts, each representing a company/registration.
    """

    if not getattr(config, 'CIPC_API_BASE_URL', None):
        return (
            "CIPC API base URL is not configured. Please set CIPC_API_BASE_URL in your .env "
            "file to a valid endpoint that returns new company registrations."
        )

    if since_date is None:
        since_date = _format_date(datetime.date.today() - datetime.timedelta(days=7))

    headers = {}
    if getattr(config, 'CIPC_API_KEY', None):
        headers['Authorization'] = f"Bearer {config.CIPC_API_KEY}"

    params = {
        'since': since_date,
        'limit': max_results,
    }

    try:
        resp = requests.get(config.CIPC_API_BASE_URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Failed to fetch CIPC data: {e}"

    try:
        payload = resp.json()
    except Exception as e:
        return f"Unable to parse CIPC response as JSON: {e}"

    # Try to be flexible about the response shape
    if isinstance(payload, dict):
        for key in ("companies", "results", "data", "items"):
            if key in payload and isinstance(payload[key], list):
                return payload[key][:max_results]
        # If the dict itself looks like a single company record, wrap it.
        if any(k in payload for k in ("name", "company_name", "registration_number", "reg_no")):
            return [payload]
        # Fallback: if it contains a list under any key, choose the first list
        for v in payload.values():
            if isinstance(v, list):
                return v[:max_results]
        return []

    if isinstance(payload, list):
        return payload[:max_results]

    return []


@tool
def email_cipc_new_businesses_to_zisandahub(
    since_date: str = None,
    max_results: int = 20,
    to_email: str = None,
    subject_prefix: str = "CIPC New Registrations",
) -> str:
    """Fetch recent CIPC registrations and email them to Zisandahub.

    This tool uses the `fetch_cipc_new_businesses` tool to retrieve data and then sends an email using the
    existing `email_tools.send_email` tool.

    Args:
        since_date (str): ISO date (YYYY-MM-DD) to fetch records since.
        max_results (int): Maximum number of registrations to include.
        to_email (str): Optional destination email address. If not provided, uses ZISANDAHUB_EMAIL from config.
        subject_prefix (str): Prefix for the email subject.

    Returns:
        A status message describing what happened.
    """

    companies = fetch_cipc_new_businesses(since_date=since_date, max_results=max_results)
    if isinstance(companies, str):
        # An error string was returned
        return companies

    if not companies:
        return "No new CIPC registrations were found for the specified period."

    to = to_email or getattr(config, 'ZISANDAHUB_EMAIL', None)
    if not to:
        return (
            "No recipient email configured. Please set ZISANDAHUB_EMAIL in your .env file or provide 'to_email'."
        )

    # Build a simple email body
    lines = [
        f"New CIPC registrations since {since_date or 'the last 7 days'}:",
        "",
    ]

    for idx, comp in enumerate(companies[:max_results], start=1):
        name = comp.get('name') or comp.get('company_name') or comp.get('business_name') or "<unknown>"
        reg_no = comp.get('registration_number') or comp.get('reg_no') or comp.get('company_number') or "<unknown>"
        reg_date = comp.get('date_registered') or comp.get('registration_date') or "<unknown>"
        lines.append(f"{idx}. {name} (Reg: {reg_no}) - Registered: {reg_date}")

    body = "\n".join(lines)
    subject = f"{subject_prefix} — {len(companies)} companies"

    result = send_email(to=to, subject=subject, body=body)
    return result


# --- Helper for ranking / sorting potential clients ---
DEFAULT_CLIENT_KEYWORDS = [
    "tech", "software", "digital", "services", "consulting", "solutions", "cloud", "data",
    "marketing", "design", "analytics", "media", "studio", "innovation", "startup",
]


def _score_company_record(company: dict, extra_keywords: list[str] | None = None) -> int:
    """Compute a simple heuristic score for how likely a company is a good lead."""
    if not isinstance(company, dict):
        return 0

    text_fields = []
    for key in ("name", "company_name", "business_name", "industry", "sector", "description"):
        val = company.get(key)
        if isinstance(val, str):
            text_fields.append(val.lower())
    text = " ".join(text_fields)

    score = 0
    keywords = list(DEFAULT_CLIENT_KEYWORDS)
    if extra_keywords:
        keywords.extend([kw.strip().lower() for kw in extra_keywords if isinstance(kw, str) and kw.strip()])

    for kw in keywords:
        if kw and kw in text:
            score += 10

    # Boost companies that have a website / email listed (more likely a business)
    for field in ("website", "url", "email", "contact_email"):
        if company.get(field):
            score += 3

    # Prefer more complete entries
    for field in ("address", "city", "country", "postcode"):
        if company.get(field):
            score += 1

    return score


@tool
def rank_potential_clients(
    since_date: str = None,
    max_results: int = 50,
    top_n: int = 10,
    keyword_boost: str = None,
) -> list:
    """Fetch CIPC registrations and sort them to surface the most likely new clients.

    The tool scores each company based on keyword matches in the name/industry/description fields
    and by whether the record contains a website/email. It then returns the top N companies.

    Args:
        since_date (str): ISO date (YYYY-MM-DD) to fetch records since.
        max_results (int): Maximum number of registrations to fetch before ranking.
        top_n (int): How many records to return after sorting.
        keyword_boost (str): Optional comma-separated keywords to boost in scoring.

    Returns:
        A list of company dicts augmented with a ``_score`` field (highest first).
    """

    companies = fetch_cipc_new_businesses(since_date=since_date, max_results=max_results)
    if isinstance(companies, str):
        return companies
    if not companies:
        return []

    extra_keywords = []
    if keyword_boost:
        extra_keywords = [kw.strip() for kw in keyword_boost.split(",") if kw.strip()]

    scored = []
    for comp in companies:
        score = _score_company_record(comp, extra_keywords=extra_keywords)
        entry = dict(comp)
        entry["_score"] = score
        scored.append(entry)

    scored.sort(key=lambda c: c.get("_score", 0), reverse=True)
    return scored[: max(1, min(top_n, len(scored)))]


tools = [fetch_cipc_new_businesses, rank_potential_clients, email_cipc_new_businesses_to_zisandahub]
