# Vastra — Customer Storefront

A clean, customer-only Django storefront for the Vastra boutique. Visitors can
browse the one-page catalogue, create their own account, sign in and add pieces
to a personal cart. All customer data lives in dedicated database tables,
completely separate from Django's staff/admin users.

Visual theme: blush pink, ivory and crimson — a modern, responsive take on
traditional Indian boutique elegance.

---

## 1. What the app does

| Area | Implementation |
|---|---|
| Public storefront | One-page Vastra site at `/`: header with search, editorial banner, category arches, product grid, cart drawer and contact footer |
| Customer accounts | Sign up with **username, phone number, password and address**; passwords are hashed with Django's PBKDF2 hasher |
| Sign in / sign out | Separate customer login at `/login/`; successful sign-in returns to the storefront; POST-only sign-out |
| Personal cart | Add/remove dresses from `/cart/add/<id>/` and `/cart/remove/<id>/`; each customer sees only their own cart, stored in the database |
| Catalogue management | Dresses are maintained by staff in the Django admin at `/admin/` |

Removed from the application: the staff dashboard, dress/customers/bookings/
bills/staff pages and their routes, role-based access, booking/payment/billing
logic, custom JSON APIs and the first-login profile flow.

---

## 2. Technology stack

- **Backend:** Python 3.11+, Django 5.2
- **Database:** SQLite for local development; MySQL 8 (production) via `mysqlclient`
- **Frontend:** HTML5, CSS3 (custom theme, no CDN dependencies), vanilla JavaScript
- **Images:** Pillow (Django `ImageField`)

---

## 3. Quick start (local development)

This project already has a virtual environment in the `venv\` folder. Use that
same folder everywhere (terminal, VS Code and scripts) so you never mix system
and project packages.

```powershell
# 1. Activate the project virtual environment
.\venv\Scripts\Activate.ps1

# 2. Install dependencies (only needed the first time or after changing requirements.txt)
python -m pip install -r requirements.txt

# 3. Apply migrations (uses local SQLite by default)
python manage.py migrate

# 4. Optional: load demo dresses on a fresh database
python manage.py seed_demo

# 5. Create a staff/admin user only if you need /admin/
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver
```

If Activation is blocked by PowerShell execution policy, run this once first:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Alternatively, skip activation and call the environment Python directly:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```

To regenerate the documentation screenshots (optional), install the dev tooling
and run the capture script:

```powershell
python -m pip install -r requirements-dev.txt
python scripts/capture_screenshots.py
```

Open <http://localhost:8000/> for the storefront.

- **Sign up:** <http://localhost:8000/signup/> — enter a username, phone number,
  password and address. After creating the account you are returned to the
  sign-in page; there is no automatic login.
- **Sign in:** <http://localhost:8000/login/> — use your username and password.
  Signing in takes you to the home page, where you can add items to your cart.
- **Cart:** open it from the header button. Products are added with normal form
  POSTs, and your cart is saved against your account in the database.
- **Admin:** <http://localhost:8000/admin/> — for catalogue maintenance only.

### VS Code setup

The repository ships ready-to-use VS Code configuration in `.vscode/`:

| File | Purpose |
|---|---|
| `settings.json` | Selects `${workspaceFolder}/venv/Scripts/python.exe` as the interpreter, enables terminal activation and hides cache/media files from search |
| `launch.json` | Debug configurations: **Vastra: Runserver**, **Vastra: Tests** and **Vastra: Migrate** |
| `tasks.json` | Terminal tasks: install dependencies, migrate, check, test and runserver |

Steps:

1. Open the **project folder** in VS Code:
   `C:\Users\chand\OneDrive\Documents\Default Project\yuga_vastra`.
2. Install the **Python** (`ms-python.python`) and **Django** (`batisteo.vscode-django`)
   extensions when VS Code prompts you.
3. Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> → **Python: Select Interpreter**
   → choose `.\venv\Scripts\python.exe`. The workspace setting already points
   here; this confirms VS Code picked it up.
