import datetime
import re
import time

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
def register_cipc_business(
    business_name: str,
    company_type: str = "Private company (Pty) Ltd",
    director_name: str = None,
    director_id_number: str = None,
    physical_address: str = None,
    postal_address: str = None,
    contact_email: str = None,
    contact_phone: str = None,
    industry: str = None,
    registration_number: str = None,
    additional_info: str = None,
) -> str:
    """Register a new business with CIPC.

    If a registration API URL is configured, it will use that endpoint.
    Otherwise it can perform browser automation against a configured registration site.
    """

    if not business_name or not contact_email or not physical_address:
        return (
            "Please provide at least business_name, contact_email, and physical_address "
            "so the registration can be submitted."
        )

    if getattr(config, 'CIPC_REGISTRATION_API_URL', None):
        return _submit_cipc_registration_api(
            business_name=business_name,
            company_type=company_type,
            director_name=director_name,
            director_id_number=director_id_number,
            physical_address=physical_address,
            postal_address=postal_address,
            contact_email=contact_email,
            contact_phone=contact_phone,
            industry=industry,
            registration_number=registration_number,
            additional_info=additional_info,
        )

    if getattr(config, 'CIPC_BROWSER_AUTOMATION_ENABLED', False) and getattr(config, 'CIPC_REGISTRATION_SITE_URL', None):
        return _submit_cipc_registration_browser(
            business_name=business_name,
            company_type=company_type,
            director_name=director_name,
            director_id_number=director_id_number,
            physical_address=physical_address,
            postal_address=postal_address,
            contact_email=contact_email,
            contact_phone=contact_phone,
            industry=industry,
            registration_number=registration_number,
            additional_info=additional_info,
        )

    return (
        "No CIPC registration automation is configured. "
        "Please set CIPC_REGISTRATION_API_URL or CIPC_REGISTRATION_SITE_URL in your .env file."
    )


