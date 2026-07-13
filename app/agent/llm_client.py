"""
Single point of contact for LLM calls so swapping providers is a one-line
config change (LLM_PROVIDER=anthropic|openai), not a code change scattered
across the agent graph. This is also where you'd add token/cost logging
for the "optimizing for token efficiency and cost" JD bullet.
"""
from app.config import settings


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    if settings.llm_provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        )

    elif settings.llm_provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
