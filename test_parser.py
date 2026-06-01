"""Test del parser con textos de ejemplo (datos ficticios).

Las fixtures imitan la estructura/etiquetas de 3 formatos reales (ticket de
supermercado, factura electrónica y factura de banco) pero con nombres y
RUCs inventados. No contienen datos de terceros.
"""
import json
from app.parser import parsear

FIXTURES = {
    "ticket_supermercado": """COMERCIAL EJEMPLO
Supermercados
R.U.C.: 80011122-3
Timbrado: 14685794
I.V.A. Incluido
Vigencia Timbrado: 01-MAR-2021
Vencimiento Timbrado: 31-MAR-2022
FACTURA Nr0.: 001 015 0014506
7842542000178 VAS0 GUA.RAYA R UN-1
10%
10,800 X
1.000
10,800
P
Importe Total Gs.
21,600
EFECTIVO GUARANI G$.
22,500
Su Vuelto
900
TOTALES:
Exentas
G5.1
0
Gravadas 5% Gs.:
(
Gravadas 10% Gs.:
21,600
LIQUIDACION DEL I.V.A.:
I.V.A.
5% Gs.
0
I.V.A.
10% Gs-:
1,964
Total I.V.A....
1,964
Fecha Exp: 31/12/2021 09:34:58 AM
Cliente: CLIENTE EJEMPLO S.A
R.U.C. : 80044455-6
Tipo Factura : CONTADO""",

    "factura_electronica": """EMPRESA EJEMPLO
%
EMPRESA EJEMPLO S.A.
RUC: 80011122-3
TIMBRADO: 18166533
INICIO DE VIGENCIA: 15/07/2025
FACTURA ELECTRONICA: 001-001-0026820
CONDICION DE VENTA: CONTADO
FECHA DE EMISION: 31/12/2025 08:53:46
CLIENTE: "CLIENTE EJEMPLO" SOCIEDAD ANÓNIMA
RUC: 80044455-6
GRAVADO 5%
GRAVADO 10%
0
0
29.300
2.663
TOTAL
29.300""",

    "factura_banco": """BANCO EJEMPLO
KuDE de Factura electrónica
RUC: 80011122-3
Timbrado N°: 14722988
BANCO EJEMPLO SAECA
Inicio de vigencia: 12/03/2021
Factura electrónica
N°: 001-001-7719249
Fecha y hora de emisión: 31/12/2025 00:00:00
Cond. de venta:
Contado
RUC/documento de identidad: 80044455-6
Nombre o razón social: CLIENTE EJEMPLO SOCIEDAD ANÓNIMA
Moneda: Guarani
SUBTOTAL
0
O
128.334
TOTAL A PAGAR: GUARANÍES
128.334
LIQUIDACIÓN IVA
5%
0
10%
11.667
TOTAL IVA
11.667""",
}

for nombre, texto in FIXTURES.items():
    print(f"\n===== {nombre} =====")
    print(json.dumps(parsear(texto, texto.split("\n")), indent=2, ensure_ascii=False))
