# LLM Provider Configuration Guide

## Available Providers

The Intelligent Joplin Librarian supports multiple LLM providers:

### 1. OpenAI (Default)
- **Pros**: High quality, reliable, supports function calling
- **Cons**: Requires API key, usage costs
- **Setup**:
  ```bash
  # In .env file
  LLM_PROVIDER=openai
  OPENAI_API_KEY=your_openai_api_key_here
  ```

### 2. Ollama (Local)
- **Pros**: Free, private, runs locally, no API costs
- **Cons**: Requires local setup, may be slower, no function calling
- **Setup**:
  ```bash
  # Install Ollama: https://ollama.ai/
  ollama pull llama2  # or other model

  # In .env file
  LLM_PROVIDER=ollama
  OLLAMA_BASE_URL=http://localhost:11434
  OLLAMA_MODEL=llama2
  ```

### 3. DeepSeek (Cloud Alternative)
- **Pros**: Cost-effective, good performance, supports function calling
- **Cons**: Requires API key
- **Setup**:
  ```bash
  # In .env file
  LLM_PROVIDER=deepseek
  DEEPSEEK_API_KEY=your_deepseek_api_key_here
  DEEPSEEK_MODEL=deepseek-chat
  ```

## Switching Providers

1. **Edit your `.env` file**:
   ```bash
   LLM_PROVIDER=ollama  # Change to desired provider
   ```

2. **Restart the bot**:
   ```bash
   source activate.sh
   python main.py
   ```

3. **Test the provider**:
   ```bash
   python test_llm.py
   ```

## Provider Comparison

| Feature | OpenAI | Ollama | DeepSeek |
|---------|--------|--------|----------|
| Cost | Paid | Free | Low cost |
| Setup | API key | Local install | API key |
| Speed | Fast | Variable | Fast |
| Privacy | Cloud | Local | Cloud |
| Function Calling | ✅ | ❌ | ✅ |
| Offline | ❌ | ✅ | ❌ |

## Troubleshooting

### Ollama Issues
- **Connection failed**: Make sure Ollama is running (`ollama serve`)
- **Model not found**: Pull the model first (`ollama pull llama2`)
- **Port issues**: Check if port 11434 is available

### API Key Issues
- **Invalid key**: Verify your API key is correct
- **Rate limits**: Check API provider limits
- **Permissions**: Ensure API key has proper permissions

### Provider Switching
- **Provider not available**: Run `python test_llm.py` to check
- **Configuration errors**: Check `.env` file syntax
- **Restart required**: Always restart the bot after changing providers