import pygame
import os
import time
import json
import re
import webbrowser
import threading
import urllib.request
import urllib.error

# PoliX is a single-file Pygame learning app. The program keeps its UI,
# application state, local persistence, and Ollama integration in this file
# so it can be run as a self-contained desktop project.

pygame.init()

# ============================================================
# WINDOW
# ============================================================

WIDTH, HEIGHT = 1000, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PoliX")

clock = pygame.time.Clock()


# ============================================================
# COLORS
# ============================================================

BACKGROUND = (16, 37, 27)
CARD = (23, 48, 36)
CARD_HOVER = (29, 57, 43)

CREAM = (245, 241, 232)
MUTED = (143, 169, 154)

PRIMARY = (95, 191, 143)
PRIMARY_DARK = (70, 150, 110)

BORDER = (48, 76, 61)


# ============================================================
# FONTS
# ============================================================

UI_FONT = pygame.font.match_font("segoeui") or pygame.font.match_font("arial")
UI_FONT_SEMIBOLD = pygame.font.match_font("segoeuisemibold") or UI_FONT

# Central font helper so the entire interface uses the same system UI typeface.
def ui_font(size, semibold=False):
    return pygame.font.Font(UI_FONT_SEMIBOLD if semibold else UI_FONT, size)

logo_font = ui_font(34, True)
title_font = ui_font(50, True)
subtitle_font = ui_font(28, True)
question_font = ui_font(34, True)
option_font = ui_font(24)
button_font = ui_font(22, True)
small_font = ui_font(18)
input_font = ui_font(24)


# ============================================================
# QUESTIONS
# ============================================================

questions = [

    # Government & Constitution
    "What are the three branches of the U.S. federal government, and what does each do?",
    "What powers belong to the federal government versus state governments?",
    "How does a bill become a federal law?",
    "What is the purpose of the Constitution and Bill of Rights?",
    "What role does the Supreme Court play in American government?",

    # Elections & Politics
    "How does the Electoral College determine the president?",
    "How do primary elections differ from general elections?",
    "What are the major differences between the House of Representatives and Senate?",
    "What do political parties actually do within the American political system?",
    "What is gerrymandering, and how can it affect elections?",

    # Economics & Government Spending
    "What are the federal government's major sources of revenue, and what does it spend money on?",
    "What are the differences between the national debt, budget deficit, and government spending?",
    "What causes inflation, and what tools does the government have to address it?",
    "What are the major arguments for and against higher or lower taxes?",
    "What are the major economic arguments for and against government regulation?",

    # Major Policy Issues
    "How does the American healthcare system work, and what are Medicare, Medicaid, and the ACA?",
    "What are the major arguments surrounding immigration policy and border enforcement?",
    "What are the major arguments surrounding gun rights and gun regulation?",
    "What are the major arguments surrounding abortion policy?",
    "What are the major approaches to addressing climate change and energy policy?",

    # Society & Government Programs
    "How do Social Security, Medicare, Medicaid, and other major government assistance programs work?",
    "What are the major debates surrounding education policy and student loans?",
    "What are the major debates surrounding crime, policing, sentencing, and incarceration?",

    # Foreign Policy & Information
    "What are America's major international alliances and strategic relationships, and why do they matter?",
    "How can you determine whether a political claim, statistic, news story, or source is reliable?"
]


# ============================================================
# SELF-ASSESSMENT OPTIONS
# ============================================================

options = [
    "0 — I don't know",
    "1 — I know the basics",
    "2 — I could explain it",
    "3 — I understand the competing arguments/evidence"
]


# ============================================================
# INFO FILE
# ============================================================
# info.txt is intentionally simple: the first line stores the name and later
# lines record completion/diagnostic data. This avoids requiring a database.

filename = "info.txt"

if not os.path.exists(filename):
    open(filename, "w").close()

with open(filename, "r") as file:
    file_contents = file.read().strip()

lines = file_contents.splitlines()

# First line is treated as the username
username = lines[0].strip() if lines else ""

# Check whether the user has already completed the quiz
already_quizzed = "quizzed" in [line.lower().strip() for line in lines]


# ============================================================
# APP STATE
# ============================================================
# These variables represent the current screen plus temporary form, quiz,
# flashcard, and chatbot state. Pygame's event loop updates them over time.

# If there is no username, start with onboarding.
# Otherwise go directly to quiz/main state.
if username == "":
    current_screen = "name"
elif already_quizzed:
    current_screen = "diagnostic"
else:
    current_screen = "quiz"


input_text = username
input_active = False

current_question = 0
selected_answer = None
answers = []
selected_topic = None

# Custom quiz builder
custom_quiz_modal = False
custom_quiz_interest = ""
custom_quiz_interest_active = False
custom_quiz_count = 5
custom_quiz_difficulty = "Intermediate"
custom_quiz_status = ""
custom_quiz_busy = False
custom_quiz_error = ""
custom_quiz_pending = None
custom_quiz_questions = []
custom_quiz_index = 0
custom_quiz_selected = None
custom_quiz_score = 0
custom_quiz_finished = False
custom_quiz_feedback_active = False
custom_quiz_feedback_busy = False
custom_quiz_feedback = ""
custom_quiz_feedback_pending = None
custom_quiz_feedback_error = ""

# ============================================================
# LOCAL OLLAMA CHATBOT
# ============================================================
# Chat and custom-quiz generation use Ollama running locally. Background
# threads are used for network/model calls so rendering remains responsive.

OLLAMA_URL = "http://localhost:11434/api/chat"
# Fast local models. Override with environment variables if desired.
# Qwen3.5 0.8B is about 1 GB in Ollama and is much lighter than the 2B model.
OLLAMA_MODEL = os.environ.get("POLIX_OLLAMA_MODEL", "qwen3.5:0.8b")
CHAT_MODEL = os.environ.get("POLIX_CHAT_MODEL", OLLAMA_MODEL)
QUIZ_MODEL = os.environ.get("POLIX_QUIZ_MODEL", "qwen3.5:0.8b")

# Inference settings tuned for short civic answers rather than long reasoning.
FAST_OPTIONS = {
    "temperature": 0.25,
    "top_k": 20,
    "top_p": 0.85,
    "num_ctx": 2048,
    "num_predict": 220,
    "keep_alive": "10m",
    "think": False,
}

chat_messages = [
    {
        "role": "assistant",
        "content": (
            "Hi! I'm the PoliX learning assistant. Ask me about American "
            "government, elections, economics, policy, or how to evaluate "
            "political information. I'll focus on explaining the issue rather "
            "than telling you what political position to take."
        )
    }
]
chat_input = ""
chat_input_active = False
chat_busy = False
chat_error = ""
chat_pending_reply = None
chat_scroll = 0

CHAT_SYSTEM_PROMPT = """
Keep answers concise and easy to read in a chat interface.
For normal questions, aim for about 80-140 words, usually 2-4 short paragraphs.
If a topic needs more explanation, use a few short bullets rather than a long essay.
Finish the answer cleanly; do not trail off or use "..." to indicate omitted content.

Prefer timeless civic education over current-events commentary.
Do not discuss or speculate about ongoing, recent, or time-sensitive political events,
current officeholders, current campaigns, current polls, breaking news, or recent legislation
unless the user explicitly asks about a specific current event.
When a question could be answered using enduring constitutional, governmental, historical,
or political concepts, answer using that stable background instead.
Do not invent dates, recent developments, or claims about what is happening "right now."

You are the PoliX educational assistant.

Your purpose is to help users understand American government, politics,
economics, public policy, civic institutions, and political information.

Remain politically neutral. Do not advocate for candidates, parties,
ideologies, or political outcomes. Do not tell the user what political
position they should adopt.

When discussing a disputed issue:
- Explain the relevant facts and institutions first.
- Separate established facts from interpretations and opinions.
- Explain major competing arguments fairly.
- Identify important evidence and uncertainty where relevant.
- If a claim depends on current events or changing facts, say that it
  should be checked against current sources rather than inventing certainty.

Use clear language appropriate for someone learning the topic. If the user
asks a complex question, break it into smaller concepts.

You are an educational assistant, not a political persuader.
"""


def send_chat_message(user_message):
    """Send a message to the local Ollama server without freezing Pygame."""
    global chat_busy, chat_pending_reply, chat_error

    try:
        payload = {
            "model": CHAT_MODEL,
            "messages": [
                {"role": "system", "content": CHAT_SYSTEM_PROMPT}
            ] + chat_messages[-8:],
            "stream": True,
            # Qwen3.5 can spend the whole small token budget on reasoning
            # unless thinking is explicitly disabled at the request level.
            "think": False,
            "options": dict(FAST_OPTIONS)
        }

        request = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(request, timeout=300) as response:
            parts = []
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                chunk = json.loads(line)
                message = chunk.get("message", {})
                content = message.get("content", "")
                if content:
                    parts.append(content)
                if chunk.get("done"):
                    break

        reply = "".join(parts).strip()

        # Some Ollama/Qwen versions can return no visible content when the
        # request is streamed. Retry once without streaming so the UI never
        # silently shows a blank assistant message.
        if not reply:
            fallback_payload = {
                "model": CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT}
                ] + chat_messages[-8:],
                "stream": False,
                "think": False,
                "options": dict(FAST_OPTIONS)
            }
            fallback_request = urllib.request.Request(
                OLLAMA_URL,
                data=json.dumps(fallback_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(fallback_request, timeout=300) as fallback_response:
                fallback_data = json.loads(fallback_response.read().decode("utf-8"))
            reply = fallback_data.get("message", {}).get("content", "").strip()

        if not reply:
            raise RuntimeError(
                f"Ollama returned no answer from '{CHAT_MODEL}'. Try pulling the model again."
            )

        chat_pending_reply = reply
        chat_error = ""

    except urllib.error.URLError:
        chat_error = (
            "Couldn't connect to Ollama. Make sure Ollama is running and "
            f"the model '{CHAT_MODEL}' is installed."
        )
    except Exception as exc:
        chat_error = f"Chatbot error: {exc}"
    finally:
        chat_busy = False


def start_chat_request(message):
    """Start an Ollama request on a background thread."""
    global chat_busy, chat_pending_reply, chat_error

    if chat_busy:
        return

    chat_busy = True
    chat_pending_reply = None
    chat_error = ""

    thread = threading.Thread(
        target=send_chat_message,
        args=(message,),
        daemon=True
    )
    thread.start()


# Validate and submit the text currently in the chat input box.
def send_current_chat_input():
    """Add the current input to the conversation and ask Ollama."""
    global chat_input, chat_scroll

    message = chat_input.strip()

    if not message or chat_busy:
        return

    chat_messages.append({"role": "user", "content": message})
    chat_input = ""
    chat_scroll = 0
    start_chat_request(message)


# Saved diagnostic results loaded from info.txt so the app remembers
# the learner's strengths and areas to develop after a restart.
saved_diagnostic_results = {}

for line in lines:
    if line.startswith("diagnostic|"):
        parts = line.split("|", 3)
        if len(parts) == 4:
            name, percentage_text, level = parts[1], parts[2], parts[3]
            try:
                saved_diagnostic_results[name] = {
                    "percentage": float(percentage_text),
                    "level": level
                }
            except ValueError:
                pass

cursor_visible = True
last_cursor_toggle = time.time()


# ============================================================
# UI ELEMENTS
# ============================================================

input_box = pygame.Rect(
    300,
    315,
    400,
    60
)

continue_button = pygame.Rect(
    350,
    410,
    300,
    58
)

# Separate button position for the diagnostic screen.
diagnostic_continue_button = pygame.Rect(
    700,
    555,
    180,
    44
)

chat_input_box = pygame.Rect(70, 555, 760, 52)
chat_send_button = pygame.Rect(845, 555, 85, 52)
chat_home_button = pygame.Rect(805, 92, 125, 42)
chat_button_center = (960, 610)
chat_button_radius = 30

# ============================================================
# FLASHCARD STATE
# ============================================================

flashcards_filename = "flashcards.json"
flashcards = []
flashcard_front = ""
flashcard_back = ""
flashcard_active_field = None
flashcard_scroll = 0
flashcard_mode = "create"
flashcard_test_index = 0
flashcard_test_revealed = False
flashcard_test_known = 0
flashcard_test_review = 0

if os.path.exists(flashcards_filename):
    try:
        with open(flashcards_filename, "r", encoding="utf-8") as file:
            loaded_flashcards = json.load(file)
            if isinstance(loaded_flashcards, list):
                flashcards = loaded_flashcards
    except (OSError, json.JSONDecodeError):
        flashcards = []

flashcard_front_box = pygame.Rect(70, 215, 410, 65)
flashcard_back_box = pygame.Rect(520, 215, 410, 65)
flashcard_add_button = pygame.Rect(680, 315, 250, 48)
flashcard_home_button = pygame.Rect(800, 82, 130, 42)
flashcard_create_mode_button = pygame.Rect(620, 142, 145, 42)
flashcard_test_mode_button = pygame.Rect(775, 142, 155, 42)
flashcard_test_card = pygame.Rect(90, 205, 820, 250)
flashcard_reveal_button = pygame.Rect(350, 470, 300, 48)
flashcard_known_button = pygame.Rect(165, 520, 300, 48)
flashcard_review_button = pygame.Rect(535, 520, 300, 48)
flashcard_restart_button = pygame.Rect(350, 470, 300, 48)
FLASHCARD_LIST_TOP = 405
FLASHCARD_LIST_BOTTOM = 585
FLASHCARD_ROW_HEIGHT = 86
FLASHCARD_GAP = 10

# Custom quiz UI
custom_quiz_open_button = pygame.Rect(70, 390, 860, 48)
custom_quiz_interest_box = pygame.Rect(110, 225, 780, 62)
custom_quiz_count_buttons = [
    (5, pygame.Rect(110, 330, 160, 44)),
    (10, pygame.Rect(285, 330, 160, 44)),
    (15, pygame.Rect(460, 330, 160, 44)),
    (20, pygame.Rect(635, 330, 160, 44)),
]
custom_quiz_difficulty_buttons = [
    ("Basics", pygame.Rect(110, 410, 235, 44)),
    ("Intermediate", pygame.Rect(355, 410, 235, 44)),
    ("Challenging", pygame.Rect(600, 410, 235, 44)),
]
custom_quiz_generate_button = pygame.Rect(650, 485, 240, 50)
custom_quiz_home_button = pygame.Rect(800, 92, 130, 42)
custom_quiz_next_button = pygame.Rect(690, 535, 180, 48)
custom_quiz_feedback_button = pygame.Rect(690, 535, 180, 48)
custom_quiz_option_rects = [pygame.Rect(150, 300 + i * 55, 700, 45) for i in range(4)]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

# Paint the global background gradient and the subtle decorative light glows.
def draw_gradient_background():
    """Modern dark gradient with subtle green ambient light."""
    top = (10, 27, 21)
    bottom = (17, 42, 31)
    for y in range(HEIGHT):
        t = y / max(1, HEIGHT - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        pygame.draw.line(screen, color, (0, y), (WIDTH, y))

    glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*PRIMARY, 22), (WIDTH - 40, 80), 260)
    pygame.draw.circle(glow, (75, 150, 110, 12), (90, HEIGHT - 40), 230)
    screen.blit(glow, (0, 0))


# Draw a soft offset shadow behind cards and controls for depth.
def draw_shadow(rect, radius=18, alpha=80, offset=(0, 6)):
    shadow = pygame.Surface((rect.width + 24, rect.height + 24), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, alpha), (12, 12, rect.width, rect.height), border_radius=radius)
    screen.blit(shadow, (rect.x - 12 + offset[0], rect.y - 12 + offset[1]))


