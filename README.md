# Coderr API

Coderr is a standalone Django REST Framework backend for a service marketplace. Business accounts publish three-tier offers; customers place orders and review businesses. Orders retain the purchased service data when an offer changes or is deleted.

Entwickelt im Rahmen des Weiterbildungsprogramms der Developer Akademie GmbH.

This repository contains the independently implemented backend only. The supplied frontend is maintained separately in a private repository and retains its original learning license. No production deployment is included.

## Features

- Registration, password hashing and DRF token authentication.
- Customer and business profiles with owner-only updates and image uploads.
- Offers with exactly three tiers: `basic`, `standard`, `premium`.
- Public offer listing with search, filters and six-item pagination.
- Customer orders with immutable service snapshots and business-controlled status.
- One review per customer/business pair, enforced in the database.
- Public platform statistics, searchable Django administration and committed migrations.
- Explicit role/object permissions and atomic multi-record writes.

## Technology and layout

Python 3.12+, Django 6.0, Django REST Framework, SQLite, django-cors-headers and Pillow. Gunicorn serves the container; Ruff checks formatting and imports. SQLite is suitable for this single-instance learning project; use a separate database design and migration plan before scaling across multiple backend replicas.

```text
core/                   Settings, central routing, common validation
users_app/              Accounts, profiles, authentication, demo command
  api/                  Serializers, permissions, views and routes
offers_app/             Offers, tiers, transactional service functions
  api/                  Read/write representations, filters and pagination
orders_app/             Persistent purchased-service snapshots
  api/                  Personal lists, creation, status and counts
reviews_app/            Unique customer reviews
  api/                  Review endpoints and platform statistics
tests/                  Contract, permission, integrity and upload tests
tools/                  Convention checker and isolated HTTP smoke test
.github/workflows/      Checks, multi-platform build and automatic GHCR publish
```

Models describe data and constraints. Multi-record writes live in service functions. Each application owns its API routes, serializers and permissions. Serializers explicitly list fields. Generated migrations are committed.

## Install and start

You need Python 3.12 or newer with `venv`, pip and SQLite support. On Linux, install your distribution's Python venv package if `python3 -m venv` is unavailable. Dependency installation requires access to a package index or a suitable local wheel mirror.

```bash
git clone git@github.com:RiGaHo/coderr-backend.git
cd coderr-backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Use `requirements.txt` if development tools are unnecessary. The API is under `http://127.0.0.1:8000/api/`; administration is at `/admin/`. Create ordinary application accounts through registration. Admin-created users receive a customer profile automatically; administrators can assign the business role in the profile administration.

No demo accounts are created by migrations, server startup, Docker or CI. To enable the original frontend's **local-only** guest logins explicitly:

```bash
python manage.py seed_demo --allow-insecure-demo
```

This creates `andrey` / `asdasd` (customer) and `kevin` / `asdasd24` (business), with `example.invalid` email addresses. These intentionally public, weak demonstration credentials are not personal credentials. The command requires `DEBUG=true`, refuses existing usernames, changes no existing accounts, and is transactional. Never expose these accounts on a public instance. It creates no offers, orders or reviews.

## Configuration

Settings read exported environment variables. `.env.example` documents examples; Django does **not** automatically load `.env` files. Never commit a real `.env`, database, token, media upload or secret.

| Variable | Development default | Purpose |
| --- | --- | --- |
| `DJANGO_DEBUG` | `true` | Use `false` outside local development |
| `DJANGO_SECRET_KEY` | Public development-only key | Required unpredictable secret when DEBUG is false |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Comma-separated accepted hostnames |
| `DJANGO_DB_PATH` | `db.sqlite3` in project root | SQLite database path |
| `DJANGO_MEDIA_ROOT` | `media/` | Uploaded image storage |
| `DJANGO_STATIC_ROOT` | `staticfiles/` | Collected Django admin assets |
| `CORS_ALLOWED_ORIGINS` | localhost and 127.0.0.1 on ports 5500 and 8080 | Explicit frontend origins |
| `CSRF_TRUSTED_ORIGINS` | Empty | HTTPS origins used for admin requests behind a proxy |
| `DJANGO_TRUST_PROXY` | `false` | Trust `X-Forwarded-Proto` only from a controlled proxy |

With DEBUG disabled, HTTPS redirects, secure session/CSRF cookies and HSTS are enabled. `DJANGO_TRUST_PROXY=true` is appropriate only when an isolated, trusted reverse proxy replaces forwarded headers and the backend cannot be reached directly by untrusted clients. Configure the proxy to forward the public host and actual HTTPS scheme. Do not enable this merely to silence an HTTPS redirect problem.

