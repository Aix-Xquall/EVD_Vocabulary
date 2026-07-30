# Vocabulary Translation and Ordering Audit

Audit date: 2026-07-31

## Scope

- Reviewed 681 source rows in the seven formal chapter CSV files.
- Did not modify `vocabulary/hard_words.csv`; it remains a Google Sheet snapshot.
- Kept examples, review counts, review dates, and audio text unchanged in surviving rows.
- Corrected 24 Chinese meanings where terminology was inaccurate or inconsistent.
- Removed 15 cross-chapter duplicate rows, leaving 666 unique formal words.

## Terminology Corrections

| Area | Normalized wording |
| --- | --- |
| EMC susceptibility | 電磁易感性；易受干擾性 |
| Compliance | 符合性；合規 |
| Requirement | 要求；需求 |
| Bonding | 搭接；等電位連接 |
| Ground loop | 接地迴路 |
| Shield termination | 屏蔽層端接 |
| Data Acquisition (DAQ) | 資料擷取 |
| EMC chamber | EMC 測試室；電磁相容性測試室 |
| HERO | 電磁輻射對軍械／火工品的危害 |
| P-static | 降水靜電 |
| Counterpoise | 天線平衡地網；天線配重地網 |
| Onboard | 機載的；機上的 |
| Bonding strap | 搭接帶；編織帶 |
| Busbar | 匯流排；母排；銅排 |

## Ordering Changes

- Added an `Electrical / EMC Fundamentals` group to `EMC航電詞彙整合1.csv`.
- Moved `resistance`, `inductance`, `capacitance`, `reactance`, `impedance`, and `coupling` into that group.
- Kept foundational words before derived terms such as `low-impedance path`, `RF impedance`, `parasitic capacitance`, `harness coupling`, and `coupling path`.
- Grouped split categories back together while preserving the established chapter ownership of other words.
- Corrected local dependency order, including `victim` before `source-victim matrix`, `chicken` before `chicken rice`, and `refund` before `tax refund`.

## Duplicate Cleanup

- Kept the first formal occurrence according to chapter order.
- Removed 13 repeated rows from `EMC航電詞彙整合2.csv`.
- Removed repeated `copper foil` and `fastener` rows from `複合材質航電環.csv`.
- Did not delete cached TTS files; removed rows are no longer referenced by the generated website.

## Authoritative References

- NASA-HDBK-4001A, Electrical Grounding Architecture for Unmanned Spacecraft:
  https://standards.nasa.gov/system/files/tmp/NASA-HDBK-4001A_Final_07152025_0.pdf
- NASA-STD-4003A, Electrical Bonding for NASA Launch Vehicles, Spacecraft, Payloads, and Flight Equipment:
  https://standards.nasa.gov/system/files/tmp/NASA-STD-4003A_w-Change%201%20-%20Revalidated%2003-13-2026.pdf
- DLA Quick Search, MIL-STD-461:
  https://quicksearch.dla.mil/qsdocdetails.aspx?ident_number=35789
- IEC Electropedia, impedance:
  https://www.electropedia.org/iev/iev.nsf/display?ievref=801-25-13&openform=
- IEC Electropedia, equipotential bonding:
  https://www.electropedia.org/iev/iev.nsf/display?ievref=195-01-10&openform=
- IEC Electropedia, electromagnetic compatibility:
  https://www.electropedia.org/iev/iev.nsf/display?ievref=161-01-07&openform=
- FAA Order 6750.54, Nondirectional Radio Beacon Systems:
  https://www.faa.gov/documentLibrary/media/Order/6750_54.pdf
- Singapore Land Transport Authority, Rail Network:
  https://www.lta.gov.sg/content/ltagov/en/getting_around/public_transport/rail_network.html
- Cambridge Dictionary:
  https://dictionary.cambridge.org/
