import os
import re
import logging
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands, tasks
import httpx
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("devops-copilot-bot")

# Load environment variables
load_dotenv(dotenv_path="../.env")
load_dotenv()  # Fallback to current dir

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

class DevOpsCopilotBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        # Slash commands don't require privileged intents
        super().__init__(command_prefix="!", intents=intents)
        self.alerted_pods = {}
        
    async def setup_hook(self):
        logger.info("Starting background SRE alert monitor loop...")
        self.check_sre_alerts.start()
        
        logger.info("Syncing slash commands globally...")
        try:
            synced = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced)} slash commands.")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {str(e)}")

    @tasks.loop(minutes=5)
    async def check_sre_alerts(self):
        alert_channel_id = os.getenv("DISCORD_ALERT_CHANNEL_ID")
        if not alert_channel_id or alert_channel_id == "your_discord_channel_id_here":
            return
            
        try:
            channel = self.get_channel(int(alert_channel_id))
            if not channel:
                channel = await self.fetch_channel(int(alert_channel_id))
                
            if not channel:
                logger.warning(f"Could not locate alert channel with ID: {alert_channel_id}")
                return
                
            logger.info("Executing proactive SRE health checks on discovered deployments...")
            async with httpx.AsyncClient(timeout=20.0) as client:
                # Dynamic service discovery
                try:
                    deploy_resp = await client.get(f"{BACKEND_API_URL}/deployments")
                    if deploy_resp.status_code == 200:
                        services = deploy_resp.json()
                        logger.info(f"Dynamically discovered deployments: {services}")
                    else:
                        logger.warning(f"Failed to fetch deployments from API ({deploy_resp.status_code}). Using static fallback.")
                        services = ["payment-service", "auth-service", "analytics-service", "frontend-service"]
                except Exception as e:
                    logger.error(f"Deployments discovery request failed: {str(e)}. Using static fallback.")
                    services = ["payment-service", "auth-service", "analytics-service", "frontend-service"]

                for svc in services:
                    # Ignore the bot and backend themselves if they show up in deployment list
                    if svc in ["sre-backend", "sre-discord-bot"]:
                        continue

                    # Use lightweight /pod-status (NO Gemini API calls) instead of /diagnose
                    resp = await client.get(f"{BACKEND_API_URL}/pod-status/{svc}")
                    if resp.status_code == 200:
                        pod_data = resp.json()
                        pods = pod_data.get("pods", [])
                        
                        # Handle case where pods is a dictionary/error object
                        if not isinstance(pods, list):
                            continue

                        for p in pods:
                            status_lower = p["status"].lower()
                            # Alert on common failing states
                            if status_lower in ["crashloopbackoff", "oomkilled", "error", "failed", "imagepullbackoff", "backoff"]:
                                # Avoid repeating alert if state hasn't changed
                                if self.alerted_pods.get(p["name"]) != p["status"]:
                                    self.alerted_pods[p["name"]] = p["status"]
                                    
                                    embed = discord.Embed(
                                        title=f"🚨 SRE ALERT: Unhealthy Pod in `{svc}`!",
                                        description=f"An active cluster incident has been detected in the service **`{svc}`**.\nRun `/diagnose {svc}` for full AI root cause analysis.",
                                        color=discord.Color.from_rgb(203, 67, 53)  # Vibrant Crimson Red
                                    )
                                    embed.add_field(name="📌 Pod Name", value=f"`{p['name']}`", inline=True)
                                    embed.add_field(name="🔴 Status Phase", value=f"**`{p['status']}`**", inline=True)
                                    embed.add_field(name="🔄 Restarts", value=f"`{p['restart_count']}`", inline=True)
                                    embed.set_footer(text="SRE DevOps Alerts System • Use /diagnose for full AI analysis")
                                    await channel.send(embed=embed)
                                    
                            elif status_lower == "running" and p["name"] in self.alerted_pods:
                                # Recovered!
                                del self.alerted_pods[p["name"]]
                                embed = discord.Embed(
                                    title=f"🟢 SRE RECOVERY: Pod `{p['name']}` is Healthy!",
                                    description=f"Service **`{svc}`** pod has successfully returned to standard **Running** state.",
                                    color=discord.Color.from_rgb(39, 174, 96)  # Emerald Green
                                )
                                embed.add_field(name="📌 Pod Name", value=f"`{p['name']}`", inline=True)
                                embed.add_field(name="Status", value="🟢 **Running**", inline=True)
                                embed.set_footer(text="SRE DevOps Alerts System • Restored State")
                                await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in SRE Alerts background task: {str(e)}")

    @check_sre_alerts.before_loop
    async def before_check_sre_alerts(self):
        await self.wait_until_ready()

    async def on_ready(self):
        logger.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        logger.info("DevOps SRE Copilot Bot is ready.")
        # Set Discord rich presence activity
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="infrastructure and logs"
        ))