4. Open a new integrated terminal (<kbd>Ctrl</kbd>+<kbd>`</kbd>). It should show
   `(venv)` at the prompt. If not, run `.\venv\Scripts\Activate.ps1` manually.
5. Run the site in either of these ways:
   - **Debug tab:** choose **Vastra: Runserver**, then press <kbd>F5</kbd>.
   - **Terminal:** `python manage.py runserver 127.0.0.1:8000 --noreload`.
6. Open <http://localhost:8000/> in your browser. For the admin, use
   <http://localhost:8000/admin/>.

Useful commands from the activated terminal:

```powershell
python manage.py check                 # verify settings
python manage.py test boutique -v 2    # run the 25 tests
python manage.py migrate               # apply migrations
```

You can also run these from **Terminal → Run Task…** in VS Code.

> The storefront banner photograph is a free-to-use Pexels stock image
> ([photo 16803130](https://www.pexels.com/photo/studio-shot-of-a-young-woman-wearing-a-pink-lehenga-dress-16803130/)).
> The category arch tiles use boutique-supplied photographs.

---

## 4. MySQL configuration

Create a schema and user in MySQL, then export environment variables before
running Django:

```sql
CREATE DATABASE vastra CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'vastra_user'@'localhost' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON vastra.* TO 'vastra_user'@'localhost';
FLUSH PRIVILEGES;
```

```powershell
$env:DB_ENGINE = "mysql"
$env:DB_NAME = "vastra"
$env:DB_USER = "vastra_user"
$env:DB_PASSWORD = "change-me"
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "3306"

python manage.py migrate
python manage.py runserver
```

Django migrations own the schema — do not create tables manually.
See `.env.example` for the full list of supported variables.

### Production environment variables

| Variable | Purpose | Example |
|---|---|---|
| `DJANGO_SECRET_KEY` | Signing key (never commit) | long random string |
| `DJANGO_DEBUG` | Debug mode | `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `boutique.example.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | CSRF origins for HTTPS | `https://boutique.example.com` |
| `DJANGO_SECURE_SSL_REDIRECT` | Force HTTPS | `True` |
| `BOUTIQUE_PHONE` | Storefront footer phone number | `+91 98765 43210` |
| `BOUTIQUE_EMAIL` | Storefront footer email | `hello@vastra.example.com` |
| `BOUTIQUE_LOCATION` | Storefront footer address | `12 MG Road, Bengaluru` |
| `BOUTIQUE_HOURS` | Storefront footer opening hours | `Mon – Sun · 10:00 AM – 8:00 PM` |

Cookie flags, HSTS, CSRF trusted origins, clickjacking protection and upload
limits are configured centrally in `config/settings.py`.

---

## 5. Tests

```powershell
python manage.py test boutique -v 1
```

The 36 tests cover the public storefront and category filter, sign-up (including
hashed passwords, duplicates and required fields), sign-in/sign-out, safe
`next` redirects, cart add/remove, stock limits, per-account cart isolation and
POST-only cart routes. `test_csrf.py` additionally runs with
`enforce_csrf_checks=True` so a missing token can never pass silently, and it
audits every `method="post"` template for `{% csrf_token %}`.

### Troubleshooting `Forbidden (403) — CSRF verification failed`

All state-changing routes (`/signup/`, `/login/`, `/logout/`,
`/cart/add/<id>/`, `/cart/remove/<id>/` and `/admin/`) require a CSRF token.
If you see a 403:

1. **Reload the page and submit the form again.** Tokens rotate; a page left open
   for a long time can hold a stale token.
2. **Use the Django server URL** — <http://localhost:8000/>. Do not open
   `storefront.html` from File Explorer or through VS Code Live Server; a
   `file://` or other-origin page cannot send a valid CSRF token.
3. **Keep cookies enabled.** The `csrftoken` cookie must be sent back with the
   POST.
4. **If testing with Postman/Thunder Client**, first GET the form page, copy the
   `csrftoken` cookie, and send it as the `X-CSRFToken` header (plus the normal
   form fields). Bare POSTs without a token are correctly rejected with 403.
5. **Stick to one hostname** while testing: either `localhost` or `127.0.0.1`.
   Both are trusted in development, but switching mid-form can confuse the
   browser's cookie/origin state.

Django's test client skips CSRF by default, which is why the original 25 tests
could pass even when a real browser posts without a token. The CSRF-enforced
tests above close that gap.

---

## 6. Project structure

```
vastra/
├── .vscode/                 # VS Code interpreter, debug and task configuration
├── config/                  # settings, root URLs, WSGI/ASGI
├── boutique/
│   ├── constants.py         # catalogue categories and sizes
│   ├── models.py            # CodeSequence, Dress, CustomerAccount, CartItem
│   ├── forms.py             # sign-up and sign-in forms
│   ├── views.py             # storefront, account and cart views
│   ├── urls.py              # storefront routes
│   ├── admin.py             # catalogue/account admin registrations
│   ├── templates/           # storefront and sign-in/sign-up pages
│   ├── static/boutique/     # CSS theme, storefront CSS/JS, images
│   ├── management/commands/ # seed_demo command (dresses only)
│   ├── tests/               # storefront/account/cart + CSRF-enforced tests
│   └── migrations/          # schema migrations
├── media/                   # uploaded dress images
├── manage.py
├── requirements.txt
├── requirements-dev.txt # optional: Playwright for screenshots
├── .env.example
└── README.md
```

---

## 7. Security notes

- Customer passwords are stored with Django's PBKDF2 hasher; never store plaintext.
- Customer accounts are kept in their own `CustomerAccount` table, separate from
  Django's `auth_user` staff/admin accounts.
- All state-changing views require CSRF tokens and POST; sign-out is POST-only.
- A customer can only read and modify their own cart — ownership is checked on
  every request from the server-side session.
- Sign-in honours only same-host `next` URLs (open-redirect protection).
- All SQL is through the ORM; no string-built queries.
- Uploaded images are restricted by extension and a 4 MB size cap.
- In production, set `DJANGO_DEBUG=False`, a strong `DJANGO_SECRET_KEY`, HTTPS,
  and correct `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`.

---

## 8. First-use flow

1. Open <http://localhost:8000/> and browse the collection.
2. Choose **Create account**, fill in username, phone, password and address.
3. You return to the sign-in page — sign in with the new credentials.
4. On the home page, choose **Add to cart** on any available dress.
5. Open the cart from the header to review items and remove any you no longer want.
