"""Edge contracts around SMTPUTF8 and invalid envelope inputs."""

import asyncio
from email.message import EmailMessage

import pytest

from aiosmtplib.errors import SMTPNotSupported
from aiosmtplib.smtp import SMTP


def _message(sender="sender@example.com", recipient="recipient@example.com"):
    message = EmailMessage()
    if sender is not None:
        message["From"] = sender
    if recipient is not None:
        message["To"] = recipient
    message.set_content("body")
    return message


def test_unicode_envelope_negotiates_without_duplicating_options():
    async def scenario():
        smtp = SMTP()
        captured = {}
        smtp._ehlo_or_helo_if_needed = lambda: asyncio.sleep(0)
        smtp.supports_extension = lambda extension: extension.lower() in {
            "smtputf8",
            "8bitmime",
        }

        async def sendmail(sender, recipients, message, **kwargs):
            captured.update(
                sender=sender,
                recipients=list(recipients),
                message=message,
                options=list(kwargs["mail_options"]),
            )
            return {}, "ok"

        smtp.sendmail = sendmail
        options = ["sMtPuTf8", "body=8BITmime"]
        await smtp.send_message(
            _message("séndér@example.com", "réçipient@example.com"),
            mail_options=options,
        )

        assert captured["sender"] == "séndér@example.com"
        assert captured["recipients"] == ["réçipient@example.com"]
        assert captured["options"] == options
        assert b"s\xc3\xa9nd\xc3\xa9r@example.com" in captured["message"]
        assert options == ["sMtPuTf8", "body=8BITmime"]

    asyncio.run(scenario())


def test_unicode_envelope_requires_smtputf8_support():
    async def scenario():
        smtp = SMTP()
        smtp._ehlo_or_helo_if_needed = lambda: asyncio.sleep(0)
        smtp.supports_extension = lambda _extension: False
        with pytest.raises(SMTPNotSupported):
            await smtp.send_message(
                _message("séndér@example.com", "recipient@example.com")
            )

    asyncio.run(scenario())


def test_explicit_smtputf8_does_not_change_ascii_envelope_serialization_policy():
    async def scenario():
        smtp = SMTP()
        captured = {}
        smtp._ehlo_or_helo_if_needed = lambda: asyncio.sleep(0)
        smtp.supports_extension = lambda _extension: False

        async def sendmail(_sender, _recipients, message, **kwargs):
            captured["message"] = message
            captured["options"] = list(kwargs["mail_options"])
            return {}, "ok"

        smtp.sendmail = sendmail
        message = _message("Séndér <sender@example.com>")
        message["Subject"] = "Résumé"
        options = ["SMTPUTF8"]

        await smtp.send_message(message, mail_options=options)

        assert captured["options"] == ["SMTPUTF8"]
        assert b"From: =?utf-8?" in captured["message"]
        assert b"Subject: =?utf-8?" in captured["message"]
        assert b"S\xc3\xa9nd\xc3\xa9r" not in captured["message"]
        assert b"R\xc3\xa9sum\xc3\xa9" not in captured["message"]
        assert options == ["SMTPUTF8"]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("message", "error"),
    [
        (_message(sender=None), "No From header"),
        (_message(recipient=None), "No recipient headers"),
    ],
)
def test_invalid_envelopes_fail_before_network_negotiation(message, error):
    async def scenario():
        smtp = SMTP()
        called = False

        async def handshake():
            nonlocal called
            called = True

        smtp._ehlo_or_helo_if_needed = handshake
        with pytest.raises(ValueError, match=error):
            await smtp.send_message(message)
        assert not called

    asyncio.run(scenario())


def test_explicit_recipient_string_is_one_envelope_address():
    async def scenario():
        smtp = SMTP()
        captured = {}
        smtp._ehlo_or_helo_if_needed = lambda: asyncio.sleep(0)
        smtp.supports_extension = lambda _extension: False

        async def sendmail(_sender, recipients, _message, **_kwargs):
            captured["recipients"] = list(recipients)
            return {}, "ok"

        smtp.sendmail = sendmail
        await smtp.send_message(_message(), recipients="one@example.com")
        assert captured["recipients"] == ["one@example.com"]

    asyncio.run(scenario())
