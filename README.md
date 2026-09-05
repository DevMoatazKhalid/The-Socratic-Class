# The Socratic Class - AI Coach

An agentic, multi-role Socratic tutoring system built on LangGraph and LangChain. The AI Coach diagnoses student learning states (misconceptions, conceptual gaps, logical errors), selects pedagogical interventions (guiding questions, hints, clarifications), generates level-appropriate responses, and enforces pedagogical guardrails.

---

## LLM Configuration

All LLM and provider configurations are driven through environment variables. The application automatically reads `.env` on startup.

### Quick Setup

1. **Copy `.env.example` to `.env` if necessary:**
   ```bash
   cp .env.example .env
   ```

2. **Select the provider (`AI_PROVIDER`):**
   Choose one of:
   - `openai`
   - `openai_compatible`
   - `nvidia` (or `nvidia_nim`)
   - `anthropic`

3. **Add the API key (`AI_API_KEY`):**
   Provide your API key for the chosen provider.

4. **Add the model (`AI_MODEL_DEFAULT`):**
   Specify the model name for your provider (e.g. `gpt-4o-mini`, `claude-3-5-haiku-20241022`, or `meta/llama-3.1-8b-instruct`).

5. **Add the base URL only when required (`AI_BASE_URL`):**
   Required when using `openai_compatible` or `nvidia` / `nvidia_nim` (e.g. `https://integrate.api.nvidia.com/v1` or `http://localhost:8000/v1`).

6. **Run the smoke test:**
   ```bash
   python scripts/test_llm.py
   ```

---

### Provider Configuration Examples

#### OpenAI
```env
AI_PROVIDER=openai
AI_API_KEY=your_openai_key_here
AI_MODEL_DEFAULT=gpt-4o-mini
```

#### NVIDIA NIM
```env
AI_PROVIDER=nvidia
AI_API_KEY=your_nvidia_api_key_here
AI_BASE_URL=https://integrate.api.nvidia.com/v1
AI_MODEL_DEFAULT=meta/llama-3.1-8b-instruct
```

#### OpenAI-Compatible (Local vLLM / Ollama / Self-Hosted)
```env
AI_PROVIDER=openai_compatible
AI_API_KEY=your_api_key_or_placeholder
AI_BASE_URL=http://localhost:8000/v1
AI_MODEL_DEFAULT=your-model-name
```

#### Anthropic
```env
AI_PROVIDER=anthropic
AI_API_KEY=your_anthropic_key_here
AI_MODEL_DEFAULT=claude-3-5-haiku-20241022
```

---

### Role-Specific Models (Optional)

The AI Coach defines four logical roles. Each role can be configured with a distinct model suited for its task:

```env
AI_MODEL_COACH=gpt-4o-mini
AI_MODEL_REASONING=gpt-4o
AI_MODEL_LIGHTWEIGHT=gpt-4o-mini
AI_MODEL_VERIFICATION=gpt-4o-mini
```

If a role-specific model is left blank, it automatically falls back to `AI_MODEL_DEFAULT`.

---

## Running Tests

### Automated Test Suite
Run all unit and graph tests (mocked, runs offline without calling external APIs):
```bash
pytest -q
```

### LLM Smoke Test
Verify credentials and connectivity to your configured LLM:
```bash
python scripts/test_llm.py
```

### Coach Integration Smoke Test
Verify the full end-to-end Coach pipeline (`diagnose` -> `choose_intervention` -> `generate_response` -> `validate`) with your configured LLM:
```bash
python scripts/test_coach.py
```
