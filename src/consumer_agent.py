import random
from core import DelegationToken, APIClient

# Simulated LLM function (in production, use OpenAI or another model)
def llm_parse_request(request_text):
    if "meeting" in request_text.lower():
        return "schedule_meeting"
    return "unknown_request"

class ConsumerAgent:
    """Handles meeting requests and interacts with the Time Server Agent."""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.agent_id = "consumer_agent_001"
        self.token = DelegationToken.create_token(user_id, self.agent_id, ["view_calendar"])

    def find_free_times(self):
        """Simulates finding free time slots in a user's calendar."""
        times = ["2025-06-10 10:00", "2025-06-10 14:00", "2025-06-10 16:00"]
        return times

    def request_meeting(self, request_text):
        """Handles the user request and sends it to the time server agent if valid."""
        action = llm_parse_request(request_text)
        if action == "schedule_meeting":
            free_times = self.find_free_times()
            print(f"ConsumerAgent: Found available times: {free_times}")

            selected_time = random.choice(free_times)  # Simulating user selection
            print(f"User selected: {selected_time}")

            time_server_agent = TimeServerAgent()
            converted_time = time_server_agent.convert_time_to_japan(selected_time)
            print(f"Final confirmed time: Local - {selected_time}, Japan Time - {converted_time}")

        else:
            print("ConsumerAgent: Unable to process request.")

# Run Consumer Agent interaction
if __name__ == "__main__":
    consumer_agent = ConsumerAgent(user_id="user_123")
    consumer_agent.request_meeting("I need a meeting next week")