# Shared card renderer used throughout the modernized interface.
def draw_modern_card(rect, fill=CARD, border=BORDER, radius=18, hover=False):
    draw_shadow(rect, radius, 55 if not hover else 75)
    pygame.draw.rect(screen, CARD_HOVER if hover else fill, rect, border_radius=radius)
    pygame.draw.rect(screen, border, rect, width=1, border_radius=radius)


# Render the green gradient used for emphasized/active controls.
def draw_gradient_pill(rect, left=PRIMARY_DARK, right=PRIMARY):
    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for x in range(rect.width):
        t = x / max(1, rect.width - 1)
        c = tuple(int(left[i] * (1 - t) + right[i] * t) for i in range(3))
        pygame.draw.line(surf, (*c, 255), (x, 0), (x, rect.height))
    mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=rect.height // 2)
    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    screen.blit(surf, rect.topleft)


# Small uppercase label used to establish hierarchy between sections.
def draw_section_label(text, x, y):
    label = ui_font(14, True).render(text.upper(), True, PRIMARY)
    screen.blit(label, (x, y))


# Draw the PoliX wordmark and its circular mark in the upper-left corner.
def draw_logo():
    # Center the emblem on the visible glyphs, not the font surface padding.
    logo = logo_font.render("PoliX", True, CREAM)
    logo_rect = logo.get_rect(topleft=(63, 26))
    bbox = logo.get_bounding_rect(min_alpha=1)
    visual_center_y = logo_rect.y + bbox.centery

    visual_center_y += 4
    pygame.draw.circle(screen, PRIMARY, (43, visual_center_y), 7)
    pygame.draw.circle(screen, (45, 110, 80), (43, visual_center_y), 12, width=2)
    screen.blit(logo, logo_rect)


# Draw the centered container used by onboarding, the diagnostic, and the quiz.
def draw_card():
    card = pygame.Rect(100, 92, 800, 500)
    draw_modern_card(card, fill=CARD, radius=24)


