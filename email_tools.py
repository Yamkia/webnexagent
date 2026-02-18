from langchain_core.tools import tool
from typing import List, Optional
import imaplib
import email
import smtplib
from email.header import decode_header
from email.utils import parseaddr
from contextlib import contextmanager
from email.message import EmailMessage
import config
import html2text

@contextmanager
def _get_imap_connection():
    """Context manager for handling IMAP connection, login, and inbox selection."""
    mail = None
    try:
        mail = imaplib.IMAP4_SSL(config.IMAP_SERVER)
        mail.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
        mail.select("inbox")
        yield mail
    finally:
        if mail:
            mail.logout()

def _decode_header(header):
    """Decodes email header to a readable string."""
    decoded_parts = decode_header(header)
    header_parts = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            header_parts.append(part.decode(encoding if encoding else 'utf-8', errors='ignore'))
        else:
            header_parts.append(part)
    return "".join(header_parts)

def _get_body_from_msg(msg: email.message.Message) -> str:
    """
    Extracts the body from an email.message.Message object.
    It prioritizes text/plain, but falls back to converting text/html to Markdown
    to preserve links and basic formatting.
    """
    plain_text_body = ""
    html_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            # Skip attachments
            if "attachment" in content_disposition:
                continue

            if content_type == "text/plain" and not plain_text_body:
                try:
                    plain_text_body = part.get_payload(decode=True).decode(errors='ignore')
                except Exception:
                    continue
            elif content_type == "text/html" and not html_body:
                try:
                    html_body = part.get_payload(decode=True).decode(errors='ignore')
                except Exception:
                    continue
    else:
        # Not a multipart message
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            try:
                plain_text_body = msg.get_payload(decode=True).decode(errors='ignore')
            except Exception:
                pass
        elif content_type == "text/html":
            try:
                html_body = msg.get_payload(decode=True).decode(errors='ignore')
            except Exception:
                pass

    # Prioritize plain text, but use HTML if plain text is not available
    if plain_text_body:
        return plain_text_body.strip()
    
    if html_body:
        # Convert HTML to Markdown to preserve links and basic formatting.
        h = html2text.HTML2Text()
        # Configure to ignore images and format links nicely.
        h.ignore_images = True
        markdown_body = h.handle(html_body)
        return markdown_body.strip()
        
    return "" # Return empty string if no body is found

@tool
def check_new_emails(max_results: int = 5) -> List[dict]:
    """
    Checks for new, unread emails in the user's inbox using IMAP and returns a summary of the most recent ones.
    Each email summary is a dictionary containing 'id', 'from', 'subject', and 'snippet'.
    """
    try:
        with _get_imap_connection() as mail:
            status, messages = mail.search(None, '(UNSEEN)')
            if status != 'OK':
                return "Failed to search for emails."

            email_ids = messages[0].split()
            if not email_ids:
                return "No new unread emails found."

            emails = []
            for email_id in reversed(email_ids[-max_results:]):
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        subject = _decode_header(msg["subject"])
                        from_ = _decode_header(msg.get("from"))

                        body = _get_body_from_msg(msg)
                        snippet = (body[:100] + '...') if len(body) > 100 else body
                        
                        emails.append({
                            "id": email_id.decode(),
                            "from": from_,
                            "subject": subject,
                            "snippet": snippet.strip().replace('\r\n', ' ')
                        })
            return emails
    except imaplib.IMAP4.error as e:
        # Provide a more specific error for common authentication issues.
        error_message = str(e).lower()
        if 'authenticationfailed' in error_message or 'invalid credentials' in error_message:
            return ("Authentication failed. Please check your email user and password. "
                    "If using Gmail, you must generate and use an 'App Password', not your regular account password.")
        return f"An IMAP error occurred: {e}"
    except Exception as e:
        return f"An unexpected error occurred while checking emails: {e}"

@tool
def read_email_content(email_id: str) -> str:
    """
    Reads the full content of a specific email given its ID using IMAP.
    """
    try:
        with _get_imap_connection() as mail:
            status, msg_data = mail.fetch(email_id.encode(), '(RFC822)')
            if status != 'OK':
                return f"Could not fetch email with ID {email_id}. Status: {status}"

            # Check if the fetch returned valid message data. An invalid ID returns [b')'].
            if not msg_data or not isinstance(msg_data[0], tuple):
                return f"No email found with ID {email_id}, or the ID is invalid."
            
            msg = email.message_from_bytes(msg_data[0][1])
            subject = _decode_header(msg["subject"])
            from_header = _decode_header(msg.get("from"))
            # Extract the address for easier use by the agent
            from_name, from_addr = parseaddr(from_header)
            
            body = _get_body_from_msg(msg)
            if not body:
                return f"Sender: {from_header}\nSender Email: {from_addr}\nSubject: {subject}\n\n[Could not extract a readable body from this email. It might be an image or have an unusual format.]"
            
            # Provide a structured output string to make it easier for the LLM to parse the sender's address.
            return f"Sender: {from_header}\nSender Email: {from_addr}\nSubject: {subject}\n\n{body.strip()}"
    except imaplib.IMAP4.error as e:
        # Provide a more specific error for common authentication issues.
        error_message = str(e).lower()
        if 'authenticationfailed' in error_message or 'invalid credentials' in error_message:
            return ("Authentication failed. Please check your email user and password. "
                    "If using Gmail, you must generate and use an 'App Password', not your regular account password.")
        return f"An IMAP error occurred: {e}"
    except Exception as e:
        return f"An unexpected error occurred while reading email: {e}"

