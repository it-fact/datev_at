# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv
import io
from datetime import datetime

from odoo import fields, models


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = "account.general.ledger.report.handler"

    def _l10n_de_datev_get_account_personenkonto_length(self):
        return self.env.company.l10n_de_datev_account_personenkonto_length

    def _l10n_at_datev_find_partner_account(self, account, partner, only_main_books=False):
        len_param = self._l10n_de_datev_get_account_length() + 1
        len_param_personenkonto = self._l10n_de_datev_get_account_personenkonto_length() + 1
        # <MOD>
        # codes = {
        #    "asset_receivable": (
        #        partner.l10n_de_datev_identifier_customer or int("2".ljust(len_param, "0")) + partner.id
        #    ),
        #    "liability_payable": (partner.l10n_de_datev_identifier
        # or int("3".ljust(len_param, "0")) + partner.id),
        # }

        # We always take the account number which is in AT 20000 for receivable and 30000 for payable
        # the number get's increased to len_param and then the Database ID is used otherwise the
        # custom account number is used l10n_de_datev_identifier_customer or l10n_de_datev_identifier
        if partner and partner.property_account_receivable_id and partner.property_account_receivable_id.code:
            base_asset_receivable = int(partner.property_account_receivable_id.code.ljust(len_param, "0"))
            base_asset_payable_personenkonto = int(
                partner.property_account_receivable_id.code.ljust(len_param_personenkonto, "0")
            )
        else:
            base_asset_receivable = "2".ljust(len_param, "0")
            base_asset_payable_personenkonto = "2".ljust(len_param_personenkonto, "0")

        if only_main_books:
            asset_receivable = base_asset_receivable
        else:
            if partner and partner.id:
                default_number = base_asset_payable_personenkonto + partner.id
            else:
                default_number = base_asset_receivable
            asset_receivable = partner.l10n_de_datev_identifier_customer or default_number

        if partner and partner.property_account_payable_id and partner.property_account_payable_id.code:
            base_asset_payable = int(partner.property_account_payable_id.code.ljust(len_param, "0"))
            base_asset_payable_personenkonto = int(
                partner.property_account_payable_id.code.ljust(len_param_personenkonto, "0")
            )
        else:
            base_asset_payable = "33".ljust(len_param, "0")
            base_asset_payable_personenkonto = "33".ljust(len_param_personenkonto, "0")
        if only_main_books:
            liability_payable = base_asset_payable
        else:
            if partner and partner.id:
                default_number = base_asset_payable_personenkonto + partner.id
            else:
                default_number = base_asset_payable
            liability_payable = partner.l10n_de_datev_identifier or default_number

        codes = {
            "asset_receivable": asset_receivable,
            "liability_payable": liability_payable,
        }

        # </MOD>

        if account.account_type in codes and partner:
            return codes[account.account_type]
        else:
            return str(account.code).ljust(len_param - 1, "0") if account else ""

    def _l10n_at_datev_get_partner_list(self, options, move_line_ids, customer=True):
        date_to = fields.Date.from_string(options.get("date").get("date_to"))
        fy = self.env.company.compute_fiscalyear_dates(date_to)

        fy = datetime.strftime(fy.get("date_from"), "%Y%m%d")
        handler_id = self.env["account.general.ledger.report.handler"]
        datev_info = handler_id._l10n_de_datev_get_client_number()
        account_length = handler_id._l10n_de_datev_get_account_length()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quotechar='"', quoting=2)
        preheader = [
            "EXTF",
            700,
            16,
            "Debitoren/Kreditoren",
            5,
            None,
            None,
            "",
            "",
            "",
            datev_info[0],
            datev_info[1],
            fy,
            account_length,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
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
            "Konto",
            "Name (Adressattyp Unternehmen)",
            "Unternehmensgegenstand",
            "Name (Adressattyp natürl. Person)",
            "Vorname (Adressattyp natürl. Person)",
            "Name (Adressattyp keine Angabe)",
            "Adressattyp",
            "Kurzbezeichnung",
            "EU-Land",
            "EU-UStID",
            "Anrede",
            "Titel/Akad. Grad",
            "Adelstitel",
            "Namensvorsatz",
            "Adressart",
            "Straße",
            "Postfach",
            "Postleitzahl",
            "Ort",
            "Land",
            "Versandzusatz",
            "Adresszusatz",
            "Abweichende Anrede",
            "Abw. Zustellbezeichnung 1",
            "Abw. Zustellbezeichnung 2",
            "Kennz. Korrespondenzadresse",
            "Adresse Gültig von",
            "Adresse Gültig bis",
            "Telefon",
            "Bemerkung (Telefon)",
            "Telefon GL",
            "Bemerkung (Telefon GL)",
            "E-Mail",
            "Bemerkung (E-Mail)",
            "Internet",
            "Bemerkung (Internet)",
            "Fax",
            "Bemerkung (Fax)",
            "Sonstige",
            "Bemerkung (Sonstige)",
            "Bankleitzahl 1",
            "Bankbezeichnung 1",
            "Bank-Kontonummer 1",
            "Länderkennzeichen 1",
            "IBAN-Nr. 1",
            "Leerfeld",
            "SWIFT-Code 1",
            "Abw. Kontoinhaber 1",
            "Kennz. Hauptbankverb. 1",
            "Bankverb 1 Gültig von",
            "Bankverb 1 Gültig bis",
            "Bankleitzahl 2",
            "Bankbezeichnung 2",
            "Bank-Kontonummer 2",
            "Länderkennzeichen 2",
            "IBAN-Nr. 2",
            "Leerfeld",
            "SWIFT-Code 2",
            "Abw. Kontoinhaber 2",
            "Kennz. Hauptbankverb. 2",
            "Bankverb 2 Gültig von",
            "Bankverb 2 Gültig bis",
            "Bankleitzahl 3",
            "Bankbezeichnung 3",
            "Bank-Kontonummer 3",
            "Länderkennzeichen 3",
            "IBAN-Nr. 3",
            "Leerfeld",
            "SWIFT-Code 3",
            "Abw. Kontoinhaber 3",
            "Kennz. Hauptbankverb. 3",
            "Bankverb 3 Gültig von",
            "Bankverb 3 Gültig bis",
            "Bankleitzahl 4",
            "Bankbezeichnung 4",
            "Bank-Kontonummer 4",
            "Länderkennzeichen 4",
            "IBAN-Nr. 4",
            "Leerfeld",
            "SWIFT-Code 4",
            "Abw. Kontoinhaber 4",
            "Kennz. Hauptbankverb. 4",
            "Bankverb 4 Gültig von",
            "Bankverb 4 Gültig bis",
            "Bankleitzahl 5",
            "Bankbezeichnung 5",
            "Bank-Kontonummer 5",
            "Länderkennzeichen 5",
            "IBAN-Nr. 5",
            "Leerfeld",
            "SWIFT-Code 5",
            "Abw. Kontoinhaber 5",
            "Kennz. Hauptbankverb. 5",
            "Bankverb 5 Gültig von",
            "Bankverb 5 Gültig bis",
            "Leerfeld",
            "Briefanrede",
            "Grußformel",
            "Kunden-/Lief.-Nr.",
            "Steuernummer",
            "Sprache",
            "Ansprechpartner",
            "Vertreter",
            "Sachbearbeiter",
            "Diverse-Konto",
            "Ausgabeziel",
            "Währungssteuerung",
            "Kreditlimit (Debitor)",
            "Zahlungsbedingung",
            "Fälligkeit in Tagen (Debitor)",
            "Skonto in Prozent (Debitor)",
            "Kreditoren-Ziel 1 Tg.",
            "Kreditoren-Skonto 1 %",
            "Kreditoren-Ziel 2 Tg.",
            "Kreditoren-Skonto 2 %",
            "Kreditoren-Ziel 3 Brutto Tg.",
            "Kreditoren-Ziel 4 Tg.",
            "Kreditoren-Skonto 4 %",
            "Kreditoren-Ziel 5 Tg.",
            "Kreditoren-Skonto 5 %",
            "Mahnung",
            "Kontoauszug",
            "Mahntext 1",
            "Mahntext 2",
            "Mahntext 3",
            "Kontoauszugstext",
            "Mahnlimit Betrag",
            "Mahnlimit %",
            "Zinsberechnung",
            "Mahnzinssatz 1",
            "Mahnzinssatz 2",
            "Mahnzinssatz 3",
            "Lastschrift",
            "Leerfeld",
            "Mandantenbank",
            "Zahlungsträger",
            "Indiv. Feld 1",
            "Indiv. Feld 2",
            "Indiv. Feld 3",
            "Indiv. Feld 4",
            "Indiv. Feld 5",
            "Indiv. Feld 6",
            "Indiv. Feld 7",
            "Indiv. Feld 8",
            "Indiv. Feld 9",
            "Indiv. Feld 10",
            "Indiv. Feld 11",
            "Indiv. Feld 12",
            "Indiv. Feld 13",
            "Indiv. Feld 14",
            "Indiv. Feld 15",
            "Abweichende Anrede (Rechnungsadresse)",
            "Adressart (Rechnungsadresse)",
            "Straße (Rechnungsadresse)",
            "Postfach (Rechnungsadresse)",
            "Postleitzahl (Rechnungsadresse)",
            "Ort (Rechnungsadresse)",
            "Land (Rechnungsadresse)",
            "Versandzusatz (Rechnungsadresse)",
            "Adresszusatz (Rechnungsadresse)",
            "Abw. Zustellbezeichnung 1 (Rechnungsadresse)",
            "Abw. Zustellbezeichnung 2 (Rechnungsadresse)",
            "Adresse Gültig von (Rechnungsadresse)",
            "Adresse Gültig bis (Rechnungsadresse)",
            "Bankleitzahl 6",
            "Bankbezeichnung 6",
            "Bank-Kontonummer 6",
            "Länderkennzeichen 6",
            "IBAN-Nr. 6",
            "Leerfeld",
            "SWIFT-Code 6",
            "Abw. Kontoinhaber 6",
            "Kennz. Hauptbankverb. 6",
            "Bankverb 6 Gültig von",
            "Bankverb 6 Gültig bis",
            "Bankleitzahl 7",
            "Bankbezeichnung 7",
            "Bank-Kontonummer 7",
            "Länderkennzeichen 7",
            "IBAN-Nr. 7",
            "Leerfeld",
            "SWIFT-Code 7",
            "Abw. Kontoinhaber 7",
            "Kennz. Hauptbankverb. 7",
            "Bankverb 7 Gültig von",
            "Bankverb 7 Gültig bis",
            "Bankleitzahl 8",
            "Bankbezeichnung 8",
            "Bank-Kontonummer 8",
            "Länderkennzeichen 8",
            "IBAN-Nr. 8",
            "Leerfeld",
            "SWIFT-Code 8",
            "Abw. Kontoinhaber 8",
            "Kennz. Hauptbankverb. 8",
            "Bankverb 8 Gültig von",
            "Bankverb 8 Gültig bis",
            "Bankleitzahl 9",
            "Bankbezeichnung 9",
            "Bank-Kontonummer 9",
            "Länderkennzeichen 9",
            "IBAN-Nr. 9",
            "Leerfeld",
            "SWIFT-Code 9",
            "Abw. Kontoinhaber 9",
            "Kennz. Hauptbankverb. 9",
            "Bankverb 9 Gültig von",
            "Bankverb 9 Gültig bis",
            "Bankleitzahl 10",
            "Bankbezeichnung 10",
            "Bank-Kontonummer 10",
            "Länderkennzeichen 10",
            "IBAN-Nr. 10",
            "Leerfeld",
            "SWIFT-Code 10",
            "Abw. Kontoinhaber 10",
            "Kennz. Hauptbankverb. 10",
            "Bankverb 10 Gültig von",
            "Bankverb 10 Gültig bis",
            "Nummer Fremdsystem",
            "Insolvent",
            "SEPA-Mandatsreferenz 1",
            "SEPA-Mandatsreferenz 2",
            "SEPA-Mandatsreferenz 3",
            "SEPA-Mandatsreferenz 4",
            "SEPA-Mandatsreferenz 5",
            "SEPA-Mandatsreferenz 6",
            "SEPA-Mandatsreferenz 7",
            "SEPA-Mandatsreferenz 8",
            "SEPA-Mandatsreferenz 9",
            "SEPA-Mandatsreferenz 10",
            "Verknüpftes OPOS-Konto",
            "Mahnsperre bis",
            "Lastschriftsperre bis",
            "Zahlungssperre bis",
            "Gebührenberechnung",
            "Mahngebühr 1",
            "Mahngebühr 2",
            "Mahngebühr 3",
            "Pauschalenberechnung",
            "Verzugspauschale 1",
            "Verzugspauschale 2",
            "Verzugspauschale 3",
            "Alternativer Suchname",
            "Status",
            "Anschrift manuell geändert (Korrespondenzadresse)",
            "Anschrift individuell (Korrespondenzadresse)",
            "Anschrift manuell geändert (Rechnungsadresse)",
            "Anschrift individuell (Rechnungsadresse)",
            "Fristberechnung bei Debitor",
            "Mahnfrist 1",
            "Mahnfrist 2",
            "Mahnfrist 3",
            "Letzte Frist",
        ]

        lines = [preheader, header]

        if len(move_line_ids):
            if customer:
                move_types = ("out_refund", "out_invoice", "out_receipt")
            else:
                move_types = ("in_refund", "in_invoice", "in_receipt")
            select = """SELECT distinct(aml.partner_id)
                        FROM account_move_line aml
                        LEFT JOIN account_move m
                        ON aml.move_id = m.id
                        WHERE aml.id IN %s
                            AND aml.tax_line_id IS NULL
                            AND aml.debit != aml.credit
                            AND m.move_type IN %s
                            AND aml.account_id != m.l10n_de_datev_main_account_id"""
            self.env.cr.execute(select, (tuple(move_line_ids), move_types))
        partners = self.env["res.partner"].browse([p.get("partner_id") for p in self.env.cr.dictfetchall()])
        for partner in partners:
            handler_id = self.env["account.general.ledger.report.handler"]
            if customer:
                code = handler_id._l10n_at_datev_find_partner_account(
                    partner.property_account_receivable_id,
                    partner,
                    only_main_books=self.env.company.only_main_books,
                )
            else:
                code = handler_id._l10n_at_datev_find_partner_account(
                    partner.property_account_payable_id, partner, self.env.company.only_main_books
                )
            line_value = {
                "code": code,
                "company_name": partner.name if partner.is_company else "",
                "person_name": "" if partner.is_company else partner.name,
                "natural": partner.is_company and "2" or "1",
                "vat": partner.vat or "",
            }
            # Idiotic program needs to have a line with 243 elements ordered in a given fashion as it
            # does not take into account the header and non mandatory fields
            array = ["" for x in range(243)]
            array[0] = line_value.get("code")
            array[1] = line_value.get("company_name")
            array[3] = line_value.get("person_name")
            array[6] = line_value.get("natural")
            array[9] = line_value.get("vat")
            lines.append(array)
        writer.writerows(lines)
        return output.getvalue()
