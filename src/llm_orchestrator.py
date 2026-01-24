"""
LLM Orchestrator for Note Generation
Handles AI-powered note creation and clarification logic.
Supports multiple LLM providers through abstraction layer.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from src.llm_providers import registry as provider_registry
from config import LLM_PROVIDER
from src.logging_service import LoggingService, LLMInteraction
from pathlib import Path

logger = logging.getLogger(__name__)

class JoplinNoteSchema(BaseModel):
    """Pydantic schema for LLM-generated note data"""
    status: str = Field(description="Either 'SUCCESS' or 'NEED_INFO'")
    confidence_score: float = Field(description="Confidence score between 0.0 and 1.0")
    question: Optional[str] = Field(description="Clarification question if status is NEED_INFO")
    log_entry: str = Field(description="Log entry describing the AI decision")
    note: Optional[Dict[str, Any]] = Field(description="Note data with title, body, parent_id, tags")

class LLMOrchestrator:
    """Orchestrates LLM interactions for note generation"""

    def __init__(self, provider_name: str = None):
        self.provider_name = provider_name or LLM_PROVIDER
        self.provider = provider_registry.get_provider(self.provider_name)
        self.logging_service = LoggingService()

        if not self.provider:
            logger.warning(f"Provider '{self.provider_name}' not found, falling back to available provider")
            available = provider_registry.get_available_providers()
            if available:
                self.provider_name = list(available.keys())[0]
                self.provider = available[self.provider_name]
                logger.info(f"Using provider: {self.provider_name}")
            else:
                raise RuntimeError("No LLM providers available")

        if not self.provider.is_available():
            raise RuntimeError(f"LLM provider '{self.provider_name}' is not available")

        # Persona storage
        self.prompts_dir = Path(__file__).parent / "prompts"
        self._personas = {}

    def process_message(self, user_message: str, context: Dict[str, Any] = None, persona: str = None, history: List[Dict[str, str]] = None) -> JoplinNoteSchema:
        """
        Process user message and generate note data using LLM

        Args:
            user_message: The message from the user
            context: Additional context (existing tags, conversation history, etc.)
            persona: Optional persona name to use for the system prompt
            history: Optional conversation history to include

        Returns:
            JoplinNoteSchema with the LLM's response
        """
        logger.info(f"🔄 Processing message with {self.provider_name} (Persona: {persona or 'default'}): '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")

        try:
            # Build the system prompt
            if persona:
                system_prompt = self._get_persona_prompt(persona, context)
            else:
                system_prompt = self._build_system_prompt(context)
            
            logger.info(f"📝 System prompt ({len(system_prompt)} chars): {system_prompt[:200]}{'...' if len(system_prompt) > 200 else ''}")

            # Prepare messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add history if provided
            if history:
                messages.extend(history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})

            logger.info(f"💬 User message: '{user_message}'")
            logger.info(f"🤖 Calling {self.provider_name} API...")

            # Handle structured output differently for each provider
            if self.provider_name in ["openai", "deepseek"]:
                # Use function calling for providers that support it
                functions = [{
                    "name": "create_joplin_note",
                    "description": "Create a structured response for Joplin note generation",
                    "parameters": JoplinNoteSchema.schema()
                }]

                logger.info("🔧 Function schema being sent to LLM:")
                logger.info(f"📋 Schema: {json.dumps(JoplinNoteSchema.schema(), indent=2)}")
                logger.debug(f"📡 Sending request to {self.provider_name} with function calling")

                response = self.provider.generate_response(
                    messages=messages,
                    functions=functions,
                    function_call={"name": "create_joplin_note"},
                    temperature=0.3,
                    max_tokens=1000
                )

                logger.info(f"✅ Received response from {self.provider_name}")
                logger.info("📄 Raw LLM response:")
                logger.info(f"   Content: {response.get('content', 'No content')}")
                logger.info(f"   Function call: {response.get('function_call', 'No function call')}")
                if response.get('usage'):
                    logger.info(f"   Usage: {response['usage']}")

                # Extract the function call result
                function_call = response.get("function_call")
                args = None

                if function_call:
                    # Parse function call arguments
                    try:
                        args = json.loads(function_call["arguments"])
                        logger.info("🔍 Parsed JSON from function call:")
                        logger.info(f"   {json.dumps(args, indent=2)}")
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.error(f"❌ Failed to parse function call arguments: {e}")
                        return self._create_error_response("Invalid function call format from LLM")
                    else:
                        # Try to parse JSON directly from content (fallback for models that don't use function calling)
                        content = response.get("content", "").strip()
                        if content:
                            try:
                                # Try to extract JSON from content
                                json_start = content.find('{')
                                json_end = content.rfind('}') + 1
                                if json_start != -1 and json_end > json_start:
                                    json_content = content[json_start:json_end]
                                    args = json.loads(json_content)
                                    logger.info("🔍 Parsed JSON from content (fallback):")
                                    logger.info(f"   {json.dumps(args, indent=2)}")
                                else:
                                    # [MODIFIED] If NO JSON found but we are in a persona flow, treat content as the next question
                                    if persona:
                                        logger.info(f"💬 Treating plain text response as persona conversation: '{content[:50]}...'")
                                        return JoplinNoteSchema(
                                            status="NEED_INFO",
                                            confidence_score=1.0,
                                            question=content,
                                            log_entry=f"Conversational response from persona: {persona}",
                                            note=None
                                        )
                                    
                                    logger.warning("⚠️ No function call in LLM response and no JSON found in content")
                                    logger.debug(f"Raw response content: {content}")
                                    return self._create_error_response("No structured response from LLM")
                            except (json.JSONDecodeError, ValueError) as e:
                                # [MODIFIED] Even if JSON parsing fails, if we have a persona, fall back to plain text
                                if persona:
                                    logger.info(f"💾 JSON parse failed, falling back to plain text for persona: '{content[:50]}...'")
                                    return JoplinNoteSchema(
                                        status="NEED_INFO",
                                        confidence_score=1.0,
                                        question=content,
                                        log_entry=f"Fallback conversational response (JSON failed)",
                                        note=None
                                    )
                                
                                logger.error(f"❌ Failed to parse JSON from content: {e}")
                                logger.debug(f"Raw content: {content}")
                                return self._create_error_response("Invalid JSON format in LLM response")
                        else:
                            logger.warning("⚠️ No function call and no content in LLM response")
                            return self._create_error_response("Empty response from LLM")

                # Process the parsed arguments
                try:
                    result = JoplinNoteSchema(**args)
                    logger.info(f"🎯 LLM decision: {result.status} (confidence: {result.confidence_score})")
                    if result.status == "NEED_INFO":
                        logger.info(f"❓ Clarification needed: {result.question}")
                    else:
                        note_title = result.note.get('title', 'N/A') if result.note else 'N/A'
                        logger.info(f"📝 Note created: '{note_title}'")
                    logger.debug(f"📊 Log entry: {result.log_entry}")
                    return result
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"❌ Failed to validate parsed arguments: {e}")
                    logger.debug(f"Parsed args: {args}")
                    return self._create_error_response("Invalid response structure from LLM")

            elif self.provider_name == "ollama":
                # For Ollama, use a different approach since it doesn't support function calling
                # We'll use a structured prompt instead
                logger.info("🔧 Using structured prompt approach for Ollama (no function calling)")

                structured_prompt = self._create_structured_prompt(system_prompt, user_message)
                logger.info("📝 Structured prompt being sent to Ollama:")
                logger.info(f"   {structured_prompt[:500]}{'...' if len(structured_prompt) > 500 else ''}")

                messages = [{"role": "user", "content": structured_prompt}]

                logger.info("📡 Sending request to Ollama...")

                response = self.provider.generate_response(
                    messages=messages,
                    temperature=0.1,  # Very low temperature for structured output
                    max_tokens=1500
                )

                logger.info("✅ Received response from Ollama")
                content = response.get("content", "").strip()
                logger.info("📄 Raw Ollama response:")
                logger.info(f"   {content[:500]}{'...' if len(content) > 500 else ''}")

                try:
                    # Try to extract JSON from the response
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_content = content[json_start:json_end]
                        logger.info("🔍 Extracted JSON from Ollama response:")
                        logger.info(f"   {json_content}")

                        args = json.loads(json_content)
                        logger.info("🔍 Parsed JSON arguments:")
                        logger.info(f"   {json.dumps(args, indent=2)}")

                        result = JoplinNoteSchema(**args)
                        logger.info(f"🎯 Ollama decision: {result.status} (confidence: {result.confidence_score})")
                        if result.status == "NEED_INFO":
                            logger.info(f"❓ Clarification needed: {result.question}")
                        else:
                            note_title = result.note.get('title', 'N/A') if result.note else 'N/A'
                            logger.info(f"📝 Note created: '{note_title}'")
                        logger.debug(f"📊 Log entry: {result.log_entry}")
                        return result
                    else:
                        # [MODIFIED] Fallback for Ollama plain text
                        if persona:
                            logger.info(f"💬 Treating plain text Ollama response as persona conversation: '{content[:50]}...'")
                            return JoplinNoteSchema(
                                status="NEED_INFO",
                                confidence_score=1.0,
                                question=content,
                                log_entry=f"Ollama conversational response from persona: {persona}",
                                note=None
                            )
                        
                        logger.error("❌ No JSON found in Ollama response")
                        logger.debug(f"Full response: {content}")
                        return self._create_error_response("No structured response from Ollama")
                except (json.JSONDecodeError, ValueError) as e:
                    # [MODIFIED] Fallback for Ollama JSON parse failure
                    if persona:
                        logger.info(f"💾 Ollama JSON parse failed, falling back to plain text: '{content[:50]}...'")
                        return JoplinNoteSchema(
                            status="NEED_INFO",
                            confidence_score=1.0,
                            question=content,
                            log_entry=f"Ollama fallback conversational response",
                            note=None
                        )
                    
                    logger.error(f"❌ Failed to parse Ollama response: {e}")
                    logger.debug(f"Attempted JSON: {json_content}")
                    return self._create_error_response("Invalid response format from Ollama")

            else:
                logger.error(f"❌ Unsupported LLM provider: {self.provider_name}")
                return self._create_error_response(f"Unsupported provider: {self.provider_name}")

        except Exception as e:
            logger.error(f"💥 Unexpected error in LLM processing with {self.provider_name}: {e}")
            logger.debug(f"Error details: {type(e).__name__}: {str(e)}", exc_info=True)
            return self._create_error_response(f"Unexpected error: {str(e)}")

    def _build_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """Build the system prompt for the LLM"""
        context = context or {}

        # Build folder list, excluding Archive and its children
        folders = context.get('folders', [])
        folder_list = ""
        if folders:
            for f in folders:
                title = f.get('title', 'Unknown').lower()
                if 'archive' in title:
                    continue  # Skip Archive folder and any with 'archive' in name
                fid = f.get('id', 'unknown')
                folder_list += f"- {fid}: {title.title()}\n"  # title() to capitalize
        else:
            folder_list = "No folders available.\n"

        prompt = f"""You are an intelligent assistant that helps users create notes in Joplin, a note-taking application.

