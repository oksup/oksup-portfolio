import os
import discord
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tools import CHANNEL_TOOLS, run_task_cli, run_code_cli

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

FUNCTION_MAP = {
    "run_task_cli": run_task_cli,
    "run_code_cli": run_code_cli
}

CHANNEL_MODELS = {
    "tasks": "gemini-3.5-flash-lite",
    "code": "gemini-3.6-flash"
}

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    channel_name = message.channel.name
    tools = CHANNEL_TOOLS.get(channel_name)

    if not tools:
        return

    selected_model = CHANNEL_MODELS.get(channel_name, "gemini-3.5-flash-lite")

    async with message.channel.typing():
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=message.content)])]
        
        for _ in range(5):
            response = client.models.generate_content(
                model=selected_model,
                contents=contents,
                config=types.GenerateContentConfig(tools=tools)
            )

            if response.function_calls:
                contents.append(response.candidates[0].content)
                tool_responses = []
                
                for call in response.function_calls:
                    func = FUNCTION_MAP.get(call.name)
                    result = func(**call.args) if func else "Function not found"
                    
                    tool_responses.append(
                        types.Part.from_function_response(
                            name=call.name,
                            response={"result": result}
                        )
                    )

                    # Auto-handoff: If a task was created in #tasks, trigger #code automatically
                    if call.name == "run_task_cli" and call.args.get("action") == "create":
                        task_title = call.args.get("title", "")
                        code_channel = discord.utils.get(message.guild.text_channels, name="code")
                        
                        if code_channel:
                            await code_channel.send(f"Auto-pilot: Starting code execution for task '{task_title}'")
                            code_result = run_code_cli(f"Build code for task: {task_title}")
                            await code_channel.send(f"Code Agent Output:\n```{code_result}```")

                contents.append(types.Content(role="user", parts=tool_responses))
            else:
                await message.reply(response.text)
                break

bot.run(DISCORD_TOKEN)
