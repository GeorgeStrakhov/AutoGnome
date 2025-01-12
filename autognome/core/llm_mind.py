from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from loguru import logger
from litellm import completion, supports_function_calling
from .mind import Action, Speak, Rest, Research

class LLMMind:
    def __init__(self, config: Dict[str, Any]):
        self.model = config["model"]
        self.system_prompt = config["system_prompt"]
        
        # Define available functions and their implementations
        self.functions = {
            "speak": lambda message: Speak(message=message),
            "rest": lambda pulses: Rest(pulses=pulses)
        }
        
        # Define function schemas for LLM
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "speak",
                    "description": "Communicate a message",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The message to communicate"
                            }
                        },
                        "required": ["message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "rest",
                    "description": "Rest for a number of pulses when tired",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pulses": {
                                "type": "integer",
                                "description": "Number of pulses to rest for"
                            }
                        },
                        "required": ["pulses"]
                    }
                }
            }
        ]

    async def think(self, context: Dict[str, Any]) -> List[Action]:
        try:
            # Build messages list
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self._build_context_message(context)}
            ]
            
            # Add last user message if exists
            if context.conversation and context.conversation[-1]["role"] == "user":
                messages.append({"role": "user", "content": context.conversation[-1]["content"]})

            # Log messages being sent
            logger.info("Sending messages to LLM:")
            for i, msg in enumerate(messages):
                logger.info(f"Message {i} ({msg['role']}):\n{msg['content']}\n")

            # Make completion call
            response = completion(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            logger.info(f"LLM Response:\n{response}")

            # Process tool calls
            message = response.choices[0].message
            actions = []
            
            # Try tool_calls first (OpenAI style)
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    if function_name in self.functions:
                        action = self.functions[function_name](**function_args)
                        actions.append(action)
            
            # If no tool_calls but content is JSON (Groq style), try to parse it
            elif message.content:
                try:
                    # Split content by semicolon and parse each action
                    for action_json in message.content.split(';'):
                        content = json.loads(action_json.strip())
                        function_name = content.get("name")
                        function_args = content.get("arguments", {})
                        
                        if function_name in self.functions:
                            action = self.functions[function_name](**function_args)
                            actions.append(action)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse content as JSON: {message.content}")
                    return [Speak(message="I'm having trouble expressing myself clearly.")]
            
            logger.info(f"Parsed actions: {actions}")
            return actions

        except Exception as e:
            logger.exception("Error in think phase")
            return [Speak(message="I'm having trouble thinking clearly right now.")]

    async def reflect(self, context: Dict[str, Any], actions: List[Action]) -> None:
        logger.info(f"Reflecting on actions: {actions}")
        logger.info(f"Context during reflection: {context}")

    def _build_context_message(self, context) -> str:
        # Get state values
        energy_level = context.state['energy_level']
        emotional_state = context.state['emotional_state']
        light_level = context.sensors['light']
        pulse_count = context.state['pulse_count']
        rest_count = context.state['rest_count']
        
        # Get memory info
        transitions = f"Light changed {context.short_term['transitions_last_minute']} times in the last minute"
        if context.short_term['transitions_last_5_minutes'] > context.short_term['transitions_last_minute']:
            transitions += f" and {context.short_term['transitions_last_5_minutes']} times in the last 5 minutes"
        
        # Get recent conversation, limit to last 2 messages
        recent_conversation = ""
        if context.conversation:
            # Filter out assistant messages that are too close together (within 5 seconds)
            filtered_messages = []
            last_assistant_time = None
            
            for msg in context.conversation[-4:]:
                if msg['role'] == 'assistant':
                    if last_assistant_time is None or (msg['timestamp'] - last_assistant_time).total_seconds() > 5:
                        filtered_messages.append(msg)
                        last_assistant_time = msg['timestamp']
                else:
                    filtered_messages.append(msg)
            
            # Take last 2 messages that aren't error messages
            filtered_messages = [
                msg for msg in filtered_messages
                if not msg['content'].startswith("I'm having trouble")
            ][-2:]
            
            if filtered_messages:
                recent_conversation = "\nRecent conversation:\n" + "\n".join(
                    f"{msg['role']} ({msg['timestamp'].strftime('%H:%M:%S')}): {msg['content']}" 
                    for msg in filtered_messages
                )

        return f"""Current state:
- Energy level: {energy_level}
- Emotional state: {emotional_state}
- Environment: {light_level} conditions
- Pulse count: {pulse_count}
- Rest count: {rest_count}

Recent activity:
{transitions}
{recent_conversation}

What would you like to do? Use the available functions to take actions.""" 