@tool
def draft_reply(to: str, subject: str, body: str, in_reply_to: Optional[str] = None) -> str:
    """
    Drafts an email but does NOT send it.
    Use the 'to', 'subject', and 'body' arguments to specify the recipient, subject, and message content.
    If replying to an existing email, provide the original email's ID in the 'in_reply_to' argument.
    Returns a formatted string containing the full draft for the user to review.
    """
    draft_content = f"To: {to}\nSubject: {subject}\n\n{body}"

    if in_reply_to:
        print(f"INFO: Drafting reply to email {in_reply_to} (placeholder).")
    else:
        print(f"INFO: Drafting new email to {to} (placeholder).")

    # The agent will now receive the full draft content as the tool's output, making it easy to show the user.
    return f"Draft created successfully. Here is the content for your review:\n\n---\n{draft_content}\n---"

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """
    Sends an email using SMTP.
    Use the 'to', 'subject', and 'body' arguments to specify the recipient, subject, and message content.
    This tool should only be used after the user has approved a draft.
    """
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = config.EMAIL_USER
        msg['To'] = to

        # Connect to the SMTP server and send the email, handling both
        # SMTP_SSL (e.g., port 465) and STARTTLS (e.g., port 587).
        if config.SMTP_PORT == 587:
            # Use STARTTLS
            with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
                server.starttls()
                server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
                server.send_message(msg)
        else:
            # Use SMTP_SSL for a secure connection from the start.
            with smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT) as server:
                server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
                server.send_message(msg)
        
        return f"Email sent successfully to {to}."
    except smtplib.SMTPAuthenticationError:
        return ("SMTP Authentication failed. Please check your email user and password. "
                "If using Gmail, you must use an 'App Password'. For other services, ensure credentials are correct.")
    except Exception as e:
        return f"An unexpected error occurred while sending the email: {e}"

tools = [check_new_emails, read_email_content, draft_reply, send_email]

# --- Helper for UI endpoints (not LangChain tools) ---
def list_emails_for_ui(limit: int = 20, page: int = 1, unread_only: bool = True, query: str | None = None):
    """
    Return a dict with emails and has_more for UI consumption.
    Supports unread-only toggle, free-text query (subject/from), and pagination.
    """
    try:
        with _get_imap_connection() as mail:
            # Base search: UNSEEN or ALL
            base_criteria = '(UNSEEN)' if unread_only else '(ALL)'

            def _do_search(criteria_parts):
                status, data = mail.search(None, *criteria_parts)
                if status != 'OK':
                    return []
                return [eid for eid in data[0].split() if eid]

            if query:
                # Try SUBJECT and FROM, union them, then intersect with base
                q = query.strip()
                base_ids = set(_do_search([base_criteria]))
                ids_subject = set(_do_search([base_criteria, 'SUBJECT', f'"{q}"']))
                ids_from = set(_do_search([base_criteria, 'FROM', f'"{q}"']))
                email_ids = list(base_ids.intersection(ids_subject.union(ids_from)))
            else:
                email_ids = _do_search([base_criteria])

            # Order newest first
            email_ids = list(reversed(email_ids))
            total = len(email_ids)
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, int(limit or 20))
            start = (page - 1) * limit
            end = start + limit
            slice_ids = email_ids[start:end]
            has_more = end < total

            emails = []
            for email_id in slice_ids:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = _decode_header(msg.get('subject', ''))
                        from_ = _decode_header(msg.get('from', ''))
                        body = _get_body_from_msg(msg)
                        snippet = (body[:120] + '...') if len(body) > 120 else body
                        emails.append({
                            'id': email_id.decode(),
                            'from': from_,
                            'subject': subject,
                            'snippet': (snippet or '').strip().replace('\r\n', ' ')
                        })
                        break
            return {'emails': emails, 'has_more': has_more, 'page': page}
    except imaplib.IMAP4.error as e:
        return {'error': f'IMAP error: {e}'}
    except Exception as e:
        return {'error': f'Unexpected error: {e}'}