import csv
import io
import re
import tempfile
import zipfile
from datetime import datetime
from io import StringIO

import pandas as pd

from odoo import _, fields, models
from odoo.tools import float_repr


class AccountReport(models.AbstractModel):
    _inherit = "account.report"

    def _init_options_buttons(self, options, previous_options):
        res = super()._init_options_buttons(options, previous_options)
        options["buttons"].append(
            {
                "name": _("DATEV AT"),
                "sequence": 110,
                "action": "export_file",
                "action_param": "l10n_at_datev_export_to_zip_manual",
                "file_export_type": _("Datev zip"),
            }
        )
        return res

    def open_datev_wizard(self, options):
        """Creates a new export wizard for this report."""
        new_context = self.env.context.copy()
        new_context["report_generation_options"] = options
        return {
            "type": "ir.actions.act_window",
            "name": _("Export"),
            "view_mode": "form",
            "res_model": "datev.export",
            "target": "new",
            "views": [[self.env.ref("datev_at.account_export_to_datev_at_form").id, "form"]],
            "context": new_context,
        }

    def l10n_at_datev_export_to_zip_manual(self, options):
        # options = self.env.context.get("report_generation_options")

        company_id = self.env.company
        options["collective_booking"] = company_id.collective_booking
        options["only_main_books"] = company_id.only_main_books
        options["export_vendor_bills"] = company_id.export_vendor_bills
        options["export_customer_invoices"] = company_id.export_customer_invoices
        options["export_journal_entries"] = company_id.export_journal_entries
        res = self.l10n_at_datev_export_to_zip(options=options)

        return res

    def l10n_at_datev_export_to_zip(self, options):
        """
        Check ir_attachment for method _get_path
        create a sha and replace 2 first letters by something not hexadecimal
        Return full_path as 2nd args, use it as name for Zipfile
        Don't need to unlink as it will be done automatically by garbage collector
        of attachment cron
        """
        report = self.env["account.report"].browse(options["report_id"])
        with tempfile.NamedTemporaryFile(mode="w+b", delete=True) as buf:
            with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED, allowZip64=False) as zf:
                move_line_ids = []
                for line in report._get_lines({**options, "export_mode": "print", "unfold_all": True}):
                    model, model_id = report._get_model_info_from_id(line["id"])
                    if model == "account.move.line":
                        move_line_ids.append(model_id)

                domain = [
                    ("line_ids", "in", move_line_ids),
                    ("company_id", "in", report.get_report_company_ids(options)),
                ]
                if options.get("all_entries"):
                    domain += [("state", "!=", "cancel")]
                else:
                    domain += [("state", "=", "posted")]
                if options.get("date"):
                    domain += [("date", "<=", options["date"]["date_to"])]
                    # cannot set date_from on move as domain depends on the move line account
                    # if "strict_range" is False
                domain += report._get_options_journals_domain(options)
                moves = self.env["account.move"].search(domain)
                if options.get("add_attachments"):
                    # add all moves attachments in zip file
                    slash_re = re.compile("[\\/]")
                    documents = []
                    for move in moves.filtered(lambda m: m.message_main_attachment_id):
                        # '\' is not allowed in file name, replace by '-'
                        base_name = slash_re.sub("-", move.name)
                        attachment = move.message_main_attachment_id
                        extension = f".{attachment.name.split('.')[-1]}"
                        foldername = "Belege"
                        name = "%(base)s%(extension)s" % {"base": base_name, "extension": extension}  # noqa: UP031
                        zf.writestr(name, attachment.raw)
                        documents.append(
                            {
                                "guid": move._l10n_de_datev_get_guid(),
                                "filename": f"{foldername}/{name}",
                                "type": 2
                                if move.is_sale_document()
                                else 1
                                if move.is_purchase_document()
                                else None,
                            }
                        )
                    if documents:
                        metadata_document = self.env["ir.qweb"]._render(
                            "l10n_de_reports.datev_export_metadata",
                            values={
                                "documents": documents,
                                "date": fields.Datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                            },
                        )
                        zf.writestr(
                            "document.xml", "<?xml version='1.0' encoding='UTF-8'?>" + str(metadata_document)
                        )
                else:
                    # ZIP for Data => csv
                    set_move_line_ids = set(move_line_ids)
                    # <MOD>
                    handler_id = self.env["account.general.ledger.report.handler"]
                    if options.get("export_vendor_bills"):
                        zf.writestr("EXTF_accounting_entries.csv", self._l10n_at_datev_get_csv(options, moves))
                    if options.get("export_customer_invoices"):
                        zf.writestr(
                            "EXTF_customer_accounts.csv",
                            handler_id._l10n_at_datev_get_partner_list(options, set_move_line_ids, customer=True),
                        )
                    if options.get("export_journal_entries"):
                        zf.writestr(
                            "EXTF_vendor_accounts.csv",
                            handler_id._l10n_at_datev_get_partner_list(options, set_move_line_ids, customer=False),
                        )
                    # <MOD>

            buf.seek(0)
            content = buf.read()

        filename, extension = report.get_default_report_filename(options, "ZIP").split(".")
        # MOD
        options["add_attachments"] = True
        return {
            "file_name": f"{filename}_atch.{extension}"
            if options.get("add_attachments")
            else f"{filename}_data.{extension}",
            "file_content": content,
            "file_type": "zip",
        }

    # Source: http://www.datev.de/dnlexom/client/app/index.html#/document/1036228/D103622800029
    def _l10n_at_datev_get_csv(self, options, moves):  # noqa: C901
        # last 2 element of preheader should be filled by "consultant number" and "client number"
        date_from = fields.Date.from_string(options.get("date").get("date_from"))
        date_to = fields.Date.from_string(options.get("date").get("date_to"))
        fy = self.env.company.compute_fiscalyear_dates(date_to)

        date_from = datetime.strftime(date_from, "%Y%m%d")
        date_to = datetime.strftime(date_to, "%Y%m%d")
        fy = datetime.strftime(fy.get("date_from"), "%Y%m%d")

        handler_id = self.env["account.general.ledger.report.handler"]
        datev_info = handler_id._l10n_de_datev_get_client_number()
        account_length = handler_id._l10n_de_datev_get_account_length()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quotechar='"', quoting=2)
        preheader = [
            "EXTF",
            700,
            21,
            "Buchungsstapel",
            13,
            "",
            "",
            "",
            "",
            "",
            datev_info[0],
            datev_info[1],
            fy,
            account_length,
            date_from,
            date_to,
            "",
            "",
            "",
            "",
            0,
            "EUR",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        header = [
            "Umsatz (ohne Soll/Haben-Kz)",
            "Soll/Haben-Kennzeichen",
            "WKZ Umsatz",
            "Kurs",
            "Basis-Umsatz",
            "WKZ Basis-Umsatz",
            "Konto",
            "Gegenkonto (ohne BU-Schlüssel)",
            "BU-Schlüssel",
            "Belegdatum",
            "Belegfeld 1",
            "Belegfeld 2",
            "Skonto",
            "Buchungstext",
            "Postensperre",
            "Diverse Adressnummer",
            "Geschäftspartnerbank",
            "Sachverhalt",
            "Zinssperre",
            "Beleglink",
            "Beleginfo - Art 1",
            "Beleginfo - Inhalt 1",
            "Beleginfo - Art 2",
            "Beleginfo - Inhalt 2",
            "Beleginfo - Art 3",
            "Beleginfo - Inhalt 3",
            "Beleginfo - Art 4",
            "Beleginfo - Inhalt 4",
            "Beleginfo - Art 5",
            "Beleginfo - Inhalt 5",
            "Beleginfo - Art 6",
            "Beleginfo - Inhalt 6",
            "Beleginfo - Art 7",
            "Beleginfo - Inhalt 7",
            "Beleginfo - Art 8",
            "Beleginfo - Inhalt 8",
            "KOST1 - Kostenstelle",
            "KOST2 - Kostenstelle",
            "Kost-Menge",
            "EU-Land u. UStID (Bestimmung)",
            "EU-Steuersatz (Bestimmung)",
            "Abw. Versteuerungsart",
            "Sachverhalt L+L",
            "Funktionsergänzung L+L",
            "BU 49 Hauptfunktionstyp",
            "BU 49 Hauptfunktionsnummer",
            "BU 49 Funktionsergänzung",
            "Zusatzinformation - Art 1",
            "Zusatzinformation- Inhalt 1",
            "Zusatzinformation - Art 2",
            "Zusatzinformation- Inhalt 2",
            "Zusatzinformation - Art 3",
            "Zusatzinformation- Inhalt 3",
            "Zusatzinformation - Art 4",
            "Zusatzinformation- Inhalt 4",
            "Zusatzinformation - Art 5",
            "Zusatzinformation- Inhalt 5",
            "Zusatzinformation - Art 6",
            "Zusatzinformation- Inhalt 6",
            "Zusatzinformation - Art 7",
            "Zusatzinformation- Inhalt 7",
            "Zusatzinformation - Art 8",
            "Zusatzinformation- Inhalt 8",
            "Zusatzinformation - Art 9",
            "Zusatzinformation- Inhalt 9",
            "Zusatzinformation - Art 10",
            "Zusatzinformation- Inhalt 10",
            "Zusatzinformation - Art 11",
            "Zusatzinformation- Inhalt 11",
            "Zusatzinformation - Art 12",
            "Zusatzinformation- Inhalt 12",
            "Zusatzinformation - Art 13",
            "Zusatzinformation- Inhalt 13",
            "Zusatzinformation - Art 14",
            "Zusatzinformation- Inhalt 14",
            "Zusatzinformation - Art 15",
            "Zusatzinformation- Inhalt 15",
            "Zusatzinformation - Art 16",
            "Zusatzinformation- Inhalt 16",
            "Zusatzinformation - Art 17",
            "Zusatzinformation- Inhalt 17",
            "Zusatzinformation - Art 18",
            "Zusatzinformation- Inhalt 18",
            "Zusatzinformation - Art 19",
            "Zusatzinformation- Inhalt 19",
            "Zusatzinformation - Art 20",
            "Zusatzinformation- Inhalt 20",
            "Stück",
            "Gewicht",
            "Zahlweise",
            "Forderungsart",
            "Veranlagungsjahr",
            "Zugeordnete Fälligkeit",
            "Skontotyp",
            "Auftragsnummer",
            "Buchungstyp",
            "USt-Schlüssel (Anzahlungen)",
            "EU-Land (Anzahlungen)",
            "Sachverhalt L+L (Anzahlungen)",
            "EU-Steuersatz (Anzahlungen)",
            "Erlöskonto (Anzahlungen)",
            "Herkunft-Kz",
            "Buchungs GUID",
            "KOST-Datum",
            "SEPA-Mandatsreferenz",
            "Skontosperre",
            "Gesellschaftername",
            "Beteiligtennummer",
            "Identifikationsnummer",
            "Zeichnernummer",
            "Postensperre bis",
            "Bezeichnung SoBil-Sachverhalt",
            "Kennzeichen SoBil-Buchung",
            "Festschreibung",
            "Leistungsdatum",
            "Datum Zuord. Steuerperiode",
            "Fälligkeit",
            "Generalumkehr (GU)",
            "Steuersatz",
            "Land",
            "Abrechnungsreferenz",
            "BVV-Position",
            "EU-Land u. UStID (Ursprung)",
            "EU-Steuersatz (Ursprung)",
            "Abw. Skontokonto",
        ]

        lines = [preheader, header]

        for m in moves:
            payment_account = 0  # Used for non-reconciled payments

            move_balance = 0
            counterpart_amount = 0
            last_tax_line_index = 0
            for aml in m.line_ids:
                if aml.debit == aml.credit:
                    # Ignore debit = credit = 0
                    continue

                # account and counterpart account
                handler_id = self.env["account.general.ledger.report.handler"]
                to_account_code = str(
                    handler_id._l10n_at_datev_find_partner_account(
                        aml.move_id.l10n_de_datev_main_account_id,
                        aml.partner_id,
                        only_main_books=self.env.company.only_main_books,
                    )
                )
                code = handler_id._l10n_at_datev_find_partner_account(
                    aml.account_id, aml.partner_id, only_main_books=self.env.company.only_main_books
                )
                account_code = f"{code}"

                # We don't want to have lines with our outstanding
                # payment/receipt as they don't represent real moves
                # So if payment skip one move line to write, while keeping the account
                # and replace bank account for outstanding payment/receipt for the other line

                if aml.payment_id:
                    if payment_account == 0:
                        payment_account = account_code
                        counterpart_amount += aml.balance
                        continue
                    else:
                        to_account_code = payment_account

                # If both account and counteraccount are the same, ignore the line
                if aml.account_id == aml.move_id.l10n_de_datev_main_account_id:
                    if aml.statement_line_id and not aml.payment_id:
                        counterpart_amount += aml.balance
                    continue
                # If line is a tax ignore it as datev requires single line
                # with gross amount and deduct tax itself based
                # on account or on the control key code
                if aml.tax_line_id:
                    continue

                if aml.price_total:
                    sign = -1 if aml.currency_id.compare_amounts(aml.balance, 0) < 0 else 1
                    line_amount = abs(aml.price_total) * sign
                    # convert line_amount in company currency
                    if aml.currency_id != aml.company_id.currency_id:
                        line_amount = aml.currency_id._convert(
                            from_amount=line_amount,
                            to_currency=aml.company_id.currency_id,
                            company=aml.company_id,
                            date=aml.date,
                        )
                else:
                    aml_taxes = aml.tax_ids.compute_all(
                        aml.balance, aml.company_id.currency_id, partner=aml.partner_id, handle_price_include=False
                    )
                    line_amount = aml_taxes["total_included"]
                move_balance += line_amount

                code_correction = ""
                if aml.tax_ids:
                    last_tax_line_index = len(lines)
                    last_tax_line_amount = line_amount
                    codes = set(aml.tax_ids.mapped("l10n_de_datev_code"))
                    if len(codes) == 1:
                        # there should only be one max, else skip code
                        code_correction = codes.pop() or ""

                # reference
                receipt1 = ref = aml.move_id.name
                if aml.move_id.journal_id.type == "purchase" and aml.move_id.ref:
                    ref = aml.move_id.ref

                # on receivable/payable aml of sales/purchases
                receipt2 = ""
                if to_account_code == account_code and aml.date_maturity:
                    receipt2 = aml.date

                currency = aml.company_id.currency_id

                # Idiotic program needs to have a line with 125 elements ordered in a given fashion as it
                # does not take into account the header and non mandatory fields
                array = ["" for x in range(125)]
                # For DateV, we can't have negative amount on a line,
                # so we need to inverse the amount and inverse the
                # credit/debit symbol.
                array[1] = "H" if aml.currency_id.compare_amounts(line_amount, 0) < 0 else "S"
                line_amount = abs(line_amount)
                array[0] = float_repr(line_amount, aml.company_id.currency_id.decimal_places).replace(".", ",")
                array[2] = currency.name
                if aml.currency_id != currency:
                    array[3] = str(aml.currency_id.rate).replace(".", ",")
                    array[4] = float_repr(aml.price_total, aml.currency_id.decimal_places).replace(".", ",")
                    array[5] = aml.currency_id.name
                array[6] = account_code
                array[7] = to_account_code
                array[8] = code_correction
                array[9] = datetime.strftime(aml.move_id.date, "%-d%m")
                array[10] = receipt1[-36:]
                array[11] = receipt2
                array[13] = (aml.name or ref).replace("\n", " ")
                if m.message_main_attachment_id:
                    array[19] = f'BEDI "{m._l10n_de_datev_get_guid()}"'
                lines.append(array)
            # In case of epd we actively fix rounding issues by checking the base line and tax line
            # amounts against the move amount missing cent and adjust the vals accordingly.
            # Since here we have to recompute the tax values for each line with tax, we need
            # to replicate the rounding fix logic adding the difference on the last tax line
            # to avoid creating a difference with the source payment move
            if (
                (m.origin_payment_id or m.statement_line_id)
                and move_balance
                and counterpart_amount
                and last_tax_line_index
            ):
                delta_balance = move_balance + counterpart_amount
                if delta_balance:
                    lines[last_tax_line_index][0] = float_repr(
                        abs(last_tax_line_amount - delta_balance), m.company_id.currency_id.decimal_places
                    ).replace(".", ",")

        # <MOD>
        # we combine the lines with the same account, partner and tax code
        # we sum the amounts and concat the texts
        writer.writerows(lines)

        input_data = output.getvalue()
        if options.get("collective_booking"):
            lines = input_data.split("\r\n")

            first_line = lines[0]

            data = "\n".join(lines[1:])

            df = pd.read_csv(StringIO(data), sep=";", header=0, dtype=str)  # skiprows=1,
            df["Umsatz (ohne Soll/Haben-Kz)"] = (
                df["Umsatz (ohne Soll/Haben-Kz)"].str.replace(",", ".").astype(float)
            )

            custom_order = df.columns.tolist()
            grouped_fields = df.columns.tolist()
            agg_fields = [
                "Umsatz (ohne Soll/Haben-Kz)",
                "Soll/Haben-Kennzeichen",
                "WKZ Umsatz",
                "Buchungstext",
            ]

            for item in agg_fields:
                while item in grouped_fields:
                    grouped_fields.remove(item)

            grouped_df = df.groupby(
                # gr_by,
                grouped_fields,
                as_index=False,
                dropna=False,
            ).agg(
                {
                    "Umsatz (ohne Soll/Haben-Kz)": "sum",  # Sum amounts
                    "Soll/Haben-Kennzeichen": "first",  # Keep the first encountered value
                    "WKZ Umsatz": "first",  # Keep the first encountered value
                    # "Buchungstext": "first"  # Keep the first encountered value
                    "Buchungstext": lambda x: " | ".join(x.dropna().unique()),  # Concatenate unique texts
                    # Add more aggregations as needed
                }
            )
            grouped_df = grouped_df[custom_order]

            # Convert the amount back to string with comma as decimal separator
            grouped_df["Umsatz (ohne Soll/Haben-Kz)"] = grouped_df["Umsatz (ohne Soll/Haben-Kz)"].apply(
                lambda x: f"{x:.2f}".replace(".", ",")
            )

            # Convert back to CSV-like format
            output_data = grouped_df.to_csv(
                sep=";", index=False, quoting=csv.QUOTE_ALL, lineterminator="\n"
            )  # , lineterminator="\r\n"

            # we readd the first line
            final_data = first_line + "\r\n" + output_data
        else:
            final_data = input_data

        return final_data
