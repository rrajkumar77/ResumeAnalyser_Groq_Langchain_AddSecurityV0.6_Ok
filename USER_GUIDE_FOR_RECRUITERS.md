# 📖 Recruiter's Quick Guide - Reading the Evidence Ledger

**5-Minute Guide for Non-Technical Recruiters**

---

## 🎯 The Simple Truth

**You don't need to read every row!** The system does the heavy lifting. Here's what you actually need to look at:

---

## ✅ Step 1: Look at the TOP Section First

When you click "Enhanced Evidence-Based Validation", you'll see this:

```
┌─────────────────────────────────────┐
│  Overall Fit Score: 87%             │
│  Validated Skills: 8                │
│  Weak Evidence: 2                   │
│  Missing Skills: 3                  │
└─────────────────────────────────────┘
```

### Quick Decision Guide:

| Fit Score | What It Means | Action |
|-----------|---------------|--------|
| **85-100%** | 🟢 Excellent match | Fast-track to interview |
| **70-84%** | 🟡 Good match | Phone screen recommended |
| **60-69%** | 🟠 Moderate match | Technical assessment needed |
| **Below 60%** | 🔴 Poor match | Likely reject (unless junior role) |

**That's it for the first decision!** ✅

---

## ✅ Step 2: Check the "Validated Skills" Tab

Click the **"Validated Skills"** tab. You'll see something like:

```
✅ AWS — 84% hands-on score 🎯 PRIORITY
   Experience Depth: PROFICIENT
   Reasoning: Led AWS migration project with 30% cost reduction
   
✅ Java — 82% hands-on score 🎯 PRIORITY
   Experience Depth: PROFICIENT
   Reasoning: Built microservices platform serving 500K users
```

### What to Look For:

1. **🎯 PRIORITY badge** = This is a must-have skill you specified
2. **Experience Depth**:
   - **EXPERT** = They're really good (5+ years equivalent)
   - **PROFICIENT** = Solid experience (2-4 years equivalent)
   - **COMPETENT** = Can do the job (1-2 years equivalent)
   - **BASIC** = Limited experience (< 1 year)

3. **Reasoning** = The actual evidence from their resume

**Action**: If all your priority skills show up here with PROFICIENT or EXPERT, you have a strong candidate! ✅

---

## ⚠️ Step 3: Check the "Weak/Ignored Skills" Tab

This shows skills that are questionable:

```
⚠️ Python: 45% hands-on score
   Reasoning: Mentioned in Skills section but no supporting
   project or hands-on experience context.
   
⊘ Docker
   Reasoning: Found only in Skills section with no supporting
   project evidence.
```

### What This Means:

- **⚠️ Weak** = They claim it but proof is thin → Ask detailed questions in interview
- **⊘ Ignored** = Just listed it, no real work experience → Probably resume padding

**Action**: Make a note to ask about these skills in the interview.

---

## 🚫 Step 4: IGNORE the Evidence Ledger Table (Usually)

**The detailed evidence table is for advanced users only.**

You only need to look at it if:
- You want to dig into WHY a skill was validated
- You're preparing specific interview questions
- You suspect resume padding and want proof

**For 90% of decisions, Steps 1-3 are enough!**

---

## 🎯 Real Example Walkthrough

### Scenario: You're hiring a Senior Cloud Engineer

**Your Priority Skills**:
- AWS
- Python
- Kubernetes
- Terraform

### You Upload JD + Resume and See:

```
Overall Fit Score: 78%
Validated Skills: 6
Weak Evidence: 1
Missing Skills: 1
```

**Step 1 Decision**: 78% = Good match 🟡 → Worth a phone screen

---

### You Click "Validated Skills" Tab:

```
✅ AWS — 92% hands-on score 🎯 PRIORITY
   Experience Depth: EXPERT
   Evidence: "Led AWS infrastructure migration for 15 
   microservices, reducing monthly costs by $50K"
   
✅ Python — 85% hands-on score 🎯 PRIORITY
   Experience Depth: PROFICIENT
   Evidence: "Built Python automation scripts for deployment
   workflows, reducing deployment time from 2 hours to 15 minutes"
   
✅ Docker — 80% hands-on score
   Experience Depth: PROFICIENT
   Evidence: "Containerized 20+ applications using Docker"
```

