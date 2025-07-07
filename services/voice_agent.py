import json
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI
from services.workout_service import WorkoutService
from schemas.workout import WorkoutIn
import logging

logger = logging.getLogger(__name__)


class VoiceAgent:
    def __init__(self, openai_client: OpenAI, workout_service: WorkoutService):
        self.openai_client = openai_client
        self.workout_service = workout_service
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        return """You are Arnold, an AI workout assistant. You help users track their workouts by understanding voice commands about exercises, reps, and weights.

Key responsibilities:
1. Parse workout information from natural language (exercise name, reps, weight)
2. Store workouts in the database
3. Query historical workout data when asked
4. Provide workout insights and progress tracking
5. Be encouraging and motivational

When a user tells you about a workout, extract:
- Exercise name (e.g., "bench press", "squats", "deadlifts")
- Number of reps
- Weight in pounds

Common exercise variations to recognize:
- Bench press (flat bench, incline bench, decline bench, dumbbell bench)
- Squats (back squats, front squats, goblet squats)
- Deadlifts (conventional, sumo, romanian/RDL)
- Overhead press (military press, shoulder press, dumbbell press)
- Rows (barbell row, cable row, dumbbell row)
- Pull-ups/chin-ups
- Curls (barbell curl, dumbbell curl, hammer curl)
- Tricep exercises (tricep extension, dips, close-grip bench)

When users ask about their history, query the database and provide relevant insights.

Available functions:
- log_workout: Store a new workout entry
- get_recent_workouts: Retrieve recent workout history
- query_workouts_by_exercise: Get history for a specific exercise"""

    def _create_functions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "log_workout",
                "description": "Log a new workout set to the database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "exercise": {
                            "type": "string",
                            "description": "The name of the exercise"
                        },
                        "reps": {
                            "type": "integer",
                            "description": "Number of repetitions performed"
                        },
                        "weight_lbs": {
                            "type": "number",
                            "description": "Weight used in pounds"
                        },
                        "workout_date": {
                            "type": "string",
                            "format": "date",
                            "description": "Date of the workout (YYYY-MM-DD format). Default to today if not specified."
                        }
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
                        "limit": {
                            "type": "integer",
                            "description": "Number of recent workouts to retrieve",
                            "default": 10
                        }
                    }
                }
            },
            {
                "name": "query_workouts_by_exercise",
                "description": "Query workout history for a specific exercise",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "exercise": {
                            "type": "string",
                            "description": "The exercise name to query"
                        },
                        "workout_date": {
                            "type": "string",
                            "format": "date",
                            "description": "Optional date filter (YYYY-MM-DD format)"
                        }
                    },
                    "required": ["exercise"]
                }
            }
        ]

    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute the requested function with the given arguments."""
        try:
            if function_name == "log_workout":
                # Default to today if no date provided
                if "workout_date" not in arguments:
                    arguments["workout_date"] = date.today().isoformat()
                else:
                    # Convert string date to date object
                    arguments["workout_date"] = datetime.fromisoformat(arguments["workout_date"]).date()
                
                workout_in = WorkoutIn(**arguments)
                result = self.workout_service.create_workout(workout_in)
                return {
                    "success": True,
                    "message": f"Logged {result.reps} reps of {result.exercise} at {result.weight_lbs} lbs",
                    "workout": {
                        "id": result.id,
                        "exercise": result.exercise,
                        "reps": result.reps,
                        "weight_lbs": result.weight_lbs,
                        "date": result.workout_date.isoformat()
                    }
                }
            
            elif function_name == "get_recent_workouts":
                limit = arguments.get("limit", 10)
                workouts = self.workout_service.get_recent_workouts(limit=limit)
                return {
                    "success": True,
                    "workouts": [
                        {
                            "id": w.id,
                            "exercise": w.exercise,
                            "reps": w.reps,
                            "weight_lbs": w.weight_lbs,
                            "date": w.workout_date.isoformat()
                        } for w in workouts
                    ]
                }
            
            elif function_name == "query_workouts_by_exercise":
                exercise = arguments["exercise"]
                workout_date = None
                if "workout_date" in arguments:
                    workout_date = datetime.fromisoformat(arguments["workout_date"]).date()
                
                workouts = self.workout_service.query_workouts(
                    exercise=exercise, 
                    workout_date=workout_date
                )
                return {
                    "success": True,
                    "exercise": exercise,
                    "workouts": [
                        {
                            "id": w.id,
                            "reps": w.reps,
                            "weight_lbs": w.weight_lbs,
                            "date": w.workout_date.isoformat()
                        } for w in workouts
                    ]
                }
            
            else:
                return {"success": False, "error": f"Unknown function: {function_name}"}
                
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {str(e)}")
            return {"success": False, "error": str(e)}

    def process_voice_command(self, transcript: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Process a voice command and return the AI response."""
        
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add the current user message
        messages.append({"role": "user", "content": transcript})
        
        try:
            # Call OpenAI with function calling enabled
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                functions=self._create_functions(),
                function_call="auto",
                temperature=0.7
            )
            
            assistant_message = response.choices[0].message
            
            # Check if the assistant wants to call a function
            if assistant_message.function_call:
                function_name = assistant_message.function_call.name
                function_args = json.loads(assistant_message.function_call.arguments)
                
                # Execute the function
                function_result = self._execute_function(function_name, function_args)
                
                # Add the function call and result to messages
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
                
                # Get final response from the assistant
                final_response = self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=messages,
                    temperature=0.7
                )
                
                return final_response.choices[0].message.content
            
            else:
                # No function call needed, return the response directly
                return assistant_message.content
                
        except Exception as e:
            logger.error(f"Error processing voice command: {str(e)}")
            return "I'm sorry, I encountered an error processing your request. Please try again."