Your task is to analyze user messages and either:
1. SUCCESS: Create a complete note with title, body, folder, and tags
2. NEED_INFO: Ask for clarification if the message is unclear

## Joplin Structure
The user organizes notes in these folders:
{folder_list}
Important: Never choose the Archive folder or any folder containing 'archive' in the name.

## Available Tags
"""

        # Add existing tags if available
        existing_tags = context.get('existing_tags', [])
        if existing_tags:
            prompt += "\nExisting tags in Joplin:\n"
            for tag in existing_tags[:20]:  # Limit to avoid token issues
                prompt += f"- {tag}\n"
        else:
            prompt += "\nNo existing tags found. You can create new tags as needed.\n"

        prompt += """
## Guidelines

### When to use SUCCESS:
- Message clearly describes what to note
- You can determine appropriate folder and tags
- Confidence is high (>0.8) that you understand the user's intent

### When to use NEED_INFO:
- Message is ambiguous or incomplete
- Multiple interpretations possible
- Missing key information (what folder? what type of content?)
- Confidence is low (<0.8)

### Note Creation Rules:
- Title should be concise but descriptive (max 100 characters)
- Body should capture the main content, can be detailed
- Choose the most appropriate folder based on content type
- Use relevant existing tags or create new meaningful ones
- Multiple tags are allowed

