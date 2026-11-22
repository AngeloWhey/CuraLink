"""Draw the actual KiCad-loaded copper, mask and paste for visual review."""
from pathlib import Path
import json
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

BASE=Path(__file__).resolve().parent
specs=json.loads((BASE/"footprint-audit.json").read_text())["footprints"]
parsed=json.loads((BASE/"footprint-loader-verification.json").read_text())["footprints"]
fig,axs=plt.subplots(1,3,figsize=(12,5.0))
for ax,s,r in zip(axs,specs,parsed):
    body=s["body_nominal_mm"]
    ax.add_patch(Rectangle((-body[0]/2,-body[1]/2),*body,fill=False,edgecolor="0.45",linestyle="--",lw=1.1))
    for p in r["numbered_pads"]:
        x,y=p["xy_mm"];w,h=p["copper_size_mm"];m=p["mask_margin_mm"]
        ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle="round,pad=0,rounding_size=0.05",facecolor="#cf741e",edgecolor="#a95911",lw=.8))
        ax.add_patch(Rectangle((x-w/2-m,y-h/2-m),w+2*m,h+2*m,fill=False,edgecolor="#168548",lw=1.0))
        ax.text(x,y,p["number"],ha="center",va="center",fontsize=9,color="black",weight="bold")
    for p in r["separate_paste_apertures"]:
        x,y=p["xy_mm"];w,h=p["copper_size_mm"]
        ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,fill=False,edgecolor="#2860bc",hatch="///",lw=.8))
    ax.text(-body[0]/2-.2,-body[1]/2-.12,"1",ha="center",va="center",fontsize=10,color="#b3261e",weight="bold")
    ax.set(xlim=(-1.8,1.8),ylim=(1.55,-1.55),xlabel="x (mm)",ylabel="y (mm)",aspect="equal")
    ax.set_title(s["mpn"]+"\n"+s["package"]+f" · {r['physical_electrical_pad_count']} copper pads",fontsize=11)
    ax.grid(alpha=.12)
fig.suptitle("Power footprint review — PCB top view, KiCad-loaded geometry",fontsize=14)
fig.text(.5,.025,"Orange: copper    Green: solder-mask opening    Blue hatch: separate paste apertures\nTerminal paste follows copper on DLH/DRV; all DSE apertures are separately defined.",ha="center",fontsize=10)
fig.tight_layout(rect=(0,.16,1,.91))
fig.savefig(BASE/"power-footprint-overlay.png",dpi=200)
fig.savefig(BASE/"power-footprint-overlay.svg")