bot = DevOpsCopilotBot()

# Helper to truncate text to fit Discord's limits (embed description max: 4096, field value max: 1024)
def truncate_text(text: str, limit: int = 1000) -> str:
    if len(text) > limit:
        return text[:limit - 3] + "..."
    return text

# ==================== BOT SLASH COMMANDS ====================

@bot.tree.command(name="help", description="Displays helpful usage information for SRE DevOps Copilot.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 AI DevOps SRE Copilot - Help Guide",
        description="I am an AI SRE Assistant that parses cluster logs, analyzes metrics, searches runbooks, and conducts root-cause investigations.",
        color=discord.Color.from_rgb(26, 82, 118)  # Steel Blue
    )
    
    embed.add_field(
        name="🔍 SRE Operations",
        value=(
            "**/diagnose `[service]`** - Performs multi-agent LangGraph diagnostics on a service (e.g. `payment-service`)\n"
            "**/logs `[service]`** - Fetches recent logs from Kubernetes pods of the service\n"
            "**/explain-error `[error]`** - Explains a custom stack trace or log entry, detailing causes & remedies"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📚 Knowledge & Runbooks",
        value=(
            "**/ask `[question]`** - Ask a general SRE/DevOps question utilizing internal runbook contexts\n"
            "**/search-docs `[query]`** - Searches the RAG vector store for relevant runbooks and files"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ System Health",
        value="**/status** - Checks API connectivity, ChromaDB, and Gemini API keys config status",
        inline=False
    )

    embed.set_footer(text="DevOps Copilot • Powered by LangGraph & Gemini 2.5 Flash")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="status", description="Checks the health and status of the Copilot system services.")
async def status_command(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_API_URL}/health")
            
        if resp.status_code == 200:
            data = resp.json()
            api_status = "🟢 Healthy"
            chroma_status = "🟢 Healthy" if data.get("chromadb") == "Healthy" else "🔴 Unhealthy"
            gemini_status = "🟢 Configured" if data.get("api_key_configured") else "🟡 Not Configured (Fallbacks Active)"
            
            embed = discord.Embed(
                title="⚙️ SRE Copilot System Status",
                color=discord.Color.green()
            )
            embed.add_field(name="FastAPI Backend", value=api_status, inline=True)
            embed.add_field(name="ChromaDB Vector DB", value=chroma_status, inline=True)
            embed.add_field(name="Gemini 2.5 Flash AI", value=gemini_status, inline=False)
            embed.set_footer(text=f"Connected to Backend: {BACKEND_API_URL}")
        else:
            raise Exception(f"Backend returned HTTP {resp.status_code}")
            
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        embed = discord.Embed(
            title="⚙️ SRE Copilot System Status",
            description="Could not connect to SRE Backend services.",
            color=discord.Color.red()
        )
        embed.add_field(name="FastAPI Backend", value="🔴 Unreachable", inline=True)
        embed.add_field(name="ChromaDB Vector DB", value="⚪ Unknown", inline=True)
        embed.set_footer(text=f"Target URL: {BACKEND_API_URL}")

    await interaction.followup.send(embed=embed)


def parse_timeframe(tf_str: str) -> int:
    tf_str = tf_str.lower().strip()
    if not tf_str:
        return 3600  # Default to 1 hour
    
    match = re.match(r"^(\d+)\s*([mhdw])$", tf_str)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if unit == 'm':
            return val * 60
        elif unit == 'h':
            return val * 3600
        elif unit == 'd':
            return val * 86400
        elif unit == 'w':
            return val * 604800
            
    try:
        return int(tf_str)
    except ValueError:
        pass
        
    return 3600

@bot.tree.command(name="logs", description="Fetches recent pod log output for a Kubernetes service.")
@app_commands.describe(
    service="Name of the service",
    query="Optional keyword search filter (e.g. ERROR)",
    timeframe="Time range to look back (e.g., 30m, 2h, 3d, 1w). Default: 1h"
)
async def logs_command(interaction: discord.Interaction, service: str, query: Optional[str] = None, timeframe: str = "1h"):
    await interaction.response.defer()
    
    since_seconds = parse_timeframe(timeframe)
    
    try:
        params = {
            "since_seconds": since_seconds
        }
        if query:
            params["query"] = query
            
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BACKEND_API_URL}/logs/{service}", params=params)
            
        if resp.status_code == 200:
            data = resp.json()
            raw_logs = data.get("logs", "")
            
            if not raw_logs.strip():
                await interaction.followup.send(
                    content=f"📝 **Log search result for `{service}`** (timeframe: `{timeframe}`, filter: `{query}`):\n```\nNo logs matched your search criteria.\n```"
                )
                return
            
            if raw_logs.startswith("[ERROR]"):
                await interaction.followup.send(
                    content=f"❌ **Failed to retrieve logs for `{service}`**:\n```\n{raw_logs}\n```"
                )
                return
                
            truncated_logs = truncate_text(raw_logs, 1900)
            await interaction.followup.send(
                content=f"📝 **Logs for service `{service}`** (timeframe: `{timeframe}`, filter: `{query}`):\n```log\n{truncated_logs}\n```"
            )
        else:
            await interaction.followup.send(
                content=f"❌ Failed to fetch logs for service `{service}`: Backend returned status code {resp.status_code}."
            )
    except Exception as e:
        logger.error(f"Logs retrieval failed: {str(e)}")
        await interaction.followup.send(
            content=f"❌ Network error: Could not reach the backend API at {BACKEND_API_URL}."
        )