API tokens do not need CSRF cookies; the admin uses normal Django session authentication and CSRF protection. Same-origin production requests do not require cross-origin CORS permission. CORS does not replace authorization.

## Authentication and roles

Send JSON unless uploading images. Protected requests require:

```http
Authorization: Token YOUR_TOKEN
```

Registration and login return `token`, `username`, `email` and integer `user_id`. Tokens persist until administratively revoked. The original frontend stores its token in browser localStorage; logout removes that browser copy and does not revoke the server-side token. To revoke a token, delete it in Django's token administration. Inactive users cannot authenticate.

Registration requires unique username and case-insensitively unique email, matching `password` and `repeated_password`, and `type` equal to `customer` or `business`. Django password validation applies. API registration cannot grant admin/staff rights. Profile PATCH cannot change role, username or identity.

| Resource | Read | Create | Update/delete |
| --- | --- | --- | --- |
| Profiles | Authenticated | Created with account | Own profile PATCH only |
| Offer list | Public | Business accounts | Owner PATCH/DELETE |
| Offer/tier detail | Authenticated | Part of an offer | Tiers updated through parent offer |
| Orders | Customer or business party only | Customers | Assigned business changes status only; no DELETE |
| Reviews | Authenticated | Customers, valid business target | Author PATCH/DELETE |
| Order counts | Authenticated | — | — |
| Base statistics | Public | — | — |

## API reference

All paths below are relative to `/api/` and include trailing slashes. The implementation provides the 22 documented operations; unsupported operations return 405.

| Path | Methods | Request / result |
| --- | --- | --- |
| `registration/` | POST | username, email, password, repeated_password, type → authentication payload (201) |
| `login/` | POST | username, password → authentication payload (200) |
| `profile/{user_id}/` | GET, PATCH | Full profile; own editable fields only |
| `profiles/business/` | GET | Unpaginated business profile array |
| `profiles/customer/` | GET | Unpaginated customer profile array |
| `offers/` | GET, POST | Paginated references / create offer with three full tiers |
| `offers/{id}/` | GET, PATCH, DELETE | Detail references / partial updates / empty 204 |
| `offerdetails/{id}/` | GET | Complete individual tier |
| `orders/` | GET, POST | Own order array / create from offer_detail_id |
| `orders/{id}/` | PATCH | status only |
| `order-count/{business_user_id}/` | GET | Number of in_progress orders |
| `completed-order-count/{business_user_id}/` | GET | Number of completed orders |
| `reviews/` | GET, POST | Filtered review array / create a review |
| `reviews/{id}/` | PATCH, DELETE | rating and description only / empty 204 |
| `base-info/` | GET | review_count, average_rating, business_profile_count, offer_count |

### Registration and login

```bash
curl http://127.0.0.1:8000/api/registration/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","email":"alice@example.invalid","password":"ExampleStrongPassword42!","repeated_password":"ExampleStrongPassword42!","type":"customer"}'

curl http://127.0.0.1:8000/api/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"ExampleStrongPassword42!"}'
```

Example successful response (token and ID are illustrative):

```json
{"token":"YOUR_TOKEN","username":"alice","email":"alice@example.invalid","user_id":1}
```

### Profiles and media

A profile response includes `user` (account ID), `username`, `first_name`, `last_name`, `file`, `location`, `tel`, `description`, `working_hours`, `type`, `email`, `created_at` and `uploaded_at`. Unset text fields are empty strings; images and an unset upload timestamp may be null. Directory responses omit email; a single authenticated profile response includes it, as required by the API contract.

PATCH accepts first/last name, email, location, tel, description, working_hours and file. Other fields are protected. Null text inputs are rejected rather than stored as null. Both JSON field edits and multipart image uploads are supported.

```bash
curl -X PATCH http://127.0.0.1:8000/api/profile/1/ \
  -H 'Authorization: Token YOUR_TOKEN' \
  -F 'first_name=Alice' -F 'file=@/path/to/profile.png'
```

Uploads must decode as JPEG, PNG or WebP, must not exceed 5 MiB, and must not exceed 20 megapixels. Image URLs point to `/media/` on the request origin. Development Django serves media with DEBUG=true; production must serve it through the web server. Media URLs are public and must not contain confidential images. Replaced or deleted model references do not automatically delete stored files; use an administrator-controlled cleanup/retention policy. Back up database and media together.

### Offers

Create an offer with `title`, `description`, optional `image` and three complete `details`, one for each tier. A tier contains `title`, `revisions`, `delivery_time_in_days`, numeric `price`, a nonempty string-array `features` and `offer_type`. Prices are stored as Decimal and returned as JSON numbers. Delivery is a positive integer; revisions are nonnegative or `-1` for unlimited revisions, matching the supplied frontend.

