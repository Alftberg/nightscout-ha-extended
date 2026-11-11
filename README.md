# Nightscout Extended

Nightscout Extended v0.1.0 läser glukos och Loop-telemetri från Nightscout API v1 till Home Assistant. Integrationen hämtar data varje minut och kräver Home Assistant 2026.1.0 eller senare.

| Entitet | Källa |
| --- | --- |
| Glukos, trend och mättid | `entries/sgv` |
| Aktivt insulin (IOB), aktiva kolhydrater (COB), Loop-resultat och rapporttid | `devicestatus.loop` |
| Insulinreserv och batteri | `devicestatus.pump` |

Glukos hämtas i mg/dL. Home Assistant hanterar visningsenheten för glukossensorn. Loop-resultatet visar utfallet i senaste aktuella Loop-rapporten. Saknade eller mer än 15 minuter gamla värden visas som okända. Mättiden för glukos kan fortfarande visas så att du kan se när senaste värdet kom in. Vid anslutningsfel blir entiteterna otillgängliga.

## Installera via HACS

1. Öppna **HACS → ⋮ → Custom repositories**.
2. Lägg till [Alftberg/nightscout-ha-extended](https://github.com/Alftberg/nightscout-ha-extended) med kategorin **Integration**.
3. Ladda ned **Nightscout Extended** och starta om Home Assistant.
4. Öppna **Inställningar → Enheter och tjänster → Lägg till integration → Nightscout Extended**.
5. Ange Nightscouts basadress, exempelvis `https://nightscout.example.org`. Ange en Nightscout-token med läsbehörighet om servern kräver det. Använd HTTPS för en fjärranslutning.

Diagnostikfilen innehåller enbart status för senaste hämtningen. Konfigurera adress och token i Home Assistant. Tester använder syntetiska data.

## Lokala kontroller

```sh
python3 -m compileall -q custom_components
python3 -m unittest discover -s tests -v
```
