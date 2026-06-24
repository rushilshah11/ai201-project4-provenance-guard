"""
Offline verification script for Signal 2 (Stylometrics).
Run with: python test_signals.py

Signal 1 (Groq) requires the Flask server + API key, so it is NOT tested here.
When running the full app, both scores are printed to the console automatically:
  [signals] signal_1=X.XXXX  signal_2=X.XXXX
"""

from signals.stylometric_signal import run_stylometric_signal

CASES = [
    (
        "Clearly AI",
        # Very uniform sentence lengths, repeated structural words, minimal punctuation.
        "The platform leverages advanced algorithms to optimize enterprise efficiency. "
        "The system utilizes intelligent solutions to maximize organizational productivity. "
        "The framework enables automated processes to streamline business operations. "
        "The technology deploys scalable infrastructure to accelerate digital transformation. "
        "The solution integrates machine learning capabilities to enhance strategic performance. "
        "The approach implements data-driven insights to facilitate operational excellence. "
        "The methodology applies predictive analytics to improve resource allocation efficiency. "
        "The initiative supports continuous innovation to drive sustainable competitive advantage.",
    ),
    (
        "Clearly human",
        # Wildly varying sentence lengths (1 word to 40+ words), heavy punctuation, casual vocabulary.
        "Oh god. "
        "I genuinely cannot — I don't even know where to begin explaining what happened to me yesterday, "
        "starting with the 5am alarm I completely slept through (twice!), then the coffee machine breaking mid-brew "
        "in a way that sprayed hot water all over my shirt, then my bus being inexplicably 40 minutes late, "
        "then ANOTHER bus showing up that was going the wrong direction entirely... and I got on it anyway "
        "because I panicked. "
        "Why?? "
        "No clue, honestly. "
        "Just one of those days, I guess — the kind where every single thing goes sideways and you just "
        "have to laugh about it eventually, right? "
        "Right?! "
        "Ugh.",
    ),
    (
        "Borderline human (academic)",
        # Varied sentence lengths, academic vocabulary, moderate punctuation.
        "This paper examines the relationship between urban density and public transportation ridership across "
        "fifteen metropolitan areas over the past two decades. "
        "The methodology employs a mixed-methods approach, combining quantitative analysis of transit data with "
        "qualitative interviews conducted among commuters, transit planners, and municipal officials. "
        "Findings suggest that density alone is an insufficient predictor of ridership. "
        "Income distribution, zoning policy, and walkability indices emerged as significant confounding variables "
        "that moderated the density-ridership relationship in ways prior literature has underexplored. "
        "These results have implications for transit-oriented development policy, particularly in mid-sized cities "
        "currently weighing infrastructure investments.",
    ),
    (
        "Borderline AI (lightly edited)",
        # Moderately uniform sentence lengths, richer vocabulary than clearly-AI, light punctuation.
        "Improving personal productivity requires a structured and intentional approach to daily habits. "
        "First, individuals should prioritize their most important tasks during peak mental energy hours. "
        "Second, eliminating unnecessary digital distractions can significantly improve sustained focus. "
        "Third, regular short breaks help prevent cognitive fatigue and maintain overall performance. "
        "Additionally, setting clear and measurable goals provides direction and motivates consistent effort. "
        "Finally, reviewing progress at regular intervals allows for timely adjustments and course corrections. "
        "By consistently applying these strategies, most people can meaningfully increase their daily output.",
    ),
]

if __name__ == "__main__":
    print("\nSignal 2 (Stylometrics) verification — higher score = more AI-like\n")
    print("%-34s  %s" % ("Case", "signal_2_score"))
    print("-" * 50)
    for name, text in CASES:
        result = run_stylometric_signal(text)
        print("%-34s  %.4f" % (name, result["score"]))
    print()
    print("Expected ordering: Clearly AI > Borderline > Clearly human")
    print("Note: Signal 1 (Groq LLM) prints alongside Signal 2 when /submit is called.")
