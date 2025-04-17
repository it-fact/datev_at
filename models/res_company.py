from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    collective_booking = fields.Boolean(
        string="Sammelbuchungen",
        default=False,
        help="Aggregate positions if they have the same Tax Code, Account and Partner.",
    )
    only_main_books = fields.Boolean(
        string="Nur Hauptbücher",
        default=False,
        help=(
            "Export only main books eg. don't separate the creditor account "
            "into separate account for each customer."
        ),
    )
    export_vendor_bills = fields.Boolean(string="Lieferantenrechnungen", default=True)
    export_customer_invoices = fields.Boolean(string="Kundenrechnungen", default=True)
    export_journal_entries = fields.Boolean(string="Journalbuchungen", default=True)