```json
{
  "title": "Website design",
  "description": "Three service options",
  "image": null,
  "details": [
    {"title":"Basic","revisions":1,"delivery_time_in_days":3,"price":100,"features":["Landing page"],"offer_type":"basic"},
    {"title":"Standard","revisions":3,"delivery_time_in_days":5,"price":200,"features":["Three pages"],"offer_type":"standard"},
    {"title":"Premium","revisions":-1,"delivery_time_in_days":7,"price":500,"features":["Full website"],"offer_type":"premium"}
  ]
}
```

POST/PATCH responses contain `id`, `title`, `image`, `description` and complete tier objects with IDs. GET responses additionally include owner/timestamps, aggregate `min_price` and `min_delivery_time`, and tier references such as `{"id":1,"url":"http://127.0.0.1:8000/api/offerdetails/1/"}`. Lists also include `user_details` with first_name, last_name and username. URLs are derived from the current request, not hard-coded to localhost.

PATCH identifies each submitted tier by `offer_type`; unchanged tiers/fields and IDs remain intact. Echoed tier IDs from the original frontend are accepted but cannot modify identity. All tiers are validated before any write. The complete mutation is atomic. Example: `{"details":[{"offer_type":"basic","price":120}]}`.

The original frontend creates offers as JSON and uploads `image` with a separate multipart PATCH. A single multipart POST with JSON-encoded `details` also works.

### Filters and pagination

`GET offers/` returns `count`, `next`, `previous` and `results`. The default page size is 6, matching the frontend. `page_size` accepts 1–100; `page` selects the page.

| Parameter | Meaning |
| --- | --- |
| `creator_id` | Offer owner's account ID |
| `min_price` | Lower bound on the offer's minimum tier price |
| `max_delivery_time` | Upper bound on its minimum tier delivery time |
| `ordering` | updated_at, -updated_at, min_price, -min_price |
| `search` | Case-insensitive substring in title or description |

Empty filter controls are ignored because the original frontend sends them. Invalid nonempty parameters return 400. Invalid pages use DRF's 404 behavior. Ordering has an ID tie-breaker for stable pagination. Reviews support `business_user_id`, `reviewer_id` and ordering by `updated_at`, `-updated_at`, `rating` or `-rating`; reviews and profile/order lists are unpaginated.

### Orders and reviews

Create an order with `{"offer_detail_id":1}`. The server selects both parties and snapshots title, revisions, delivery time, price, features and offer type. Order responses contain those fields plus `id`, `customer_user`, `business_user`, `status`, `created_at` and `updated_at`. Status can be `in_progress`, `completed` or `cancelled`; only the assigned business can change it. Other writes are rejected. Unrelated users cannot list or address another order (404); its customer cannot change its status (403).

`order-count` returns `{"order_count":1}`. `completed-order-count` returns both `{"completed_order_count":1,"order_count":1}` because the original frontend consumes both names. Cancelled orders count toward neither endpoint. Missing or non-business targets return 404.

Create a review with `{"business_user":2,"rating":4,"description":"Good service"}`. Ratings are integers 1–5. A unique database constraint prevents duplicate reviewer/business pairs, including concurrent submissions. Duplicate reviews consistently return 400 (the source documentation lists both 400 and 403). Review responses include immutable reviewer/business IDs, rating, description and timestamps. PATCH accepts only rating and description.

Public statistics use stored records and return numeric counts plus a mean rounded to one decimal (0.0 when there are no reviews).

### Error behavior

Successful reads/updates return 200, creates 201, deletes empty 204. Validation returns 400 with field or non_field_errors details. Invalid login credentials return 400. Missing/invalid tokens return 401 with a Token challenge. Role/ownership violations return 403, except unrelated orders are concealed as 404. Missing objects return 404. Unexpected infrastructure failures are not presented as successful API operations.