def _submit_cipc_registration_api(
    business_name: str,
    company_type: str,
    director_name: str,
    director_id_number: str,
    physical_address: str,
    postal_address: str,
    contact_email: str,
    contact_phone: str,
    industry: str,
    registration_number: str,
    additional_info: str,
) -> str:
    headers = {
        'Content-Type': 'application/json',
    }
    if getattr(config, 'CIPC_REGISTRATION_API_KEY', None):
        headers['Authorization'] = f"Bearer {config.CIPC_REGISTRATION_API_KEY}"

    payload = {
        'business_name': business_name,
        'company_type': company_type,
        'director_name': director_name,
        'director_id_number': director_id_number,
        'physical_address': physical_address,
        'postal_address': postal_address,
        'contact_email': contact_email,
        'contact_phone': contact_phone,
        'industry': industry,
        'registration_number': registration_number,
        'additional_info': additional_info,
    }

    try:
        resp = requests.post(
            config.CIPC_REGISTRATION_API_URL,
            json={k: v for k, v in payload.items() if v is not None},
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Failed to submit CIPC registration: {e}"

    try:
        response_payload = resp.json()
    except Exception:
        return f"Registration API responded with status {resp.status_code}: {resp.text}"

    if isinstance(response_payload, dict):
        if response_payload.get('success') is False:
            return f"CIPC registration failed: {response_payload.get('message') or response_payload}"
        return f"CIPC registration request submitted successfully: {response_payload.get('message', response_payload)}"

    return f"CIPC registration response: {response_payload}"


def _submit_cipc_registration_browser(
    business_name: str,
    company_type: str,
    director_name: str,
    director_id_number: str,
    physical_address: str,
    postal_address: str,
    contact_email: str,
    contact_phone: str,
    industry: str,
    registration_number: str,
    additional_info: str,
) -> str:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service as ChromeService
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.common.exceptions import WebDriverException
    except ImportError as e:
        return (
            "Browser automation requires Selenium and webdriver-manager. "
            "Please install them and restart the app."
        )

    options = Options()
    if getattr(config, 'CIPC_BROWSER_HEADLESS', True):
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1600,1200')
    if getattr(config, 'CIPC_CHROME_EXECUTABLE_PATH', None):
        options.binary_location = config.CIPC_CHROME_EXECUTABLE_PATH

    try:
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options,
        )
    except WebDriverException as e:
        return f"Failed to start browser automation: {e}"

    try:
        driver.get(config.CIPC_REGISTRATION_SITE_URL)
        time.sleep(3)

        field_map = {
            'business_name': ['business_name', 'company_name', 'entity_name', 'businessname', 'companyname'],
            'company_type': ['company_type', 'entity_type', 'business_type', 'companytype'],
            'director_name': ['director_name', 'name_of_director', 'directorname', 'director'],
            'director_id_number': ['director_id_number', 'id_number', 'idnumber', 'identity_number', 'id'],
            'physical_address': ['physical_address', 'address', 'business_address', 'street_address'],
            'postal_address': ['postal_address', 'postal_address1', 'postal', 'pobox'],
            'contact_email': ['contact_email', 'email', 'email_address', 'contactemail'],
            'contact_phone': ['contact_phone', 'phone', 'telephone', 'mobile'],
            'industry': ['industry', 'sector', 'business_sector', 'industry_type'],
            'registration_number': ['registration_number', 'company_number', 'reg_no', 'registrationno'],
            'additional_info': ['additional_info', 'notes', 'comments', 'other_details'],
        }

        values = {
            'business_name': business_name,
            'company_type': company_type,
            'director_name': director_name,
            'director_id_number': director_id_number,
            'physical_address': physical_address,
            'postal_address': postal_address,
            'contact_email': contact_email,
            'contact_phone': contact_phone,
            'industry': industry,
            'registration_number': registration_number,
            'additional_info': additional_info,
        }

        def _match_element(field_names):
            candidates = driver.find_elements(By.XPATH, "//input|//textarea|//select")
            lowered = [name.lower() for name in field_names if name]
            for element in candidates:
                attrs = [
                    element.get_attribute('name') or '',
                    element.get_attribute('id') or '',
                    element.get_attribute('placeholder') or '',
                    element.get_attribute('aria-label') or '',
                    element.get_attribute('title') or '',
                ]
                attrs_text = ' '.join(attrs).lower()
                for keyword in lowered:
                    if keyword in attrs_text:
                        return element
            return None

        for field_key, field_names in field_map.items():
            value = values.get(field_key)
            if not value:
                continue
            element = _match_element(field_names)
            if not element:
                continue
            tag_name = element.tag_name.lower()
            if tag_name == 'select':
                options_elems = element.find_elements(By.TAG_NAME, 'option')
                selected = False
                for option in options_elems:
                    if value.lower() in (option.text or '').lower():
                        option.click()
                        selected = True
                        break
                if not selected and options_elems:
                    options_elems[0].click()
                continue
            try:
                element.clear()
                element.send_keys(value)
            except Exception:
                continue

        # Try to click a submit button
        submit_texts = ['submit', 'register', 'continue', 'next', 'complete', 'finish', 'apply']
        buttons = driver.find_elements(By.XPATH, "//button|//input[@type='submit']")
        clicked = False
        for btn in buttons:
            text = (btn.text or btn.get_attribute('value') or '').lower()
            for keyword in submit_texts:
                if keyword in text:
                    try:
                        btn.click()
                        clicked = True
                        break
                    except Exception:
                        continue
            if clicked:
                break

        if not clicked:
            # Try pressing enter in the last input we filled
            last_input = None
            for field_key, field_names in field_map.items():
                if values.get(field_key):
                    last_input = _match_element(field_names)
            if last_input:
                last_input.send_keys('\n')

        time.sleep(getattr(config, 'CIPC_BROWSER_WAIT_SECONDS', 15))
        success_message = driver.page_source[:5000]
        return "Registration automation attempted. Check the browser session for results. Response snippet: " + success_message[:1000]
    except Exception as exc:
        return f"Browser automation error: {exc}"
    finally:
        try:
            driver.quit()
        except Exception:
            pass


