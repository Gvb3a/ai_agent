![](logo.png)
# Ai agent
This telegram bot gives access to an ai agent that can search for information on the internet, use WolframAlpha, summarize youtube videos and search for pictures.

### Tools:
- [aiogram](https://aiogram.dev/) - library for interacting with telegram
- [Gemini](https://aistudio.google.com/app/prompts/new_chat) - Google gives free access to the smartest models. [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference)
- [Groq](https://console.groq.com/docs/overview) - Also totally free access to very fast llm (mostly llama). They also give you free access to [whisper](https://console.groq.com/docs/speech-text)
- [WolframAlpha](https://products.wolframalpha.com/api) - allows for complex calculations and much more
- [DuckDuckGo](https://pypi.org/project/duckduckgo-search/) - A fast and free alternative to google (search links, pictures). [Official Site](https://duckduckgo.com/)
- [Tavily](https://tavily.com/) - A very cool API to connect LLM to the web. Allows you to give context and also parse text from pages.
- [YouTube Transcript API](https://pypi.org/project/youtube-transcript-api/) - Allows you to summarize youtube videos
- [Whisper](https://github.com/openai/whisper) - Free speech to text model (can run locally)
- [e2b](https://e2b.dev/) - Python compilator
- [latexonline.cc](https://latexonline.cc/) and [Equation Render](https://latex.codecogs.com/) as LaTeX compilator
- [pythonanywhere](https://www.pythonanywhere.com/) - hosting

### Lanch
Download the necessary libraries (requirements.txt)\
Create this `.env` file and fill api keys
```
BOT_TOKEN=
GROQ_API_KEY=
TAVILY_API_KEY=
WOLFRAM_SIMPLE_API_KEY=
WOLFRAM_SHOW_STEPS_RESULT=
DETECT_LANGUAGE_API=
GOOGLE_API_KEY=
E2B_API_KEY=
```
Then run `bot.py`


### Todo:

- [ ] Local llm wia hugging face and ollama
- [ ] Start and Help message
- [ ] Integration with Todoist, Calendar, Gmail, Notion
- [ ] Memory as in ChatGPT
- [ ] Embedings and vector datebase
- [ ] Picture generate
- [ ] ElevenLabs
- [ ] Working with multiple files (merge pdf) and sending files
- [ ] Upgrate `google_full_search` and `wolfram_full_answer`
- [ ] See what can be taken from https://github.com/theurs/tb1
- [ ] [Gpt Researcher](https://github.com/assafelovic/gpt-researcher)
  
---
You can try it [here](https://t.me/personalised_ai_assistant_bot) if it is enabled