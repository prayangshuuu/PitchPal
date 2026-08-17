# PitchPal — My Interview Coach Built in 3 Hours

## Why I Built This

I was preparing for tech interviews and realized a problem: practicing alone doesn't help without feedback.

My friends couldn't evaluate my communication. Coaching cost $100-500/hour. Online platforms gave generic questions with no feedback loop.

So I asked: what if an AI could be my always-available coach?

## What I Built

PitchPal is an AI interview coach built on the Gemini API.

Users:

- Choose a role (Software Engineer, Product Manager, Designer, QA, Other) and a mode (Interview, Pitch, Presentation)
- Get AI-generated questions matched to their role and difficulty level (Junior/Mid/Senior)
- Practice by recording voice answers in the browser
- Get feedback: a score out of 100, strengths, and areas to improve
- Track past sessions and scores over time

Built in 3 hours with Django, PostgreSQL, and the Gemini API.

## How I Built It

- **Phase 1 (40 min):** Django setup + database models
- **Phase 2 (45 min):** Gemini service — question generation, feedback scoring, voice transcription
- **Phase 3 (30 min):** REST API endpoints
- **Phase 4 (35 min):** Frontend — Django templates, vanilla JS, in-browser voice recording
- **Phase 5 (15 min):** Landing page, deploy to Heroku
- **Phase 6 (15 min):** Testing, demo data, polish

## Challenges I Solved

**Challenge 1:** Gemini returned JSON wrapped in markdown code fences.
**Solution:** Strip the markdown before parsing, with a fallback feedback response if parsing still fails.

**Challenge 2:** Voice transcription was slow.
**Solution:** Optimized the Gemini API calls to cut transcription time down significantly.

**Challenge 3:** Feedback was too generic.
**Solution:** Added job context to the prompts — seniority level, role, and mode — so feedback is specific to what was actually asked.

**Challenge 4:** Building this in 3 hours seemed impossible.
**Solution:** Ruthless scope cutting. MVP first, everything else second.

## What I Learned

- Gemini's multimodal API (text + audio) handles both question generation and voice transcription without a separate speech-to-text service
- Django templates + vanilla JS were enough — I didn't need a frontend framework for this
- Fallbacks matter: hardcoded backup questions keep the app usable if the API call fails
- A hard deadline forces better decisions than an open-ended one
- Affordability is itself a feature, next to $100-500/hour human coaching

## Result

A working AI interview coach that:

- Generates questions based on role, mode, and difficulty
- Scores answers and gives written feedback
- Records voice answers in the browser and transcribes them
- Keeps a history of past sessions and scores

## Tech Stack

**Backend:** Django 5, Django REST Framework, PostgreSQL (via `psycopg`), `django-allauth` for authentication

**AI:** Google Gemini API — question generation, answer evaluation, and voice transcription, with a configurable model + fallback chain

**Frontend:** Django templates, vanilla JavaScript, the browser MediaRecorder API for voice capture

**Infra:** Gunicorn, WhiteNoise, deployed on Heroku (Docker support also included)

**Testing:** pytest, pytest-django

## Links

- Live: https://pitchpal-649c0a175842.herokuapp.com/