@tool
def email_cipc_new_businesses_to_zisandahub(
    since_date: str = None,
    max_results: int = 20,
    to_email: str = None,
    subject_prefix: str = "CIPC New Registrations",
    business_info: str = None,
    request_text: str = None,
) -> str:
    """Fetch recent CIPC registrations and email them to Zisandahub.

    This tool uses the `fetch_cipc_new_businesses` tool to retrieve data and then sends an email using the
    existing `email_tools.send_email` tool.

    Args:
        since_date (str): ISO date (YYYY-MM-DD) to fetch records since.
        max_results (int): Maximum number of registrations to include.
        to_email (str): Optional destination email address. If not provided, uses ZISANDAHUB_EMAIL from config.
        subject_prefix (str): Prefix for the email subject.
        business_info (str): Optional text describing the user's business.
        request_text (str): Optional text describing the user's request or goal.

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

    if business_info:
        lines.extend([
            "Business context:",
            business_info.strip(),
            "",
        ])

    if request_text:
        lines.extend([
            "Requested action:",
            request_text.strip(),
            "",
        ])

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


def _extract_category_values(company: dict) -> list[str]:
    values: list[str] = []
    if not isinstance(company, dict):
        return values

    for key in (
        'business_category', 'category', 'industry', 'sector', 'subsector',
        'business_type', 'classification', 'primary_activity', 'service_category'
    ):
        value = company.get(key)
        if isinstance(value, str):
            for part in re.split(r'[;,/|]', value):
                clean_part = part.strip()
                if clean_part:
                    values.append(clean_part)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    values.append(item.strip())

    return values


@tool
def list_cipc_business_categories(since_date: str = None, max_results: int = 50) -> list:
    """Return a list of business categories found in the latest CIPC registrations."""
    companies = fetch_cipc_new_businesses(since_date=since_date, max_results=max_results)
    if isinstance(companies, str):
        return companies

    categories: set[str] = set()
    for company in companies:
        for category in _extract_category_values(company):
            categories.add(category)

    if not categories:
        # Fallback to useful category examples when CIPC data does not include explicit fields.
        categories = {
            'Accounting', 'Agriculture', 'Automotive', 'Consulting', 'Construction',
            'Education', 'Financial Services', 'Food & Beverage', 'Healthcare',
            'Hospitality', 'IT & Software', 'Logistics', 'Manufacturing',
            'Marketing', 'Media', 'Real Estate', 'Retail', 'Telecoms', 'Transport',
            'Wholesale'
        }

    return sorted(categories)


@tool
def create_cipc_registration_plan(
    business_name: str,
    industry: str = None,
    location: str = None,
    owner_name: str = None,
    business_description: str = None,
) -> str:
    """Create a tailored CIPC registration plan and checklist for a new business."""
    if not business_name:
        return "Please provide the business_name so I can create a registration plan."

    lines = [
        f"CIPC registration plan for '{business_name}':",
        "",
        "1. Choose your company type:",
        "   - Private company (Pty) Ltd is the most common for small and medium businesses.",
        "   - Personal liability company (Inc), public company, or non-profit are alternatives based on your goals.",
        "",
        "2. Reserve or use a company name:",
        "   - If you already have a name, check availability on CIPC and reserve it.",
        "   - If you already have a registration number, use that instead of reserving.",
        "",
        "3. Gather required documents and details:",
        "   - Certified copies of ID/passport for directors and members.",
        "   - Proof of business address and director address.",
        "   - Share structure and percentage ownership details.",
        "   - Business activity description and industry classification.",
        "",
        "4. Complete the CIPC registration form:",
        "   - Enter business name, address, and contact details.",
        "   - Add director and member information.",
        "   - Confirm shareholding structure and company rules.",
        "",
        "5. Register for related requirements:",
        "   - Apply for tax registration with SARS if needed.",
        "   - Register for UIF and PAYE if you will employ staff.",
        "",
        "6. Open a business bank account:",
        "   - Choose a bank that supports small business accounts.",
        "   - Prepare the CIPC registration certificate, proof of address, and ID documents.",
        "",
        "7. Launch and brand your business:",
        "   - Create a business card design or choose from curated options.",
        "   - Prepare a basic website or social presence if needed.",
    ]

    if industry:
        lines.insert(2, f"Industry: {industry}")
        lines.insert(3, "")
    if location:
        lines.insert(2, f"Location: {location}")
        lines.insert(3, "")
    if owner_name:
        lines.insert(2, f"Owner: {owner_name}")
        lines.insert(3, "")
    if business_description:
        lines.insert(2, f"Business description: {business_description}")
        lines.insert(3, "")

    return "\n".join(lines)


@tool
def generate_business_card_options(
    business_name: str,
    industry: str = None,
    tagline: str = None,
    color_palette: str = None,
) -> str:
    """Generate three business card design options for a new company."""
    if not business_name:
        return "Please provide the business_name so I can generate business card options."

    industry_text = f"Industry: {industry}" if industry else ""
    tagline_text = f"Tagline: {tagline}" if tagline else ""
    palette_text = f"Preferred palette: {color_palette}" if color_palette else ""

    options = [
        {
            'name': 'Classic Professional',
            'layout': 'Minimal white background, dark navy accent border, left-aligned logo area, right side contact details.',
            'headline': business_name,
            'details': [
                tagline or 'Reliable business services.',
                'Phone: +27 71 000 0000',
                'Email: info@yourcompany.co.za',
                'Web: www.yourcompany.co.za',
            ],
            'notes': 'Great for corporate, consulting and finance businesses.',
        },
        {
            'name': 'Modern Creative',
            'layout': 'Full-width colored band with bold typography, rounded icon/logo in top-left, contact details centered below.',
            'headline': business_name,
            'details': [
                tagline or 'Creative solutions for modern businesses.',
                'Phone: +27 71 000 0000',
                'Email: hello@yourcompany.co.za',
                'Address: Cape Town, South Africa',
            ],
            'notes': 'Works well for design, marketing, hospitality and lifestyle brands.',
        },
        {
            'name': 'Bold Minimal',
            'layout': 'Dark background with a bright brand accent, single-column contact block, clean serif headline.',
            'headline': business_name,
            'details': [
                tagline or 'Professional and memorable.',
                'Phone: +27 71 000 0000',
                'Email: contact@yourcompany.co.za',
                'Registration: CIPC 2026/123456/07',
            ],
            'notes': 'Ideal for premium service brands and boutique companies.',
        },
    ]

    if color_palette:
        options[0]['notes'] += f' Use {color_palette} accents.'
        options[1]['notes'] += f' Use {color_palette} gradients.'
        options[2]['notes'] += f' Use {color_palette} highlights.'

    formatted = [
        f"Option {idx + 1}: {opt['name']}\n"
        f"Layout: {opt['layout']}\n"
        f"Headline: {opt['headline']}\n"
        f"Details:\n  - " + "\n  - ".join(opt['details']) + "\n"
        f"Notes: {opt['notes']}"
        for idx, opt in enumerate(options)
    ]

    return "\n\n".join(formatted)


@tool
def prepare_bank_outreach_email(
    bank_name: str,
    bank_email: str,
    business_name: str,
    owner_name: str = None,
    account_type: str = 'business account',
    reason: str = 'opening a new business bank account',
) -> str:
    """Draft a professional email to a bank requesting an account or business banking service."""
    if not bank_name or not bank_email or not business_name:
        return "Please provide bank_name, bank_email, and business_name so I can draft the outreach email."

    owner_line = f"My name is {owner_name}. " if owner_name else ""
    subject = f"Request to open a {account_type} for {business_name}"
    body_lines = [
        f"Dear {bank_name} team,",
        "",
        f"My name is {owner_name if owner_name else 'a business owner'}, and I am preparing to register my company, {business_name}, with CIPC.",
        f"I am interested in {reason} and would like to understand the documentation, account packages, and onboarding process you offer for a new South African business.",
        "",
        "Key business details:",
        f"- Business name: {business_name}",
        f"- Account type requested: {account_type}",
        f"- CIPC registration status: pending / in progress",
        "",
        "Please let me know what information you require, the expected timeline, and any preferred next steps.",
        "",
        "Kind regards,",
        f"{owner_name if owner_name else business_name}",
    ]
    body = "\n".join(body_lines)

    return f"Subject: {subject}\nTo: {bank_email}\n\n{body}"


tools = [
    fetch_cipc_new_businesses,
    rank_potential_clients,
    email_cipc_new_businesses_to_zisandahub,
    list_cipc_business_categories,
    create_cipc_registration_plan,
    generate_business_card_options,
    prepare_bank_outreach_email,
    register_cipc_business,
]
