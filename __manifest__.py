# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Datev AT",
    "version": "18.0.1.0",
    "author": "it-fact GmbH",
    "website": "https://it-fact.com",
    "category": "Accounting",
    "summary": "Adaptionen, um Datev für AT zu verwenden",
    "application": True,
    "license": "OPL-1",
    "depends": [
        "base",
        "account",
        "l10n_de",
        "l10n_de_reports",
        "account_reports",
        "l10n_at",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company_views.xml",
        "views/res_partner_views.xml",
        "views/account_view.xml",
    ],
    "images": ["static/description/icon.png"],
    "external_dependencies": {
        "python": ["pandas"],
    },
    "support": "o@it-fact.com",
    "maintainer": "it-fact GmbH",
    "price": "1200.00",
    "currency": "EUR",
}
