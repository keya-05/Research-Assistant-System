"""
Agent Memory Module - The Core of RLHF (Reinforcement Learning from Human Feedback)
-----------------------------------------------------------------------------------
This module is the "brain" of the learning system. It manages:
- Reward computation: Assigning scores based on human feedback (+2 for correct, -1/-2 for errors).
- Example promotion: High-reward classifications become "Golden Examples" for future few-shot learning.
- Mistake tracking: Logging errors with corrections to prevent repetition.
- Dynamic context building: Injecting learned patterns into the LLM prompt for improved classifications.

The RLHF loop works as follows:
1. Agent classifies a ticket.
2. Human provides feedback (correct or correction).
3. Reward is computed and stored.
4. High-reward examples are promoted to the few-shot pool.
5. Mistakes are logged with lessons.
6. Next classification pulls this context into the prompt, making the agent "learn" over time.
"""

from app.database import SessionLocal
from app.models import Feedback  # Import database session and Feedback model
from sqlalchemy import func  # For SQL aggregation functions like count

# Thresholds for promoting/demoting examples based on cumulative reward scores
REWARD_THRESHOLD_PROMOTE = 3  # If a classification gets +3 or more (confirmed correct multiple times), it becomes a "Golden Example"
REWARD_THRESHOLD_DEMOTE = -2  # If corrected multiple times (score <= -2), it's a critical mistake pattern (though not used in current logic)

def compute_reward(was_correct: bool, confidence_match: bool = True) -> int:
    """
    Computes the reward signal for a classification based on human feedback.
    
    This is the core of RLHF: positive rewards reinforce good behavior, negative penalties discourage errors.
    
    Args:
        was_correct (bool): True if the human agreed with the agent's classification.
        confidence_match (bool): Optional; if True, gives extra reward for being correct confidently.
    
    Returns:
        int: Reward score.
             +2: Correct and confident (strong positive reinforcement).
             +1: Correct but uncertain (still good, but less reward).
             -1: Incorrect (base penalty; caller may add more for high-stakes errors).
    
    Note: The caller (main.py) adds an extra -1 if urgency was wrong, making it -2 total.
    """
    if was_correct:
        # Reward for being right; extra for confidence
        return 2 if confidence_match else 1
    # Penalty for being wrong
    return -1  # Base penalty; urgency errors get extra -1

def get_agent_context(db_session, n_examples=5, n_mistakes=3) -> dict:
    """
    Retrieves the most relevant learning context from the database for prompt injection.
    
    This function queries the Feedback table to build a context dict containing:
    - Golden examples: Best-performing classifications (high reward, human-verified).
    - Mistakes: Recent errors with corrections (to learn from failures).
    - Accuracy stats: Overall performance for self-awareness in the prompt.
    
    Args:
        db_session: SQLAlchemy session for database queries.
        n_examples (int): Number of golden examples to retrieve (default 5).
        n_mistakes (int): Number of recent mistakes to include (default 3).
    
    Returns:
        dict: Context with keys 'golden_examples', 'mistakes', 'accuracy', 'total_feedback'.
    """
    # Query for Golden Examples: Feedback with high cumulative reward (>= threshold), ordered by reward descending
    golden = db_session.query(Feedback)\
        .filter(Feedback.reward_score >= REWARD_THRESHOLD_PROMOTE)\
        .order_by(Feedback.reward_score.desc())\
        .limit(n_examples).all()
    
    # Query for Recent Mistakes: Feedback where agent was wrong, ordered by most recent
    mistakes = db_session.query(Feedback)\
        .filter(Feedback.was_correct == False)\
        .order_by(Feedback.created_at.desc())\
        .limit(n_mistakes).all()
    
    # Calculate accuracy stats for self-awareness
    total_feedback = db_session.query(func.count(Feedback.id)).scalar() or 1  # Avoid division by zero
    correct_feedback = db_session.query(func.count(Feedback.id))\
        .filter(Feedback.was_correct == True).scalar() or 0
    accuracy = round((correct_feedback / total_feedback) * 100, 1)  # Percentage with 1 decimal place
    
    return {
        "golden_examples": golden,  # List of Feedback objects with high rewards
        "mistakes": mistakes,  # List of Feedback objects where agent was wrong
        "accuracy": accuracy,  # Float: accuracy percentage
        "total_feedback": total_feedback  # Int: total feedback count
    }

def build_dynamic_prompt_section(context: dict) -> str:
    """
    Converts the agent context into a formatted text string for injection into the LLM prompt.
    
    This text becomes part of the system prompt, allowing the agent to "remember" past feedback.
    It includes:
    - Self-awareness: Current accuracy and performance message.
    - Golden examples: Positive reinforcement patterns to follow.
    - Mistakes: Negative examples with corrections to avoid.
    
    Args:
        context (dict): Output from get_agent_context().
    
    Returns:
        str: Formatted text block for the prompt.
    """
    sections = []  # List to build sections of the prompt text
    
    # Section 1: Self-Awareness - Inject accuracy stats so the LLM knows how it's performing
    acc = context["accuracy"]
    total = context["total_feedback"]
    if total >= 3:  # Only show if there's enough data
        performance_msg = "You are performing well — maintain this standard." if acc >= 80 else \
                          "You have room to improve — study the mistake patterns below carefully."
        sections.append(f"YOUR CURRENT ACCURACY: {acc}% over {total} human-verified tickets. {performance_msg}")
    
    # Section 2: Golden Examples - Positive reinforcement, show patterns that work
    if context["golden_examples"]:
        sections.append("\nVERIFIED CORRECT EXAMPLES (follow these patterns closely):")
        for ex in context["golden_examples"]:
            sections.append(
                f'  Ticket: "{ex.original_text[:120]}"\n'  # Truncate long text for brevity
                f'  ✅ Correct: category={ex.correct_category}, urgency={ex.correct_urgency}'
                f'  (reward score: +{ex.reward_score})'  # Show cumulative reward
            )
    
    # Section 3: Mistakes - Learn from errors, show what went wrong and corrections
    if context["mistakes"]:
        sections.append("\nMISTAKES YOU MADE — LEARN FROM THESE:")
        for m in context["mistakes"]:
            sections.append(
                f'  Ticket: "{m.original_text[:120]}"\n'  # Truncate text
                f'  ❌ You said: category={m.agent_category}, urgency={m.agent_urgency}\n'  # Agent's wrong answer
                f'  ✅ Correct: category={m.correct_category}, urgency={m.correct_urgency}\n'  # Human correction
                f'  Lesson: {m.correction_reason or "Human correction — adjust your pattern."}'  # Optional reason
            )
    
    # Join all sections with newlines
    return "\n".join(sections)
