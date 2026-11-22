"""Create review front matter and append actual KiCad schematic PDF pages."""
from pathlib import Path
import csv,json,math,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.colors import HexColor,white
from pypdf import PdfReader,PdfWriter

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'hardware/rev-a'
TMP=ROOT/'tmp/pdfs'
PDF=ROOT/'output/pdf/curalink-rev-a-review.pdf'
NAVY=HexColor('#16354C'); TEAL=HexColor('#006B73'); GREY=HexColor('#52636C')
LIGHT=HexColor('#EFF4F5'); AMBER=HexColor('#8E4B00')
W,H=landscape(A3)

def figures():
    sys.path.insert(0,str(OUT/'afe'))
    from calculate_afe import Circuit
    f=np.geomspace(100,100000,320)
    cc=Circuit();y,_=cc.solve(f);h=y[:,cc.nodes['adc'],0]
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(7.2,3.2),layout='constrained')
    ax.semilogx(f,20*np.log10(abs(h)),color='#006b73',lw=2)
    ax.axvspan(300,7000,color='#006b73',alpha=.08)
    ax.axvline(43000,color='#8e4b00',ls=':',label='43 kHz first alias edge at 50 kS/s')
    ax.set(xlabel='Frequency (Hz)',ylabel='Gain (dB V/V)',xlim=(100,100000),ylim=(-25,65))
    ax.grid(alpha=.2);ax.legend(loc='lower left',fontsize=8)
    fig.savefig(TMP/'gain.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.2,3.2),layout='constrained')
    caps=np.linspace(0,100,101)
    for rs,col in [(47e3,'#006b73'),(100e3,'#8e4b00')]:
        vals=[]
        for cp in caps:
            c=Circuit(source=rs,ffc=cp*1e-12);z,_=c.solve([7000]);vals.append(100*(1-abs(z[0,c.nodes['chp'],0])))
        ax.plot(caps,vals,color=col,label=f'{rs/1000:g} kohm source')
    ax.set(xlabel='Assumed FFC capacitance per conductor (pF)',ylabel='Input voltage loss at 7 kHz (%)',xlim=(0,100))
    ax.grid(alpha=.2);ax.legend()
    fig.savefig(TMP/'loading.png',dpi=180);plt.close(fig)

def main():
    TMP.mkdir(parents=True,exist_ok=True);PDF.parent.mkdir(parents=True,exist_ok=True)
    figures()
    c=canvas.Canvas(str(TMP/'review.pdf'),pagesize=(W,H))
    c.setTitle('CuraLink Rev A schematic and engineering review')
    def txt(s,x,y,size=12,color=NAVY,bold=False):
        c.setFillColor(color);c.setFont('Helvetica-Bold' if bold else 'Helvetica',size);c.drawString(x,y,s)
    def para(s,x,y,width=510,size=12,leading=17):
        words=s.split();lines=[];line=''
        for word in words:
            test=line+' '+word if line else word
            if c.stringWidth(test,'Helvetica',size)>width and line:lines.append(line);line=word
            else:line=test
        lines.append(line)
        for line in lines:txt(line,x,y,size);y-=leading
        return y
    def head(title,n):
        c.setFillColor(NAVY);c.rect(0,H-86,W,86,fill=1,stroke=0)
        txt('CURALINK / REV A ENGINEERING HANDOFF',36,H-30,11,white,True)
        txt(title,36,H-62,25,white,True)
        txt('2026-10-02 | America/New_York | Candidate schematic, PCB and models; not fabrication released',36,28,10,GREY)
        txt(str(n),W-45,28,11,GREY)
    def box(x,y,w,h,title,body):
        c.setFillColor(LIGHT);c.roundRect(x,y,w,h,7,fill=1,stroke=0)
        txt(title,x+12,y+h-24,13,TEAL,True)
        para(body,x+12,y+h-45,w-24,11,15)
    def rowtable(rows,x,y,widths,fontsize=11):
        for i,row in enumerate(rows):
            maxlines=[]
            for j,s in enumerate(row):
                words=str(s).split();lines=[];line=''
                for word in words:
                    test=line+' '+word if line else word
                    if c.stringWidth(test,'Helvetica',fontsize)>widths[j]-16 and line:lines.append(line);line=word
                    else:line=test
                lines.append(line);maxlines.append(lines)
            rh=max(30,max(len(ls) for ls in maxlines)*15+12)
            c.setFillColor(NAVY if i==0 else (LIGHT if i%2 else white));c.rect(x,y-rh,sum(widths),rh,fill=1,stroke=0)
            xx=x
            for j,ls in enumerate(maxlines):
                for k,line in enumerate(ls):txt(line,xx+8,y-20-k*15,fontsize,white if i==0 else NAVY,i==0)
                xx+=widths[j]
            y-=rh
        return y
    head('Architecture and recommended acquisition',1)
    y=H-116
    y=para('Recommendation: use STM32WBA52CGU6 ADC acquisition with digital thresholds and count bins. This retains the selected MCU family and gives waveform visibility for first-board debugging. A whole-system power advantage over comparators is not yet measured.',36,y,W-72,14,20)
    y-=18
    rowtable([
        ['Choice','Advantages','Qualification / tradeoff'],
        ['Analog comparator events','Avoid continuous conversions; direct event pulses.','Threshold, hysteresis, bipolar detection and recovery need extra circuits; less diagnostic evidence.'],
        ['ADC and digital detection - recommended','Adjustable thresholds/baseline; channel calibration; diagnostic waveforms.','ADC/BLE ownership, settling, aliases, continuity and power must be demonstrated.']
    ],36,y,[260,430,W-762],12)
    txt('SIGNAL PATH - EIGHT CHANNELS PLUS ONE SHARED REF',36,493,13,TEAL,True)
    blocks=[('Input / REF','Low-C ESD\n5.1 kohm / 10 nF'),('Preamp x11','TLV9004\n22 Mohm bias return'),('HP / difference','311 Hz / x35.58\nREF minus CH'),('LP section 1','7.04 kHz / x1.15\nLow Q / TLV9004'),('LP section 2','7.04 kHz / x2.24\nHigh Q / TLV9054'),('ADC interface','150 ohm / 470 pF\n1.656 us candidate')]
    gap=12;bw=(W-72-5*gap)/6
    for i,(title,body) in enumerate(blocks):
        x=36+i*(bw+gap);box(x,372,bw,100,title,body.replace('\n',' / '))
        if i<5:
            c.setStrokeColor(TEAL);c.line(x+bw+2,420,x+bw+gap-2,420)
    txt('POWER POLICY - HARDWARE CHARGE / RUN EXCLUSION',36,333,13,TEAL,True)
    box(36,183,(W-84)/2,128,'CHARGE: field present, recording rails OFF',
        'Qualified 5 V input -> polarity/eFuse -> BQ25185 -> protected-pack interface. Provisional 20 mA / 4.1 V; cell-mounted NTC. Charge enable waits for RUN rails to discharge. Receiver link and unqualified PCM remain DNP in bench build.')
    box(W/2+6,183,(W-84)/2,128,'RUN: field absent, battery valid',
        'Battery -> opposed PMOS isolation -> fault limiter -> 3 V digital LDO -> digital-good supervisor -> 3 V analog LDO and 1.5 V midpoint. Nominal UVLO: 3.50 V cutoff / 3.80 V restart. Count bins and short diagnostic captures over BLE.')
    para('The circuit preserves a bench neural-like-signal prototype. The published WPT coil efficiency, LCSC stock and a clean ERC do not establish charging performance, cell compatibility, RF match or a manufacturing release.',36,143,W-72,12,17)
    c.showPage()
    head('Actual LTspice frequency response and DC rejection',2)
    data=json.loads((OUT/'afe/afe-calculations.json').read_text())
    rowtable([
        ['Quantity','Actual simulation / retained calculation','Boundary / limitation'],
        ['LTspice equilibrium','All 36 units valid; ADC 1.503360 V; VMID 1.500596 V','Original-equation TI family macros; nominal 3 V and passives'],
        ['Gain and band','969.744 V/V at 1 kHz; sampled -3 dB band 316 Hz-6.88 kHz','47 kohm source / 20 pF FFC; not measured response'],
        ['DC offset sweep','18.36 uV total ADC baseline change across +/-100 mV','Declared 10 Gohm insulation across coupling capacitors, 25 C; PCB leakage not qualified'],
        ['Noise / 300-7000 Hz','3.44 uVrms electronics; 3.17 uVrms source; 4.68 total','Typical density fits; ideal VMID; excludes ADC/layout/interference'],
        ['AFE current','4.474 mA in LTspice including midpoint divider','Nominal model; excludes MCU and power control'],
        ['Unmet input target','About 3 Mohm at 7 kHz even with zero FFC','Existing >=10 Mohm requirement retained; alternative limits pending']
    ],36,H-112,[250,380,W-702],12)
    c.drawImage(str(OUT/'ltspice/afe/figures/frequency-response.png'),36,156,width=(W-92)/2,height=260,preserveAspectRatio=True,mask='auto')
    c.drawImage(str(OUT/'ltspice/afe/figures/dc-rejection-leakage.png'),W/2+10,156,width=(W-92)/2,height=260,preserveAspectRatio=True,mask='auto')
    para('Actual saved LTspice raw data. The earlier full-AFE ngspice adapter failure remains invalid historical evidence; the original-equation LTspice model now gives valid nominal equilibria. These results do not establish noise, ESD or real ADC accuracy.',36,127,W-72,12,17)
    para('50/60 Hz differential attenuation is only 15.7/14.1 dB versus 1 kHz: this is not a mains notch. Alias-edge rejection is 43.13 dB at 23 kHz / 68.59 dB at 43 kHz. The retained periodic 7 kHz / 10 pF driver total error is 196.83 uV (0.269 LSB), above the quarter-LSB engineering target.',36,83,W-72,11,15)
    c.showPage()
    head('Actual LTspice startup and offset recovery',3)
    rowtable([
        ['Fixture','Actual nominal result','Design implication'],
        ['Cold startup, 0-to-3 V in 1 ms','Quarter ideal LSB reached after 2.336 s; residual at 2 s: -531 uV','The earlier 2 s startup delay fails this check. Candidate 3 s blank plus validity checks; no PVT guarantee.'],
        ['CH1 +/-100 mV offset steps','ADC reaches 0.0149-2.9851 V; later stages saturate','Steady DC rejection does not prevent step or hotplug artifacts.'],
        ['Shared bias / recovery','Unexcited channel about 8 mVpp; quarter-LSB recovery after 1.585 s','Blank and qualify the shared AFE after an event; 2 s recovery covers only this tested sequence.']
    ],36,H-116,[260,410,W-742],12)
    c.drawImage(str(OUT/'ltspice/afe/figures/startup.png'),36,151,width=(W-92)/2,height=315,preserveAspectRatio=True,mask='auto')
    c.drawImage(str(OUT/'ltspice/afe/figures/offset-recovery.png'),W/2+10,151,width=(W-92)/2,height=315,preserveAspectRatio=True,mask='auto')
    para('Use rail, baseline and clipping validity checks before accepting counts. All external inputs are grounded in the startup case. The family macro below its rated supply is not guaranteed; these runs omit regulator/interlock dynamics, PCB contamination, actual ADC and RF activity.',36,125,W-72,12,17)
    para('The startup deck ends at 2.4 s: 3 s is a proposed guard interval, not a directly sampled or guaranteed settling result. Recovery is evaluated against the independently inspected powered equilibrium, rather than the last sample alone.',36,78,W-72,11,15)
    c.showPage()
    head('Power OVP: tested nodes and limits',4)
    rowtable([
        ['Fixture / correction','Actual result','Boundary'],
        ['Independent eFuse startup','RAW 5 V -> CHG_IN 4.722 V; RAW 6.5 V -> 5.399 V; high faults turn off','Nominal TI-derived transient macro; raw source includes the SS14 drop'],
        ['1 us RAW 5-to-18 V ramp, 1 uF input/output','CHG_IN peak 5.868 V; control-LDO input 4.650 V','Overshoot exceeds the static clamp maximum. 18 V is a stress fixture, not an approved board supply.'],
        ['Physical-pin and tolerance repairs','TPS25200 OUT1/ILIM2/FAULT3/EN4/GND5/IN6; SS14 A1/K2; R511 1 Mohm','Earlier source maps were wrong. Fresh CAD and exact-pin invariants pass; audit physical pads in Altium.'],
        ['Current limit / battery','Approximate eFuse bound 56.9-138.4 mA','Equipment limiter, not guaranteed 50 mA cell OCP. Charger/cell model and compatible PCM remain unqualified.']
    ],36,H-116,[280,410,W-762],12)
    c.drawImage(str(OUT/'ltspice/power/results/protected-control-faults.png'),36,160,width=(W-92)/2,height=280,preserveAspectRatio=True,mask='auto')
    c.drawImage(str(OUT/'ltspice/power/results/ovp-static-boundaries.png'),W/2+10,160,width=(W-92)/2,height=280,preserveAspectRatio=True,mask='auto')
    para('Left: actual TI-derived transient models and regulator-pin peaks. Right: separately authored datasheet-bound DC calculations, not a manufacturer transistor model. The TPS25200 macro DC sweep returned NaNs and is explicitly rejected. Effective MLCC capacitance and silicon/thermal corners remain hardware checks.',36,128,W-72,12,17)
    para('Protection remains bounded: raw RF nodes and PACK+ branches before the eFuse are not clamped; a failed-high LDO or externally driven 3 V rail/AFE pin is not covered. Initial source is current-limited 4.75-5.25 V bench DC with a battery emulator. No lithium or receiver release is implied.',36,76,W-72,11,15)
    c.showPage()
    head('CAD verification and release checks',5)
    vr=json.loads((OUT/'verification-report.json').read_text())
    rowtable([
        ['Completed','Evidence'],
        ['Editable CAD and pin transfer',f'{vr["physical_components"]} physical components; {vr["connected_pins_compared"]} connected pins and {vr["intentional_NC_pins_compared"]} intentional NC pins match KiCad-exported connectivity.'],
        ['Electrical rule check','KiCad 9.0.9: zero errors, warnings or excluded findings. Supply-through-isolation flags are explicit; ERC is not behavioral validation.'],
        ['Procurement / 2026-10-02','All 80 current BOM SKUs + cable have sufficient immediate LCSC stock for one board, including DNP. MCU stock: 9. Cell C19632326 globally unconfirmed. MOQ subtotal ~$103.55 excludes cell/PCB/assembly/freight; final quote remains open.'],
        ['Model record','Actual LTspice DC/AC/startup/recovery and power faults; original model/provenance hashes; retained noise/loading/driver calculations. Invalid diagnostics explicitly rejected.']
    ],36,H-116,[330,W-402],12)
    txt('CLOSE BEFORE FABRICATION / BATTERY OPERATION',36,461,14,AMBER,True)
    gates=[
        ('1. Loading requirement','Accept measured amplitude/phase limits or redesign the input/FFC architecture to meet >=10 Mohm. The present candidate cannot be called compliant.'),
        ('2. Cell and receiver boundaries','Global cell sourcing and a compatible independent protector / documented protected pack are not yet qualified. Begin with battery emulator and bench 5 V. WPT DC/stress qualification remains separate.'),
        ('3. MCU timing and real signal behavior','Prefer 50 kS/s/channel: a 48 MHz / 79.5-cycle eight-channel scan takes 15.33 us in a 20 us frame. A 17.23 us temperature conversion needs separate service. Prove ADC ownership, continuity, noise, recovery and measured current.'),
        ('4. Altium and manufacture','Audit every symbol-to-pad mapping and exact land pattern, including RUC op amps with no EP, MCU EP, RF CSP, antenna anchor and FFC orientation. Complete PCB DRC, MLCC bias audit, assembly eligibility and budget quote.')]
    y=432
    for title,body in gates:
        txt(title,36,y,13,TEAL,True);y=para(body,36,y-21,W-72,12,17)-17
    para('Primary sources and detailed derivations: hardware/rev-a/README.md; afe/AFE-design-review.md; mcu/mcu-design.md; power/power-design.md. The following pages are the actual connected KiCad schematic export, with global labels and exact physical pin numbers.',36,110,W-72,11,15)
    c.showPage()
    head('Candidate mainboard and signal-integrity findings',6)
    board_image=OUT/'pcb/figures/board-placement.png'
    c.drawImage(str(board_image),36,150,width=730,height=590,preserveAspectRatio=True,anchor='c',mask='auto')
    xx=800;ww=W-xx-36
    box(xx,554,ww,177,'EDITABLE MAINBOARD / CANDIDATE',
        '80 x 74 mm; 446 physical references and 30 assigned footprint types. Four copper layers: surface signals with two internal ground planes. Forward eight-channel AFE banks; local ADC/bypass access; separate lower power region. The original compact-size objective remains open.')
    box(xx,340,ww,193,'ACTUAL LTSPICE CROSSTALK',
        'Shared VMID gives -52.22 dB worst at 300 Hz: 0.490 uVpp equivalent for 200 uVpp or 2.449 uVpp for 1 mVpp. An assumed 0.01 pF amplified-output-to-input path gives 17.25 uVpp equivalent for 1 mVpp. These are nominal/sensitivity results, not extracted PCB parasitics. Proposed -60 dB criterion is unaccepted and unmet.')
    box(xx,156,ww,163,'CLOSE PHYSICAL AND CIRCUIT GATES',
        'RF filter ground/stack adaptation remains open; RF feed routing is excluded. Input loading, shared bias/package coupling, routing/DRC, FFC orientation, EP via/paste process, cell protection and measured behavior remain release gates. Read pcb/README.md and signal-integrity/README.md for current checks and board hashes.')
    para('The illustration is generated from actual native PCB geometry. It is a review artifact, not a manufacturing drawing or proof of signal integrity. The larger floorplan and routing remain Candidate choices; no assembly order or fabrication approval is implied.',36,113,W-72,12,17)
    c.showPage();c.save()
    writer=PdfWriter()
    for file in [TMP/'review.pdf',TMP/'schematic.pdf']:
        for page in PdfReader(file).pages: writer.add_page(page)
    writer.add_metadata({'/Title':'CuraLink Rev A schematic, PCB and engineering review','/Author':'CuraLink engineering record','/Subject':'Candidate implementation and nominal simulation; not fabrication released'})
    with PDF.open('wb') as f: writer.write(f)
    print(json.dumps({'pdf':str(PDF),'pages':len(writer.pages)},indent=2))

if __name__=='__main__':main()