**Looks good! AWS and Python are strong.** ✅

---

### You Click "Weak/Ignored Skills" Tab:

```
⚠️ Kubernetes — 55% hands-on score 🎯 PRIORITY
   Experience Depth: BASIC
   Reasoning: Mentioned Kubernetes setup but lacks metrics
   and detailed evidence of hands-on management.
```

**Hmm, Kubernetes is weak but it's a priority skill.** ⚠️

---

### You Click "Missing Skills":

```
❌ Terraform 🎯 PRIORITY
   Not mentioned in resume.
```

**Missing Terraform completely.** ❌

---

### Your Decision:

**Option 1: Phone Screen with Focus**
- Strong AWS and Python (your top priorities)
- Ask detailed questions about Kubernetes experience
- Ask if they're willing to learn Terraform (or if they have different IaC tool experience)

**Option 2: Click "Skills Gap Analysis"**
- System will tell you: "Candidate needs 2-3 months to reach PROFICIENT in Kubernetes and Terraform"
- Recommendation: "HIRE_AND_TRAIN as Mid-Level with training path"

---

## 📊 Understanding the Evidence Ledger (Advanced)

**Only read this if you need to dig deeper.**

### Why Do Skills Appear Multiple Times?

Each row = one place the skill was found in the resume.

**Example**:
```
Skill: AWS
Row 1: Context = WORK_EXPERIENCE | Score = 84% | PROFICIENT
Row 2: Context = EDUCATION | Score = 30% | MENTIONED_ONLY
```

**Translation**:
- **Row 1**: Found AWS in their work experience with strong evidence
- **Row 2**: Also found AWS mentioned in education (took a course)

**Which one matters?** Row 1 (the highest score) ✅

**Why show both?** For transparency - you can see ALL evidence

---

### Quick Reference: Column Meanings

| Column | What It Means | What to Look For |
|--------|---------------|------------------|
| **Priority** | Is this a must-have skill? | ✅ "Yes" = Your priority skills |
| **Hands-On Score** | How strong is the evidence? | ✅ 70%+ = Good<br>⚠️ 40-69% = Weak<br>❌ <40% = Resume padding |
| **Experience Depth** | How much experience? | ✅ EXPERT/PROFICIENT<br>⚠️ COMPETENT/BASIC<br>❌ MENTIONED_ONLY |
| **Context** | Where was it found? | ✅ WORK_EXPERIENCE<br>⚠️ PROJECT<br>❌ EDUCATION (weak)<br>❌ SKILLS_SECTION (ignored) |
| **Verb Intensity** | How did they describe it? | ✅ LEADERSHIP ("led", "architected")<br>⚠️ CORE_DELIVERY ("built", "developed")<br>❌ PASSIVE ("familiar with") |
| **Has Metrics** | Did they include numbers? | ✅ Yes = "reduced by 40%"<br>❌ No = vague claims |

---

## 🎯 The 3-Click Hiring Decision

### Click 1: Overall Fit Score
- **85%+** → Schedule interview
- **70-84%** → Phone screen
- **60-69%** → Technical assessment
- **<60%** → Likely pass

### Click 2: Validated Skills Tab
- Check if all your priority skills (🎯) are validated
- Check if experience depth is PROFICIENT or EXPERT

### Click 3: Recommendations
- Read the recommendations section
- It tells you exactly what to do

**Done!** You've made an informed decision in 3 clicks.

---

## 🚩 Red Flags to Watch For

### In "Validated Skills":

```
❌ Python — 95% hands-on score
   Evidence: "Built ML models, deployed APIs, created dashboards..."
```

**Red Flag**: Lists 10 different things for one skill → Might be overselling

---

### In "Weak/Ignored Skills":

