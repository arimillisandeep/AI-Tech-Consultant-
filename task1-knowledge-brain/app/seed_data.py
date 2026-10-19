"""
Seed articles so the demo/evals run OFFLINE before any live crawl.
These mirror the *style* of Brilliant Directories help articles. Replace/extend
them by running the real ingestion (POST /ingestion/run) against the sitemap.
Each image entry carries: url, alt text, nearby text, and a vision description.
In offline mode the vision description comes from alt+context and is labelled as
such; with ANTHROPIC_API_KEY set, app/llm.py's Claude vision describer is used.
"""
SEED_ARTICLES = [
 {
  "title": "How to Process a Refund for a Member Payment",
  "url": "https://support.brilliantdirectories.com/support/solutions/articles/refund-member-payment",
  "category": "Payments", "folder": "Refunds and Cancellations",
  "body": """## Overview
Refunds are issued from the admin dashboard. Only admins with billing permission can issue a refund.
## Steps to issue a refund
Go to Finance, then Transactions. Find the transaction and click Actions, then Refund.
Choose full or partial refund, enter the amount, and confirm. The member receives an email receipt.
Refunds return to the original payment method and typically appear in 5 to 10 business days depending on the bank.
## Cancelling a subscription versus refunding
Cancelling stops future charges but does not refund a past payment. To cancel, open the member record,
go to Billing, and click Cancel Subscription. The member keeps access until the end of the paid period.
## Limits
Transactions older than 180 days cannot be refunded through the dashboard and must be handled with the payment provider directly.""",
  "images": [{"url": "https://example.com/img/refund-actions-menu.png", "alt": "Refund option in the Actions menu",
              "nearby_text": "Find the transaction and click Actions, then Refund.",
              "vision_description": "Screenshot of Finance > Transactions table. The Actions dropdown shows View, Refund, and Download Receipt. The Refund button is highlighted."}]},
 {
  "title": "Changing Your Website Logo and Favicon",
  "url": "https://support.brilliantdirectories.com/support/solutions/articles/change-logo",
  "category": "Design", "folder": "Branding",
  "body": """## Steps
Go to Settings, then Design Settings, then Logo. Upload a PNG or SVG logo. Recommended width is 300 pixels.
To change the favicon, upload a 32 by 32 pixel ICO or PNG in the same panel. Click Save.
Changes can take up to 10 minutes to appear because of caching. Clear your browser cache if the old logo still shows.""",
  "images": [{"url": "https://example.com/img/logo-upload.png", "alt": "Logo upload panel",
              "nearby_text": "Upload a PNG or SVG logo.",
              "vision_description": "Settings panel titled Logo with an Upload Logo button, a favicon uploader below it, and a Save button at the bottom right."}]},
 {
  "title": "Setting Up a Payment Gateway (Stripe and PayPal)",
  "url": "https://support.brilliantdirectories.com/support/solutions/articles/payment-gateway-setup",
  "category": "Payments", "folder": "Payment Gateways",
  "body": """## Supported gateways
Stripe and PayPal are supported out of the box. Other gateways require a custom integration.
## Connect Stripe
Go to Settings, then Payment Settings. Click Connect with Stripe and complete the Stripe login.
Test mode must be turned off before accepting live payments.
## Troubleshooting failed payments
If payments fail, check that the gateway is in live mode, that the currency matches the gateway account currency,
and that webhook signing is enabled. A mismatched currency is the most common cause of failed charges.""",
  "images": []},
 {
  "title": "Improving Member Search with Filters and Categories",
  "url": "https://support.brilliantdirectories.com/support/solutions/articles/search-filters",
  "category": "Members", "folder": "Search",
  "body": """## Built-in search settings
Search filters are configured under Settings, then Search Settings. You can filter by category, location,
and membership level without custom code. Keyword search matches member name, category and tags.
## Location radius search
Enable radius search in Search Settings to let visitors search within a distance of a postcode or city.
## Limits of built-in search
Built-in search does not support AI semantic ranking or typo tolerance beyond simple partial matches.
Custom relevance ranking requires custom development.""",
  "images": [{"url": "https://example.com/img/search-settings.png", "alt": "Search Settings filters",
              "nearby_text": "Search filters are configured under Settings, then Search Settings.",
              "vision_description": "Search Settings screen with toggles for Category Filter, Location Filter, Membership Level Filter, and Radius Search, each with an on/off switch."}]},
 {
  "title": "Managing Member Plans and Pricing",
  "url": "https://support.brilliantdirectories.com/support/solutions/articles/member-plans",
  "category": "Members", "folder": "Membership Plans",
  "body": """## Create a plan
Go to Members, then Membership Plans, then Add Plan. Set the price, billing period (monthly or yearly), and included features.
## Free trials
A free trial of up to 30 days can be enabled per plan. A card is still required at signup if Require Card for Trial is on.
## Changing a price
Price changes apply to new signups only. Existing members keep their current price until they change plan.""",
  "images": []},
 {
  "title": "Sending Email Notifications and Order Confirmations",
  "url": "https://support.brilliantdirectories.com/support/solutions/articles/email-notifications",
  "category": "Emails", "folder": "Notifications",
  "body": """## Notification templates
Order confirmations, welcome emails and renewal reminders are edited under Emails, then Email Templates.
Each template can be turned on or off. Use the Test Send button to preview a template before enabling it.
## If emails go to spam
Add SPF and DKIM records for your sending domain. Without SPF and DKIM, notification emails are often marked as spam.
Custom SMTP can be configured under Settings, then Email Settings.""",
  "images": []},
 {
  "title": "Updating General Website Settings and Contact Details",
  "url": "https://support.brilliantdirectories.com/support/solutions/articles/general-settings",
  "category": "Settings", "folder": "General",
  "body": """## General settings
Site name, contact email, phone and address are edited under Settings, then General Settings.
The contact email is used as the sender for system notifications and displayed in the site footer.
## Timezone and currency
Timezone and default currency are set in the same panel. Changing currency does not convert existing prices.""",
  "images": []},
 {
  "title": "Mobile Layout and Responsive Design Settings",
  "url": "https://support.brilliantdirectories.com/support/solutions/articles/mobile-layout",
  "category": "Design", "folder": "Mobile",
  "body": """## Responsive behaviour
All default themes are responsive. On screens under 768 pixels the navigation collapses into a hamburger menu automatically.
## Mobile search bar
The mobile search bar position is controlled under Design Settings, then Mobile. It can be shown above or below the header image.
Custom mobile-only layouts beyond these settings require custom CSS or development.""",
  "images": []},
 {
  "title": "Importing and Exporting Member Data (CSV)",
  "url": "https://support.brilliantdirectories.com/support/solutions/articles/import-export-members",
  "category": "Members", "folder": "Data",
  "body": """## Import members
Go to Members, then Import. Upload a CSV with columns email, first_name, last_name and plan. Email must be unique per member.
Duplicate emails are skipped and reported in the import log. A maximum of 5000 rows can be imported per file.
## Export members
Go to Members, then Export to download a CSV of members including plan and signup date. Passwords are never exported.""",
  "images": []},
 {
  "title": "Password Reset and Account Access Troubleshooting",
  "url": "https://support.brilliantdirectories.com/support/solutions/articles/password-reset",
  "category": "Accounts", "folder": "Access",
  "body": """## Reset a member password
Members reset their own password from the login page using Forgot Password. The reset link expires after 60 minutes.
Admins can send a reset link from the member record, but admins cannot see or set a member's actual password.
## Locked accounts
After 8 failed login attempts an account locks for 30 minutes. An admin can unlock it early from the member record.""",
  "images": []},
]
