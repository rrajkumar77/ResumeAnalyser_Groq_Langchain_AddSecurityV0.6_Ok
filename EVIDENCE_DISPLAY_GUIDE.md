# Evidence Display - What Users See

## Problem: Users Don't Understand Why Scores Are Different

**Before:**
```
Python — 82.2%
'python' has PROFICIENT evidence of hands-on use

Gen AI — 53.3%
'Gen AI' has BASIC evidence of hands-on use
```

❌ Users ask: "Why is Python 82% but Gen AI only 53%? What's the difference?"

---

## Solution: Show Actual Evidence from Resume

### ✅ Enhanced Display with Evidence

**Now when user clicks on a skill card:**

```
🟢 Python ⭐⭐ 🎯 PRIORITY — 82% hands-on
[Click to expand]

┌─────────────────────────────────────────────────────────┐
│ Score: 82% (Excellent)                                   │
│ Experience: Proficient                                   │
│ Has Metrics: ✅ Yes                                      │
└─────────────────────────────────────────────────────────┘

Why this skill is validated:
'python' has PROFICIENT evidence of hands-on use (hands-on 
score: 82.2%). Evidence shows LEADERSHIP-level action verbs...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 Evidence from Resume:

▼ Evidence 1 - 🟢 Strong (85%)

   > "Led Python microservices development for payment 
      processing system handling 1M+ daily transactions,
      reducing latency by 40% through optimization"

   Why this validates hands-on experience:
   ✓ Found in Work Experience (not just Skills section)
   ✓ Leadership verb (Led, Architected, Designed)
   ✓ Includes measurable outcomes (40% reduction, 1M transactions)
   ✓ Project duration: 18 months

▼ Evidence 2 - 🟡 Good (78%)

   > "Built RESTful APIs using Python FastAPI serving
      100K+ requests per day with 99.9% uptime"

   Why this validates hands-on experience:
   ✓ Found in Work Experience
   ✓ Action verb (Built, Implemented, Developed)
   ✓ Includes measurable outcomes (100K requests, 99.9% uptime)
   ✓ Project duration: 12 months

▼ Evidence 3 - 🟡 Good (75%)

   > "Developed automated testing framework in Python,
      increasing test coverage from 45% to 92%"

   Why this validates hands-on experience:
   ✓ Found in Work Experience
   ✓ Action verb (Built, Implemented, Developed)
   ✓ Includes measurable outcomes (45% → 92%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Compare with Lower Score:

```
🟠 Gen AI ◐ — 53% hands-on
[Click to expand]

┌─────────────────────────────────────────────────────────┐
│ Score: 53% (Moderate)                                    │
│ Experience: Basic                                        │
│ Has Metrics: ❌ No                                       │
└─────────────────────────────────────────────────────────┘

Why this skill is validated:
'Gen AI' has BASIC evidence of hands-on use (hands-on score: 
53.3%). Recommend manual verification for depth of expertise.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 Evidence from Resume:

▼ Evidence 1 - 🟠 Moderate (55%)

   > "Worked on Gen AI project exploring LLM applications
      for customer service automation"

   Why this validates hands-on experience:
   ✓ Found in Work Experience (not just Skills section)

   How to verify in interview:
   ⚠️ Could be stronger with measurable outcomes
   ⚠️ Could be stronger with action verbs (Led, Built, etc.)

▼ Evidence 2 - 🟠 Moderate (51%)

   > "Participated in team discussions about implementing
      ChatGPT for internal tools"

   Why this validates hands-on experience:
   ✓ Found in Work Experience

   How to verify in interview:
   ⚠️ Could be stronger with measurable outcomes
   ⚠️ Could be stronger with action verbs (Led, Built, etc.)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## What Makes a High Score (80%+)

Users can now see that **Python 82%** has:
- ✅ **Leadership verbs**: "Led", "Built", "Developed"
- ✅ **Measurable outcomes**: "40% reduction", "1M transactions", "99.9% uptime"
- ✅ **Long projects**: 18 months, 12 months
- ✅ **Work experience**: Not just mentioned in Skills section
- ✅ **Multiple projects**: 3 different projects showing sustained use

## What Makes a Low Score (50-60%)

Users can now see that **Gen AI 53%** has:
- ❌ **Passive verbs**: "Worked on", "Participated"
- ❌ **No metrics**: No numbers or percentages
- ❌ **Vague descriptions**: "exploring", "discussions"
- ⚠️ **Limited evidence**: Only 2 mentions
- ⚠️ **Shallow involvement**: Not leading, just participating

---

## How This Helps Recruiters

### 1. **Explain to Hiring Managers**

Before:
- Manager: "Why is this candidate rated 82% for Python?"
- Recruiter: "Um... the system calculated it somehow..."

After:
- Manager: "Why is this candidate rated 82% for Python?"
- Recruiter: "They led a payment processing system with 1M daily transactions, built APIs serving 100K requests, and have 18 months of documented experience with measurable outcomes."

### 2. **Interview Preparation**

Before:
- "They have Python on their resume, ask generic Python questions"

After:
- "They claim 40% latency reduction. Ask: 'How did you measure that? What profiling tools? What optimizations?'"
- "They mention 99.9% uptime. Ask: 'What monitoring did you use? How did you handle failures?'"

### 3. **Spot Resume Padding**

Before:
- Can't tell if skills are real or padded

After:
- **Strong evidence**: Multiple projects, metrics, leadership = Real skill ✅
- **Weak evidence**: Vague mentions, no metrics, passive verbs = Maybe padding ⚠️

### 4. **Compare Candidates Fairly**

Before:
- "Both have Python, who's better?"

After:
- Candidate A: 3 projects, 18 months, measurable outcomes = 85%
- Candidate B: Listed in skills, one mention, no details = 55%
- **Clear winner: Candidate A** ✅

---

## Technical Implementation

The enhanced evidence display shows:

1. **Actual text from resume** (quoted)
2. **Quality indicators**:
   - Where found (Work Experience vs Skills)
   - Action verb type (Leadership, Action, Passive)
   - Has measurable outcomes (numbers, %)
   - Project duration
3. **Score badge** (Strong/Good/Moderate)
4. **Interview guidance** (what to verify if evidence is weak)

---

## Benefits

| Metric | Before | After |
|--------|--------|-------|
| **Transparency** | ❌ Black box scoring | ✅ See exact resume text |
| **Trust** | ⚠️ Users skeptical | ✅ Users understand |
| **Interview prep** | ❌ Generic questions | ✅ Evidence-based questions |
| **Resume padding detection** | ❌ Hard to spot | ✅ Obvious from evidence |
| **Manager buy-in** | ⚠️ "Just a number" | ✅ "Here's why..." |

---

## Example User Flow

1. User sees: "Python — 82%"
2. User thinks: "Why 82%? What's the evidence?"
3. User clicks to expand skill card
4. User sees actual quotes from resume
5. User thinks: "Oh! They led a 1M transaction system with metrics. That's why it's high!"
6. User prepares interview questions about that specific system
7. User explains to manager: "Strong Python - led payment system with documented outcomes"

**Result: Complete transparency and trust!** 🎯
