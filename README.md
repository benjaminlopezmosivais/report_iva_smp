# IVA Cliente Cash Report

Este módulo de Odoo permite generar un reporte detallado de IVA trasladado, acreditable y retenciones, mostrando las bases, impuestos y totales por cliente o proveedor.

## Características

- Reporte con 25 columnas:
  - Datos generales (partner, factura, fechas)
  - IVA trasladado (bases e impuestos)
  - IVA acreditable (bases e impuestos)
  - Retenciones (IVA e ISR)
  - Totales (subtotal sin IVA, IVA neto, total neto)
- Compatible con Odoo 18.
- Handler personalizado (`report_iva_cliente_cash_handler.py`).
- Definición de columnas en XML (`account.report.column`).

## Instalación

1. Copiar el módulo en la carpeta `custom-addons` de tu instalación de Odoo.
2. Actualizar la lista de módulos:
   ```bash
   odoo -u iva_cliente_cash_report