```
⊘ AWS
⊘ Python  
⊘ React
⊘ Node.js
⊘ Docker
(20+ skills in this list)
```

**Red Flag**: Everything in Skills section, nothing validated → Resume padding

---

### In "Missing Skills":

```
❌ Java 🎯 PRIORITY
❌ Spring Boot 🎯 PRIORITY
❌ Microservices 🎯 PRIORITY
```

**Red Flag**: Missing ALL priority skills → Wrong candidate

---

## 💡 Pro Tips

### Tip 1: Use the "Download" Buttons
- Export the analysis to share with hiring managers
- No need to copy-paste or screenshot

### Tip 2: Focus on Priority Skills
- You marked them as priority for a reason
- If those are validated, the candidate is worth talking to

### Tip 3: Trust the Recommendations
- The system has analyzed thousands of patterns
- If it says "HIRE_AND_TRAIN", consider it seriously

### Tip 4: Use Interview Questions Generator
- Click "Generate Interview Questions" after validation
- Get ready-made questions based on their actual resume

### Tip 5: Compare Multiple Candidates
- Use Batch Processing for 10+ candidates
- Get a ranked list automatically

---

## 🎓 Training Scenarios

### Scenario 1: "All Skills Look Validated But Fit is 65%"

**What happened?**
- They have ALL the skills but at BASIC or COMPETENT level
- Not enough depth for a senior role

**Action**:
- Consider for mid-level or junior role
- Or click "Skills Gap Analysis" to see training path

---

### Scenario 2: "Fit is 90% But Missing One Priority Skill"

**What happened?**
- Strong overall match but gaps in one area
- Might be a critical skill

**Action**:
- Check if the missing skill is learnable quickly
- Click "Skills Gap Analysis" for training recommendation
- Often still worth interviewing

---

### Scenario 3: "Evidence Ledger Shows 50 Rows"

**What happened?**
- System found the skills mentioned many times across resume
- This is NORMAL, not an error

**Action**:
- IGNORE the table
- Just look at the "Validated Skills" tab summary
- The system automatically picks the best evidence

---

## ❓ FAQ

**Q: Do I need to understand the Evidence Ledger table?**  
A: **No!** 90% of users never look at it. Use the summary tabs.

**Q: What if a skill appears 5 times in the table?**  
A: Normal. The system found it in 5 different places. Only the highest score matters.

**Q: Why is "Singapore" showing up as a skill?**  
A: False positive (location detected as skill). Ignore it. The system filters it out in the summary.

**Q: Can I trust the hands-on scores?**  
A: Yes. They're based on actual evidence (action verbs, metrics, project context). Much more reliable than keyword matching.

**Q: What if I disagree with the assessment?**  
A: The "Evidence Details" section shows exactly what was found. You can verify yourself.

---

## 🎯 Final Checklist

Before making a hiring decision, verify:

- [ ] Overall fit score makes sense for the role level
- [ ] All priority skills (🎯) are validated or have an acceptable gap
- [ ] Experience depth matches role requirements (Senior = EXPERT, Mid = PROFICIENT)
- [ ] Weak/Ignored skills list isn't too long (resume padding indicator)
- [ ] Read the recommendations section
- [ ] Consider "Skills Gap Analysis" for near-miss candidates (70-80% fit)

**If all checkboxes pass → Schedule interview!** ✅

---

## 📞 Need Help?

**Common Issues**:
- "I don't understand the table" → Don't use it! Use the summary tabs instead
- "Too many skills showing up" → Focus only on Priority = Yes skills
- "Scores seem wrong" → Check the "Evidence Details" to see the actual resume text
- "Want to compare candidates" → Use Batch Processing feature

**Still confused?** 
- Watch the 2-minute walkthrough video (link in app)
- Contact support with specific questions

---

**Remember**: The tool is designed to HELP you make decisions faster, not make them FOR you. Use it as a smart assistant, not a replacement for human judgment.

**Trust your instincts + Trust the data = Better hires** 🎯
