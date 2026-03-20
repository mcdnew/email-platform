# tests/test_mailer.py — mailer unit tests

import smtplib
from unittest.mock import patch, MagicMock

from app.mailer import render_template, send_email


def test_render_template_basic():
    result = render_template("Hello {{name}}", {"name": "Alice"})
    assert result == "Hello Alice"


def test_render_template_multiple_vars():
    result = render_template("{{name}} from {{company}}", {"name": "Bob", "company": "Acme"})
    assert result == "Bob from Acme"


def test_render_template_undefined_var_fallback():
    """Undefined variable returns the raw template text, no exception."""
    result = render_template("Hello {{missing_var}}", {"name": "Alice"})
    assert "{{missing_var}}" in result or result == "Hello {{missing_var}}"


def test_send_email_returns_true_on_success():
    with patch("app.mailer.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        result = send_email(
            to_email="test@example.com",
            subject="Hi",
            body="<p>Hello</p>",
        )
    assert result == "sent"
    mock_server.send_message.assert_called_once()


def test_send_email_returns_false_on_smtp_error():
    with patch("app.mailer.smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.side_effect = Exception("Connection refused")
        result = send_email(
            to_email="test@example.com",
            subject="Hi",
            body="<p>Hello</p>",
        )
    assert result == "failed"


def test_send_email_injects_tracking_pixel():
    """When email_id and TRACKING_BASE_URL are set, the pixel appears in the HTML part."""
    captured_msg = {}

    def fake_send_message(msg):
        captured_msg["msg"] = msg

    with patch("app.mailer.smtplib.SMTP") as mock_smtp, \
         patch("app.mailer.TRACKING_BASE_URL", "http://testserver"):
        mock_server = MagicMock()
        mock_server.send_message.side_effect = fake_send_message
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_email(
            to_email="a@b.com",
            subject="Test",
            body="<p>Body</p>",
            email_id=42,
        )

    msg = captured_msg["msg"]
    html_part = next(
        p.get_payload() for p in msg.get_payload()
        if p.get_content_type() == "text/html"
    )
    assert "track_open?email_id=42" in html_part


def test_send_email_no_pixel_without_email_id():
    """No tracking pixel appended when email_id is not provided."""
    captured_msg = {}

    def fake_send_message(msg):
        captured_msg["msg"] = msg

    with patch("app.mailer.smtplib.SMTP") as mock_smtp, \
         patch("app.mailer.TRACKING_BASE_URL", "http://testserver"):
        mock_server = MagicMock()
        mock_server.send_message.side_effect = fake_send_message
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_email(to_email="a@b.com", subject="Test", body="<p>Body</p>")

    msg = captured_msg["msg"]
    html_part = next(
        p.get_payload() for p in msg.get_payload()
        if p.get_content_type() == "text/html"
    )
    assert "track_open" not in html_part


# ─── SMTP exception branches ─────────────────────────────────────────────────

def test_send_email_returns_bounced_on_recipients_refused():
    """SMTPRecipientsRefused → 'bounced'."""
    with patch("app.mailer.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_server.send_message.side_effect = smtplib.SMTPRecipientsRefused(
            {"bad@example.com": (550, b"User unknown")}
        )
        mock_smtp.return_value.__enter__.return_value = mock_server
        result = send_email(to_email="bad@example.com", subject="Hi", body="<p>Hi</p>")
    assert result == "bounced"


def test_send_email_returns_bounced_on_5xx_data_error():
    """SMTPDataError with 5xx code → 'bounced' (permanent failure)."""
    with patch("app.mailer.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_server.send_message.side_effect = smtplib.SMTPDataError(550, b"Message rejected")
        mock_smtp.return_value.__enter__.return_value = mock_server
        result = send_email(to_email="a@b.com", subject="Hi", body="<p>Hi</p>")
    assert result == "bounced"


def test_send_email_returns_failed_on_4xx_data_error():
    """SMTPDataError with 4xx code → 'failed' (transient failure)."""
    with patch("app.mailer.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_server.send_message.side_effect = smtplib.SMTPDataError(421, b"Service unavailable")
        mock_smtp.return_value.__enter__.return_value = mock_server
        result = send_email(to_email="a@b.com", subject="Hi", body="<p>Hi</p>")
    assert result == "failed"


# ─── BCC header ──────────────────────────────────────────────────────────────

def test_send_email_sets_bcc_header():
    """When bcc_email is provided, the Bcc header is set on the outgoing message."""
    captured_msg = {}

    def fake_send_message(msg):
        captured_msg["msg"] = msg

    with patch("app.mailer.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_server.send_message.side_effect = fake_send_message
        mock_smtp.return_value.__enter__.return_value = mock_server
        send_email(
            to_email="a@b.com",
            subject="Hi",
            body="<p>Hi</p>",
            bcc_email="bcc@b.com",
        )

    assert captured_msg["msg"]["Bcc"] == "bcc@b.com"


# ─── Link rewriting ──────────────────────────────────────────────────────────

def test_send_email_rewrites_links_with_tracking():
    """href= links in the body are rewritten to /track_click when email_id is set."""
    captured_msg = {}

    def fake_send_message(msg):
        captured_msg["msg"] = msg

    with patch("app.mailer.smtplib.SMTP") as mock_smtp, \
         patch("app.mailer.TRACKING_BASE_URL", "http://testserver"):
        mock_server = MagicMock()
        mock_server.send_message.side_effect = fake_send_message
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_email(
            to_email="a@b.com",
            subject="Hi",
            body='<p><a href="http://example.com">Click</a></p>',
            email_id=99,
        )

    html_part = next(
        p.get_payload() for p in captured_msg["msg"].get_payload()
        if p.get_content_type() == "text/html"
    )
    assert "track_click?email_id=99" in html_part
    assert "http://example.com" not in html_part  # original URL replaced


def test_send_email_renders_context_placeholders():
    """When context is provided, subject and body placeholders are rendered before sending."""
    captured_msg = {}

    def fake_send_message(msg):
        captured_msg["msg"] = msg

    with patch("app.mailer.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_server.send_message.side_effect = fake_send_message
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_email(
            to_email="a@b.com",
            subject="Hello {{name}}",
            body="<p>Dear {{name}}</p>",
            context={"name": "Alice"},
        )

    msg = captured_msg["msg"]
    assert msg["Subject"] == "Hello Alice"
    html_part = next(
        p.get_payload() for p in msg.get_payload()
        if p.get_content_type() == "text/html"
    )
    assert "Dear Alice" in html_part


def test_send_email_does_not_rewrite_mailto_links():
    """mailto: links are never rewritten to tracking URLs."""
    captured_msg = {}

    def fake_send_message(msg):
        captured_msg["msg"] = msg

    with patch("app.mailer.smtplib.SMTP") as mock_smtp, \
         patch("app.mailer.TRACKING_BASE_URL", "http://testserver"):
        mock_server = MagicMock()
        mock_server.send_message.side_effect = fake_send_message
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_email(
            to_email="a@b.com",
            subject="Hi",
            body='<p><a href="mailto:contact@example.com">Email us</a></p>',
            email_id=7,
        )

    html_part = next(
        p.get_payload() for p in captured_msg["msg"].get_payload()
        if p.get_content_type() == "text/html"
    )
    assert 'href="mailto:contact@example.com"' in html_part
