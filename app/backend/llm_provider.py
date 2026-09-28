"""Provider-neutral chat model construction for Groq and OpenRouter."""

from langchain_groq import ChatGroq

from settings_service import get_setting


DEFAULT_TEMPERATURES = {
    "supervisor": 0.0,
    "inquiry": 0.3,
    "booking": 0.1,
    "human_handoff": 0.0,
    "guardrail": 0.0,
}


def create_llm(agent_name: str):
    if agent_name not in DEFAULT_TEMPERATURES:
        raise ValueError(f"Unknown agent: {agent_name}")

    provider = get_setting(f"provider_{agent_name}", "groq").lower()
    model = get_setting(f"model_{agent_name}")
    agent_key = get_setting(f"api_key_{agent_name}", "")
    temperature = DEFAULT_TEMPERATURES[agent_name]

    if provider == "groq":
        api_key = agent_key or get_setting("groq_api_key", "")
        if not api_key:
            raise ValueError(f"No Groq API key is configured for the {agent_name} agent")
        return ChatGroq(model=model, temperature=temperature, groq_api_key=api_key)

    if provider == "openrouter":
        api_key = agent_key or get_setting("openrouter_api_key", "")
        if not api_key:
            raise ValueError(f"No OpenRouter API key is configured for the {agent_name} agent")
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError("OpenRouter requires the langchain-openai dependency") from exc

        headers = {}
        site_url = get_setting("openrouter_site_url", "")
        app_name = get_setting("openrouter_app_name", "AI Customer Support")
        if site_url:
            headers["HTTP-Referer"] = site_url
        if app_name:
            headers["X-Title"] = app_name

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers=headers or None,
        )

    raise ValueError(f"Unsupported provider '{provider}' for the {agent_name} agent")