@bot.tree.command(name="diagnose", description="Runs the AI multi-agent diagnosis workflow on a cluster service.")
@app_commands.describe(service="The Kubernetes service name to diagnose (e.g., payment-service)")
async def diagnose_command(interaction: discord.Interaction, service: str):
    # Defer is critical: SRE analysis graph can take 5-15 seconds to execute
    await interaction.response.defer()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{BACKEND_API_URL}/diagnose",
                json={"service_name": service}
            )
            
        if resp.status_code == 200:
            report = resp.json()
            
            # Extract basic pod states
            pod_data = report.get("pod_status", {})
            pods_list = pod_data.get("pods", [])
            pod_status_str = "No pods found."
            if pods_list:
                pod_details = []
                for p in pods_list:
                    pod_details.append(f"• `{p['name']}`: **{p['status']}** ({p['ready']} Ready, {p['restart_count']} restarts)")
                pod_status_str = "\n".join(pod_details)
                
            # Determine color based on confidence & failure status
            color = discord.Color.red() if "unhealthy" in report.get("metrics_analysis", "").lower() or report.get("confidence_score", 0.0) > 0.8 else discord.Color.orange()
            if report.get("confidence_score", 0.0) < 0.6:
                color = discord.Color.gold()
            
            embed = discord.Embed(
                title=f"🔍 AI SRE Incident Report: `{service}`",
                description=f"Confidence Score: **{int(report.get('confidence_score', 0.0) * 100)}%**",
                color=color
            )
            
            embed.add_field(name="📍 Kubernetes Pod Status", value=pod_status_str, inline=False)
            embed.add_field(name="🪵 Log Analysis Summary", value=truncate_text(report.get("log_analysis", "No anomalies"), 1000), inline=False)
            embed.add_field(name="📊 Metrics Anomaly Detection", value=truncate_text(report.get("metrics_analysis", "Normal"), 1000), inline=False)
            embed.add_field(name="🕵️ Root Cause Diagnosis", value=truncate_text(report.get("root_cause", "Undetermined"), 1000), inline=False)
            embed.add_field(name="🛠️ Actionable Remediation steps", value=truncate_text(report.get("recommendations", "Check baseline"), 1000), inline=False)
            
            embed.set_footer(text=f"RAG Runbook Search: {'✅ Matched & Applied' if report.get('runbook_matched') else '❌ No Matching Runbook Found'}")
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                content=f"❌ SRE Diagnosis failed: Backend returned status code {resp.status_code}."
            )
            
    except Exception as e:
        logger.error(f"Diagnosis command execution failed: {str(e)}")
        await interaction.followup.send(
            content=f"❌ Network error: Unable to contact the SRE API backend at {BACKEND_API_URL}."
        )


@bot.tree.command(name="explain-error", description="Explains a log error message or stack trace.")
@app_commands.describe(error="The error text or log entry to explain")
async def explain_error_command(interaction: discord.Interaction, error: str):
    await interaction.response.defer()
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{BACKEND_API_URL}/explain-error",
                json={"error_message": error}
            )
            
        if resp.status_code == 200:
            data = resp.json()
            
            embed = discord.Embed(
                title="🕵️ Error Diagnostic Breakdown",
                color=discord.Color.dark_red()
            )
            
            embed.add_field(name="Explanation", value=truncate_text(data.get("explanation", ""), 1000), inline=False)
            
            causes_str = "\n".join([f"{i+1}. {cause}" for i, cause in enumerate(data.get("potential_causes", []))])
            embed.add_field(name="Possible Causes", value=truncate_text(causes_str, 1000), inline=False)
            
            remediations_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(data.get("reremediation_steps", data.get("remediation_steps", [])))])
            embed.add_field(name="Suggested Remediation", value=truncate_text(remediations_str, 1000), inline=False)
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                content=f"❌ Error analysis failed: Backend returned status {resp.status_code}."
            )
    except Exception as e:
        logger.error(f"Explain error command execution failed: {str(e)}")
        await interaction.followup.send(
            content=f"❌ Network error: Unable to connect to the backend SRE service."
        )