## Verification

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test tests --settings=tests.settings
ruff check .
ruff format --check .
python tools/check_conventions.py
python tools/http_smoke.py
```

The test-only settings use a fast password hasher for isolated test databases. Never use `tests.settings` to serve the application. Run `python manage.py test tests` to use the normal configured password hasher instead.

Tests check contract keys/values, permissions, malformed input, database uniqueness, transaction rollback, stable tier IDs, snapshots, pagination, real image decoding, admin access, CORS and safe demo initialization. The convention checker counts the full physical function span, including docstrings and blank lines: at most 14 lines per handwritten function/method. It excludes generated migrations and third-party packages. Declarative Meta classes need no redundant docstring. Ruff handles imports, formatting and basic linting; responsibilities and commented-out code require review.

The HTTP smoke tool migrates a temporary database, launches an actual loopback server, exercises workflows using HTTP requests, stops the process and removes its temporary data. It requires permission to create sockets. An environment denying sockets will fail explicitly, not simulate a pass. No existing data or server is needed.

Optional coverage: `coverage run manage.py test tests --settings=tests.settings`, then `coverage report`. Local coverage does not establish the external PM-test requirement. External PM tests are not supplied here and are not claimed to have passed.

## Docker and persistence

```bash
docker build -t coderr-backend:local .
docker volume create coderr-data
docker run --rm --name backend \
  --network web-stack-proxy --network-alias backend \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=128m \
  --cap-drop ALL --security-opt no-new-privileges \
  -p 127.0.0.1:8000:8000 -v coderr-data:/data \
  -e DJANGO_DEBUG=true -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
  coderr-backend:local
```

This command is a local HTTP example and assumes the existing `web-stack-proxy` network. For production, use DEBUG=false, provide a real secret through the deployment's secret mechanism, configure allowed hosts/CSRF origins, and terminate HTTPS at a trusted proxy. Do not expose the backend port publicly. The image runs as UID/GID 10001, not root. Ensure bind-mounted data is writable by that identity; a newly created named volume can inherit the image directory ownership. Keep `/data` persistent and `/tmp` writable while the root filesystem remains read-only.

The entrypoint applies migrations and collects admin static files; it does not create admin/demo accounts. `/data/db.sqlite3`, `/data/media` and `/data/static` survive image replacement. Do not run simultaneous migration entrypoints against one SQLite file. Back up the database consistently and include media. Serve media/static from read-only mounts in the frontend web server. Mount no Docker socket or unrelated host paths. No privileged mode or additional Linux capabilities are required.

The private frontend image provides Nginx on port 8080, routes `/api/` to a network service named `backend:8000`, and expects media/static read-only mounts. Public `/admin` and `/admin/` access is blocked; keep Django administration internal and do not expose an alternative admin route through Traefik. Production routing is frontend `/`, API `/api/`, images `/media/`. The deployment uses only the existing Docker network `web-stack-proxy`; attach the backend with network alias `backend` and the frontend to the same network. Do not create another application network. The intended domain is `coderr.skullrabbit.dev`; configure `DJANGO_ALLOWED_HOSTS=coderr.skullrabbit.dev` and the corresponding HTTPS CSRF origin for deployment. Keep private host-specific OMV Compose, Traefik, tunnel and network definitions outside this public repository. Deployment on the Raspberry Pi 5/OMV, Cloudflare, DNS and public HTTPS verification are separate work.

## GitHub Actions and GHCR

`ci.yml` runs the existing checks once on pushes to `main` and pull requests. After the test job succeeds, a push to `main` automatically builds `linux/amd64` and `linux/arm64` and publishes `ghcr.io/rigaho/coderr-backend:latest` and `sha-<full commit SHA>`. Pull requests only build, without publishing. The former manual `publish.yml` is consolidated into `ci.yml`; no separate publish trigger or duplicate test run is needed. Only the publish job has packages:write, using GITHUB_TOKEN; all jobs have contents:read.

Configuration does not prove a successful remote run. Check Actions for the exact commit and inspect the GHCR manifests after the later push. The separate frontend workflow requires a private source repository, rejects an existing non-private package before uploading, permits a missing package to be created, and verifies package privacy afterward. GHCR creates new packages private by default ([GitHub documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)). Existing packages must grant their workflow repository access; no personal token is embedded.

## Limits and release checks

- Local code/tests do not establish a production deployment, legal compliance or an external PM-test result.
- Complete real contact, privacy, retention, hosting and licensing decisions before public frontend use.
- The original frontend renders API data in HTML templates; its unchanged rendering code is outside this backend's HTML-escaping guarantees. Use trusted synthetic content for the local demonstration and review client-side output encoding before any public deployment.
- No automatic account deletion, token expiry, media garbage collection or email delivery is implemented; these are not documented API operations.
- Request/media logging and backups need deployment-specific retention policies. Do not log tokens or passwords.
- CI, Docker, remote visibility and actual published images must be checked in an environment with those capabilities.

## License and provenance

The independently written backend is released under the MIT License; see LICENSE. Django, DRF, Pillow, Gunicorn and other dependencies retain their own licenses. The Developer Akademie learning license applies to the separately supplied frontend and its assets, not to these independent backend sources. The original API specification and checklist are review inputs and are deliberately not redistributed in this public repository. The frontend's license notices, portfolio conditions and duration restrictions remain unchanged.
