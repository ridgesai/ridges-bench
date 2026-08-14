"""Direct configuration and message-envelope contracts for SMTP."""

import asyncio
from email.message import EmailMessage

from aiosmtplib.smtp import SMTP


def test_configuration_updates_preserve_both_sentinel_conventions():
    smtp = SMTP(
        hostname="smtp.example",
        port=2525,
        username="alice",
        password="secret",
        local_hostname="client.example",
        source_address=("127.0.0.1", 0),
        use_tls=False,
        start_tls=True,
        validate_certs=False,
        client_cert="client.pem",
        client_key="client.key",
        cert_bundle="ca.pem",
    )
    # Keep construction valid, then seed the private update state directly.
    smtp.socket_path = "/tmp/old.sock"
    smtp._update_settings_from_kwargs(
        hostname=None,
        port=None,
        username=None,
        password=None,
        local_hostname=None,
        source_address=None,
        use_tls=None,
        start_tls=None,
        validate_certs=None,
        client_cert=None,
        client_key=None,
        cert_bundle=None,
        socket_path=None,
    )

    assert smtp.hostname is None
    assert smtp.port is None
    assert smtp._login_username is None
    assert smtp._login_password is None
    assert smtp.local_hostname is None
    assert smtp.source_address is None
    assert smtp._start_tls_on_connect is None
    assert smtp.client_cert is None
    assert smtp.client_key is None
    assert smtp.cert_bundle is None
    assert smtp.socket_path is None
    assert smtp.use_tls is False, "None must leave use_tls unchanged"
    assert smtp.validate_certs is False, "None must leave validation unchanged"

    snapshot = dict(smtp.__dict__)
    smtp._update_settings_from_kwargs()
    assert smtp.__dict__ == snapshot, "omitted settings must remain untouched"


def test_header_envelope_bcc_and_transport_options_are_preserved():
    async def scenario():
        smtp = SMTP()
        captured = {}

        async def handshake():
            captured["handshake"] = True

        async def sendmail(
            sender,
            recipients,
            message,
            *,
            mail_options,
            rcpt_options,
            timeout,
        ):
            captured.update(
                sender=sender,
                recipients=list(recipients),
                message=message,
                mail_options=list(mail_options),
                rcpt_options=rcpt_options,
                timeout=timeout,
            )
            return {"refused@example": object()}, "queued"

        smtp._ehlo_or_helo_if_needed = handshake
        smtp.supports_extension = lambda extension: extension.lower() == "8bitmime"
        smtp.sendmail = sendmail

        message = EmailMessage()
        message["From"] = "Alice <alice@example.com>"
        message["To"] = "to@example.com"
        message["Cc"] = "cc@example.com"
        message["Bcc"] = "blind@example.com"
        message.set_content("hello")
        mail_options = ["SIZE=123"]
        rcpt_options = ("NOTIFY=SUCCESS",)

        result = await smtp.send_message(
            message,
            mail_options=mail_options,
            rcpt_options=rcpt_options,
            timeout=4.25,
        )

        assert result[1] == "queued"
        assert captured["sender"] == "alice@example.com"
        assert captured["recipients"] == [
            "to@example.com",
            "cc@example.com",
            "blind@example.com",
        ]
        assert b"Bcc:" not in captured["message"]
        assert message["Bcc"] == "blind@example.com"
        assert captured["mail_options"] == ["SIZE=123", "BODY=8BITMIME"]
        assert captured["rcpt_options"] is rcpt_options
        assert captured["timeout"] == 4.25
        assert mail_options == ["SIZE=123"], "caller-owned options were mutated"

    asyncio.run(scenario())
