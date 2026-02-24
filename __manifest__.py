{
    "name": "IVA por Cliente (Cash/Paid) - Reporte",
    "version": "1.0",
    "depends": ["account", "account_reports"],
    "data": [
        'views/res_partner_view.xml',
        "data/iva_cliente_cash_report.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}