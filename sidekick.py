from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from typing import List, Any, Optional, Dict
from pydantic import BaseModel, Field
from sidekick_tools import playwright_tools, other_tools
import os
import uuid
import asyncio
from datetime import datetime

load_dotenv(override=True)

EVALUATOR_MODEL = "gpt-5.5"
WORKER_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")


class State(TypedDict):
    messages: Annotated[List[Any], add_messages]
    success_criteria: str
    feedback_on_work: Optional[str]
    success_criteria_met: bool
    user_input_needed: bool
    attempt_count: int


class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="Feedback on the assistant's response")
    success_criteria_met: bool = Field(description="Whether the success criteria have been met")
    user_input_needed: bool = Field(
        description="True if more input is needed from the user, or clarifications, or the assistant is stuck"
    )


class Sidekick:
    def __init__(self):
        self.worker_llm_with_tools = None
        self.evaluator_llm_with_output = None
        self.tools = None
        self.llm_with_tools = None
        self.graph = None
        self.sidekick_id = str(uuid.uuid4())
        self.memory = MemorySaver()
        self.browser = None
        self.playwright = None

    async def setup(self):
        self.tools, self.browser, self.playwright = await playwright_tools()
        self.tools += await other_tools()
        worker_llm = ChatOpenAI(model=WORKER_MODEL)
        self.worker_llm_with_tools = worker_llm.bind_tools(self.tools)
        evaluator_llm = ChatOpenAI(model=EVALUATOR_MODEL)
        self.evaluator_llm_with_output = evaluator_llm.with_structured_output(EvaluatorOutput)
        await self.build_graph()
        if self.graph is None:
            raise RuntimeError("Échec de compilation du graphe LangGraph.")

    def worker(self, state: State) -> Dict[str, Any]:
        # Incrémenter le compteur de tentatives
        current_attempt = state.get("attempt_count", 0) + 1
        
        # Si trop de tentatives, forcer l'arrêt
        if current_attempt > 8:
            return {
                "messages": [{
                    "role": "assistant", 
                    "content": "Je n'arrive pas à terminer cette tâche après plusieurs tentatives. Pouvez-vous reformuler votre demande ou fournir plus de détails ?"
                }],
                "attempt_count": current_attempt,
                "user_input_needed": True
            }
        
        system_message = f"""You are a helpful assistant that can use tools to complete tasks.
    You keep working on a task until either you have a question or clarification for the user, or the success criteria is met.
    You have many tools to help you, including tools to browse the internet, navigating and retrieving web pages.
    You have a tool to run python code, but note that you would need to include a print() statement if you wanted to receive output.
    The current date and time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    
    IMPORTANT: This is attempt #{current_attempt} out of 8 maximum attempts. Try to be more decisive and complete the task efficiently.
    
    CRITICAL RULE: When users ask for specific content (recipes, code, instructions, etc.), you MUST include the complete content in your response. 
    - Don't just say "I created a recipe" - show the actual recipe with ingredients and steps
    - Don't just say "I wrote the code" - include the complete code
    - Always provide the actual requested content in your response text

    This is the success criteria:
    {state["success_criteria"]}
    You should reply either with a question for the user about this assignment, or with your final response.
    If you have a question for the user, you need to reply by clearly stating your question. An example might be:

    Question: please clarify whether you want a summary or a detailed answer

    If you've finished, reply with the final answer, and don't ask a question; simply reply with the answer.
    """

        if state.get("feedback_on_work"):
            system_message += f"""
    Previously you thought you completed the assignment, but your reply was rejected because the success criteria was not met.
    Here is the feedback on why this was rejected:
    {state["feedback_on_work"]}
    With this feedback, please continue the assignment, ensuring that you meet the success criteria or have a question for the user."""

        # Add in the system message

        found_system_message = False
        messages = state["messages"]
        for message in messages:
            if isinstance(message, SystemMessage):
                message.content = system_message
                found_system_message = True

        if not found_system_message:
            messages = [SystemMessage(content=system_message)] + messages

        # Invoke the LLM with tools
        try:
            response = self.worker_llm_with_tools.invoke(messages)
        except Exception as e:
            # En cas d'erreur, retourner un message d'erreur
            error_response = AIMessage(content=f"Erreur lors de l'utilisation des outils: {str(e)}. Je vais essayer de répondre sans utiliser d'outils.")
            return {
                "messages": [error_response],
                "attempt_count": current_attempt,
                "user_input_needed": True
            }

        # Return updated state
        return {
            "messages": [response],
            "attempt_count": current_attempt,
        }

    def worker_router(self, state: State) -> str:
        last_message = state["messages"][-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        else:
            return "evaluator"

    def format_conversation(self, messages: List[Any]) -> str:
        conversation = "Conversation history:\n\n"
        for message in messages:
            if isinstance(message, HumanMessage):
                conversation += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                text = message.content or "[Tools use]"
                conversation += f"Assistant: {text}\n"
        return conversation

    def evaluator(self, state: State) -> State:
        last_response = state["messages"][-1].content
        current_attempt = state.get("attempt_count", 1)

        system_message = f"""You are an evaluator that determines if a task has been completed successfully by an Assistant.
    Assess the Assistant's last response based on the given criteria. Respond with your feedback, and with your decision on whether the success criteria has been met,
    and whether more input is needed from the user.
    
    IMPORTANT: This is attempt #{current_attempt} out of 8. After attempt 6, be more lenient and accept reasonable partial answers to avoid infinite loops."""

        user_message = f"""You are evaluating a conversation between the User and Assistant. You decide what action to take based on the last response from the Assistant.

    The entire conversation with the assistant, with the user's original request and all replies, is:
    {self.format_conversation(state["messages"])}

    The success criteria for this assignment is:
    {state["success_criteria"]}

    And the final response from the Assistant that you are evaluating is:
    {last_response}

    Respond with your feedback, and decide if the success criteria is met by this response.
    Also, decide if more user input is required, either because the assistant has a question, needs clarification, or seems to be stuck and unable to answer without help.

    The Assistant has access to a tool to write files. If the Assistant says they have written a file, then you can assume they have done so.
    
    CRITICAL: If the user asks for specific content (like a recipe, instructions, code, etc.), the Assistant MUST provide the actual content in their response, not just say they created it. 
    - If asking for a recipe: the full recipe with ingredients and steps must be visible
    - If asking for code: the actual code must be shown
    - If asking for instructions: the complete instructions must be provided
    
    Do not accept responses that claim to have provided something without actually showing it in the response text.

    """
        if state["feedback_on_work"]:
            user_message += f"Also, note that in a prior attempt from the Assistant, you provided this feedback: {state['feedback_on_work']}\n"
            user_message += "If you're seeing the Assistant repeating the same mistakes, then consider responding that user input is required."
        
        if current_attempt >= 6:
            user_message += f"\n\nIMPORTANT: This is attempt #{current_attempt}. The Assistant has been working on this for a while. Unless the response is completely off-topic or wrong, please accept it to avoid infinite loops."

        evaluator_messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message),
        ]

        eval_result = self.evaluator_llm_with_output.invoke(evaluator_messages)
        new_state = {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Evaluator Feedback on this answer: {eval_result.feedback}",
                }
            ],
            "feedback_on_work": eval_result.feedback,
            "success_criteria_met": eval_result.success_criteria_met,
            "user_input_needed": eval_result.user_input_needed,
        }
        return new_state

    def route_based_on_evaluation(self, state: State) -> str:
        if state["success_criteria_met"] or state["user_input_needed"]:
            return "END"
        else:
            return "worker"

    async def build_graph(self):
        # Set up Graph Builder with State
        graph_builder = StateGraph(State)

        # Add nodes
        graph_builder.add_node("worker", self.worker)
        graph_builder.add_node("tools", ToolNode(tools=self.tools))
        graph_builder.add_node("evaluator", self.evaluator)

        # Add edges
        graph_builder.add_conditional_edges(
            "worker", self.worker_router, {"tools": "tools", "evaluator": "evaluator"}
        )
        graph_builder.add_edge("tools", "worker")
        graph_builder.add_conditional_edges(
            "evaluator", self.route_based_on_evaluation, {"worker": "worker", "END": END}
        )
        graph_builder.add_edge(START, "worker")

        # Compile the graph with increased recursion limit
        self.graph = graph_builder.compile(
            checkpointer=self.memory,
            interrupt_before=[],
            interrupt_after=[]
        )

    def _initial_state(self, message, success_criteria):
        if isinstance(message, str):
            messages = [HumanMessage(content=message)]
        else:
            messages = message
        return {
            "messages": messages,
            "success_criteria": success_criteria or "The answer should be clear and accurate",
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False,
            "attempt_count": 0,
        }

    def _extract_result_payload(self, result):
        messages = result.get("messages", [])
        report_content = ""
        evaluator_feedback = ""
        for msg in reversed(messages):
            content = msg.content if hasattr(msg, "content") else (msg.get("content") if isinstance(msg, dict) else str(msg))
            if not content:
                continue
            if "Evaluator Feedback" in content:
                if not evaluator_feedback:
                    evaluator_feedback = content
                continue
            if not report_content:
                report_content = content
                break
        return {
            "messages": messages,
            "report_content": report_content,
            "evaluator_feedback": evaluator_feedback,
            "attempt_count": result.get("attempt_count", 1),
            "success_criteria_met": result.get("success_criteria_met", False),
        }

    async def run_superstep_streaming(self, message, success_criteria, on_event=None):
        if self.graph is None:
            await self.setup()
        if self.graph is None:
            raise RuntimeError("Graph LangGraph non initialisé.")

        config = {
            "configurable": {"thread_id": self.sidekick_id},
            "recursion_limit": 50,
        }
        state = self._initial_state(message, success_criteria)
        final_result = None
        try:
            async for event in self.graph.astream_events(state, config=config, version="v2"):
                if on_event:
                    on_event(
                        {
                            "event": event.get("event"),
                            "name": event.get("name") or "",
                            "data": event.get("data") or {},
                        }
                    )
                if event.get("event") == "on_chain_end" and event.get("name") == "LangGraph":
                    output = event.get("data", {}).get("output")
                    if output:
                        final_result = output
            if final_result is None:
                final_result = await self.graph.ainvoke(state, config=config)
            return self._extract_result_payload(final_result)
        except Exception as e:
            error_msg = str(e)
            if "tool_calls" in error_msg and "tool_call_id" in error_msg:
                report = "Erreur technique lors de l'utilisation des outils de recherche. Veuillez reformuler votre demande ou essayer une recherche plus simple."
            else:
                report = f"Erreur lors de la recherche: {error_msg}"
            return {
                "messages": [],
                "report_content": report,
                "evaluator_feedback": "La recherche a échoué à cause d'un problème technique.",
                "attempt_count": state.get("attempt_count", 1),
                "success_criteria_met": False,
            }

    async def run_superstep(self, message, success_criteria, history):
        if self.graph is None:
            await self.setup()
        if self.graph is None:
            raise RuntimeError("Graph LangGraph non initialisé.")

        config = {
            "configurable": {"thread_id": self.sidekick_id},
            "recursion_limit": 50  # Augmenter la limite de récursion
        }

        state = self._initial_state(message, success_criteria)
        try:
            result = await self.graph.ainvoke(state, config=config)
            user = {"role": "user", "content": message}
            
            # Vérifier qu'il y a assez de messages
            if len(result["messages"]) >= 2:
                reply = {"role": "assistant", "content": result["messages"][-2].content}
                feedback = {"role": "assistant", "content": result["messages"][-1].content}
            else:
                reply = {"role": "assistant", "content": result["messages"][-1].content if result["messages"] else "Erreur: aucune réponse générée"}
                feedback = {"role": "assistant", "content": "Recherche terminée avec des difficultés techniques"}
            
            return history + [user, reply, feedback]
            
        except Exception as e:
            # Gestion des erreurs de format de message ou autres erreurs LangChain
            error_msg = str(e)
            if "tool_calls" in error_msg and "tool_call_id" in error_msg:
                error_response = "Erreur technique lors de l'utilisation des outils de recherche. Veuillez reformuler votre demande ou essayer une recherche plus simple."
            else:
                error_response = f"Erreur lors de la recherche: {error_msg}"
            
            user = {"role": "user", "content": message}
            reply = {"role": "assistant", "content": error_response}
            feedback = {"role": "assistant", "content": "La recherche a échoué à cause d'un problème technique."}
            return history + [user, reply, feedback]

    def cleanup(self):
        if self.browser:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.browser.close())
                if self.playwright:
                    loop.create_task(self.playwright.stop())
            except RuntimeError:
                # If no loop is running, do a direct run
                asyncio.run(self.browser.close())
                if self.playwright:
                    asyncio.run(self.playwright.stop())
