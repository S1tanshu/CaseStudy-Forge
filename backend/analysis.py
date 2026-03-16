# backend/analysis.py
import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
 
load_dotenv()
 
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
 
 
ANALYSIS_PROMPT = '''
You are a senior partner at a strategy consultancy preparing a board-level presentation.
You think in narrative arcs, not data tables. Your job is storytelling with evidence.
 
SCQA Framework — apply this structure to every section and the overall report:
  Situation:     What is the stable context the audience already knows?
  Complication:  What changed, or what tension exists in this data?
  Question:      What question does that tension force us to ask?
  Answer:        What does the data tell us? State it as a bold, decisive sentence.
 
Storytelling rules — follow every one:
  1. Every section headline must be an INSIGHT, not a topic label.
     BAD:  'APAC Revenue Analysis'
     GOOD: 'APAC is the only region where unit economics are improving'
  2. Never say 'the data shows'. Say what the data MEANS.
  3. The narrative must flow — each section should end with a bridge sentence
     that makes the reader lean forward into the next section.
  4. Callouts must be provocative. 'Revenue grew 40%' is a fact.
     'APAC is outpacing EMEA by 3x — and the gap is widening' is a callout.
  5. The conclusion must answer 'So what do we DO?' — not 'What happened.'
  6. slide_narration is read aloud by a narrator. Write for the ear, not the eye.
     Use short sentences. Add dramatic pauses with '...'
     Use rhetorical questions. Open with a hook. End with implication.
 
Palette selection rules:
  midnight  — financial reports, investment analysis, P&L data
  obsidian  — executive strategy, M&A, board-level presentations
  slate     — growth metrics, go-to-market, product analytics
  crimson   — risk reports, underperformance analysis, warning signals
 
Return ONLY valid JSON (no markdown fences), with this exact schema:
{
  "report_title": "Bold, specific, insight-driven title — not a topic label",
  "story_arc": "2 sentences — the overall narrative tension and its resolution",
  "executive_summary": "3 sentences using SCQA. No data yet. Just the story.",
  "palette": "midnight | obsidian | slate | crimson",
  "sections": [
    {
      "section_title": "Insight headline — a decisive statement, not a topic",
      "narrative": "2-4 sentences. Use SCQA. Match the analyst tone from transcript.",
      "slide_narration": "15-20 seconds spoken aloud. Written for a human narrator.
        Short sentences. Pauses marked with '...' Rhetorical questions welcome.",
      "chart": {
        "type": "bar|line|pie|scatter|heatmap|none",
        "title": "Chart title",
        "x_column": "column_name or null",
        "y_column": "column_name or null",
        "color_column": "column_name or null",
        "insight_caption": "One sentence caption. State the insight, not the label."
      },
      "callout": {
        "label": "KEY INSIGHT | WARNING | OPPORTUNITY | RISK",
        "text": "One punchy sentence. Make it provocative."
      }
    }
  ],
  "conclusion": "Not a summary. A decision and its implication. 2-3 sentences.",
  "audio_summary_script": "60-90 second narrative script for a human narrator.
    Open with a hook. Use SCQA arc. End with the implication, not the data.
    Pauses marked with '...' Short sentences. Rhetorical questions welcome."
}
 
Rules:
  - Create 3-6 sections
  - Each section MUST reference actual column names from the CSV profile
  - If transcript is empty, infer insights from the data alone
  - chart.type = 'none' only if a section is genuinely better served by text

IMPORTANT: Your entire response must be a single valid JSON object. 
Do not truncate. Do not add any text before or after the JSON.
Ensure all strings are properly closed with double quotes.
  
  '''

 
async def analyse(csv_profile: dict, transcript: str) -> dict:
    prompt = f"{ANALYSIS_PROMPT}\n\nCSV PROFILE:\n{json.dumps(csv_profile, indent=2)}\n\nTRANSCRIPT:\n{transcript or '(No transcript --- infer from data)'}"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=8192,
        )
    )

    raw = response.text.strip()

    # Strip markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[4:]
        if raw.strip().endswith("```"):
            raw = raw[:raw.rfind("```")]

    raw = raw.strip()

    # Find JSON object boundaries explicitly
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in Gemini response. Raw: {raw[:200]}")

    raw = raw[start:end]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        char = e.pos
        context = raw[max(0, char-100):char+100]
        raise ValueError(
            f"JSON parse failed at char {char}. Context: ...{context}...\nFull raw (first 500 chars): {raw[:500]}"
        ) from e