@bot.tree.command(name="search-docs", description="Searches SRE runbooks for relevant documentation.")
@app_commands.describe(query="Topic or query to search (e.g. database connection timeout)")
async def search_docs_command(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{BACKEND_API_URL}/search-docs",
                json={"query": query, "limit": 3}
            )
            
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            
            if not results:
                await interaction.followup.send(content=f"🔍 No documentation found matching: `{query}`.")
                return
                
            embed = discord.Embed(
                title=f"🔍 Runbook Search Results for: `{query}`",
                color=discord.Color.blue()
            )
            
            for index, r in enumerate(results):
                meta = r.get("metadata", {})
                filename = meta.get("filename", f"Doc-{index+1}")
                # Format snippet
                content_snippet = truncate_text(r.get("content", ""), 250)
                distance = r.get("distance", 0.0)
                
                embed.add_field(
                    name=f"📄 {filename} (Distance: {distance:.4f})",
                    value=content_snippet,
                    inline=False
                )
                
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(content="❌ Documentation search failed.")
    except Exception as e:
        logger.error(f"Search docs command failed: {str(e)}")
        await interaction.followup.send(content="❌ Network error: Could not connect to vector search database.")


@bot.tree.command(name="ask", description="Asks the SRE Assistant a general SRE/DevOps question.")
@app_commands.describe(question="SRE question to ask (e.g., How do I troubleshoot an OOMKilled pod?)")
async def ask_command(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                f"{BACKEND_API_URL}/ask",
                json={"question": question}
            )
            
        if resp.status_code == 200:
            data = resp.json()
            
            embed = discord.Embed(
                title=f"💬 SRE Assistant Response",
                color=discord.Color.purple()
            )
            embed.add_field(name="Question", value=truncate_text(question, 200), inline=False)
            embed.add_field(name="Answer", value=truncate_text(data.get("answer", ""), 2000), inline=False)
            
            sources = data.get("sources", [])
            if sources:
                embed.set_footer(text=f"Reference Sources: {', '.join(sources)}")
            else:
                embed.set_footer(text="Reference Sources: General Knowledge")
                
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(content="❌ Failed to retrieve answer from DevOps Copilot SRE pipeline.")
    except Exception as e:
        logger.error(f"Ask command failed: {str(e)}")
        await interaction.followup.send(content="❌ Network error: Could not contact SRE Assistant backend.")


@bot.tree.command(name="history", description="Fetches past SRE diagnostic runs from the database.")
@app_commands.describe(
    service="Optional filter by service name",
    limit="Max number of runs to fetch (default: 5)"
)
async def history_command(interaction: discord.Interaction, service: Optional[str] = None, limit: int = 5):
    await interaction.response.defer()
    
    try:
        params = {"limit": limit}
        if service:
            params["service_name"] = service
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_API_URL}/history", params=params)
            
        if resp.status_code == 200:
            history = resp.json()
            if not history:
                await interaction.followup.send(content="📜 No SRE diagnostic history found in the database.")
                return
                
            embed = discord.Embed(
                title="📜 SRE Diagnostic History Log",
                color=discord.Color.from_rgb(46, 134, 193)  # Lighter Blue
            )
            for item in history:
                timestamp = item.get("timestamp", "Unknown")
                if timestamp != "Unknown" and "T" in timestamp:
                    timestamp = timestamp.split(".")[0].replace("T", " ")
                    
                svc_name = item.get("service_name", "Unknown")
                rc = item.get("root_cause", "No analysis")
                if len(rc) > 150:
                    rc = rc[:147] + "..."
                    
                embed.add_field(
                    name=f"Service: `{svc_name}` • {timestamp}",
                    value=f"**Confidence**: {int(item.get('confidence_score', 0.0) * 100)}%\n**Root Cause**: {rc}",
                    inline=False
                )
            await interaction.followup.send(embed=embed)
        elif resp.status_code == 503:
            await interaction.followup.send(content="❌ History log is unavailable: Database persistence is disabled.")
        else:
            await interaction.followup.send(content=f"❌ Failed to retrieve history: Backend returned status {resp.status_code}.")
    except Exception as e:
        logger.error(f"History command failed: {str(e)}")
        await interaction.followup.send(content="❌ Network error: Could not reach the backend API.")


# Direct execution capability
if __name__ == "__main__":
    if not DISCORD_TOKEN or DISCORD_TOKEN == "your_discord_bot_token_here":
        logger.error("DISCORD_TOKEN is missing or not configured. Cannot launch Discord Bot. Please update .env")
    else:
        logger.info("Starting Discord Bot...")
        bot.run(DISCORD_TOKEN)
