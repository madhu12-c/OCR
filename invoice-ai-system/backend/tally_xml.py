import xml.etree.ElementTree as ET
from datetime import datetime

class TallyExporter:
    def __init__(self):
        pass

    def generate_purchase_xml(self, invoice_data):
        """
        Generates a basic Tally ERP XML for a Purchase Voucher.
        """
        envelope = ET.Element("ENVELOPE")
        header = ET.SubElement(envelope, "HEADER")
        TALLYREQUEST = ET.SubElement(header, "TALLYREQUEST")
        TALLYREQUEST.text = "Import Data"

        body = ET.SubElement(envelope, "BODY")
        import_data = ET.SubElement(body, "IMPORTDATA")
        request_desc = ET.SubElement(import_data, "REQUESTDESC")
        REPORTNAME = ET.SubElement(request_desc, "REPORTNAME")
        REPORTNAME.text = "Vouchers"
        
        request_data = ET.SubElement(import_data, "REQUESTDATA")
        tally_msg = ET.SubElement(request_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        
        voucher = ET.SubElement(tally_msg, "VOUCHER", {"VCHTYPE": "Purchase", "ACTION": "Create"})
        
        # Core fields
        date_obj = datetime.strptime(invoice_data['invoice_date'], "%Y-%m-%d")
        ET.SubElement(voucher, "DATE").text = date_obj.strftime("%Y%m%d")
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = "Purchase"
        ET.SubElement(voucher, "REFERENCE").text = invoice_data['invoice_number']
        ET.SubElement(voucher, "PARTYLEDGERNAME").text = invoice_data['vendor_name']
        
        # Ledger entries (Simplified: Party Cr, Purchase Dr)
        # Party Cr
        all_ledger_party = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(all_ledger_party, "LEDGERNAME").text = invoice_data['vendor_name']
        ET.SubElement(all_ledger_party, "ISDEEMEDPOSITIVE").text = "No"
        ET.SubElement(all_ledger_party, "AMOUNT").text = str(invoice_data['total_amount'])
        
        # Purchase Dr
        all_ledger_purc = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(all_ledger_purc, "LEDGERNAME").text = "Purchase Account"
        ET.SubElement(all_ledger_purc, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(all_ledger_purc, "AMOUNT").text = "-" + str(invoice_data['total_amount'])

        return ET.tostring(envelope, encoding='unicode')

if __name__ == "__main__":
    # Test block
    exporter = TallyExporter()
    data = {
        "invoice_number": "INV-101",
        "invoice_date": "2024-03-11",
        "vendor_name": "Test Vendor",
        "total_amount": 5000
    }
    # print(exporter.generate_purchase_xml(data))
