# tests/test_mailer.py — mailer unit tests

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
