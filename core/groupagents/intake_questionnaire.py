"""
Intake questionnaire definitions for different case types.

This module defines structured questions for collecting initial case information
from users after case creation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IntakeQuestion:
    """Single question in the intake questionnaire"""

    id: str  # Unique identifier for the question
    question: str  # Question text to show user
    memory_key: str  # Key for storing in semantic memory
    memory_category: str  # Category tag for memory record
    help_text: str | None = None  # Optional help text
    required: bool = True  # Whether the question is required
    example: str | None = None  # Example answer


# EB-1A Intake Questions
EB1A_QUESTIONS = [
    IntakeQuestion(
        id="field_of_work",
        question="What is your primary field of work or expertise? (e.g., Software Engineering, Machine Learning, Academic Research, Business)",
        memory_key="field_of_expertise",
        memory_category="background",
        required=True,
        example="Machine Learning and Computer Vision Research",
    ),
    IntakeQuestion(
        id="education",
        question="Please describe your educational background (highest degree, institution, field of study):",
        memory_key="education",
        memory_category="background",
        required=True,
        example="PhD in Computer Science from Stanford University, specialized in Neural Networks",
    ),
    IntakeQuestion(
        id="current_position",
        question="What is your current position and employer?",
        memory_key="current_position",
        memory_category="background",
        required=True,
        example="Senior Research Scientist at Google DeepMind",
    ),
    IntakeQuestion(
        id="years_of_experience",
        question="How many years of experience do you have in your field?",
        memory_key="years_of_experience",
        memory_category="background",
        required=True,
        example="12 years",
    ),
    IntakeQuestion(
        id="major_achievements",
        question="What are your top 3-5 major achievements or contributions in your field?",
        memory_key="major_achievements",
        memory_category="achievements",
        required=True,
        help_text="Focus on quantifiable achievements: awards, publications, patents, significant projects, leadership roles",
        example="1) Developed breakthrough algorithm with 10,000+ citations\n2) Won Best Paper Award at NeurIPS 2023\n3) Led team of 15 researchers on $5M project",
    ),
    IntakeQuestion(
        id="publications",
        question="How many peer-reviewed publications do you have? Please provide total count and highlight most cited ones:",
        memory_key="publications",
        memory_category="evidence",
        required=False,
        example="47 peer-reviewed papers, h-index of 32. Top paper has 3,500+ citations.",
    ),
    IntakeQuestion(
        id="awards",
        question="Have you received any major awards, honors, or recognition in your field?",
        memory_key="awards_honors",
        memory_category="evidence",
        required=False,
        help_text="Include academic awards, industry recognition, competitive grants, etc.",
        example="Best Paper Award NeurIPS 2023, NSF CAREER Award 2022, Forbes 30 Under 30",
    ),
    IntakeQuestion(
        id="media_coverage",
        question="Has your work been featured in media or press coverage? (publications, interviews, articles about your work)",
        memory_key="media_coverage",
        memory_category="evidence",
        required=False,
        example="Featured in MIT Technology Review, interviewed by TechCrunch, research covered in Nature News",
    ),
    IntakeQuestion(
        id="judging_experience",
        question="Have you served as a judge, reviewer, or evaluator for others in your field? (peer review, conference program committees, grant panels)",
        memory_key="judging_experience",
        memory_category="evidence",
        required=False,
        example="Served on program committee for ICML 2023, reviewed 50+ papers for top AI conferences, NSF grant panelist",
    ),
    IntakeQuestion(
        id="critical_role",
        question="Have you played a critical or leading role in distinguished organizations or projects?",
        memory_key="critical_role",
        memory_category="evidence",
        required=False,
        example="Led AI research group at Google (15 people), co-founded startup acquired for $50M",
    ),
    IntakeQuestion(
        id="high_salary",
        question="Do you command a high salary or remuneration compared to others in your field?",
        memory_key="high_salary",
        memory_category="evidence",
        required=False,
        help_text="You can provide general range or comparison to industry standards (not required to give exact numbers)",
        example="Total compensation in top 5% for field according to industry surveys",
    ),
    IntakeQuestion(
        id="current_location",
        question="Where are you currently located? (US or abroad)",
        memory_key="current_location",
        memory_category="logistics",
        required=True,
        example="Currently in US on H-1B visa in San Francisco, CA",
    ),
    IntakeQuestion(
        id="timeline",
        question="What is your desired timeline for filing the EB-1A petition?",
        memory_key="timeline",
        memory_category="logistics",
        required=True,
        example="Would like to file within 3-4 months",
    ),
]


# O-1 Visa Intake Questions (similar structure but adapted for O-1 criteria)
O1_QUESTIONS = [
    IntakeQuestion(
        id="field_of_work",
        question="What is your primary field of extraordinary ability? (sciences, arts, education, business, athletics)",
        memory_key="field_of_expertise",
        memory_category="background",
        required=True,
        example="Film Director and Producer",
    ),
    IntakeQuestion(
        id="education",
        question="Please describe your educational background or formal training:",
        memory_key="education",
        memory_category="background",
        required=True,
        example="MFA in Film Production from USC School of Cinematic Arts",
    ),
    IntakeQuestion(
        id="major_achievements",
        question="What are your most significant achievements demonstrating extraordinary ability?",
        memory_key="major_achievements",
        memory_category="achievements",
        required=True,
        example="Directed 3 feature films, 2 premiered at Sundance, won Best Director at Tribeca Film Festival",
    ),
    IntakeQuestion(
        id="awards",
        question="Have you received nationally or internationally recognized prizes or awards?",
        memory_key="awards_honors",
        memory_category="evidence",
        required=False,
        example="Sundance Grand Jury Prize, Tribeca Best Director, Emmy nomination",
    ),
    IntakeQuestion(
        id="critical_role",
        question="Have you performed in a leading or critical role for distinguished organizations?",
        memory_key="critical_role",
        memory_category="evidence",
        required=False,
        example="Creative Director at A24 Films, Led production of Oscar-nominated film",
    ),
    IntakeQuestion(
        id="current_location",
        question="Where are you currently located?",
        memory_key="current_location",
        memory_category="logistics",
        required=True,
        example="Currently in Los Angeles, CA on tourist visa",
    ),
    IntakeQuestion(
        id="us_employer",
        question="Do you have a US employer or agent who will petition for you?",
        memory_key="us_employer",
        memory_category="logistics",
        required=True,
        example="Warner Bros. Pictures will serve as petitioning employer",
    ),
]


# General Immigration Intake (fallback for other case types)
GENERAL_IMMIGRATION_QUESTIONS = [
    IntakeQuestion(
        id="immigration_goal",
        question="What is your immigration goal? (visa type, green card category, etc.)",
        memory_key="immigration_goal",
        memory_category="background",
        required=True,
        example="Seeking EB-2 NIW green card",
    ),
    IntakeQuestion(
        id="background",
        question="Please provide a brief overview of your professional background:",
        memory_key="professional_background",
        memory_category="background",
        required=True,
        example="10 years as software engineer, currently tech lead at major tech company",
    ),
    IntakeQuestion(
        id="current_status",
        question="What is your current immigration status in the US (if applicable)?",
        memory_key="current_status",
        memory_category="logistics",
        required=True,
        example="H-1B valid until 2026",
    ),
    IntakeQuestion(
        id="timeline",
        question="What is your desired timeline for this case?",
        memory_key="timeline",
        memory_category="logistics",
        required=True,
        example="Would like to file within 6 months",
    ),
]


def get_questions_for_category(category: str | None) -> list[IntakeQuestion]:
    """
    Get the appropriate intake questions based on case category.

    Args:
        category: Case category (EB1A, O1, etc.)

    Returns:
        List of IntakeQuestion objects
    """
    if not category:
        return GENERAL_IMMIGRATION_QUESTIONS

    category_upper = category.upper()

    if category_upper in ("EB1A", "EB-1A"):
        return EB1A_QUESTIONS
    if category_upper in ("O1", "O-1"):
        return O1_QUESTIONS
    return GENERAL_IMMIGRATION_QUESTIONS


def format_question_with_help(question: IntakeQuestion, question_num: int, total: int) -> str:
    """
    Format a question with its help text and example for display to user.

    Args:
        question: The IntakeQuestion to format
        question_num: Current question number (1-indexed)
        total: Total number of questions

    Returns:
        Formatted question string for Telegram
    """
    parts = [f"📝 Question {question_num}/{total}\n"]

    # Main question
    parts.append(f"*{question.question}*\n")

    # Help text if available
    if question.help_text:
        parts.append(f"💡 _{question.help_text}_\n")

    # Example if available
    if question.example:
        parts.append(f"Example: `{question.example}`\n")

    # Required indicator
    if not question.required:
        parts.append("\n_Optional - send /skip to skip this question_")
    else:
        parts.append("\n_Required - please provide an answer_")

    return "\n".join(parts)
