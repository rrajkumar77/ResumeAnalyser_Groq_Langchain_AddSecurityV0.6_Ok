const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType, VerticalAlign,
  HeadingLevel, LevelFormat, PageNumber, Header, Footer
} = require('docx');
const fs = require('fs');

// ── Sample data (replace with dynamic data from app) ──────────────────────────
const data = {
  candidateName: "Ramanan S",
  jdTitle: "Data Analyst – Caterpillar",
  overallScore: 88,
  fitLabel: "Strong Fit",
  execSummary: "The candidate aligns very well with the Data Analyst role, especially in BI development, ETL automation, KPI reporting, and BigQuery/GCP capabilities.",

  strengths: [
    {
      title: "Advanced BI & Visualization (Power BI, Tableau)",
      evidence: "Built 30+ Power BI dashboards; experience in KPI tracking and ROI reporting."
    },
    {
      title: "BigQuery & Cloud Experience",
      evidence: "Processes 100M+ rows monthly using Google BigQuery; uses GCP VMs."
    },
    {
      title: "ETL Automation & Pipeline Optimization",
      evidence: "SSIS & Mage pipeline automation reducing reporting time by 80% and manual errors by 95%."
    },
    {
      title: "Business Impact & Insight Delivery",
      evidence: "Improved ad budget by 20% and ROI by 12% through analytics."
    }
  ],

  gaps: [
    {
      title: "No Qlik Experience",
      detail: "JD explicitly lists Qlik; candidate lacks this skill."
    },
    {
      title: "Limited Data Modeling / Architecture Detail",
      detail: "JD requires solution architecture; resume does not highlight this."
    },
    {
      title: "No Explicit Collaboration with Data Engineering / Data Science Teams",
      detail: "JD requires cross-functional partnership; resume does not state this clearly."
    }
  ],

  recommendation: "Proceed to next round. Candidate offers strong alignment in analytics, BI, automation, big data processing, and stakeholder insights. Gaps are minor and can be validated in technical rounds.",

  responsibilities: [
    { jd: "Build partnerships through interviews and designing solutions",    resume: "Provided weekly insights leading to 20% budget increase and 12% ROI improvement" },
    { jd: "Own metrics, dashboards, reports",                                 resume: "Built 30+ Power BI dashboards; automated reporting" },
    { jd: "Use visualization tools (Qlik, Tableau, Power BI)",               resume: "Strong Power BI; some Tableau; no Qlik" },
    { jd: "Deep-dive data issue analysis",                                    resume: "Conducted RCA, improved data quality by 60%" },
    { jd: "Optimize analytics tools/methods",                                 resume: "ETL automation cut reporting time by 80%" },
    { jd: "Create metrics & KPIs",                                            resume: "Developed KPI dashboards for Uber & real estate" },
    { jd: "Collaborate with Data Engineering/Science",                        resume: "Not explicitly mentioned" }
  ],

  skillMatch: [
    { skill: "Power BI",              candidate: "Yes",              match: "✅ Strong"  },
    { skill: "Data Conversion",       candidate: "SSIS, ETL",        match: "✅ Strong"  },
    { skill: "Big Query",             candidate: "Extensive",        match: "✅ Strong"  },
    { skill: "Data Analysis",         candidate: "Extensive",        match: "✅ Strong"  },
    { skill: "Data Collection",       candidate: "Yes",              match: "✅ Good"    },
    { skill: "Dashboards",            candidate: "30+",              match: "✅ Strong"  },
    { skill: "Google Cloud Platform", candidate: "Yes",              match: "✅ Strong"  },
    { skill: "Business Analytics",    candidate: "Strong",           match: "✅ Strong"  },
    { skill: "Qlik, Tableau",         candidate: "Tableau only",     match: "⚠️ Partial" }
  ],

  gapTable: [
    { requirement: "Proficiency in Qlik",              gap: "No Qlik experience"    },
    { requirement: "Technical data modeling",           gap: "Not mentioned"         },
    { requirement: "Collaboration with DE/DS",          gap: "Not explicit"          },
    { requirement: "Multiple visualization tools",      gap: "Primarily Power BI"    }
  ]
};