# Shared button styling: hover/active states use the primary gradient.
def draw_button(rect, text, active=False):
    mouse_pos = pygame.mouse.get_pos()
    hovered = rect.collidepoint(mouse_pos)
    enabled = active or hovered
    if enabled:
        draw_gradient_pill(rect)
    else:
        pygame.draw.rect(screen, (31, 67, 50), rect, border_radius=12)
        pygame.draw.rect(screen, BORDER, rect, width=1, border_radius=12)
    rendered = button_font.render(text, True, BACKGROUND if enabled else CREAM)
    screen.blit(rendered, (rect.centerx - rendered.get_width() // 2, rect.centery - rendered.get_height() // 2))


# Break text into lines that fit a specified pixel width.
def wrap_text(text, font, max_width):

    words = text.split()
    lines = []
    current_line = ""

    for word in words:

        test_line = current_line + " " + word

        if font.size(test_line)[0] <= max_width:
            current_line = test_line.strip()

        else:
            if current_line:
                lines.append(current_line)

            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def draw_wrapped_text(text, font, color, x, y, max_width, line_gap=None, max_lines=None, max_height=None):
    """Draw wrapped text within width/line/height bounds so it cannot escape its container."""
    lines = wrap_text(text, font, max_width)

    if line_gap is None:
        line_gap = font.get_height() + 2

    # Convert a pixel-height limit into a safe line limit.
    if max_height is not None:
        safe_lines = max(1, int((max_height - font.get_height()) // line_gap) + 1)
        max_lines = safe_lines if max_lines is None else min(max_lines, safe_lines)

    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]

        # Add an ellipsis to the final visible line if content was truncated.
        last = lines[-1]
        while last and font.size(last + "...")[0] > max_width:
            last = last[:-1].rstrip()

        lines[-1] = (last + "...") if last else "..."

    # Clip drawing to the requested height as a final safety boundary.
    old_clip = screen.get_clip()
    if max_height is not None:
        clip_rect = pygame.Rect(x, y, max_width, max_height)
        screen.set_clip(old_clip.clip(clip_rect))

    for index, line in enumerate(lines):
        rendered = font.render(line, True, color)
        screen.blit(rendered, (x, y + index * line_gap))

    if max_height is not None:
        screen.set_clip(old_clip)

    return len(lines)


def render_fitted_text(text, font_name, max_size, min_size, max_width, color):
    """Render one line of text, reducing the font size until it fits."""
    size = max_size

    while size > min_size:
        font = pygame.font.Font(None, size)
        if font.size(text)[0] <= max_width:
            return font.render(text, True, color)

        size -= 1

    font = pygame.font.Font(None, min_size)
    rendered = font.render(text, True, color)
    return rendered


# Persist user-created flashcards locally so they survive app restarts.
def save_flashcards():
    try:
        with open(flashcards_filename, "w", encoding="utf-8") as file:
            json.dump(flashcards, file, indent=2, ensure_ascii=False)
    except OSError:
        pass


# Keep the flashcard list scroll position within its valid range.
def clamp_flashcard_scroll():
    global flashcard_scroll
    total_height = len(flashcards) * (FLASHCARD_ROW_HEIGHT + FLASHCARD_GAP) - FLASHCARD_GAP
    max_scroll = max(0, total_height - (FLASHCARD_LIST_BOTTOM - FLASHCARD_LIST_TOP))
    flashcard_scroll = max(0, min(flashcard_scroll, max_scroll))


# Render the flashcard editor/list and the Create/Test controls.
def draw_flashcards():
    global flashcard_scroll

    title = title_font.render("Flashcards", True, CREAM)
    screen.blit(title, (65, 85))

    draw_button(flashcard_home_button, "< Home")

    # Compact segmented mode switch: one clear control for Create vs Test.
    mode_group = pygame.Rect(620, 142, 310, 42)
    pygame.draw.rect(screen, (20, 47, 35), mode_group, border_radius=12)
    pygame.draw.rect(screen, BORDER, mode_group, width=1, border_radius=12)
    draw_button(flashcard_create_mode_button, "Create", active=flashcard_mode == "create")
    draw_button(flashcard_test_mode_button, "Test", active=flashcard_mode == "test")

    if flashcard_mode == "test":
        draw_flashcard_test()
        return

    subtitle = small_font.render(
        "Create your own cards and review what you want to remember.",
        True,
        MUTED
    )
    screen.blit(subtitle, (68, 145))

    # Input labels
    front_label = small_font.render("FRONT / QUESTION", True, PRIMARY)
    back_label = small_font.render("BACK / ANSWER", True, PRIMARY)
    screen.blit(front_label, (70, 188))
    screen.blit(back_label, (520, 188))

    for box, text_value, active in [
        (flashcard_front_box, flashcard_front, flashcard_active_field == "front"),
        (flashcard_back_box, flashcard_back, flashcard_active_field == "back"),
    ]:
        pygame.draw.rect(screen, (18, 42, 31), box, border_radius=12)
        pygame.draw.rect(
            screen, PRIMARY if active else BORDER, box, width=2, border_radius=12
        )
        rendered = render_fitted_text(
            text_value, None, 24, 17, box.width - 30, CREAM
        ) if text_value else None
        if rendered:
            screen.blit(
                rendered,
                (box.x + 15, box.centery - rendered.get_height() // 2)
            )
        else:
            placeholder = small_font.render("Type here...", True, MUTED)
            screen.blit(
                placeholder,
                (box.x + 15, box.centery - placeholder.get_height() // 2)
            )

        # Blinking text cursor for both flashcard text boxes.
        if active and cursor_visible:
            cursor_x = box.x + 15 + (rendered.get_width() if rendered else 0)
            pygame.draw.line(
                screen,
                PRIMARY,
                (cursor_x, box.y + 15),
                (cursor_x, box.bottom - 15),
                2
            )

    add_enabled = bool(flashcard_front.strip() and flashcard_back.strip())
    draw_button(flashcard_add_button, "Add Flashcard", active=add_enabled)

    count_text = small_font.render(
        f"YOUR CARDS  •  {len(flashcards)}", True, MUTED
    )
    screen.blit(count_text, (70, 375))

    clamp_flashcard_scroll()
    old_clip = screen.get_clip()
    list_rect = pygame.Rect(60, FLASHCARD_LIST_TOP, 880, FLASHCARD_LIST_BOTTOM - FLASHCARD_LIST_TOP)
    screen.set_clip(list_rect)

    for i, card in enumerate(flashcards):
        y = FLASHCARD_LIST_TOP + i * (FLASHCARD_ROW_HEIGHT + FLASHCARD_GAP) - flashcard_scroll
        rect = pygame.Rect(70, y, 860, FLASHCARD_ROW_HEIGHT)
        hovered = rect.collidepoint(pygame.mouse.get_pos())

        pygame.draw.rect(
            screen, CARD_HOVER if hovered else CARD, rect, border_radius=14
        )
        pygame.draw.rect(
            screen, PRIMARY if hovered else BORDER, rect, width=1, border_radius=14
        )

        number = small_font.render(f"{i + 1:02d}", True, PRIMARY)
        screen.blit(number, (rect.x + 15, rect.y + 12))

        front = render_fitted_text(
            str(card.get("front", "")), None, 22, 16, 370, CREAM
        )
        back = render_fitted_text(
            str(card.get("back", "")), None, 20, 15, 370, MUTED
        )
        screen.blit(front, (rect.x + 60, rect.y + 10))
        screen.blit(back, (rect.x + 60, rect.y + 43))

    screen.set_clip(old_clip)

    total_height = len(flashcards) * (FLASHCARD_ROW_HEIGHT + FLASHCARD_GAP) - FLASHCARD_GAP
    view_height = FLASHCARD_LIST_BOTTOM - FLASHCARD_LIST_TOP
    max_scroll = max(0, total_height - view_height)
    if max_scroll > 0:
        track = pygame.Rect(944, FLASHCARD_LIST_TOP, 6, view_height)
        pygame.draw.rect(screen, BORDER, track, border_radius=3)
        thumb_height = max(35, int(view_height * view_height / total_height))
        thumb_y = FLASHCARD_LIST_TOP + int(
            (view_height - thumb_height) * (flashcard_scroll / max_scroll)
        )
        pygame.draw.rect(
            screen, PRIMARY, pygame.Rect(944, thumb_y, 6, thumb_height), border_radius=3
        )

    if not flashcards:
        empty = small_font.render(
            "No flashcards yet. Add your first one above.", True, MUTED
        )
        screen.blit(empty, (70, 415))


# Render the one-card-at-a-time review mode and its progress controls.
def draw_flashcard_test():
    """Study the saved cards one at a time and rate recall."""
    global flashcard_test_index

    subtitle = small_font.render(
        "Test yourself: try to answer before revealing the back.",
        True,
        MUTED
    )
    screen.blit(subtitle, (68, 145))

    if not flashcards:
        empty_title = subtitle_font.render("No flashcards to test yet.", True, CREAM)
        screen.blit(empty_title, (WIDTH // 2 - empty_title.get_width() // 2, 270))
        empty = small_font.render(
            "Create a few cards first, then come back to Test mode.", True, MUTED
        )
        screen.blit(empty, (WIDTH // 2 - empty.get_width() // 2, 315))
        return

    # End-of-session summary.
    if flashcard_test_index >= len(flashcards):
        summary = subtitle_font.render("Test complete", True, CREAM)
        screen.blit(summary, (WIDTH // 2 - summary.get_width() // 2, 235))

        stats = small_font.render(
            f"Knew it: {flashcard_test_known}    •    Needs review: {flashcard_test_review}",
            True,
            MUTED
        )
        screen.blit(stats, (WIDTH // 2 - stats.get_width() // 2, 290))

        draw_button(flashcard_restart_button, "Test Again", active=True)
        return

    card = flashcards[flashcard_test_index]
    card_rect = flashcard_test_card

    pygame.draw.rect(screen, CARD, card_rect, border_radius=22)
    pygame.draw.rect(screen, BORDER, card_rect, width=1, border_radius=22)

    counter = small_font.render(
        f"CARD {flashcard_test_index + 1} / {len(flashcards)}", True, PRIMARY
    )
    screen.blit(counter, (card_rect.x + 25, card_rect.y + 20))

    prompt = "QUESTION"
    label = small_font.render(prompt, True, MUTED)
    screen.blit(label, (card_rect.centerx - label.get_width() // 2, card_rect.y + 55))

    front_lines = wrap_text(str(card.get("front", "")), subtitle_font, 650)
    y = card_rect.y + 105
    for line in front_lines[:3]:
        rendered = subtitle_font.render(line, True, CREAM)
        screen.blit(rendered, (card_rect.centerx - rendered.get_width() // 2, y))
        y += 34

    if flashcard_test_revealed:
        divider_y = card_rect.y + 170
        pygame.draw.line(screen, BORDER, (card_rect.x + 80, divider_y), (card_rect.right - 80, divider_y), 1)
        answer_label = small_font.render("ANSWER", True, PRIMARY)
        screen.blit(answer_label, (card_rect.centerx - answer_label.get_width() // 2, divider_y + 12))

        back_lines = wrap_text(str(card.get("back", "")), small_font, 650)
        y = divider_y + 40
        for line in back_lines[:2]:
            rendered = small_font.render(line, True, CREAM)
            screen.blit(rendered, (card_rect.centerx - rendered.get_width() // 2, y))
            y += 25

        draw_button(flashcard_known_button, "✓ I knew it", active=True)
        draw_button(flashcard_review_button, "× Needs review", active=False)
    else:
        draw_button(flashcard_reveal_button, "Reveal Answer", active=True)


# ============================================================
# DIAGNOSTIC / HOME DATA
# ============================================================

areas = [
    ("Government & Constitution", "Build your foundation in how the U.S. government is structured and constrained.", 0, 5),
    ("Elections & Politics", "Understand elections, representation, political parties, and how votes translate into power.", 5, 10),
    ("Economics", "Build a foundation in inflation, taxes, government spending, debt, and regulation.", 10, 15),
    ("Major Policy Issues", "Understand the basic facts and competing arguments behind major domestic policy debates.", 15, 20),
    ("Society & Government Programs", "Learn how major government programs and debates around education and public safety work.", 20, 23),
    ("Foreign Policy & Information", "Understand America's international relationships and how to evaluate political information.", 23, 25),
]


# Convert the 25 self-assessment answers into six topic-level results.
def get_area_results():
    results = []

    for name, description, start, end in areas:
        area_answers = answers[start:end]

        # Use the current quiz answers when available. After a restart,
        # fall back to the diagnostic values saved in info.txt.
        if area_answers:
            percentage = (sum(area_answers) / (len(area_answers) * 3)) * 100

            if percentage >= 67:
                level = "Strong"
            elif percentage >= 34:
                level = "Developing"
            else:
                level = "Needs Attention"
        elif name in saved_diagnostic_results:
            percentage = saved_diagnostic_results[name]["percentage"]
            level = saved_diagnostic_results[name]["level"]
        else:
            percentage = 0
            level = "Needs Attention"

        results.append({
            "name": name,
            "description": description,
            "percentage": percentage,
            "level": level
        })

    return results


def get_recommended_area():
    results = get_area_results()

    # Lower knowledge scores are prioritized as learning opportunities.
    return min(results, key=lambda result: result["percentage"])


def save_diagnostic_results():
    """Persist the diagnostic results while preserving the username/quizzed flag."""
    global saved_diagnostic_results

    results = get_area_results()

    # Re-read info.txt because the username and "quizzed" marker may have
    # been written during this run after the original startup read.
    with open(filename, "r", encoding="utf-8") as file:
        current_lines = file.read().splitlines()

    non_diagnostic_lines = [
        line for line in current_lines
        if not line.startswith("diagnostic|")
    ]

    if username and username not in non_diagnostic_lines:
        non_diagnostic_lines.insert(0, username)

    if "quizzed" not in [line.lower().strip() for line in non_diagnostic_lines]:
        non_diagnostic_lines.append("quizzed")

    diagnostic_lines = [
        f"diagnostic|{result['name']}|{result['percentage']:.2f}|{result['level']}"
        for result in results
    ]

    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(non_diagnostic_lines))
        if non_diagnostic_lines and diagnostic_lines:
            file.write("\n")
        file.write("\n".join(diagnostic_lines))

    saved_diagnostic_results = {
        result["name"]: {
            "percentage": result["percentage"],
            "level": result["level"]
        }
        for result in results
    }


# Render topic strengths, progress bars, and the recommended starting area.
def draw_diagnostic():
    results = get_area_results()
    recommended = get_recommended_area()

    title = title_font.render("Your Civic Knowledge", True, CREAM)
    screen.blit(
        title,
        (WIDTH // 2 - title.get_width() // 2, 105)
    )

    subtitle = small_font.render(
        "This shows where your current knowledge is strongest and where you can build.",
        True,
        MUTED
    )
    screen.blit(
        subtitle,
        (WIDTH // 2 - subtitle.get_width() // 2, 180)
    )

    # Two columns of diagnostic cards.
    # Keep a clear visual gap below the heading so the subtitle never
    # collides with the first row of results.
    card_width = 350
    card_height = 62
    left_x = 125
    right_x = 525
    start_y = 225

    for index, result in enumerate(results):
        column = index % 2
        row = index // 2

        x = left_x if column == 0 else right_x
        y = start_y + row * 70

        rect = pygame.Rect(x, y, card_width, card_height)

        pygame.draw.rect(
            screen,
            (18, 42, 31),
            rect,
            border_radius=12
        )

        pygame.draw.rect(
            screen,
            BORDER,
            rect,
            width=1,
            border_radius=12
        )

        level_text = render_fitted_text(
            result["level"],
            None,
            22,
            18,
            155,
            PRIMARY if result["level"] == "Strong" else MUTED
        )

        # Reserve a dedicated area for the status label so long topic names
        # can never collide with labels such as "Needs Attention".
        level_x = rect.right - 15 - level_text.get_width()
        name_max_width = max(120, level_x - (rect.x + 15) - 12)

        name_text = render_fitted_text(
            result["name"],
            None,
            22,
            18,
            name_max_width,
            CREAM
        )

        screen.blit(
            name_text,
            (rect.x + 15, rect.y + 11)
        )

        screen.blit(
            level_text,
            (
                level_x,
                rect.y + 11
            )
        )

        # Small progress bar.
        bar = pygame.Rect(
            rect.x + 15,
            rect.y + 39,
            rect.width - 30,
            8
        )

        pygame.draw.rect(
            screen,
            BORDER,
            bar,
            border_radius=4
        )

        fill_width = int(bar.width * (result["percentage"] / 100))

        if fill_width > 0:
            fill = pygame.Rect(
                bar.x,
                bar.y,
                fill_width,
                bar.height
            )

            pygame.draw.rect(
                screen,
                PRIMARY,
                fill,
                border_radius=4
            )

    # Recommendation box.
    recommendation_rect = pygame.Rect(
        125,
        440,
        750,
        105
    )

    pygame.draw.rect(
        screen,
        CARD_HOVER,
        recommendation_rect,
        border_radius=16
    )

    pygame.draw.rect(
        screen,
        BORDER,
        recommendation_rect,
        width=1,
        border_radius=16
    )

    rec_label = small_font.render(
        "RECOMMENDED STARTING POINT",
        True,
        PRIMARY
    )

    screen.blit(
        rec_label,
        (recommendation_rect.x + 20, recommendation_rect.y + 14)
    )

    rec_name = subtitle_font.render(
        recommended["name"],
        True,
        CREAM
    )

    screen.blit(
        rec_name,
        (recommendation_rect.x + 20, recommendation_rect.y + 38)
    )

    draw_wrapped_text(
        recommended["description"],
        ui_font(16),
        MUTED,
        recommendation_rect.x + 20,
        recommendation_rect.y + 72,
        recommendation_rect.width - 40,
        line_gap=18,
        max_lines=2
    )



# ============================================================
# LEARNING RESOURCES
# ============================================================

# Resources are labeled by source type rather than described as
# "unbiased." PoliX presents them as learning materials and
# lets the learner decide what they find useful.
resources = {
    "Government": [
        {
            "title": "American Government 3e",
            "publisher": "OpenStax",
            "type": "Free open textbook",
            "description": "A broad introduction to American government, institutions, participation, elections, and political structures.",
            "url": "https://openstax.org/books/american-government-3e/pages/1-introduction"
        },
        {
            "title": "Constitution 101",
            "publisher": "National Constitution Center",
            "type": "Free course",
            "description": "A 15-unit course covering constitutional text, history, structure, interpretation, and landmark cases.",
            "url": "https://constitutioncenter.org/education/constitution-101-curriculum"
        },
        {
            "title": "Bill of Rights: Transcript",
            "publisher": "National Archives",
            "type": "Primary source",
            "description": "The text of the first ten amendments to the U.S. Constitution.",
            "url": "https://www.archives.gov/founding-docs/bill-of-rights-transcript"
        },
        {"title": "Six Big Ideas in the Constitution", "publisher": "National Archives", "type": "Free lesson", "description": "An educational lesson exploring limited government, republicanism, checks and balances, federalism, separation of powers, and popular sovereignty.", "url": "https://www.archives.gov/legislative/resources/education/constitution"},
        {"title": "The Constitution", "publisher": "Library of Congress", "type": "Primary-source collection", "description": "Classroom materials and primary sources for studying the Constitution, its development, and its continuing role in U.S. government.", "url": "https://www.loc.gov/classroom-materials/constitution/"},
        {"title": "What Congress Does and Why It Matters", "publisher": "National Archives", "type": "Free lesson", "description": "A lesson using primary sources to examine representation, separation of powers, and Congress's constitutional role.", "url": "https://www.archives.gov/legislative/resources/education/what-congress-does"},
    ],
    "Elections": [
        {
            "title": "Presidential Elections and Voting in U.S. History",
            "publisher": "Library of Congress",
            "type": "Primary-source collection",
            "description": "Historical materials on nominations, campaigns, voters, and the development of voting rights.",
            "url": "https://www.loc.gov/classroom-materials/elections/"
        },
        {
            "title": "U.S. Political Parties: Resource Guide",
            "publisher": "Library of Congress",
            "type": "Research guide",
            "description": "Historical and primary-source materials for understanding political parties and their role in U.S. politics.",
            "url": "https://guides.loc.gov/political-parties"
        },
        {
            "title": "American Government 3e",
            "publisher": "OpenStax",
            "type": "Free open textbook",
            "description": "Provides background on elections, representation, political parties, and the institutions that shape elections.",
            "url": "https://openstax.org/books/american-government-3e/pages/1-introduction"
        },
        {"title": "Elections and Voting", "publisher": "Library of Congress", "type": "Free classroom collection", "description": "Primary sources and classroom materials covering elections, voting, campaigns, and the history of participation in U.S. elections.", "url": "https://www.loc.gov/classroom-materials/elections/"},
        {"title": "Studying U.S. Elections with Political Cartoons", "publisher": "National Archives", "type": "Free lesson", "description": "Historical political cartoons used to explore elections and enduring features of the U.S. two-party political system.", "url": "https://www.archives.gov/legislative/resources/education"},
        {"title": "American Government: Elections and Voting", "publisher": "OpenStax", "type": "Free open textbook", "description": "Open textbook chapters covering voting, elections, campaigns, political parties, and representation in American government.", "url": "https://openstax.org/books/american-government-3e/pages/7-introduction"},
    ],
    "Economics": [
        {
            "title": "Principles of Economics 3e",
            "publisher": "OpenStax",
            "type": "Free open textbook",
            "description": "An introductory economics text covering markets, inflation, unemployment, taxes, government policy, microeconomics, and macroeconomics.",
            "url": "https://openstax.org/books/principles-economics-3e/pages/1-introduction"
        },
        {
            "title": "Budget and Economic Analysis",
            "publisher": "Congressional Budget Office",
            "type": "Government analysis",
            "description": "Nonpartisan analyses, projections, and reports on federal spending, revenues, deficits, debt, and the economy.",
            "url": "https://www.cbo.gov/topics"
        },
        {
            "title": "FRED Economic Data",
            "publisher": "Federal Reserve Bank of St. Louis",
            "type": "Economic data",
            "description": "A large public database of economic indicators that can be used to explore inflation, employment, output, interest rates, and more.",
            "url": "https://fred.stlouisfed.org/"
        },
        {"title": "Economic Indicators", "publisher": "Federal Reserve Bank of St. Louis", "type": "Free data resource", "description": "Explore public economic indicators and charts covering prices, employment, output, interest rates, and other measures.", "url": "https://fred.stlouisfed.org/"},
        {"title": "Fiscal Policy and the Economy", "publisher": "Congressional Budget Office", "type": "Government analysis", "description": "Research and analysis explaining federal revenues, spending, deficits, debt, and the effects of fiscal policy.", "url": "https://www.cbo.gov/topics/budget"},
        {"title": "Principles of Economics: Macroeconomics", "publisher": "OpenStax", "type": "Free open textbook", "description": "Free chapters explaining inflation, unemployment, monetary policy, fiscal policy, economic growth, and related concepts.", "url": "https://openstax.org/books/principles-economics-3e/pages/1-introduction"},
    ],
    "Policy": [
        {
            "title": "Congressional Research Service Reports",
            "publisher": "Congressional Research Service",
            "type": "Government research",
            "description": "Research reports explaining policy questions, legislation, programs, and policy options across many issue areas.",
            "url": "https://crsreports.congress.gov/"
        },
        {
            "title": "Health Policy Resources",
            "publisher": "Congressional Budget Office",
            "type": "Government analysis",
            "description": "Reports and analyses on health insurance, healthcare spending, Medicare, Medicaid, and related policy questions.",
            "url": "https://www.cbo.gov/topics/health-care"
        },
        {
            "title": "Energy and Climate Resources",
            "publisher": "U.S. Energy Information Administration",
            "type": "Government data and analysis",
            "description": "Public data and analysis on energy production, consumption, markets, emissions, and energy policy.",
            "url": "https://www.eia.gov/energyexplained/"
        },
        {"title": "Policy Arenas", "publisher": "OpenStax", "type": "Free open textbook", "description": "An overview of major domestic policy areas, including social welfare programs, regulation, and government spending.", "url": "https://openstax.org/books/american-government-4e/pages/16-3-policy-arenas"},
        {"title": "Health Policy", "publisher": "Congressional Budget Office", "type": "Government analysis", "description": "Research and analysis on health insurance, healthcare spending, Medicare, Medicaid, and health policy questions.", "url": "https://www.cbo.gov/topics/health-care"},
        {"title": "Energy Explained", "publisher": "U.S. Energy Information Administration", "type": "Government data and analysis", "description": "Accessible explanations and data on energy production, consumption, markets, emissions, and energy-related policy questions.", "url": "https://www.eia.gov/energyexplained/"},
    ],
    "Society": [
        {
            "title": "Social Security",
            "publisher": "Social Security Administration",
            "type": "Government resource",
            "description": "Official explanations of Social Security programs, eligibility, benefits, and how the system works.",
            "url": "https://www.ssa.gov/benefits/"
        },
        {
            "title": "Medicare",
            "publisher": "Medicare.gov",
            "type": "Government resource",
            "description": "Official information about Medicare coverage, costs, enrollment, and program structure.",
            "url": "https://www.medicare.gov/"
        },
        {
            "title": "Federal Student Aid",
            "publisher": "U.S. Department of Education",
            "type": "Government resource",
            "description": "Official information about federal student aid, loans, grants, repayment, and eligibility.",
            "url": "https://studentaid.gov/"
        },
        {"title": "Social Security: Understanding the Benefits", "publisher": "Social Security Administration", "type": "Government resource", "description": "Official information explaining Social Security programs, retirement and disability benefits, eligibility, and program basics.", "url": "https://www.ssa.gov/benefits/"},
        {"title": "Medicaid", "publisher": "Medicaid.gov", "type": "Government resource", "description": "Official information about Medicaid, including program structure, eligibility, financing, and state and federal roles.", "url": "https://www.medicaid.gov/"},
        {"title": "Education Resources", "publisher": "U.S. Department of Education", "type": "Government resource", "description": "Federal education information covering schools, higher education, student aid, and education policy programs.", "url": "https://www.ed.gov/"},
    ],
    "Information": [
        {
            "title": "Civic Online Reasoning",
            "publisher": "Digital Inquiry Group",
            "type": "Free skills curriculum",
            "description": "Free lessons that teach students to evaluate online information by asking who is behind it, what the evidence is, and what other sources say.",
            "url": "https://cor.inquirygroup.org/"
        },
        {
            "title": "Sorting Truth From Fiction: Civic Online Reasoning",
            "publisher": "MIT OpenCourseWare",
            "type": "Free course materials",
            "description": "Course materials focused on evaluating online information and developing civic online reasoning skills.",
            "url": "https://ocw.mit.edu/courses/res-cms-504-sorting-truth-from-fiction-civic-online-reasoning-spring-2021/"
        },
        {
            "title": "Civic Online Reasoning for the Civics Classroom",
            "publisher": "Digital Inquiry Group",
            "type": "Free lesson collection",
            "description": "Civics-focused activities for evaluating political claims, social media posts, evidence, sources, and sponsored content.",
            "url": "https://cor.inquirygroup.org/curriculum/collections/cor-for-the-civics-classroom/"
        },
        {"title": "Regulating the Media", "publisher": "OpenStax", "type": "Free open textbook", "description": "A chapter explaining the role of media in American politics, the First Amendment, and the limits and responsibilities surrounding the press.", "url": "https://openstax.org/books/american-government-4e/pages/8-3-regulating-the-media"},
        {"title": "Educator Resources", "publisher": "National Archives", "type": "Free educational resources", "description": "Free resources for working with primary sources, including documents, historical context, and activities for civic learning.", "url": "https://www.archives.gov/education"},
        {"title": "American Government: The Media", "publisher": "OpenStax", "type": "Free open textbook", "description": "Open textbook material covering media, political communication, information, and the role of media in American government.", "url": "https://openstax.org/books/american-government-4e/pages/8-introduction"},
    ]
}


# Resource-page scrolling state
resource_scroll = 0
RESOURCE_CARD_HEIGHT = 130
RESOURCE_GAP = 10
RESOURCE_TOP = 190
RESOURCE_BOTTOM = 585
RESOURCE_VIEW_HEIGHT = RESOURCE_BOTTOM - RESOURCE_TOP


# Prevent resource scrolling from moving beyond the available cards.
def clamp_resource_scroll(topic):
    global resource_scroll
    total_height = len(resources[topic]) * (RESOURCE_CARD_HEIGHT + RESOURCE_GAP) - RESOURCE_GAP
    max_scroll = max(0, total_height - RESOURCE_VIEW_HEIGHT)
    resource_scroll = max(0, min(resource_scroll, max_scroll))


# Translate diagnostic category names into the resource-library topic names.
def topic_key_for_area(area_name):
    mapping = {
        "Government & Constitution": "Government",
        "Elections & Politics": "Elections",
        "Economics": "Economics",
        "Major Policy Issues": "Policy",
        "Society & Government Programs": "Society",
        "Foreign Policy & Information": "Information",
    }
    return mapping.get(area_name, "Government")


# Render one learning-resource card with bounded text and an Open action.
def draw_resource_card(rect, resource, hovered=False):
    # Keep every piece of content inside the card's bounds.
    pygame.draw.rect(
        screen,
        CARD_HOVER if hovered else CARD,
        rect,
        border_radius=16
    )

    pygame.draw.rect(
        screen,
        PRIMARY if hovered else BORDER,
        rect,
        width=1,
        border_radius=16
    )

    padding = 18
    content_width = rect.width - (padding * 2)

    type_text = render_fitted_text(
        resource["type"].upper(),
        None,
        22,
        16,
        content_width,
        PRIMARY
    )
    screen.blit(type_text, (rect.x + padding, rect.y + 13))

    title_text = render_fitted_text(
        resource["title"],
        None,
        30,
        22,
        content_width - 105,
        CREAM
    )
    screen.blit(title_text, (rect.x + padding, rect.y + 39))

    publisher = render_fitted_text(
        resource["publisher"],
        None,
        22,
        18,
        content_width - 105,
        MUTED
    )
    screen.blit(publisher, (rect.x + padding, rect.y + 69))

    desc_font = pygame.font.Font(None, 18)
    draw_wrapped_text(
        resource["description"],
        desc_font,
        MUTED,
        rect.x + padding,
        rect.y + 92,
        content_width - 120,
        line_gap=17,
        max_lines=2
    )

    open_text = small_font.render(
        "Open  >",
        True,
        PRIMARY if hovered else MUTED
    )
    screen.blit(
        open_text,
        (
            rect.right - open_text.get_width() - padding,
            rect.bottom - open_text.get_height() - 12
        )
    )


# Render the selected topic's free resources with clipping and scrolling.
def draw_resources(topic):
    global resource_scroll
    resource_list = resources[topic]
    clamp_resource_scroll(topic)

    title = title_font.render(topic, True, CREAM)
    screen.blit(title, (65, 85))
    subtitle = small_font.render("Free learning materials, labeled by source type and publisher.", True, MUTED)
    screen.blit(subtitle, (68, 145))

    back_rect = pygame.Rect(800, 92, 130, 42)
    draw_button(back_rect, "< Home")

    old_clip = screen.get_clip()
    screen.set_clip(pygame.Rect(50, RESOURCE_TOP, 900, RESOURCE_VIEW_HEIGHT))
    for i, resource in enumerate(resource_list):
        y = RESOURCE_TOP + i * (RESOURCE_CARD_HEIGHT + RESOURCE_GAP) - resource_scroll
        rect = pygame.Rect(65, y, 870, RESOURCE_CARD_HEIGHT)
        hovered = rect.collidepoint(pygame.mouse.get_pos()) and rect.bottom > RESOURCE_TOP and rect.top < RESOURCE_BOTTOM
        draw_resource_card(rect, resource, hovered)
    screen.set_clip(old_clip)

    total_height = len(resource_list) * (RESOURCE_CARD_HEIGHT + RESOURCE_GAP) - RESOURCE_GAP
    max_scroll = max(0, total_height - RESOURCE_VIEW_HEIGHT)
    if max_scroll > 0:
        track = pygame.Rect(944, RESOURCE_TOP, 6, RESOURCE_VIEW_HEIGHT)
        pygame.draw.rect(screen, BORDER, track, border_radius=3)
        thumb_height = max(35, int(RESOURCE_VIEW_HEIGHT * RESOURCE_VIEW_HEIGHT / total_height))
        thumb_y = RESOURCE_TOP + int((RESOURCE_VIEW_HEIGHT - thumb_height) * (resource_scroll / max_scroll))
        pygame.draw.rect(screen, PRIMARY, pygame.Rect(944, thumb_y, 6, thumb_height), border_radius=3)

    note = small_font.render("Scroll to browse resources. PoliX does not rank these sources.", True, MUTED)
    screen.blit(note, (68, 610))

# Ask Ollama for a structured custom quiz without blocking the UI thread.
def start_custom_quiz_generation():
    """Generate a neutral, knowledge-focused quiz without blocking Pygame."""
    global custom_quiz_busy, custom_quiz_pending, custom_quiz_error, custom_quiz_status

    interest = custom_quiz_interest.strip()
    if not interest or custom_quiz_busy:
        return

    custom_quiz_busy = True
    custom_quiz_pending = None
    custom_quiz_error = ""
    custom_quiz_status = "Generating your quiz..."

    def extract_questions(raw):
        """Extract and validate whatever complete questions Ollama returned."""
        outer = json.loads(raw)
        content = outer.get("message", {}).get("content", "")
        if not isinstance(content, str):
            content = str(content or "")
        content = content.strip()

        if not content:
            raise ValueError("Ollama returned an empty quiz response.")

        if "```" in content:
            content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
            content = re.sub(r"\s*```$", "", content)

        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("The quiz model did not return a JSON object.")

        data = json.loads(content[start:end + 1])
        generated = data.get("questions", [])
        if not isinstance(generated, list):
            raise ValueError("The quiz response did not contain a questions list.")

        cleaned = []
        for item in generated:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            options_data = item.get("options", [])
            answer = item.get("answer")
            if not question or not isinstance(options_data, list) or len(options_data) != 4:
                continue
            if isinstance(answer, bool) or not isinstance(answer, int) or answer not in range(4):
                continue
            options = [str(x).strip() for x in options_data]
            if any(not option for option in options):
                continue
            cleaned.append({
                "question": question,
                "options": options,
                "answer": answer,
            })

        if not cleaned:
            raise ValueError("The quiz model did not return any complete questions.")
        return cleaned

    def call_ollama(prompt, num_predict, use_json_format=True):
        payload = {
            "model": QUIZ_MODEL,
            "messages": [
                {"role": "system", "content": (
                    "You create short, neutral educational American civics quizzes. "
                    "Never advocate for a party, candidate, ideology, or policy outcome. "
                    "Return exactly the requested quiz data and nothing else."
                )},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.1,
                "top_k": 20,
                "top_p": 0.8,
                "num_ctx": 2048,
                "num_predict": num_predict,
                "keep_alive": "10m",
            }
        }
        if use_json_format:
            payload["format"] = "json"

        request = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read().decode("utf-8")

    def worker():
        global custom_quiz_busy, custom_quiz_pending, custom_quiz_error, custom_quiz_status
        try:
            target = custom_quiz_count
            prompt = f"""Create {target} neutral American civics questions about: {interest}
Difficulty: {custom_quiz_difficulty}.

Keep every question short, factual, self-contained, and objectively answerable.
Each question must have exactly 4 short answer choices and exactly 1 correct choice.
Do not ask about current officeholders, current polls, or breaking news.
Do not advocate for any political side.

Return ONLY this JSON object:
{{"questions":[{{"question":"...","options":["...","...","...","..."],"answer":0}}]}}

The answer value must be the zero-based index of the correct choice (0, 1, 2, or 3).
Do not include markdown, explanations, or text outside the JSON object.
Make sure you provide all {target} questions."""

            generated = None
            last_error = None

            # First attempt. The small model sometimes stops one question early;
            # do not fail the entire quiz when that happens.
            for use_json_format in (True, False):
                try:
                    raw = call_ollama(
                        prompt,
                        num_predict=max(1200, target * 230),
                        use_json_format=use_json_format
                    )
                    generated = extract_questions(raw)
                    break
                except Exception as exc:
                    last_error = exc
                    if use_json_format:
                        custom_quiz_status = "Retrying quiz generation..."

            if not generated:
                raise ValueError(str(last_error) if last_error else "Quiz generation failed.")

            # If the 0.8B model stopped early, ask only for the missing questions.
            # This is much more reliable than throwing away a valid partial quiz.
            if len(generated) < target:
                missing = target - len(generated)
                custom_quiz_status = f"Adding {missing} more question{'s' if missing != 1 else ''}..."
                existing = "\n".join(
                    f"- {q['question']}" for q in generated
                )
                top_up_prompt = f"""Create exactly {missing} additional neutral American civics questions about: {interest}
Difficulty: {custom_quiz_difficulty}.

These questions are already in the quiz, so do not repeat them:
{existing}

Each new question must have exactly 4 short answer choices and exactly 1 correct choice.
Keep them factual, self-contained, and objectively answerable.
Do not ask about current officeholders, current polls, or breaking news.
Do not advocate for any political side.

Return ONLY JSON in this exact shape:
{{"questions":[{{"question":"...","options":["...","...","...","..."],"answer":0}}]}}
The answer must be the zero-based correct-choice index."""

                top_up = None
                for use_json_format in (True, False):
                    try:
                        raw = call_ollama(
                            top_up_prompt,
                            num_predict=max(500, missing * 230),
                            use_json_format=use_json_format
                        )
                        top_up = extract_questions(raw)
                        break
                    except Exception as exc:
                        last_error = exc

                if top_up:
                    generated.extend(top_up[:missing])

            if len(generated) < target:
                # Last-resort behavior: show the valid questions we actually got
                # rather than showing an error screen with no quiz at all.
                custom_quiz_status = (
                    f"Generated {len(generated)} of {target} questions."
                )
            else:
                generated = generated[:target]
                custom_quiz_status = "Quiz ready."

            custom_quiz_pending = generated

        except urllib.error.HTTPError as exc:
            custom_quiz_error = f"Ollama returned HTTP {exc.code}. Make sure the model is available."
            custom_quiz_status = ""
        except urllib.error.URLError:
            custom_quiz_error = (
                "Couldn't connect to Ollama. Make sure Ollama is running and "
                f"the model '{QUIZ_MODEL}' is installed."
            )
            custom_quiz_status = ""
        except Exception as exc:
            custom_quiz_error = f"Couldn't create the quiz: {exc}"
            custom_quiz_status = ""
        finally:
            custom_quiz_busy = False

    threading.Thread(target=worker, daemon=True).start()


# Generate a short explanation only when a custom-quiz answer is incorrect.
def start_custom_quiz_feedback(question, selected_option, correct_option):
    """Generate a very short explanation only when the learner answers incorrectly."""
    global custom_quiz_feedback_busy, custom_quiz_feedback_pending
    global custom_quiz_feedback_error

    if custom_quiz_feedback_busy:
        return

    custom_quiz_feedback_busy = True
    custom_quiz_feedback_pending = None
    custom_quiz_feedback_error = ""

    def worker():
        global custom_quiz_feedback_busy, custom_quiz_feedback_pending
        global custom_quiz_feedback_error
        try:
            prompt = f"""Explain this quiz mistake in 1 short sentence (maximum 2 sentences).

Question: {question}
Learner's answer: {selected_option}
Correct answer: {correct_option}

Briefly explain the factual reason the learner's answer is wrong and why the correct answer fits.
Be neutral, clear, and educational. Do not say 'you are wrong' and do not use markdown.
Return only the explanation text."""

            payload = {
                "model": QUIZ_MODEL,
                "messages": [
                    {"role": "system", "content": (
                        "You are a concise civic education tutor. Give factual, neutral "
                        "explanations. Never advocate for a political side."
                    )},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "think": False,
                "options": {
                    "temperature": 0.1,
                    "top_k": 20,
                    "top_p": 0.8,
                    "num_ctx": 1536,
                    "num_predict": 90,
                    "keep_alive": "10m",
                }
            }

            request = urllib.request.Request(
                OLLAMA_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(request, timeout=90) as response:
                raw = response.read().decode("utf-8")

            outer = json.loads(raw)
            explanation = str(outer.get("message", {}).get("content", "")).strip()
            explanation = re.sub(r"^```(?:text)?\s*", "", explanation, flags=re.IGNORECASE)
            explanation = re.sub(r"\\s*```$", "", explanation).strip()

            if not explanation:
                raise ValueError("The explanation model returned an empty response.")

            # Keep the UI concise even if the small model ignores the instruction.
            sentences = re.split(r"(?<=[.!?])\s+", explanation)
            explanation = " ".join(sentences[:2]).strip()
            custom_quiz_feedback_pending = explanation

        except Exception as exc:
            custom_quiz_feedback_error = str(exc)
        finally:
            custom_quiz_feedback_busy = False

    threading.Thread(target=worker, daemon=True).start()


# Move from feedback/current question to the next custom-quiz question.
def advance_custom_quiz_question():
    """Move to the next custom-quiz question after feedback is finished."""
    global custom_quiz_index, custom_quiz_selected
    global custom_quiz_feedback_active, custom_quiz_feedback
    global custom_quiz_feedback_pending, custom_quiz_feedback_error
    global custom_quiz_finished

    custom_quiz_index += 1
    custom_quiz_selected = None
    custom_quiz_feedback_active = False
    custom_quiz_feedback = ""
    custom_quiz_feedback_pending = None
    custom_quiz_feedback_error = ""

    if custom_quiz_index >= len(custom_quiz_questions):
        custom_quiz_finished = True


# Show a simple waiting state while the local quiz model is generating questions.
def draw_quiz_loading_screen():
    """Animated loading screen shown while Ollama builds the custom quiz."""
    title = title_font.render("Building your quiz", True, CREAM)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 165))

    phase = int(time.time() * 4) % 4
    dots = "." * phase
    status = subtitle_font.render(dots, True, PRIMARY)
    screen.blit(status, (WIDTH // 2 - status.get_width() // 2, 250))

    detail = small_font.render(
        f"Using {QUIZ_MODEL} to create {custom_quiz_count} {custom_quiz_difficulty.lower()} questions",
        True, MUTED
    )
    screen.blit(detail, (WIDTH // 2 - detail.get_width() // 2, 320))

    hint = small_font.render(
        "PoliX is generating the questions in the background. Please wait...",
        True, MUTED
    )
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 355))


# Render the custom-quiz setup dialog for topic, count, and difficulty.
def draw_custom_quiz_modal():
    global custom_quiz_pending, custom_quiz_modal, custom_quiz_interest_active

    # Dim the home screen behind the modal.
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 145))
    screen.blit(overlay, (0, 0))

    modal = pygame.Rect(70, 85, 860, 500)
    pygame.draw.rect(screen, CARD, modal, border_radius=24)
    pygame.draw.rect(screen, BORDER, modal, width=1, border_radius=24)

    title = subtitle_font.render("Build a Custom Quiz", True, CREAM)
    screen.blit(title, (110, 112))
    subtitle = small_font.render(
        "Tell PoliX what you want to understand. It will build a neutral knowledge quiz.",
        True, MUTED
    )
    screen.blit(subtitle, (110, 153))

    label = small_font.render("YOUR INTEREST", True, PRIMARY)
    screen.blit(label, (110, 200))

    pygame.draw.rect(screen, (18, 42, 31), custom_quiz_interest_box, border_radius=12)
    pygame.draw.rect(
        screen,
        PRIMARY if custom_quiz_interest_active else BORDER,
        custom_quiz_interest_box,
        width=2,
        border_radius=12
    )
    if custom_quiz_interest:
        rendered = render_fitted_text(
            custom_quiz_interest, None, 25, 18,
            custom_quiz_interest_box.width - 30, CREAM
        )
        screen.blit(rendered, (custom_quiz_interest_box.x + 15,
                               custom_quiz_interest_box.centery - rendered.get_height() // 2))
    else:
        placeholder = small_font.render(
            "e.g. the Electoral College, healthcare policy, or climate policy",
            True, MUTED
        )
        screen.blit(placeholder, (custom_quiz_interest_box.x + 15,
                                  custom_quiz_interest_box.centery - placeholder.get_height() // 2))

    if custom_quiz_interest_active and cursor_visible:
        cursor_x = custom_quiz_interest_box.x + 15
        if custom_quiz_interest:
            cursor_x += render_fitted_text(
                custom_quiz_interest, None, 25, 18,
                custom_quiz_interest_box.width - 30, CREAM
            ).get_width()
        pygame.draw.line(screen, PRIMARY,
                         (cursor_x, custom_quiz_interest_box.y + 13),
                         (cursor_x, custom_quiz_interest_box.bottom - 13), 2)

    count_label = small_font.render("QUESTIONS", True, PRIMARY)
    screen.blit(count_label, (110, 300))
    for count, rect in custom_quiz_count_buttons:
        draw_button(rect, str(count), active=custom_quiz_count == count)

    difficulty_label = small_font.render("DIFFICULTY", True, PRIMARY)
    screen.blit(difficulty_label, (110, 380))
    for difficulty, rect in custom_quiz_difficulty_buttons:
        draw_button(rect, difficulty, active=custom_quiz_difficulty == difficulty)

    if custom_quiz_status:
        status = small_font.render(custom_quiz_status, True, MUTED)
        screen.blit(status, (110, 505))
    if custom_quiz_error:
        draw_wrapped_text(custom_quiz_error, pygame.font.Font(None, 18), MUTED,
                          110, 505, 500, line_gap=18, max_lines=2)

    if custom_quiz_busy:
        disabled = pygame.Rect(custom_quiz_generate_button)
        pygame.draw.rect(screen, BORDER, disabled, border_radius=12)
        txt = small_font.render("Generating...", True, MUTED)
        screen.blit(txt, (disabled.centerx - txt.get_width() // 2,
                          disabled.centery - txt.get_height() // 2))
    else:
        draw_button(custom_quiz_generate_button, "Generate Quiz")

    close = small_font.render("Cancel", True, MUTED)
    screen.blit(close, (110, 545))


# Render the generated custom quiz, answer choices, and feedback state.
def draw_custom_quiz():
    global custom_quiz_pending

    # Move generated data from the worker into the main-thread state.
    if custom_quiz_pending is not None:
        custom_quiz_questions = custom_quiz_pending
        custom_quiz_pending = None
        return custom_quiz_questions
    return None


# Wrapper for the custom quiz page layout and its navigation controls.
def draw_custom_quiz_screen():
    global custom_quiz_questions, custom_quiz_feedback

    # Move feedback result from the worker into the main-thread state.
    if custom_quiz_feedback_pending is not None:
        custom_quiz_feedback = custom_quiz_feedback_pending
        globals()["custom_quiz_feedback_pending"] = None

    title = title_font.render("Custom Quiz", True, CREAM)
    screen.blit(title, (65, 85))
    draw_button(custom_quiz_home_button, "< Home")

    if not custom_quiz_questions:
        return

    if custom_quiz_finished:
        score = subtitle_font.render(
            f"You scored {custom_quiz_score} / {len(custom_quiz_questions)}",
            True, CREAM
        )
        screen.blit(score, (WIDTH // 2 - score.get_width() // 2, 190))
        summary = small_font.render(
            "Review the topic or generate another quiz from Home.", True, MUTED
        )
        screen.blit(summary, (WIDTH // 2 - summary.get_width() // 2, 240))
        draw_button(custom_quiz_next_button, "Back to Home")
        return

    # Wrong-answer feedback screen.
    if custom_quiz_feedback_active:
        label = subtitle_font.render("Not quite", True, CREAM)
        screen.blit(label, (WIDTH // 2 - label.get_width() // 2, 175))

        if custom_quiz_feedback_busy:
            dots = "." * (int(time.time() * 4) % 4)
            loading = small_font.render("Explaining" + dots, True, PRIMARY)
            screen.blit(loading, (WIDTH // 2 - loading.get_width() // 2, 245))
        else:
            why = small_font.render("Why?", True, PRIMARY)
            screen.blit(why, (90, 235))
            feedback_text = custom_quiz_feedback
            if not feedback_text:
                feedback_text = "The correct answer is " + custom_quiz_questions[custom_quiz_index]["options"][custom_quiz_questions[custom_quiz_index]["answer"]] + "."
            draw_wrapped_text(
                feedback_text,
                small_font,
                CREAM,
                90,
                270,
                820,
                line_gap=26,
                max_lines=3
            )
            draw_button(custom_quiz_feedback_button, "Continue  >")
        return

    q = custom_quiz_questions[custom_quiz_index]
    counter = small_font.render(
        f"{custom_quiz_index + 1} / {len(custom_quiz_questions)}  •  {custom_quiz_difficulty}",
        True, MUTED
    )
    screen.blit(counter, (100, 165))

    lines = wrap_text(q["question"], question_font, 760)
    y = 205
    for line in lines[:3]:
        rendered = question_font.render(line, True, CREAM)
        screen.blit(rendered, (WIDTH // 2 - rendered.get_width() // 2, y))
        y += 40

    for i, option in enumerate(q["options"]):
        rect = custom_quiz_option_rects[i]
        selected = custom_quiz_selected == i
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        fill = PRIMARY if selected else (CARD_HOVER if hovered else (18, 42, 31))
        pygame.draw.rect(screen, fill, rect, border_radius=10)
        if not selected:
            pygame.draw.rect(screen, BORDER, rect, width=1, border_radius=10)
        color = BACKGROUND if selected else CREAM
        rendered = render_fitted_text(option, None, 25, 18, rect.width - 36, color)
        screen.blit(rendered, (rect.x + 18, rect.centery - rendered.get_height() // 2))

    if custom_quiz_selected is not None:
        draw_button(custom_quiz_next_button, "Next  >")


# Render the main dashboard: recommendation, study tools, and topic navigation.
def draw_home():
    mouse_pos = pygame.mouse.get_pos()
    recommended = get_recommended_area()

    title = title_font.render("Explore PoliX", True, CREAM)
    screen.blit(title, (70, 88))
    subtitle = small_font.render("Build your understanding, one topic at a time.", True, MUTED)
    screen.blit(subtitle, (73, 180))

    # Profile chip
    profile = pygame.Rect(760, 96, 170, 42)
    draw_modern_card(profile, fill=(20, 49, 37), radius=21)
    avatar = pygame.Rect(profile.x + 9, profile.y + 8, 26, 26)
    pygame.draw.circle(screen, PRIMARY, avatar.center, 13)
    initials = (username[:1] if username else "L").upper()
    av = ui_font(14, True).render(initials, True, BACKGROUND)
    screen.blit(av, (avatar.centerx-av.get_width()//2, avatar.centery-av.get_height()//2))
    pt = render_fitted_text(username if username else "Learner", None, 17, 13, 112, CREAM)
    screen.blit(pt, (profile.x + 43, profile.centery - pt.get_height()//2))

    # Featured recommendation with subtle gradient accent.
    featured = pygame.Rect(70, 224, 860, 116)
    hovered = featured.collidepoint(mouse_pos)
    draw_modern_card(featured, fill=(22, 51, 39), radius=20, hover=hovered)
    accent = pygame.Rect(featured.x, featured.y, 7, featured.height)
    draw_gradient_pill(accent)
    draw_section_label("Recommended for you", featured.x + 28, featured.y + 17)
    rt = subtitle_font.render(recommended["name"], True, CREAM)
    screen.blit(rt, (featured.x + 28, featured.y + 42))
    # Keep the recommendation description strictly inside the featured card.
    recommendation_font = ui_font(16)
    recommendation_x = featured.x + 28
    recommendation_y = featured.y + 77
    recommendation_height = featured.bottom - recommendation_y - 9
    draw_wrapped_text(
        recommended["description"],
        recommendation_font,
        MUTED,
        recommendation_x,
        recommendation_y,
        620,
        line_gap=17,
        max_lines=2,
        max_height=recommendation_height,
    )
    explore = button_font.render("Explore  →", True, PRIMARY)
    screen.blit(explore, (featured.right - explore.get_width() - 28, featured.centery - explore.get_height()//2))

    # Study tools as compact modern cards.
    for rect, title, desc, button_rect in [
        (pygame.Rect(70, 356, 420, 62), "Create Flashcards", "Make your own study cards and review them anytime.", flashcard_home_button),
        (pygame.Rect(510, 356, 420, 62), "Build a Custom Quiz", "Choose an interest and let PoliX build a quiz around it.", custom_quiz_open_button),
    ]:
        hov = rect.collidepoint(mouse_pos)
        draw_modern_card(rect, radius=16, hover=hov)
        title_s = ui_font(19, True).render(title, True, CREAM)
        screen.blit(title_s, (rect.x + 18, rect.y + 11))
        draw_wrapped_text(desc, ui_font(15), MUTED, rect.x + 18, rect.y + 37, rect.width - 55, line_gap=15, max_lines=1)
        arrow = ui_font(22, True).render("→", True, PRIMARY if hov else MUTED)
        screen.blit(arrow, (rect.right - 30, rect.centery - arrow.get_height()//2))

    draw_section_label("Explore topics", 70, 440)
    topics = [
        ("Government", "Constitution, Congress & courts", "01"),
        ("Elections", "Voting, parties & representation", "02"),
        ("Economics", "Inflation, taxes & spending", "03"),
        ("Policy", "Healthcare, immigration & more", "04"),
        ("Society", "Education & public programs", "05"),
        ("Information", "Sources, claims & media", "06"),
    ]
    for i, (topic, description, number) in enumerate(topics):
        col, row = i % 3, i // 3
        rect = pygame.Rect(70 + col * 285, 464 + row * 82, 260, 70)
        hov = rect.collidepoint(mouse_pos)
        draw_modern_card(rect, radius=16, hover=hov)
        marker = pygame.Rect(rect.x + 13, rect.y + 13, 35, 35)
        pygame.draw.rect(screen, (18, 54, 40), marker, border_radius=10)
        n = ui_font(13, True).render(number, True, PRIMARY)
        screen.blit(n, (marker.centerx-n.get_width()//2, marker.centery-n.get_height()//2))
        tt = ui_font(18, True).render(topic, True, CREAM)
        screen.blit(tt, (rect.x + 59, rect.y + 8))
        draw_wrapped_text(description, ui_font(14), MUTED, rect.x + 59, rect.y + 34, 165, line_gap=15, max_lines=2)
        arrow = ui_font(21, True).render("→", True, PRIMARY if hov else MUTED)
        screen.blit(arrow, (rect.right - 29, rect.bottom - 29))


def draw_chat_message(message, x, y, width, is_user):
    """Draw one chat bubble and return the vertical space it used."""
    font = pygame.font.Font(None, 21)
    lines = wrap_text(message, font, width - 30)

    line_height = 22
    bubble_height = max(48, 22 + len(lines) * line_height)

    bubble = pygame.Rect(x, y, width, bubble_height)
    pygame.draw.rect(
        screen,
        PRIMARY if is_user else CARD,
        bubble,
        border_radius=14
    )

    if not is_user:
        pygame.draw.rect(
            screen,
            BORDER,
            bubble,
            width=1,
            border_radius=14
        )

    text_color = BACKGROUND if is_user else CREAM

    for index, line in enumerate(lines):
        rendered = font.render(line, True, text_color)
        screen.blit(rendered, (x + 15, y + 11 + index * line_height))

    return bubble_height


# Render the local assistant conversation, input field, and scrolling history.
def draw_chat():
    global chat_scroll, chat_pending_reply

    title = title_font.render("PoliX Assistant", True, CREAM)
    screen.blit(title, (65, 85))

    subtitle = small_font.render(
        f"Local educational chat  •  {CHAT_MODEL}",
        True,
        MUTED
    )
    screen.blit(subtitle, (68, 145))

    draw_button(chat_home_button, "< Home")

    # Conversation area
    chat_area = pygame.Rect(65, 175, 870, 365)
    pygame.draw.rect(screen, (13, 31, 23), chat_area, border_radius=18)
    pygame.draw.rect(screen, BORDER, chat_area, width=1, border_radius=18)

    # Add a completed background reply once the worker thread finishes.
    new_reply_added = False
    if chat_pending_reply is not None:
        chat_messages.append({"role": "assistant", "content": chat_pending_reply})
        chat_pending_reply = None
        new_reply_added = True

    bubbles = []
    y = chat_area.y + 15

    # First calculate the natural conversation height.
    for message in chat_messages:
        is_user = message["role"] == "user"
        width = 600 if is_user else 700
        font = pygame.font.Font(None, 21)
        lines = wrap_text(message["content"], font, width - 30)
        bubble_height = max(48, 22 + len(lines) * 22)
        bubbles.append((message, width, bubble_height, is_user))
        y += bubble_height + 10

    content_height = y - chat_area.y
    max_scroll = max(0, content_height - chat_area.height + 15)
    # chat_scroll is the distance from the top of the conversation.
    # Keep the newest reply at the bottom instead of resetting to the top.
    if new_reply_added:
        chat_scroll = max_scroll
    else:
        chat_scroll = max(0, min(chat_scroll, max_scroll))

    y = chat_area.y + 15 - chat_scroll

    # Clip bubbles to the conversation viewport.
    old_clip = screen.get_clip()
    screen.set_clip(chat_area)

    for message, width, bubble_height, is_user in bubbles:
        x = chat_area.right - width - 15 if is_user else chat_area.x + 15
        draw_chat_message(message["content"], x, y, width, is_user)
        y += bubble_height + 10

    screen.set_clip(old_clip)

    if chat_busy:
        thinking = small_font.render("PoliX is thinking...", True, MUTED)
        screen.blit(thinking, (chat_area.x + 18, chat_area.bottom - 30))

    if chat_error:
        error_text = pygame.font.Font(None, 18).render(chat_error, True, MUTED)
        screen.blit(error_text, (chat_area.x + 18, chat_area.bottom - 30))

    # Input bar
    pygame.draw.rect(screen, (18, 42, 31), chat_input_box, border_radius=12)
    pygame.draw.rect(
        screen,
        PRIMARY if chat_input_active else BORDER,
        chat_input_box,
        width=2,
        border_radius=12
    )

    if chat_input:
        input_rendered = render_fitted_text(
            chat_input, None, 24, 18, chat_input_box.width - 30, CREAM
        )
        screen.blit(
            input_rendered,
            (chat_input_box.x + 15, chat_input_box.centery - input_rendered.get_height() // 2)
        )
    else:
        placeholder = small_font.render(
            "Ask a civic question...",
            True,
            MUTED
        )
        screen.blit(
            placeholder,
            (chat_input_box.x + 15, chat_input_box.centery - placeholder.get_height() // 2)
        )

    # Blinking cursor for the chat text box.
    if chat_input_active and cursor_visible:
        if chat_input:
            cursor_x = chat_input_box.x + 15 + input_rendered.get_width()
        else:
            cursor_x = chat_input_box.x + 15
        pygame.draw.line(
            screen,
            PRIMARY,
            (cursor_x, chat_input_box.y + 12),
            (cursor_x, chat_input_box.bottom - 12),
            2
        )

    send_color = BORDER if chat_busy or not chat_input.strip() else PRIMARY_DARK
    pygame.draw.rect(screen, send_color, chat_send_button, border_radius=12)
    send_text = small_font.render("Send", True, BACKGROUND if send_color != BORDER else MUTED)
    screen.blit(
        send_text,
        (
            chat_send_button.centerx - send_text.get_width() // 2,
            chat_send_button.centery - send_text.get_height() // 2
        )
    )


# Draw the floating chat button shown on the home dashboard.
def draw_chat_launcher():
    """Draw the floating assistant button on the home screen."""
    center = chat_button_center
    hovered = pygame.math.Vector2(pygame.mouse.get_pos()).distance_to(center) <= chat_button_radius

    # Subtle shadow
    pygame.draw.circle(screen, (8, 22, 15), (center[0] + 2, center[1] + 3), chat_button_radius + 2)
    pygame.draw.circle(
        screen,
        PRIMARY if hovered else PRIMARY_DARK,
        center,
        chat_button_radius
    )

    # Simple speech-bubble icon
    bubble = pygame.Rect(center[0] - 14, center[1] - 11, 28, 21)
    pygame.draw.rect(screen, BACKGROUND, bubble, border_radius=8)
    pygame.draw.polygon(
        screen,
        BACKGROUND,
        [
            (center[0] - 5, center[1] + 7),
            (center[0] - 1, center[1] + 15),
            (center[0] + 5, center[1] + 7)
        ]
    )

    dot_y = center[1] - 1
    for dot_x in (-7, 0, 7):
        pygame.draw.circle(screen, PRIMARY if not hovered else PRIMARY_DARK, (center[0] + dot_x, dot_y), 2)


# ============================================================
# MAIN LOOP
# ============================================================

running = True

while running:

    # Every frame follows the same pattern: read input, update state, draw the
    # active screen, then present the frame and cap the loop at 60 FPS.
    mouse_pos = pygame.mouse.get_pos()


    # ========================================================
    # EVENTS
    # ========================================================

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False


        # ----------------------------------------------------
        # NAME SCREEN
        # ----------------------------------------------------

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

            if custom_quiz_modal:
                if custom_quiz_interest_box.collidepoint(event.pos):
                    custom_quiz_interest_active = True
                elif custom_quiz_generate_button.collidepoint(event.pos) and not custom_quiz_busy:
                    if custom_quiz_interest.strip():
                        custom_quiz_modal = False
                        custom_quiz_interest_active = False
                        custom_quiz_questions = []
                        custom_quiz_index = 0
                        custom_quiz_selected = None
                        custom_quiz_score = 0
                        custom_quiz_finished = False
                        custom_quiz_feedback_active = False
                        custom_quiz_feedback_busy = False
                        custom_quiz_feedback = ""
                        custom_quiz_feedback_pending = None
                        custom_quiz_feedback_error = ""
                        current_screen = "custom_quiz"
                        start_custom_quiz_generation()
                    else:
                        custom_quiz_error = "Enter an interest first."
                elif custom_quiz_count_buttons[0][1].collidepoint(event.pos) or custom_quiz_count_buttons[1][1].collidepoint(event.pos) or custom_quiz_count_buttons[2][1].collidepoint(event.pos) or custom_quiz_count_buttons[3][1].collidepoint(event.pos):
                    for count, rect in custom_quiz_count_buttons:
                        if rect.collidepoint(event.pos):
                            custom_quiz_count = count
                            break
                elif custom_quiz_difficulty_buttons[0][1].collidepoint(event.pos) or custom_quiz_difficulty_buttons[1][1].collidepoint(event.pos) or custom_quiz_difficulty_buttons[2][1].collidepoint(event.pos):
                    for difficulty, rect in custom_quiz_difficulty_buttons:
                        if rect.collidepoint(event.pos):
                            custom_quiz_difficulty = difficulty
                            break
                elif pygame.Rect(95, 530, 120, 35).collidepoint(event.pos):
                    custom_quiz_modal = False
                    custom_quiz_interest_active = False
                continue

            if current_screen == "name":

                if input_box.collidepoint(event.pos):

                    input_active = True

                elif continue_button.collidepoint(event.pos):

                    if input_text.strip():

                        username = input_text.strip()

                        with open(filename, "w") as file:
                            file.write(username)

                        current_screen = "quiz"
                        input_active = False

                else:

                    input_active = False


            # ------------------------------------------------
            # QUIZ SCREEN
            # ------------------------------------------------

            elif current_screen == "quiz":

                # Answer buttons
                for i in range(4):

                    option_rect = pygame.Rect(
                        200,
                        300 + (i * 55),
                        600,
                        45
                    )

                    if option_rect.collidepoint(event.pos):

                        selected_answer = i


                # Next button
                next_rect = pygame.Rect(
                    650,
                    515,
                    150,
                    50
                )

                if next_rect.collidepoint(event.pos):

                    if selected_answer is not None:

                        answers.append(selected_answer)

                        current_question += 1
                        selected_answer = None

                        # Quiz finished
                        if current_question >= len(questions):

                            with open(filename, "a", encoding="utf-8") as file:
                                file.write("\nquizzed")

                            # Save the diagnostic immediately so it survives
                            # closing and reopening PoliX.
                            save_diagnostic_results()

                            current_screen = "diagnostic"

            # ------------------------------------------------
            # DIAGNOSTIC SCREEN
            # ------------------------------------------------

            elif current_screen == "diagnostic":

                if diagnostic_continue_button.collidepoint(event.pos):
                    current_screen = "home"

            # ------------------------------------------------
            # HOME SCREEN
            # ------------------------------------------------

            elif current_screen == "home":

                # Recommended feature card
                recommended = get_recommended_area()
                featured_rect = pygame.Rect(70, 195, 860, 125)

                chat_distance = pygame.math.Vector2(event.pos).distance_to(chat_button_center)

                # These hitboxes match the two modern study-tool cards
                # drawn on the home screen.  The old wide hitboxes overlapped,
                # which caused Build a Custom Quiz to open Flashcards.
                flashcard_home_card = pygame.Rect(70, 330, 420, 62)
                custom_quiz_home_card = pygame.Rect(510, 330, 420, 62)

                if chat_distance <= chat_button_radius:
                    current_screen = "chat"
                    chat_input_active = False
                elif custom_quiz_home_card.collidepoint(event.pos):
                    custom_quiz_modal = True
                    custom_quiz_interest_active = True
                    custom_quiz_error = ""
                    custom_quiz_status = ""
                elif flashcard_home_card.collidepoint(event.pos):
                    flashcard_active_field = None
                    flashcard_mode = "create"
                    flashcard_test_index = 0
                    flashcard_test_revealed = False
                    flashcard_test_known = 0
                    flashcard_test_review = 0
                    current_screen = "flashcards"
                    flashcard_scroll = 0
                elif featured_rect.collidepoint(event.pos):
                    selected_topic = topic_key_for_area(recommended["name"])
                    resource_scroll = 0
                    current_screen = "resources"
                else:
                    topics = [
                        "Government",
                        "Elections",
                        "Economics",
                        "Policy",
                        "Society",
                        "Information",
                    ]

                    for i, topic in enumerate(topics):
                        column = i % 3
                        row = i // 3
                        rect = pygame.Rect(70 + column * 285, 474 + row * 78, 260, 68)

                        if rect.collidepoint(event.pos):
                            selected_topic = topic
                            resource_scroll = 0
                            current_screen = "resources"
                            break

            # ------------------------------------------------
            # CHAT SCREEN
            # ------------------------------------------------

            elif current_screen == "chat":

                if chat_home_button.collidepoint(event.pos):
                    current_screen = "home"
                    chat_input_active = False
                elif chat_input_box.collidepoint(event.pos):
                    chat_input_active = True
                elif chat_send_button.collidepoint(event.pos):
                    chat_input_active = True
                    send_current_chat_input()
                else:
                    chat_input_active = False

            # ------------------------------------------------
            # FLASHCARD SCREEN
            # ------------------------------------------------

            elif current_screen == "flashcards":

                if flashcard_home_button.collidepoint(event.pos):
                    current_screen = "home"
                    flashcard_active_field = None
                elif flashcard_create_mode_button.collidepoint(event.pos):
                    flashcard_mode = "create"
                    flashcard_active_field = None
                elif flashcard_test_mode_button.collidepoint(event.pos):
                    flashcard_mode = "test"
                    flashcard_active_field = None
                    flashcard_test_index = 0
                    flashcard_test_revealed = False
                    flashcard_test_known = 0
                    flashcard_test_review = 0
                elif flashcard_mode == "create":
                    if flashcard_front_box.collidepoint(event.pos):
                        flashcard_active_field = "front"
                    elif flashcard_back_box.collidepoint(event.pos):
                        flashcard_active_field = "back"
                    elif flashcard_add_button.collidepoint(event.pos):
                        if flashcard_front.strip() and flashcard_back.strip():
                            flashcards.append({
                                "front": flashcard_front.strip(),
                                "back": flashcard_back.strip(),
                            })
                            save_flashcards()
                            flashcard_front = ""
                            flashcard_back = ""
                            flashcard_active_field = "front"
                            flashcard_scroll = 0
                else:
                    if flashcard_test_index >= len(flashcards):
                        if flashcard_restart_button.collidepoint(event.pos):
                            flashcard_test_index = 0
                            flashcard_test_revealed = False
                            flashcard_test_known = 0
                            flashcard_test_review = 0
                    elif not flashcard_test_revealed:
                        if flashcard_reveal_button.collidepoint(event.pos):
                            flashcard_test_revealed = True
                    else:
                        if flashcard_known_button.collidepoint(event.pos):
                            flashcard_test_known += 1
                            flashcard_test_index += 1
                            flashcard_test_revealed = False
                        elif flashcard_review_button.collidepoint(event.pos):
                            flashcard_test_review += 1
                            flashcard_test_index += 1
                            flashcard_test_revealed = False

            # ------------------------------------------------
            # CUSTOM QUIZ SCREEN
            # ------------------------------------------------

            elif current_screen == "custom_quiz":

                if custom_quiz_home_button.collidepoint(event.pos):
                    current_screen = "home"
                    custom_quiz_selected = None
                elif custom_quiz_feedback_active:
                    if (not custom_quiz_feedback_busy and
                            custom_quiz_feedback_button.collidepoint(event.pos)):
                        advance_custom_quiz_question()
                elif custom_quiz_next_button.collidepoint(event.pos) and (custom_quiz_finished or custom_quiz_error or not custom_quiz_questions):
                    current_screen = "home"
                    custom_quiz_selected = None
                elif custom_quiz_questions and not custom_quiz_finished:
                    for i, rect in enumerate(custom_quiz_option_rects):
                        if rect.collidepoint(event.pos):
                            custom_quiz_selected = i
                    if custom_quiz_selected is not None and custom_quiz_next_button.collidepoint(event.pos):
                        q = custom_quiz_questions[custom_quiz_index]
                        if custom_quiz_selected == q["answer"]:
                            custom_quiz_score += 1
                            advance_custom_quiz_question()
                        else:
                            custom_quiz_feedback_active = True
                            start_custom_quiz_feedback(
                                q["question"],
                                q["options"][custom_quiz_selected],
                                q["options"][q["answer"]]
                            )

            # ------------------------------------------------
            # RESOURCE SCREEN
            # ------------------------------------------------

            elif current_screen == "resources":

                back_rect = pygame.Rect(800, 92, 130, 42)

                if back_rect.collidepoint(event.pos):
                    current_screen = "home"
                    resource_scroll = 0
                elif RESOURCE_TOP <= event.pos[1] <= RESOURCE_BOTTOM:
                    for i, resource in enumerate(resources[selected_topic]):
                        y = RESOURCE_TOP + i * (RESOURCE_CARD_HEIGHT + RESOURCE_GAP) - resource_scroll
                        rect = pygame.Rect(65, y, 870, RESOURCE_CARD_HEIGHT)
                        if rect.collidepoint(event.pos):
                            webbrowser.open(resource["url"])
                            break


        # ----------------------------------------------------
        # CHAT SCROLLING
        # ----------------------------------------------------

        elif event.type == pygame.MOUSEWHEEL and current_screen == "chat":
            # Wheel up moves toward the top; wheel down moves toward the bottom.
            chat_scroll -= event.y * 35

        elif event.type == pygame.MOUSEWHEEL and current_screen == "resources":
            resource_scroll -= event.y * 45
            clamp_resource_scroll(selected_topic)

        elif event.type == pygame.MOUSEWHEEL and current_screen == "flashcards" and flashcard_mode == "create":
            flashcard_scroll -= event.y * 45
            clamp_flashcard_scroll()

        # ----------------------------------------------------
        # KEYBOARD
        # ----------------------------------------------------

        elif event.type == pygame.KEYDOWN:

            if custom_quiz_modal and custom_quiz_interest_active:
                if event.key == pygame.K_BACKSPACE:
                    custom_quiz_interest = custom_quiz_interest[:-1]
                elif event.key == pygame.K_ESCAPE:
                    custom_quiz_modal = False
                    custom_quiz_interest_active = False
                elif event.key == pygame.K_RETURN:
                    if custom_quiz_interest.strip() and not custom_quiz_busy:
                        custom_quiz_modal = False
                        custom_quiz_interest_active = False
                        custom_quiz_questions = []
                        custom_quiz_index = 0
                        custom_quiz_selected = None
                        custom_quiz_score = 0
                        custom_quiz_finished = False
                        custom_quiz_feedback_active = False
                        custom_quiz_feedback_busy = False
                        custom_quiz_feedback = ""
                        custom_quiz_feedback_pending = None
                        custom_quiz_feedback_error = ""
                        current_screen = "custom_quiz"
                        start_custom_quiz_generation()
                elif event.unicode.isprintable() and len(custom_quiz_interest) < 180:
                    custom_quiz_interest += event.unicode

            elif current_screen == "custom_quiz" and custom_quiz_questions and not custom_quiz_finished:
                if custom_quiz_feedback_active:
                    if event.key == pygame.K_RETURN and not custom_quiz_feedback_busy:
                        advance_custom_quiz_question()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    custom_quiz_selected = event.key - pygame.K_1
                elif event.key == pygame.K_RETURN and custom_quiz_selected is not None:
                    q = custom_quiz_questions[custom_quiz_index]
                    if custom_quiz_selected == q["answer"]:
                        custom_quiz_score += 1
                        advance_custom_quiz_question()
                    else:
                        custom_quiz_feedback_active = True
                        start_custom_quiz_feedback(
                            q["question"],
                            q["options"][custom_quiz_selected],
                            q["options"][q["answer"]]
                        )

            elif current_screen == "name" and input_active:

                if event.key == pygame.K_RETURN:

                    if input_text.strip():

                        username = input_text.strip()

                        with open(filename, "w") as file:
                            file.write(username)

                        current_screen = "quiz"
                        input_active = False

                elif event.key == pygame.K_BACKSPACE:

                    input_text = input_text[:-1]

                else:

                    if event.unicode.isprintable():

                        input_text += event.unicode

            elif current_screen == "chat" and chat_input_active:

                if event.key == pygame.K_RETURN:
                    send_current_chat_input()
                elif event.key == pygame.K_BACKSPACE:
                    chat_input = chat_input[:-1]
                elif event.key == pygame.K_ESCAPE:
                    chat_input_active = False
                else:
                    if event.unicode.isprintable():
                        chat_input += event.unicode

            elif current_screen == "flashcards" and flashcard_mode == "create" and flashcard_active_field:

                if event.key == pygame.K_BACKSPACE:
                    if flashcard_active_field == "front":
                        flashcard_front = flashcard_front[:-1]
                    else:
                        flashcard_back = flashcard_back[:-1]
                elif event.key == pygame.K_TAB:
                    flashcard_active_field = "back" if flashcard_active_field == "front" else "front"
                elif event.key == pygame.K_RETURN:
                    if flashcard_active_field == "front":
                        flashcard_active_field = "back"
                    elif flashcard_front.strip() and flashcard_back.strip():
                        flashcards.append({
                            "front": flashcard_front.strip(),
                            "back": flashcard_back.strip(),
                        })
                        save_flashcards()
                        flashcard_front = ""
                        flashcard_back = ""
                        flashcard_active_field = "front"
                elif event.unicode.isprintable():
                    if flashcard_active_field == "front" and len(flashcard_front) < 180:
                        flashcard_front += event.unicode
                    elif flashcard_active_field == "back" and len(flashcard_back) < 240:
                        flashcard_back += event.unicode


    # ========================================================
    # CURSOR
    # ========================================================

    any_text_input_active = input_active or chat_input_active or bool(flashcard_active_field) or custom_quiz_interest_active

    if any_text_input_active:

        if time.time() - last_cursor_toggle >= 0.5:

            cursor_visible = not cursor_visible
            last_cursor_toggle = time.time()

    else:

        cursor_visible = False


    # ========================================================
    # BACKGROUND
    # ========================================================

    draw_gradient_background()

    draw_logo()


    # ========================================================
    # NAME SCREEN
    # ========================================================

    if current_screen == "name":

        draw_card()

        title = title_font.render(
            "Let's get started.",
            True,
            CREAM
        )

        screen.blit(
            title,
            (
                WIDTH // 2 - title.get_width() // 2,
                165
            )
        )

        subtitle = subtitle_font.render(
            "What should we call you?",
            True,
            MUTED
        )

        screen.blit(
            subtitle,
            (
                WIDTH // 2 - subtitle.get_width() // 2,
                240
            )
        )

        # Input
        pygame.draw.rect(
            screen,
            (18, 42, 31),
            input_box,
            border_radius=12
        )

        pygame.draw.rect(
            screen,
            PRIMARY if input_active else BORDER,
            input_box,
            width=2,
            border_radius=12
        )

        # Keep long names inside the input box.
        available_input_width = input_box.width - 40
        text = render_fitted_text(
            input_text,
            None,
            30,
            18,
            available_input_width,
            CREAM
        )

        screen.blit(
            text,
            (
                input_box.x + 20,
                input_box.y + 16
            )
        )

        if not input_text:

            placeholder = input_font.render(
                "Enter your name",
                True,
                MUTED
            )

            screen.blit(
                placeholder,
                (
                    input_box.x + 20,
                    input_box.y + 16
                )
            )

        # Cursor
        if input_active and cursor_visible:

            cursor_x = (
                input_box.x
                + 20
                + text.get_width()
            )

            pygame.draw.line(
                screen,
                PRIMARY,
                (cursor_x, input_box.y + 15),
                (cursor_x, input_box.y + 45),
                2
            )

        draw_button(
            continue_button,
            "Continue  >"
        )


    # ========================================================
    # QUIZ SCREEN
    # ========================================================

    elif current_screen == "quiz":

        draw_card()

        # Question counter
        counter = small_font.render(
            f"{current_question + 1} / {len(questions)}",
            True,
            MUTED
        )

        screen.blit(
            counter,
            (170, 135)
        )

        # Title
        title = subtitle_font.render(
            "Let's see what you already know.",
            True,
            CREAM
        )

        screen.blit(
            title,
            (
                WIDTH // 2 - title.get_width() // 2,
                155
            )
        )

        # Question
        # Keep the question visually separated from the answer choices.
        # Longer questions automatically use a smaller font so they fit
        # within the question area instead of continuing behind the options.
        question_text = questions[current_question]
        question_area_width = 760
        question_font_size = 38
        question_lines = []

        while question_font_size >= 28:

            current_question_font = pygame.font.Font(None, question_font_size)
            question_lines = wrap_text(
                question_text,
                current_question_font,
                question_area_width
            )

            if len(question_lines) <= 2:
                break

            question_font_size -= 2

        # Final fallback: keep the question to two lines if it is unusually long.
        if len(question_lines) > 2:
            current_question_font = pygame.font.Font(None, 28)
            question_lines = wrap_text(
                question_text,
                current_question_font,
                question_area_width
            )

        line_height = current_question_font.get_linesize()
        question_y = 205

        for line in question_lines[:2]:

            rendered = current_question_font.render(
                line,
                True,
                CREAM
            )

            screen.blit(
                rendered,
                (
                    WIDTH // 2 - rendered.get_width() // 2,
                    question_y
                )
            )

            question_y += line_height


        # Answer choices
        for i, option in enumerate(options):

            option_rect = pygame.Rect(
                200,
                300 + (i * 55),
                600,
                45
            )

            selected = selected_answer == i

            if selected:

                pygame.draw.rect(
                    screen,
                    PRIMARY,
                    option_rect,
                    border_radius=10
                )

                text_color = BACKGROUND

            elif option_rect.collidepoint(mouse_pos):

                pygame.draw.rect(
                    screen,
                    CARD_HOVER,
                    option_rect,
                    border_radius=10
                )

                pygame.draw.rect(
                    screen,
                    BORDER,
                    option_rect,
                    width=1,
                    border_radius=10
                )

                text_color = CREAM

            else:

                pygame.draw.rect(
                    screen,
                    (18, 42, 31),
                    option_rect,
                    border_radius=10
                )

                pygame.draw.rect(
                    screen,
                    BORDER,
                    option_rect,
                    width=1,
                    border_radius=10
                )

                text_color = CREAM

            option_text = render_fitted_text(
                option,
                None,
                28,
                20,
                option_rect.width - 36,
                text_color
            )

            screen.blit(
                option_text,
                (
                    option_rect.x + 18,
                    option_rect.centery - option_text.get_height() // 2
                )
            )


        # Next button
        next_rect = pygame.Rect(
            650,
            515,
            150,
            50
        )

        if selected_answer is not None:

            draw_button(
                next_rect,
                "Next  >"
            )

        else:

            pygame.draw.rect(
                screen,
                BORDER,
                next_rect,
                border_radius=12
            )

            next_text = button_font.render(
                "Next  >",
                True,
                MUTED
            )

            screen.blit(
                next_text,
                (
                    next_rect.centerx - next_text.get_width() // 2,
                    next_rect.centery - next_text.get_height() // 2
                )
            )


    # ========================================================
    # DIAGNOSTIC SCREEN
    # ========================================================

    elif current_screen == "diagnostic":

        draw_card()
        draw_diagnostic()

        draw_button(
            diagnostic_continue_button,
            "Continue"
        )


    # ========================================================
    # HOME SCREEN
    # ========================================================

    elif current_screen == "home":

        draw_home()
        draw_chat_launcher()

        if custom_quiz_modal:
            draw_custom_quiz_modal()


    # ========================================================
    # CHAT SCREEN
    # ========================================================

    elif current_screen == "chat":

        draw_chat()


    # ========================================================
    # FLASHCARD SCREEN
    # ========================================================

    elif current_screen == "flashcards":

        draw_flashcards()


    # ========================================================
    # CUSTOM QUIZ SCREEN
    # ========================================================

    elif current_screen == "custom_quiz":

        # Worker threads never draw directly. They place results in a pending
        # variable, and the main Pygame thread picks those results up here.
        if custom_quiz_pending is not None:
            custom_quiz_questions = custom_quiz_pending
            custom_quiz_pending = None

        if custom_quiz_error and not custom_quiz_questions:
            draw_custom_quiz_screen()
            draw_wrapped_text(custom_quiz_error, pygame.font.Font(None, 22), MUTED,
                              100, 250, 800, line_gap=24, max_lines=3)
            draw_button(custom_quiz_next_button, "Back to Home")
        elif not custom_quiz_questions:
            draw_quiz_loading_screen()
        else:
            draw_custom_quiz_screen()


    # ========================================================
    # RESOURCE SCREEN
    # ========================================================

    elif current_screen == "resources":

        draw_resources(selected_topic)


    # ========================================================
    # DISPLAY
    # ========================================================
    # Flip the completed frame to the window, then limit the loop to 60 FPS.

    pygame.display.flip()

    clock.tick(60)


pygame.quit()