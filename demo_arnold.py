#!/usr/bin/env python3
"""
Interactive demo of Arnold.ai functionality
This demonstrates the voice agent without needing the full server
"""

import os
import json
from datetime import date
from dotenv import load_dotenv
from db.database import engine
from sqlalchemy import text

load_dotenv()

# Initialize OpenAI with compatibility handling
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

try:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
except (ImportError, TypeError) as e:
    print("Note: Using alternative OpenAI initialization due to compatibility issues")
    import openai
    openai.api_key = OPENAI_API_KEY
    
    # Create a compatibility wrapper
    class OpenAICompat:
        class ChatCompletions:
            @staticmethod
            def create(**kwargs):
                # Map new parameter names to old ones
                messages = kwargs.get('messages', [])
                model = kwargs.get('model', 'gpt-4-turbo-preview')
                functions = kwargs.get('functions', None)
                function_call = kwargs.get('function_call', None)
                temperature = kwargs.get('temperature', 0.7)
                
                params = {
                    'model': model,
                    'messages': messages,
                    'temperature': temperature
                }
                
                if functions:
                    params['functions'] = functions
                if function_call:
                    params['function_call'] = function_call
                
                response = openai.ChatCompletion.create(**params)
                
                # Wrap response to match new format
                class Message:
                    def __init__(self, msg):
                        self.content = msg.get('content', '')
                        fc = msg.get('function_call', None)
                        if fc:
                            self.function_call = type('FunctionCall', (), {
                                'name': fc['name'],
                                'arguments': fc['arguments']
                            })()
                        else:
                            self.function_call = None
                
                class Choice:
                    def __init__(self, choice):
                        self.message = Message(choice['message'])
                
                class Response:
                    def __init__(self, resp):
                        self.choices = [Choice(resp['choices'][0])]
                
                return Response(response)
        
        class Chat:
            completions = ChatCompletions()
        
        chat = Chat()
    
    client = OpenAICompat()

def get_ai_response(user_input, conversation_history=[]):
    """Get AI response for user input"""
    
    system_prompt = """You are Arnold, an AI workout assistant. You help users track their workouts by understanding voice commands about exercises, reps, and weights.

When a user tells you about a workout, extract:
- Exercise name (e.g., "bench press", "squats", "deadlifts")
- Number of reps
- Weight in pounds

You have access to these functions:
- log_workout: Store a new workout entry
- get_recent_workouts: Retrieve recent workout history
- query_workouts_by_exercise: Get history for a specific exercise

Be encouraging and motivational!"""

    functions = [
        {
            "name": "log_workout",
            "description": "Log a new workout set to the database",
            "parameters": {
                "type": "object",
                "properties": {
                    "exercise": {"type": "string", "description": "The name of the exercise"},
                    "reps": {"type": "integer", "description": "Number of repetitions performed"},
                    "weight_lbs": {"type": "number", "description": "Weight used in pounds"},
                    "workout_date": {"type": "string", "format": "date", "description": "Date of the workout (YYYY-MM-DD format)"}
                },
                "required": ["exercise", "reps", "weight_lbs"]
            }
        },
        {
            "name": "get_recent_workouts",
            "description": "Get the most recent workout entries",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of recent workouts to retrieve", "default": 10}
                }
            }
        },
        {
            "name": "query_workouts_by_exercise",
            "description": "Query workout history for a specific exercise",
            "parameters": {
                "type": "object",
                "properties": {
                    "exercise": {"type": "string", "description": "The exercise name to query"}
                },
                "required": ["exercise"]
            }
        }
    ]

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            functions=functions,
            function_call="auto",
            temperature=0.7
        )
        
        assistant_message = response.choices[0].message
        
        # Check if function call is needed
        if assistant_message.function_call:
            function_name = assistant_message.function_call.name
            function_args = json.loads(assistant_message.function_call.arguments)
            
            # Execute the function
            function_result = execute_function(function_name, function_args)
            
            # Add function call and result to messages
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "function_call": {
                    "name": function_name,
                    "arguments": assistant_message.function_call.arguments
                }
            })
            messages.append({
                "role": "function",
                "name": function_name,
                "content": json.dumps(function_result)
            })
            
            # Get final response
            final_response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0.7
            )
            
            return final_response.choices[0].message.content
        else:
            return assistant_message.content
            
    except Exception as e:
        return f"Error: {str(e)}"

def execute_function(function_name, arguments):
    """Execute the requested function"""
    
    with engine.connect() as conn:
        if function_name == "log_workout":
            # Default to today if no date provided
            workout_date = arguments.get("workout_date", date.today().isoformat())
            
            # Insert workout
            conn.execute(
                text("""
                    INSERT INTO workouts (workout_date, exercise, reps, weight_lbs, created_at)
                    VALUES (:date, :exercise, :reps, :weight, datetime('now'))
                """),
                {
                    "date": workout_date,
                    "exercise": arguments["exercise"].lower(),
                    "reps": arguments["reps"],
                    "weight": arguments["weight_lbs"]
                }
            )
            conn.commit()
            
            return {
                "success": True,
                "message": f"Logged {arguments['reps']} reps of {arguments['exercise']} at {arguments['weight_lbs']} lbs"
            }
        
        elif function_name == "get_recent_workouts":
            limit = arguments.get("limit", 10)
            result = conn.execute(
                text("""
                    SELECT exercise, reps, weight_lbs, workout_date 
                    FROM workouts 
                    ORDER BY id DESC 
                    LIMIT :limit
                """),
                {"limit": limit}
            )
            
            workouts = []
            for row in result:
                workouts.append({
                    "exercise": row[0],
                    "reps": row[1],
                    "weight_lbs": row[2],
                    "date": row[3]
                })
            
            return {"success": True, "workouts": workouts}
        
        elif function_name == "query_workouts_by_exercise":
            exercise = arguments["exercise"].lower()
            result = conn.execute(
                text("""
                    SELECT reps, weight_lbs, workout_date 
                    FROM workouts 
                    WHERE exercise = :exercise
                    ORDER BY workout_date DESC
                    LIMIT 20
                """),
                {"exercise": exercise}
            )
            
            workouts = []
            for row in result:
                workouts.append({
                    "reps": row[0],
                    "weight_lbs": row[1],
                    "date": row[2]
                })
            
            return {"success": True, "exercise": exercise, "workouts": workouts}
        
    return {"success": False, "error": f"Unknown function: {function_name}"}

def main():
    print("🏋️  Welcome to Arnold.ai - Your AI Workout Assistant!")
    print("=" * 50)
    print("\nI can help you:")
    print("- Log your workouts (e.g., 'I did 10 reps of bench press at 135 pounds')")
    print("- Check your recent workouts ('Show me my recent workouts')")
    print("- Query specific exercises ('What's my bench press history?')")
    print("\nType 'quit' to exit\n")
    
    conversation_history = []
    
    while True:
        user_input = input("\n💬 You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("\n🏋️  Arnold: Keep up the great work! See you at the gym!")
            break
        
        print("\n🏋️  Arnold: ", end="", flush=True)
        response = get_ai_response(user_input, conversation_history)
        print(response)
        
        # Add to conversation history
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": response})
        
        # Keep conversation history manageable
        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🏋️  Arnold: Keep pushing! See you next time!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure your OPENAI_API_KEY is set in the .env file")