// ── Colour palette ─────────────────────────────────────────────────────────────
const C = {
  headerBg:     "1F4E79",   // dark navy
  headerText:   "FFFFFF",   // white
  sectionBg:    "2E74B5",   // blue
  sectionText:  "FFFFFF",
  strengthBg:   "E2EFDA",   // light green
  strengthHdr:  "375623",
  gapBg:        "FCE4D6",   // light red/orange
  gapHdr:       "843C0C",
  recBg:        "EBF3FB",   // light blue
  tableHdr:     "D5E8F0",   // table header blue
  altRow:       "F5F9FD",   // alternate row
  scoreBg:      "00B050",   // green for strong
  border:       "BFBFBF",
  text:         "2E2E2E"
};

// ── Helpers ────────────────────────────────────────────────────────────────────
const border = (color = C.border) => ({
  top:    { style: BorderStyle.SINGLE, size: 4, color },
  bottom: { style: BorderStyle.SINGLE, size: 4, color },
  left:   { style: BorderStyle.SINGLE, size: 4, color },
  right:  { style: BorderStyle.SINGLE, size: 4, color }
});

const noBorder = () => ({
  top:    { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  left:   { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  right:  { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }
});

const cell = (text, opts = {}) => new TableCell({
  borders: opts.borders || border(),
  shading: { fill: opts.fill || "FFFFFF", type: ShadingType.CLEAR },
  verticalAlign: opts.vAlign || VerticalAlign.CENTER,
  margins: { top: 100, bottom: 100, left: 150, right: 150 },
  width: { size: opts.width || 4680, type: WidthType.DXA },
  children: [
    new Paragraph({
      alignment: opts.align || AlignmentType.LEFT,
      children: [
        new TextRun({
          text,
          bold: opts.bold || false,
          color: opts.color || C.text,
          size: opts.size || 20,
          font: "Arial"
        })
      ]
    })
  ]
});

const sectionHeading = (text) => new Paragraph({
  spacing: { before: 260, after: 80 },
  children: [
    new TextRun({
      text,
      bold: true,
      size: 26,
      color: C.sectionBg,
      font: "Arial"
    })
  ]
});

const spacer = (pt = 120) => new Paragraph({
  spacing: { before: pt, after: 0 },
  children: [new TextRun({ text: "" })]
});

// ── Score badge (colored table cell) ──────────────────────────────────────────
const scoreBadge = (score, label) => new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [9360],
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders: noBorder(),
          shading: { fill: score >= 75 ? "00B050" : score >= 60 ? "FFC000" : "FF0000", type: ShadingType.CLEAR },
          margins: { top: 160, bottom: 160, left: 200, right: 200 },
          width: { size: 9360, type: WidthType.DXA },
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [
                new TextRun({ text: `Overall Match Score: ${score}%  —  ${label}`, bold: true, size: 32, color: "FFFFFF", font: "Arial" })
              ]
            })
          ]
        })
      ]
    })
  ]
});

// ── Section banner ─────────────────────────────────────────────────────────────
const banner = (text, fill = C.sectionBg) => new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [9360],
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders: noBorder(),
          shading: { fill, type: ShadingType.CLEAR },
          margins: { top: 100, bottom: 100, left: 160, right: 160 },
          width: { size: 9360, type: WidthType.DXA },
          children: [
            new Paragraph({
              children: [
                new TextRun({ text, bold: true, size: 24, color: "FFFFFF", font: "Arial" })
              ]
            })
          ]
        })
      ]
    })
  ]
});

// ── Strength card ──────────────────────────────────────────────────────────────
const strengthCard = (title, evidence) => new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [400, 8960],
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders: noBorder(),
          shading: { fill: "00B050", type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 100, right: 100 },
          width: { size: 400, type: WidthType.DXA },
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "✅", size: 22, font: "Arial" })] })]
        }),
        new TableCell({
          borders: { top: { style: BorderStyle.SINGLE, size: 4, color: "00B050" }, bottom: { style: BorderStyle.SINGLE, size: 4, color: "00B050" }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.SINGLE, size: 4, color: "00B050" } },
          shading: { fill: C.strengthBg, type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 160, right: 160 },
          width: { size: 8960, type: WidthType.DXA },
          children: [
            new Paragraph({ children: [new TextRun({ text: title, bold: true, size: 22, color: C.strengthHdr, font: "Arial" })] }),
            new Paragraph({ children: [new TextRun({ text: evidence, size: 20, color: C.text, font: "Arial" })] })
          ]
        })
      ]
    })
  ]
});