### Confidence Scoring:
- 0.9-1.0: Very clear, no ambiguity
- 0.7-0.8: Mostly clear, minor uncertainty
- 0.5-0.6: Some ambiguity, needs clarification
- 0.0-0.4: Very unclear, definitely needs more info

## Response Format
Always respond with the structured format containing:
- status: "SUCCESS" or "NEED_INFO"
- confidence_score: float between 0.0 and 1.0
- question: (only if NEED_INFO) specific question to clarify
- log_entry: brief description of your decision process
- note: (only if SUCCESS) object with title, body, parent_id (folder ID), tags (array)

## Examples

### SUCCESS Example:
User: "Meeting notes from client call about new website project"
Response: {
  "status": "SUCCESS",
  "confidence_score": 0.95,
  "question": null,
  "log_entry": "Clear request for meeting notes in project context",
  "note": {
    "title": "Client Meeting - New Website Project",
    "body": "Meeting notes from client call discussing requirements for new website project.",
    "parent_id": "01-Projects",
    "tags": ["meeting", "client", "website"]
  }
}

### NEED_INFO Example:
User: "Add this to my notes"
Response: {
  "status": "NEED_INFO",
  "confidence_score": 0.3,
  "question": "What would you like me to add to your notes? Please provide the content and specify what type of note this is.",
  "log_entry": "Message too vague, no content or context provided",
  "note": null
}

