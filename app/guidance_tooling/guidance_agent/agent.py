# import the necessary libraries
from typing import Callable, Dict

from colorama import Fore
from colorama import Style
from prompts.guicance_cot import ChainOfThoughts, PROMPT_START_STRING
from prompts import guidance_check_question
from andromeda_chain import AndromedaChain


def color_print(msg, color):
    print(color + Style.BRIGHT + msg  + Style.RESET_ALL)


class AgentHistory:
    def __init__(self) -> None:
        self.raw_history = []

    def append(self, item):
        self.raw_history.append(item)

    def __str__(self) -> str:
        return str(self.raw_history)


class CustomAgentGuidance:
    def __init__(self, andromeda: AndromedaChain, tools: Dict[str, Callable[[str], str]], num_iter=3):
        self.andromeda = andromeda
        self.tools = tools
        self.num_iter = num_iter
        self.valid_tools = list(tools.keys()) + ["Reply"]
        self.valid_answers = ["Action", "Final Answer"]

    def do_tool(self, tool_name, act_input):
        color_print(f"Using tool: {tool_name}", Fore.GREEN)
        result = self.tools[tool_name](act_input)
        color_print(f"Tool result: {result}", Fore.BLUE)
        return result

    def __call__(self, query):
        print(self.valid_answers)
        result_start = self.andromeda.run_guidance_prompt(
            ChainOfThoughts.prompt_start,
            input_vars={
                "prompt_start": PROMPT_START_STRING,
                "question": query,
                "valid_answers": self.valid_answers,
            },
        )
        history = result_start.expanded_generation
        answer = result_start.result_vars["answer"]

        color_print(f"Result start: {result_start.result_vars}", Fore.YELLOW)
        for _ in range(self.num_iter - 1):
            if answer == "Final Answer":
                break

            # Choose action
            chosen_action_result = self.andromeda.run_guidance_prompt(
                ChainOfThoughts.choose_action,
                input_vars={
                    "history": history,
                    "valid_tools": self.valid_tools,
                },
            )
            history = chosen_action_result.expanded_generation
            tool_name = chosen_action_result.result_vars["tool_name"]
            color_print(f"Chosen action: {tool_name}", Fore.GREEN)

            # Provide action input
            action_input_result = self.andromeda.run_guidance_prompt(
                ChainOfThoughts.action_input,
                input_vars={
                    "history": history
                }
            )
            history = action_input_result.expanded_generation
            action_input = action_input_result.result_vars["actInput"]
            color_print(f"Action Input: {action_input}", Fore.YELLOW)

            if tool_name == "Reply":
                break

            # Execute tool
            observation = self.do_tool(tool_name, action_input)
            color_print(f"Observation: {observation}", Fore.LIGHTMAGENTA_EX)

            if "Search" in tool_name:
                check_question = self.andromeda.run_guidance_prompt(
                    guidance_check_question.PROMPT_CHECK_QUESTION,
                    input_vars={
                        "context": observation,
                        "question": query,
                    }
                )
                color_print(f"Check question: {check_question}", Fore.YELLOW)
                if check_question.result_vars["answer"] == "no":
                    color_print(f"I don't know", Fore.RED)
                    return "I could not answer this question given the context"


                thought_result = self.andromeda.run_guidance_prompt(
                    ChainOfThoughts.thought_gen,
                    input_vars={
                        "history": history,
                        "observation": observation,
                        "valid_answers": self.valid_answers,
                    },
                )
                color_print(f"Thought result: {thought_result.result_vars}", Fore.CYAN)
                answer = thought_result.result_vars["answer"]
                history = thought_result.expanded_generation

        # Generate final answer
        result_final = self.andromeda.run_guidance_prompt(
            ChainOfThoughts.final_prompt,
            {
                "history": history,
            }
        )
        color_print(f"Final resut: {result_final.result_vars}", Fore.GREEN)
        return result_final.result_vars["final_answer"]