// ── Gap card ──────────────────────────────────────────────────────────────────
const gapCard = (title, detail) => new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [400, 8960],
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders: noBorder(),
          shading: { fill: "FF0000", type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 100, right: 100 },
          width: { size: 400, type: WidthType.DXA },
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "❌", size: 22, font: "Arial" })] })]
        }),
        new TableCell({
          borders: { top: { style: BorderStyle.SINGLE, size: 4, color: "FF0000" }, bottom: { style: BorderStyle.SINGLE, size: 4, color: "FF0000" }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.SINGLE, size: 4, color: "FF0000" } },
          shading: { fill: C.gapBg, type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 160, right: 160 },
          width: { size: 8960, type: WidthType.DXA },
          children: [
            new Paragraph({ children: [new TextRun({ text: title, bold: true, size: 22, color: C.gapHdr, font: "Arial" })] }),
            new Paragraph({ children: [new TextRun({ text: detail, size: 20, color: C.text, font: "Arial" })] })
          ]
        })
      ]
    })
  ]
});

// ── Recommendation box ─────────────────────────────────────────────────────────
const recBox = (text) => new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [9360],
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders: border("2E74B5"),
          shading: { fill: C.recBg, type: ShadingType.CLEAR },
          margins: { top: 140, bottom: 140, left: 200, right: 200 },
          width: { size: 9360, type: WidthType.DXA },
          children: [
            new Paragraph({ children: [new TextRun({ text: "💡 Recommendation", bold: true, size: 24, color: C.sectionBg, font: "Arial" })] }),
            spacer(60),
            new Paragraph({ children: [new TextRun({ text, size: 20, color: C.text, font: "Arial" })] })
          ]
        })
      ]
    })
  ]
});

// ── Table header row helper ────────────────────────────────────────────────────
const tblHdrRow = (labels, widths) => new TableRow({
  tableHeader: true,
  children: labels.map((lbl, i) => new TableCell({
    borders: border(C.sectionBg),
    shading: { fill: C.tableHdr, type: ShadingType.CLEAR },
    margins: { top: 100, bottom: 100, left: 150, right: 150 },
    width: { size: widths[i], type: WidthType.DXA },
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: lbl, bold: true, size: 20, color: C.sectionBg, font: "Arial" })] })]
  }))
});

const tblDataRow = (values, widths, rowIndex) => new TableRow({
  children: values.map((val, i) => {
    const isMatch = widths.length === 3 && i === 2;
    const matchColor = val.startsWith("✅") ? "375623" : val.startsWith("⚠️") ? "843C0C" : C.text;
    return new TableCell({
      borders: border(),
      shading: { fill: rowIndex % 2 === 0 ? "FFFFFF" : C.altRow, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 150, right: 150 },
      width: { size: widths[i], type: WidthType.DXA },
      children: [new Paragraph({ children: [new TextRun({ text: val, size: 20, color: isMatch ? matchColor : C.text, bold: isMatch, font: "Arial" })] })]
    });
  })
});

