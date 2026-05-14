# Viber Bot Onboarding Runbook

Last updated: 2026-05-07

Source: [Viber REST Bot API](https://developers.viber.com/docs/api/rest-bot-api/)

## Preconditions

- Active Viber bot account. Viber's current docs say bots are created on commercial terms.
- Bot authentication token from Viber Admin Panel or the bot edit screen.
- Public backend URL with valid HTTPS certificate from a trusted CA.
- Local `.env` contains secrets; never put Viber tokens in Git.

The webhook URL must be public HTTPS. Viber will reject localhost, self-signed
certificates and webhook URLs that do not answer with HTTP 200.

## Local Environment

```text
NOTIFICATION_PROVIDER=viber
VIBER_AUTH_TOKEN=
VIBER_REVIEWER_IDS=
VIBER_SENDER_NAME=AI Content Factory
VIBER_WEBHOOK_PUBLIC_URL=https://your-public-domain.example/api/webhooks/viber
VIBER_WEBHOOK_EVENT_TYPES=message,conversation_started,subscribed,unsubscribed,failed
VIBER_WEBHOOK_SECRET_REQUIRED=true
OPERATOR_CONSOLE_URL=https://your-public-console.example
```

Keep `VIBER_WEBHOOK_SECRET_REQUIRED=false` only while doing local unsigned webhook
simulation. For a real webhook it should be `true`.

## Set Webhook

Preview the payload without calling Viber:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli viber-webhook-payload
```

Or with an explicit URL:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli viber-webhook-payload --url https://your-public-domain.example/api/webhooks/viber
```

Register the webhook with Viber:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli viber-set-webhook --confirm-real-call
```

The command refuses to call Viber unless `--confirm-real-call` is passed.

## Onboard Reviewers

1. Open the bot on a phone with Viber.
2. Send any text message to the bot. This subscribes the user and gives Viber
   permission to receive bot messages.
3. Inspect the callback payload on the backend and copy `sender.id`.
4. Add that value to `VIBER_REVIEWER_IDS`, comma-separated for multiple reviewers.
5. Restart the backend after changing `.env`.

Viber can send messages only to users who subscribed or initiated conversation with
the bot. Phone numbers alone are not enough for the normal Bot API.

## Approval Test

1. Create and enqueue a content task.
2. Wait until it reaches `waiting_approval`.
3. Click `Notify review` in the operator console or call:

```text
POST /api/tasks/{task_id}/notify-approval
```

The reviewer receives a Viber message with:

- `approve:{task_id}`
- `rewrite:{task_id}`
- operator console link

Viber callbacks arrive at:

```text
POST /api/webhooks/viber
```

The backend verifies `X-Viber-Content-Signature` when
`VIBER_WEBHOOK_SECRET_REQUIRED=true`.

## Remove Webhook

Use this only when you intentionally want to disable the bot's one-on-one webhook:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli viber-remove-webhook --confirm-real-call
```

## Troubleshooting

- `invalidUrl`: webhook URL is not public HTTPS, certificate is invalid, or backend
  does not return HTTP 200 to Viber's `webhook` callback.
- `missing_auth_token`: `VIBER_AUTH_TOKEN` is absent from the request header.
- `invalidAuthToken`: rotate or re-copy the token from the Viber bot settings.
- Send failure for a reviewer: the user has not subscribed, blocked the bot, or
  `VIBER_REVIEWER_IDS` contains the wrong `sender.id`.
