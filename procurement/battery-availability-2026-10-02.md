# Battery sourcing check

**Checked 2026-10-02 using the client date, America/New_York. Research only; no accepted baseline or canonical BOM changed.**

The battery must be an orderable LCSC 1S Li-ion/LiPo cell, support the charger's worst-case current around the provisional 20 mA setting and 4.1 V regulation, deliver the complete system's continuous/peak current, and leave enough usable capacity for the one-hour objective. A protected pack with a manufacturer specification is preferable to an unidentified bare cell. Physical pack dimensions, connector polarity and temperature limits also matter.

**The accepted Taisko 401020-55mah / C19632326 is not confirmed as a globally orderable LCSC purchase.** The fresh [LCSC detail API](https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=C19632326) returned a null product record; its [public global product URL](https://www.lcsc.com/product-detail/C19632326.html) returned HTTP 404; exact-code global search returned zero products. These are availability failures, not a disclosed numerical stock count. Do not substitute zero for unknown stock or claim a definitive global export prohibition.

The [primary JLCPCB listing](https://jlcpcb.com/partdetail/Taisko-40102055mah/C19632326) still identifies the exact cell and its assembly category, but provides no verified inventory in the retrieved response. It states that parts-library purchases cannot ship separately. A JLCPCB catalog listing therefore does not establish a separately orderable LCSC cell or a confirmed assembled-pack shipment. The page's “Wave Soldering” label is not a manufacturer permission to heat/reflow the pouch cell.

**Search trap:** the exact-looking query `401020-55mah` silently returned an unrelated crystal, C5526774 / 7V-45.835555MAHQ-T. It was rejected because neither code nor model matches. Preserve exact identity checks for future stock work.

Alternative research covered the prior C19632322 / 302020-100mah candidate, several common pouch-cell model strings, PGEB201212, and rechargeable-battery queries. No stocked, exactly identified global LCSC LiPo replacement with a manufacturer specification was verified. LCSC's current global “Batteries Rechargeable (Secondary)” category search reports two listed products with the stock filter off and zero with it on; broad stocked battery searches return holders/clips rather than cells. These searches do not prove that no regional, private or supplier-assisted option exists.

The [manufacturer PS-401020-01 Rev A](https://atta.szlcsc.com/upload/public/pdf/source/20250905/9CA17359854FCF37A94D02BC391F6AF0.pdf) remains a valid electrical reference: 55 mAh typical / 50 mAh minimum, nominal 3.7 V, 4.2 V charge and 3.0 V discharge endpoints. Its charge/discharge limits depend on temperature, and nominal capacity is measured after its specified full-charge/termination procedure. Thus the 20 mA / 4.1 V configuration remains conditional on current tolerance, temperature control, independent protection and measured usable capacity; sourcing is a separate unresolved issue.

**Recommendation:** retain the accepted cell as the electrical design reference while marking procurement unconfirmed. Obtain exact cell/pack supply and shipping confirmation through the user's chosen assembly route before committing to the battery. If that fails, reopen the sourcing constraint or cell baseline explicitly; do not silently replace it with a coin-cell chemistry, a holder, an undocumented pack or a lower-capacity cell. No verified LCSC replacement SKU can be recommended from this audit.

Evidence is saved in [battery-availability-2026-10-02.json](battery-availability-2026-10-02.json) and the [raw-response directory](battery-raw-2026-10-02/).
