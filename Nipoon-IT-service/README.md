# Nipoon-IT-service (Netlify)

## Deploy
1. Upload the `Nipoon-IT-service` folder to Netlify (or connect repo and set publish dir to `Nipoon-IT-service`).
2. Enable **Netlify Forms** in site settings.

## CRM + Database behavior
- **CRM pipeline**: Contact + workflow forms submit to Netlify Forms submissions.
- **Database**: Form submissions are stored in Netlify's submissions backend (acts as CRM database for leads/requests).
- **Account state**: Client account/session data is browser-side (localStorage with consent, sessionStorage without consent).

## UX behavior
- Dashboard is **not in menu**.
- Dashboard opens via the account button when a user is logged in; otherwise account button opens signup.
