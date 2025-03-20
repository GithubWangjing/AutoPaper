import os
import json
import logging
from datetime import datetime
from .base_agent import BaseAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommunicationAgent(BaseAgent):
    """Agent responsible for facilitating communication between other agents.
    
    This agent acts as a central hub for communication, tracking conversations 
    between agents and enabling them to share information directly.
    """

    def __init__(self, model_type="siliconflow", custom_model_config=None):
        """Initialize the communication agent.
        
        Args:
            model_type: Type of model to use for text generation
            custom_model_config: Custom model configuration for custom model types
        """
        super().__init__(model_type=model_type, custom_model_config=custom_model_config)
        self.name = "Communication Agent"
        self.description = "Facilitates communication between agents"
        self.conversations = {}  # Stores conversation history between agents
        self.agent_states = {}   # Tracks the current state of each agent

    def register_agent(self, agent_id, agent_type, description=None):
        """Register a new agent in the communication network.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent (research, writing, review, etc.)
            description: Optional description of the agent's role
        
        Returns:
            Boolean indicating success
        """
        if agent_id not in self.agent_states:
            self.agent_states[agent_id] = {
                "type": agent_type,
                "description": description or f"{agent_type.capitalize()} Agent",
                "status": "idle",
                "last_active": datetime.now().isoformat()
            }
            logger.info(f"Registered new agent: {agent_id} ({agent_type})")
            return True
        else:
            logger.warning(f"Agent {agent_id} already registered")
            return False

    def send_message(self, sender_id, recipient_id, message, message_type="information"):
        """Send a message from one agent to another.
        
        Args:
            sender_id: ID of the sending agent
            recipient_id: ID of the receiving agent
            message: Content of the message
            message_type: Type of message (information, question, response, etc.)
        
        Returns:
            Dict with conversation ID and success status
        """
        # Validate sender and recipient
        if sender_id not in self.agent_states:
            logger.error(f"Unknown sender: {sender_id}")
            return {"success": False, "error": "Unknown sender"}
            
        if recipient_id not in self.agent_states:
            logger.error(f"Unknown recipient: {recipient_id}")
            return {"success": False, "error": "Unknown recipient"}
        
        # Create conversation ID if this is a new conversation
        conv_id = f"{sender_id}_{recipient_id}"
        alt_conv_id = f"{recipient_id}_{sender_id}"
        
        # Check if there's an existing conversation in the reverse direction
        if alt_conv_id in self.conversations and conv_id not in self.conversations:
            conv_id = alt_conv_id
        
        # Create or update conversation
        timestamp = datetime.now().isoformat()
        
        if conv_id not in self.conversations:
            self.conversations[conv_id] = {
                "participants": [sender_id, recipient_id],
                "started": timestamp,
                "messages": []
            }
        
        # Add message to conversation
        message_obj = {
            "id": len(self.conversations[conv_id]["messages"]) + 1,
            "sender": sender_id,
            "recipient": recipient_id,
            "content": message,
            "type": message_type,
            "timestamp": timestamp
        }
        
        self.conversations[conv_id]["messages"].append(message_obj)
        self.conversations[conv_id]["updated"] = timestamp
        
        # Update agent states
        self.agent_states[sender_id]["last_active"] = timestamp
        self.agent_states[sender_id]["status"] = "sent_message"
        self.agent_states[recipient_id]["status"] = "received_message"
        
        logger.info(f"Message sent from {sender_id} to {recipient_id}")
        return {
            "success": True, 
            "conversation_id": conv_id,
            "message_id": message_obj["id"]
        }

    def get_conversation(self, conversation_id):
        """Retrieve a specific conversation by ID.
        
        Args:
            conversation_id: ID of the conversation to retrieve
            
        Returns:
            Dict containing conversation data or error
        """
        if conversation_id in self.conversations:
            return {
                "success": True,
                "conversation": self.conversations[conversation_id]
            }
        else:
            return {
                "success": False,
                "error": f"Conversation {conversation_id} not found"
            }

    def get_agent_conversations(self, agent_id):
        """Get all conversations involving a specific agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of conversation summaries
        """
        if agent_id not in self.agent_states:
            return {"success": False, "error": f"Unknown agent: {agent_id}"}
        
        agent_conversations = []
        
        for conv_id, conv in self.conversations.items():
            if agent_id in conv["participants"]:
                # Create a summary of this conversation
                other_participant = conv["participants"][0] if conv["participants"][0] != agent_id else conv["participants"][1]
                
                # Count messages from and to this agent
                messages_sent = sum(1 for msg in conv["messages"] if msg["sender"] == agent_id)
                messages_received = sum(1 for msg in conv["messages"] if msg["recipient"] == agent_id)
                
                # Get the most recent message
                latest_message = conv["messages"][-1] if conv["messages"] else None
                
                agent_conversations.append({
                    "conversation_id": conv_id,
                    "with_agent": other_participant,
                    "with_agent_type": self.agent_states[other_participant]["type"],
                    "messages_count": len(conv["messages"]),
                    "messages_sent": messages_sent,
                    "messages_received": messages_received,
                    "started": conv["started"],
                    "updated": conv.get("updated", conv["started"]),
                    "latest_message": latest_message
                })
        
        return {
            "success": True,
            "agent_id": agent_id,
            "conversations": agent_conversations
        }

    def process(self, request_type, **kwargs):
        """Process different types of communication requests.
        
        Args:
            request_type: Type of request (register, send_message, get_conversation, etc.)
            **kwargs: Additional arguments specific to the request type
            
        Returns:
            Result of the requested operation
        """
        self.progress = 10
        
        try:
            if request_type == "register_agent":
                result = self.register_agent(
                    kwargs.get("agent_id"), 
                    kwargs.get("agent_type"),
                    kwargs.get("description")
                )
            
            elif request_type == "send_message":
                result = self.send_message(
                    kwargs.get("sender_id"),
                    kwargs.get("recipient_id"),
                    kwargs.get("message"),
                    kwargs.get("message_type", "information")
                )
            
            elif request_type == "get_conversation":
                result = self.get_conversation(kwargs.get("conversation_id"))
            
            elif request_type == "get_agent_conversations":
                result = self.get_agent_conversations(kwargs.get("agent_id"))
            
            elif request_type == "get_all_agents":
                result = {
                    "success": True,
                    "agents": self.agent_states
                }
                
            elif request_type == "generate_summary":
                # Generate a summary of communications using LLM
                result = self._generate_communication_summary(
                    kwargs.get("agent_id"),
                    kwargs.get("topic")
                )
            
            else:
                result = {
                    "success": False,
                    "error": f"Unknown request type: {request_type}"
                }
            
            self.progress = 100
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Error processing communication request: {str(e)}")
            self.progress = 100
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def _generate_communication_summary(self, agent_id=None, topic=None):
        """Generate a summary of communications using the LLM.
        
        Args:
            agent_id: Optional ID of agent to focus on
            topic: Optional topic to provide context
            
        Returns:
            Generated summary
        """
        # Gather data to summarize
        if agent_id:
            # Get conversations for specific agent
            conv_data = self.get_agent_conversations(agent_id)
            if not conv_data.get("success", False):
                return conv_data
            
            conversations = conv_data.get("conversations", [])
            agent_type = self.agent_states[agent_id]["type"] if agent_id in self.agent_states else "unknown"
            
            # Build prompt for the specific agent
            system_prompt = "You are a communication specialist summarizing interactions between AI agents."
            user_prompt = f"""
            Summarize the communication patterns for the {agent_type} agent with ID '{agent_id}'.
            
            This agent has participated in {len(conversations)} conversations.
            
            Communication statistics:
            - Total messages sent: {sum(c.get('messages_sent', 0) for c in conversations)}
            - Total messages received: {sum(c.get('messages_received', 0) for c in conversations)}
            
            The agent has communicated with:
            {', '.join(f"{c.get('with_agent_type', 'unknown')} agent" for c in conversations)}
            
            {f'These communications are related to the topic: {topic}' if topic else ''}
            
            Please provide a brief summary of this agent's communication patterns and effectiveness.
            """
        else:
            # Summarize all communications
            system_prompt = "You are a communication specialist summarizing interactions between AI agents."
            user_prompt = f"""
            Summarize the overall communication patterns between all agents.
            
            Number of agents: {len(self.agent_states)}
            Number of conversations: {len(self.conversations)}
            
            Agent types involved:
            {', '.join(f"{a_data.get('type', 'unknown')}" for a_id, a_data in self.agent_states.items())}
            
            {f'These communications are related to the topic: {topic}' if topic else ''}
            
            Please provide a brief summary of the overall communication patterns, highlighting any trends, 
            bottlenecks, or suggestions for improving communication flow.
            """
        
        # Call LLM for summary
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        self.progress = 50
        summary = self._make_api_call(messages)
        self.progress = 100
        
        return {
            "success": True,
            "summary": summary,
            "agent_id": agent_id,
            "topic": topic
        }

    def facilitate_collaboration(self, topic, agents, max_rounds=3):
        """Facilitate structured collaboration between multiple agents.
        
        Args:
            topic: The topic being worked on
            agents: Dict mapping agent IDs to their agent objects
            max_rounds: Maximum number of collaboration rounds
            
        Returns:
            Collaboration result summary
        """
        logger.info(f"Starting facilitated collaboration on topic: {topic}")
        self.progress = 10
        
        try:
            # Register all agents if they aren't already
            for agent_id, agent in agents.items():
                if agent_id not in self.agent_states:
                    self.register_agent(agent_id, agent.name.lower().replace(" agent", ""))
            
            collaboration_rounds = []
            
            # Run the collaboration for a specified number of rounds
            for round_num in range(1, max_rounds + 1):
                logger.info(f"Starting collaboration round {round_num}/{max_rounds}")
                
                round_results = {
                    "round": round_num,
                    "messages": [],
                    "outcomes": {}
                }
                
                # Each agent gets a turn in this round
                for agent_id, agent in agents.items():
                    # Get relevant previous messages for this agent
                    agent_convs = self.get_agent_conversations(agent_id)
                    
                    # Create a context message for this agent
                    context = f"Round {round_num}/{max_rounds} - Your task is to contribute to the topic: {topic}"
                    
                    if round_num > 1:
                        # Add summary of previous communications
                        context += "\n\nPrevious collaboration context:\n"
                        for prev_round in collaboration_rounds:
                            if agent_id in prev_round["outcomes"]:
                                context += f"\nYour contribution in round {prev_round['round']}: {prev_round['outcomes'][agent_id]}\n"
                    
                    # Each agent sends a message to every other agent
                    for recipient_id, recipient in agents.items():
                        if recipient_id != agent_id:
                            # Generate a message for this recipient
                            message_prompt = [
                                {"role": "system", "content": f"You are the {agent.name} communicating with the {recipient.name}."},
                                {"role": "user", "content": f"{context}\n\nBased on your role and expertise, what information, questions, or suggestions would you share with the {recipient.name}?"}
                            ]
                            
                            self.progress = 30 + (round_num * 10)
                            message_content = self._make_api_call(message_prompt)
                            
                            # Send the message
                            message_result = self.send_message(
                                agent_id,
                                recipient_id,
                                message_content,
                                "collaboration"
                            )
                            
                            round_results["messages"].append({
                                "from": agent_id,
                                "to": recipient_id,
                                "content": message_content
                            })
                    
                    # Each agent produces an outcome for this round
                    outcome_prompt = [
                        {"role": "system", "content": f"You are the {agent.name} participating in a collaborative project."},
                        {"role": "user", "content": f"{context}\n\nBased on your role and the communications in this round, summarize your key contribution or findings related to the topic: {topic}"}
                    ]
                    
                    self.progress = 50 + (round_num * 10)
                    outcome = self._make_api_call(outcome_prompt)
                    round_results["outcomes"][agent_id] = outcome
                
                collaboration_rounds.append(round_results)
                logger.info(f"Completed collaboration round {round_num}/{max_rounds}")
            
            # Generate final collaboration summary
            summary_prompt = [
                {"role": "system", "content": "You are a collaboration specialist summarizing the outcomes of a multi-agent collaboration."},
                {"role": "user", "content": f"Summarize the collaborative work on the topic: {topic}\n\n" + 
                                          f"The collaboration involved {len(agents)} agents over {max_rounds} rounds.\n\n" +
                                          "Provide a synthesis of the key outcomes, areas of agreement, and any unresolved questions or next steps."}
            ]
            
            self.progress = 90
            collaboration_summary = self._make_api_call(summary_prompt)
            
            self.progress = 100
            logger.info(f"Completed facilitated collaboration on topic: {topic}")
            
            return {
                "success": True,
                "topic": topic,
                "rounds": collaboration_rounds,
                "summary": collaboration_summary
            }
            
        except Exception as e:
            logger.error(f"Error in facilitated collaboration: {str(e)}")
            self.progress = 100
            return {
                "success": False,
                "error": str(e)
            } 