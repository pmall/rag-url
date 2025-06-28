import os
import lancedb
from google import genai
from pydantic_ai import Agent
from rag_url.prompts import AGENT_SYSTEM_PROMPT


class RagAgent:
    def __init__(self, dbfile: str, collection: str):
        self.db = lancedb.connect(dbfile)
        self.collection = collection
        self.agent = Agent(
            model="gemini-2.0-flash", system_prompt=AGENT_SYSTEM_PROMPT()
        )
        self.register_tools()

    def register_tools(self):
        @self.agent.tool_plain
        def query_knowledge_base(query: str) -> str:
            """Query the knowledge base to find relevant information."""
            return self.query_knowledge_base(query)

    def _embed_content(self, text: str):
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        GEMINI_EMBED_MODEL_NAME = os.getenv(
            "GEMINI_EMBED_MODEL_NAME", "text-embedding-004"
        )

        if not GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY env var must be defined")

        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.embed_content(
            model=GEMINI_EMBED_MODEL_NAME,
            contents=text,
        )

        if not response.embeddings:
            raise Exception("Unable to embed content")

        return response.embeddings[0].values

    def query_knowledge_base(self, query: str) -> str:
        print(f"[TOOL] Searching knowledge base for: {query}")
        embedding = self._embed_content(query)

        tbl = self.db.open_table(self.collection)

        results = tbl.search(embedding).limit(5).to_list()

        context = ""
        for r in results:
            context += f"Source URL: {r['url']}\n"
            context += f"Content: {r['text']}\n"
            if r["code"]:
                context += f"Code Example:\n```\n{r['code']}\n```\n"
            context += "---\n"

        return context

    def run(self):
        """Run the chat loop"""
        print("RAG Agent Chat")
        print("Type '/quit' or '/exit' or '/q' to stop")
        print("-" * 40)

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if user_input.lower() in ["/quit", "/exit", "/q"]:
                    print("Goodbye!")
                    break

                if not user_input:
                    continue

                print("\nAgent: ", end="")
                result = self.agent.run_sync(user_input)

                # Simple output - just print the response data
                if hasattr(result, "data"):
                    print(result.output)
                else:
                    print(result)

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
                continue
