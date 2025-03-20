import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class SupervisorAgent(BaseAgent):
    """Supervisor Agent that coordinates and monitors interactions between other agents.
    
    The supervisor agent is responsible for:
    1. Task allocation between research, writing, and review agents
    2. Evaluating feedback from the review agent
    3. Managing the iterative improvement process
    """
    
    def __init__(self, model_type="siliconflow", custom_model_config=None):
        """Initialize the supervisor agent.
        
        Args:
            model_type: The model type to use for the agent
            custom_model_config: Custom model configuration if needed
        """
        super().__init__(model_type, custom_model_config)
        
        # Add name and description attributes
        self.name = "Supervisor Agent"
        self.description = "Coordinates and monitors interactions between other agents"
        
        # Track the iteration round
        self.iteration_round = 0
        
    def process(self, topic, research_result=None, paper_draft=None, review_feedback=None):
        """Decide on the next action to take in the multi-agent workflow.
        
        Args:
            topic: The paper topic
            research_result: Results from the research agent (if available)
            paper_draft: Draft from the writing agent (if available)
            review_feedback: Feedback from the review agent (if available)
            
        Returns:
            Dictionary with the supervisor's decision and reasoning
        """
        self.progress = 10
        
        # Determine which stage we're at based on available inputs
        if research_result is None:
            # Initial stage, assign research task
            return self._assign_research_task(topic)
        elif paper_draft is None:
            # Research complete, assign writing task
            return self._assign_writing_task(topic, research_result)
        elif review_feedback is None:
            # Draft complete, assign review task
            return self._assign_review_task(topic, paper_draft)
        else:
            # Review feedback received, evaluate it
            return self._evaluate_review_feedback(topic, paper_draft, review_feedback)
    
    def _assign_research_task(self, topic):
        """Assign the research task to the research agent."""
        system_prompt = "You are a supervisor agent coordinating a multi-agent workflow to produce a high-quality academic paper."
        user_prompt = f"""
        You are initiating a multi-agent workflow to produce an academic paper on the topic: "{topic}".
        
        Please provide detailed instructions for the research agent who will be collecting relevant literature and information.
        
        Your instructions should include:
        1. The key aspects of the topic to focus on
        2. Types of sources that would be most valuable
        3. What kind of information would be most useful for the writing phase
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        self.progress = 50
        instructions = self._make_api_call(messages)
        self.progress = 100
        
        return {
            "action": "research",
            "instructions": instructions,
            "reasoning": "Starting workflow with research phase to gather relevant literature."
        }
    
    def _assign_writing_task(self, topic, research_result):
        """Assign the writing task to the writing agent."""
        system_prompt = "You are a supervisor agent coordinating a multi-agent workflow to produce a high-quality academic paper."
        user_prompt = f"""
        You have received research results related to the topic: "{topic}".
        
        Research summary:
        ```
        {research_result[:1500]}  # Limit size to avoid token limits
        ```
        
        Please provide detailed instructions for the writing agent who will be drafting the paper.
        
        Your instructions should include:
        1. Suggested structure for the paper
        2. Important points that should be highlighted based on the research
        3. Any stylistic preferences or academic standards to follow
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        self.progress = 50
        instructions = self._make_api_call(messages)
        self.progress = 100
        
        return {
            "action": "write",
            "instructions": instructions,
            "reasoning": "Research phase complete, moving to writing phase to draft the paper."
        }
    
    def _assign_review_task(self, topic, paper_draft):
        """Assign the review task to the review agent."""
        system_prompt = "You are a supervisor agent coordinating a multi-agent workflow to produce a high-quality academic paper."
        user_prompt = f"""
        A draft paper on the topic: "{topic}" has been written.
        
        Draft excerpt:
        ```
        {paper_draft[:1500]}  # Limit size to avoid token limits
        ```
        
        Please provide detailed instructions for the review agent who will be evaluating this draft.
        
        Your instructions should include:
        1. Key aspects to evaluate (structure, clarity, argumentation, evidence, etc.)
        2. How to present constructive feedback that the writing agent can use to improve the paper
        3. The format in which the feedback should be provided
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        self.progress = 50
        instructions = self._make_api_call(messages)
        self.progress = 100
        
        return {
            "action": "review",
            "instructions": instructions,
            "reasoning": "Writing phase complete, moving to review phase to evaluate the draft."
        }
    
    def _evaluate_review_feedback(self, topic, paper_draft, review_feedback):
        """Evaluate the review feedback and decide next steps."""
        self.iteration_round += 1
        
        system_prompt = "You are a supervisor agent coordinating a multi-agent workflow to produce a high-quality academic paper."
        user_prompt = f"""
        You are at iteration {self.iteration_round} of the paper development process for the topic: "{topic}".
        
        The review agent has provided feedback on the current draft.
        
        Paper draft excerpt:
        ```
        {paper_draft[:1000]}  # Limit size to avoid token limits
        ```
        
        Review feedback:
        ```
        {review_feedback[:1500]}  # Limit size to avoid token limits
        ```
        
        Please evaluate the review feedback and decide on the next steps:
        
        1. Is the feedback constructive, specific, and actionable? (Yes/No)
        2. Does the feedback address substantive issues in the paper? (Yes/No)
        3. Would implementing this feedback improve the paper? (Yes/No)
        
        Based on your evaluation, decide whether to:
        A. Accept the feedback and instruct the writing agent to revise the paper
        B. Reject the feedback and ask the review agent to provide better feedback
        C. Consider the paper complete if the feedback is minor and the paper is of high quality
        
        Provide your decision with detailed reasoning.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        self.progress = 50
        evaluation = self._make_api_call(messages)
        self.progress = 100
        
        # Extract decision from evaluation
        if "Accept the feedback" in evaluation or "accept the feedback" in evaluation:
            decision = "revise"
            action = "write"
        elif "Reject the feedback" in evaluation or "reject the feedback" in evaluation:
            decision = "reject_feedback"
            action = "review"
        else:
            decision = "complete"
            action = "complete"
        
        return {
            "action": action,
            "decision": decision,
            "evaluation": evaluation,
            "iteration": self.iteration_round,
            "reasoning": f"Evaluation complete, decided to {decision} in iteration {self.iteration_round}."
        }
    
    def test_connection(self):
        """Test the connection to the model API."""
        system_prompt = "You are a supervisor agent coordinating a multi-agent workflow."
        user_prompt = "Please confirm that you're functioning correctly by responding with a short confirmation."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self._make_api_call(messages)
            if response and not response.startswith("API"):
                return {"status": "success", "message": "Connection to supervisor agent successful", "response": response}
            else:
                return {"status": "error", "message": response}
        except Exception as e:
            return {"status": "error", "message": f"Connection test failed: {str(e)}"} 