Remember: Be helpful, accurate, and ask for clarification when needed rather than making assumptions."""

        return prompt

    def _get_persona_prompt(self, persona: str, context: Dict[str, Any] = None) -> str:
        """Get the system prompt for a specific persona"""
        # Check cache
        if persona in self._personas:
            return self._personas[persona]

        # Load from file
        prompt_path = self.prompts_dir / f"{persona}.txt"
        if not prompt_path.exists():
            logger.warning(f"Persona file not found: {prompt_path}, falling back to default")
            return self._build_system_prompt(context)

        try:
            with open(prompt_path, "r") as f:
                prompt_content = f.read()
                self._personas[persona] = prompt_content
                return prompt_content
        except Exception as e:
            logger.error(f"Error loading persona {persona}: {e}")
            return self._build_system_prompt(context)

    def _create_error_response(self, error_msg: str) -> JoplinNoteSchema:
        """Create an error response schema"""
        return JoplinNoteSchema(
            status="NEED_INFO",
            confidence_score=0.0,
            question="I'm sorry, I encountered an error processing your request. Please try again.",
            log_entry=f"Error: {error_msg}",
            note=None
        )

    def validate_note_data(self, note_data: Dict[str, Any]) -> bool:
        """Validate that note data has required fields"""
        required_fields = ['title', 'body', 'parent_id']
        return all(field in note_data for field in required_fields)

    def _create_structured_prompt(self, system_prompt: str, user_message: str) -> str:
        """Create a structured prompt for providers without function calling support"""
        return f"""{system_prompt}

User message: {user_message}

IMPORTANT: Respond with ONLY a valid JSON object in this exact format:
{{
  "status": "SUCCESS" or "NEED_INFO",
  "confidence_score": number between 0.0 and 1.0,
  "question": "clarification question if status is NEED_INFO, otherwise null",
  "log_entry": "brief description of your decision",
  "note": {{
    "title": "note title",
    "body": "note content",
    "parent_id": "folder_id",
    "tags": ["tag1", "tag2"]
  }} or null if status is NEED_INFO
}}

Do not include any other text or explanation."""

    def enhance_prompt_with_history(self, base_prompt: str, conversation_history: List[Dict[str, Any]]) -> str:
        """Enhance prompt with recent conversation history for context"""
        if not conversation_history:
            return base_prompt

        # Add recent context (limit to avoid token limits)
        history_text = "\n## Recent Conversation Context:\n"
        for item in conversation_history[-3:]:  # Last 3 messages
            history_text += f"User: {item.get('message', '')}\n"
            if 'response' in item:
                history_text += f"Assistant: {item.get('response', '')}\n"

        return base_prompt + history_text

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider"""
        return {
            "provider_name": self.provider_name,
            "model_name": self.provider.model_name,
            "is_available": self.provider.is_available()
        }