# Package Tracker

Self-hosted app that scans your Gmail for shipment tracking numbers, plots each
package on a world map at its last known scan location, refreshes tracking
data on a schedule, and notifies Discord when something is delivered.

## Quick start (Docker Desktop)

1. Copy `.env.example` to `.env` and fill in `SECRET_KEY` (e.g. `openssl rand -hex 32`)
   and a `POSTGRES_PASSWORD`. Leave the rest at their defaults unless you're
   changing the port.
2. Run:
   ```bash
   docker compose up --build
   ```
3. Open http://localhost:8080 — the first visit prompts you to create the
   admin account (username + password). There's no separate sign-up flow:
   whoever completes this first-run screen is the one account, and it's
   permanently disabled afterward. Log back in with the same credentials on
   later visits; change the password anytime from **Settings → Account**.

The map and manual "add tracking number" flow work immediately once you're
logged in. The rest needs one-time setup, all walked through inside the
app's **Settings** page, which is organized into three tabs:

- **General** — scan intervals, light/dark/system theme toggle, last-run status.
- **Connections** — step-by-step setup wizards for Gmail and each carrier.
  Each one collapses to a ✅/❌ status badge once configured; click
  **Reconfigure** to re-run the wizard and enter new credentials, or
  **Remove connection** to clear one out entirely. A **Test connection**
  button on each checks the credentials actually work without waiting for
  the next scheduled run.
- **Account** — change your password, or log out.

### Connections tab, in detail

- **Carrier tracking** — each carrier's official free developer API is
  called directly (no third-party tracking aggregator, no TrackingMore).
  Register a free developer app with whichever carriers you actually ship
  with and paste the credentials in:
  - **UPS** — [developer.ups.com](https://developer.ups.com/) → Client ID + Client secret (OAuth2)
  - **FedEx** — [developer.fedex.com](https://developer.fedex.com/) → API key + Secret key (OAuth2)
  - **USPS** — [developers.usps.com](https://developers.usps.com/) → Consumer key + Consumer secret (OAuth2)
  - **DHL** — [developer.dhl.com](https://developer.dhl.com/) → API key

  Packages from a carrier you haven't configured just won't refresh — the
  rest of the app still works.
- **Gmail** — connects over IMAP with a Gmail App Password (Settings walks
  through generating one at myaccount.google.com/apppasswords). No Google
  Cloud project, no OAuth consent screen, and no expiry timer.
- **Discord** — paste an incoming webhook URL (Server Settings → Integrations
  → Webhooks) and use "Send test notification" to confirm it works.

## Deploying via Portainer

Portainer can deploy this stack straight from GitHub — no local clone needed.

1. In Portainer: **Stacks → Add stack**.
2. Name it (e.g. `package-tracker`).
3. Build method: **Repository**.
   - Repository URL: `https://github.com/tet0r/package-tracker`
   - Repository reference: `main`
   - Compose path: `docker-compose.yml` (default)
4. Under **Environment variables**, add:

   | Variable | Value |
   |---|---|
   | `SECRET_KEY` | a long random string, e.g. the output of `openssl rand -hex 32` |
   | `POSTGRES_PASSWORD` | any password |
   | `HOST_PORT` | port to expose the app on (default `8080`) |
   | `NOMINATIM_USER_AGENT` | optional — identifies your instance to the free geocoding API per its usage policy |

   There's no `.env` file in the repo (it's gitignored on purpose, so secrets
   never get committed) — these stack environment variables are how you
   supply the same values `.env.example` documents for the Docker Desktop
   path above.
5. **Deploy the stack**.
6. Once the containers are healthy, open `http://<your-portainer-host>:<HOST_PORT>`
   and complete the first-run admin account setup described above.

To pick up later changes, use Portainer's **Pull and redeploy** on the stack
— it re-clones the repo and rebuilds the images.

## Known limitations

- **Single-user, cookie-based sessions over plain HTTP by default**: the app
  supports exactly one account (created on first run; sign-ups are disabled
  after that). Sessions are an httpOnly cookie, which is fine on localhost or
  a trusted home network, but if you expose this beyond that (a reverse proxy
  to the internet, for example), put HTTPS in front of it — the cookie isn't
  marked `Secure` since that would break plain-HTTP localhost access.
- **Why not scraping / a tracking aggregator**: UPS, FedEx, and USPS all run
  bot-detection (Akamai and similar) on their public tracking pages that
  blocks automated access outright — confirmed by testing directly before
  building this. TrackingMore-style aggregators work around that by using
  these same official carrier APIs on your behalf; this app just calls them
  directly instead, at the cost of registering with each carrier separately.
- **Amazon Logistics**: packages delivered by Amazon's own last-mile network
  (not handed off to UPS/USPS/FedEx) have no public tracking API without
  logging into your Amazon account, which this app doesn't do. Amazon orders
  that do get a real carrier tracking number (common for UPS/USPS/FedEx
  handoffs) are picked up normally by the email scanner.
- **Why IMAP + App Password instead of OAuth**: Gmail's `gmail.readonly`
  OAuth scope is "restricted," and Google requires a paid third-party CASA
  security audit before an app using it can leave "Testing" publishing
  status — in Testing, refresh tokens expire every 7 days. That's not
  practical for a personal single-user app, so this app authenticates over
  IMAP with a Gmail App Password instead, which has no such expiry. If the
  app password is revoked or wrong, Settings shows the last error (and pings
  Discord, if configured) rather than silently failing.
- **Carrier API field mapping**: the parsing in
  `backend/app/services/carriers/{ups,fedex,usps,dhl}.py` follows each
  carrier's publicly documented response schema and has been smoke-tested
  against mocked responses matching those docs, but hasn't been run against
  a real live response yet (a free developer account is needed to get one).
  If a real response differs, these are the files to adjust.
- **Geocoding**: location strings from carrier scans are geocoded via the
  free OpenStreetMap Nominatim API and cached in the database, respecting its
  ~1 req/sec usage policy — city-level accuracy, not precise addresses.
- **Map tiles**: pulled live from OpenStreetMap over the internet; the app
  isn't usable fully offline.

## Architecture

- `backend/` — FastAPI + SQLAlchemy + Postgres. Owns Gmail IMAP scanning,
  direct carrier API polling, geocoding, Discord notifications, single-user
  auth (bcrypt password hashing + DB-backed session cookies), and the REST
  API. Two background loops (email scan, tracking refresh) run in-process
  and re-read their configured intervals every minute, so interval changes
  in Settings take effect without a restart.
- `frontend/` — React + Vite + Leaflet, built and served by nginx, which also
  reverse-proxies `/api` to the backend container.

## Manual triggers

Useful before Gmail/carrier credentials are configured, or any time: the map page
has "Scan emails now" and "Refresh tracking now" buttons that run the
background jobs immediately.