// ── Build Document ─────────────────────────────────────────────────────────────
const doc = new Document({
  numbering: { config: [] },
  styles: {
    default: { document: { run: { font: "Arial", size: 22, color: C.text } } }
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 }
      }
    },
    headers: {
      default: new Header({
        children: [
          new Table({
            width: { size: 9360, type: WidthType.DXA },
            columnWidths: [6500, 2860],
            rows: [
              new TableRow({
                children: [
                  new TableCell({
                    borders: noBorder(),
                    shading: { fill: C.headerBg, type: ShadingType.CLEAR },
                    margins: { top: 100, bottom: 100, left: 200, right: 100 },
                    width: { size: 6500, type: WidthType.DXA },
                    children: [
                      new Paragraph({ children: [new TextRun({ text: "🎯 Candidate–JD Match Report", bold: true, size: 28, color: "FFFFFF", font: "Arial" })] }),
                      new Paragraph({ children: [new TextRun({ text: `${data.candidateName}  ·  ${data.jdTitle}`, size: 20, color: "DDDDDD", font: "Arial" })] })
                    ]
                  }),
                  new TableCell({
                    borders: noBorder(),
                    shading: { fill: C.headerBg, type: ShadingType.CLEAR },
                    margins: { top: 100, bottom: 100, left: 100, right: 200 },
                    width: { size: 2860, type: WidthType.DXA },
                    verticalAlign: VerticalAlign.CENTER,
                    children: [
                      new Paragraph({
                        alignment: AlignmentType.RIGHT,
                        children: [new TextRun({ text: `Generated: ${new Date().toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' })}`, size: 18, color: "BBBBBB", font: "Arial" })]
                      })
                    ]
                  })
                ]
              })
            ]
          })
        ]
      })
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Confidential – For Internal Hiring Use Only  |  Page ", size: 18, color: "888888", font: "Arial" }),
              new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888", font: "Arial" }),
              new TextRun({ text: " of ", size: 18, color: "888888", font: "Arial" }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, color: "888888", font: "Arial" })
            ]
          })
        ]
      })
    },
    children: [
      spacer(200),

      // ── Score Badge ──────────────────────────────────────────────────────────
      scoreBadge(data.overallScore, data.fitLabel),
      spacer(180),

      // ── Executive Summary ────────────────────────────────────────────────────
      banner("📋  Hiring Manager Summary"),
      spacer(100),
      new Paragraph({
        children: [new TextRun({ text: data.execSummary, size: 21, color: C.text, font: "Arial" })]
      }),
      spacer(200),

      // ── Key Strengths ────────────────────────────────────────────────────────
      banner("✅  Key Strengths", "375623"),
      spacer(100),
      ...data.strengths.flatMap((s, i) => [
        strengthCard(s.title, s.evidence),
        spacer(i < data.strengths.length - 1 ? 80 : 0)
      ]),
      spacer(200),

      // ── Key Gaps ─────────────────────────────────────────────────────────────
      banner("❌  Key Gaps", "C00000"),
      spacer(100),
      ...data.gaps.flatMap((g, i) => [
        gapCard(g.title, g.detail),
        spacer(i < data.gaps.length - 1 ? 80 : 0)
      ]),
      spacer(200),

      // ── Recommendation ───────────────────────────────────────────────────────
      recBox(data.recommendation),
      spacer(200),

      // ── Side-by-Side: Responsibilities ──────────────────────────────────────
      banner("📊  Side-by-Side Comparison: JD vs. Resume"),
      spacer(100),
      sectionHeading("1. Responsibilities"),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [4680, 4680],
        rows: [
          tblHdrRow(["Job Description (JD)", "Candidate Resume Evidence"], [4680, 4680]),
          ...data.responsibilities.map((r, i) => tblDataRow([r.jd, r.resume], [4680, 4680], i))
        ]
      }),
      spacer(200),

      // ── Side-by-Side: Skills ─────────────────────────────────────────────────
      sectionHeading("2. Technical Skill Match"),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3120, 3120, 3120],
        rows: [
          tblHdrRow(["JD Skill Requirement", "Candidate Skill", "Match"], [3120, 3120, 3120]),
          ...data.skillMatch.map((s, i) => tblDataRow([s.skill, s.candidate, s.match], [3120, 3120, 3120], i))
        ]
      }),
      spacer(200),

      // ── Gaps Table ───────────────────────────────────────────────────────────
      sectionHeading("3. Gaps Summary"),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [4680, 4680],
        rows: [
          tblHdrRow(["JD Requirement", "Gap in Resume"], [4680, 4680]),
          ...data.gapTable.map((g, i) => tblDataRow([g.requirement, g.gap], [4680, 4680], i))
        ]
      }),

      spacer(160)
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('/home/claude/HM_Summary_Report.docx', buf);
  console.log('✅ Report generated: HM_Summary_Report.docx');
});
