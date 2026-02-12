#!/usr/bin/env python3
"""
Upcoming Space Launch Events Agent

Fetches upcoming space launches from The Space Devs API,
filters for launches with status "Go", generates AI summaries,
and saves them to upcoming_events.json for the React app to consume.
"""

import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path

from config import HF_MODEL, HF_TOKEN, request_timeout
from hf_client import call_hf_api
from launch_data import (
    make_api_request,
    filter_and_enhance_launches,
    load_existing_launches,
    save_launches_to_json,
)

# Configuration
API_URL = "https://ll.thespacedevs.com/2.0.0/launch/upcoming/"
OUTPUT_FILE = "../public/upcoming_events.json"
MAX_EVENTS = 50


class AILaunchSummarizer:
    """AI-powered launch summarizer using Hugging Face API."""

    def __init__(self):
        self.available = False

        if not HF_TOKEN:
            print("❌ HF_TOKEN environment variable not set")
            print("❌ AI model loading failed, continuing without AI summaries")
            return

        try:
            print(f"🤖 Using Hugging Face API with model: {HF_MODEL}")
            print("🔐 Using authenticated Hugging Face access")
            self.available = True
            print(f"✅ AI API access configured successfully!")
        except Exception as e:
            print(f"❌ Failed to configure AI API: {e}")
            print("❌ AI model loading failed, continuing without AI summaries")

    def create_launch_prompt(self, launch_data):
        """Create a structured prompt for the AI model to summarize launch information."""
        name = launch_data.get('name', 'Unknown Launch')
        lsp_name = launch_data.get('lsp_name', 'Unknown Agency')
        lsp_description = launch_data.get('lsp_description', 'Unknown Agency')
        mission_type = launch_data.get('mission_type', '')
        mission_description = launch_data.get('mission_description', '')
        rocket_description = launch_data.get('rocket_config_description', '')
        launch_site = launch_data.get('launch_site', launch_data.get('location', ''))
        rocket_stats = f"({launch_data.get('rocket_config_successful_launches', 0)}/{launch_data.get('rocket_config_total_launch_count', 0)} successful launches)"

        rocket_family = launch_data.get('rocket_config_family', '')
        rocket_manufacturer_name = launch_data.get('rocket_manufacturer_name', '')
        rocket_manufacturer_description = launch_data.get('rocket_manufacturer_description', '')
        rocket_manufacturer_stats = f"({launch_data.get('rocket_manufacturer_successful_launches', 0)}/{launch_data.get('rocket_manufacturer_total_launch_count', 0)} manufacturer successful launches)"

        pad_name = launch_data.get('pad', '')
        orbit = launch_data.get('orbit', '')

        content_to_summarize = f"""
{lsp_name} will launch {name} from {launch_site} using their {rocket_description or 'rocket'}.
This {mission_type} mission involves {mission_description or 'a space mission'} to {orbit or 'orbit'}.
The launch provider {lsp_name} is {lsp_description or 'a space company'}.
The rocket has a track record of {rocket_stats}.
The manufacturer {rocket_manufacturer_name or 'of the rocket'} {rocket_manufacturer_description or 'builds launch vehicles'} with {rocket_manufacturer_stats}.
Launch pad: {pad_name}. Target orbit: {orbit}. Mission type: {mission_type}.
"""
        return content_to_summarize.strip()

    async def generate_summary(self, launch_data, session):
        """Generate an AI summary for a launch using Hugging Face API."""
        if not self.available or not HF_TOKEN:
            return ""

        try:
            prompt = self.create_launch_prompt(launch_data)
            summary = await call_hf_api(session, prompt, max_new_tokens=150, min_length=30)
            return summary.strip() if summary else ""
        except Exception as e:
            print(f"⚠️  AI summarization failed for {launch_data.get('name', 'Unknown')}: {e}")
            return ""


async def fetch_upcoming_launches(session, limit=MAX_EVENTS):
    """Fetch upcoming launches from The Space Devs API."""
    params = {
        'mode': 'list',
        'limit': limit
    }

    data = await make_api_request(
        session,
        API_URL,
        params=params,
        description=f"upcoming launches (limit={limit})"
    )

    if data and 'results' in data:
        print(f"✅ Successfully fetched {len(data.get('results', []))} upcoming launches")
        return data
    else:
        print("❌ No valid data received from API")
        return None


async def enhance_all_launches_with_ai(launches, ai_summarizer, session, existing_launches=None):
    """Enhance launches with AI-generated summaries.

    Only generates new summaries for launches that need them.
    Continues with empty summaries if AI fails.
    """
    if not launches:
        return launches

    existing_launches = existing_launches or {}
    launches_needing_ai = []
    reused_summaries = 0
    new_summaries = 0
    failed_summaries = 0

    for launch in launches:
        if 'ai_summary' not in launch:
            launches_needing_ai.append(launch)
        else:
            reused_summaries += 1

    print(f"🔍 AI Summary Status:")
    print(f"   ♻️  {reused_summaries} launches already have AI summaries (reused)")
    print(f"   🆕 {len(launches_needing_ai)} launches need new AI summaries")

    if launches_needing_ai:
        print(f"🤖 Generating AI summaries for {len(launches_needing_ai)} launches...")

        for i, launch in enumerate(launches_needing_ai):
            launch_name = launch.get('name', 'Unknown')
            print(f"🔄 Processing launch {i+1}/{len(launches_needing_ai)}: {launch_name}")

            if ai_summarizer and ai_summarizer.available:
                try:
                    ai_summary = await ai_summarizer.generate_summary(launch, session)
                    if ai_summary:
                        launch['ai_summary'] = ai_summary
                        new_summaries += 1
                        print(f"   🤖 AI Summary: {ai_summary}")
                    else:
                        launch['ai_summary'] = ""
                        failed_summaries += 1
                        print(f"   ⚠️  AI returned empty summary, saved as empty string")
                except Exception as e:
                    print(f"   ❌ AI summarization failed: {e}")
                    launch['ai_summary'] = ""
                    failed_summaries += 1
                    print(f"   📝 Saved empty AI summary due to error")
            else:
                launch['ai_summary'] = ""
                failed_summaries += 1
                print(f"   📝 AI not available, saved empty summary")

    for launch in launches:
        if 'ai_summary' not in launch:
            launch['ai_summary'] = ""
            failed_summaries += 1

    print(f"✅ AI Summary Results:")
    print(f"   ♻️ {reused_summaries} reused existing summaries")
    print(f"   🆕 {new_summaries} new AI summaries generated")
    print(f"   ⚠️ {failed_summaries} empty summaries (AI failed/unavailable)")
    return launches


async def main():
    """Main function to fetch, filter, and save upcoming launches."""
    print("🚀 Starting Upcoming Launch Events Agent...")
    print(f"📡 Fetching data from: {API_URL}")

    # Initialize AI summarizer
    print("🤖 Initializing AI summarizer...")
    ai_summarizer = AILaunchSummarizer()
    if not ai_summarizer.available:
        print("⚠️ AI summarizer initialization failed, continuing without AI summaries")
        ai_summarizer = None

    # Get the absolute path for the output file
    script_dir = Path(__file__).parent
    output_path = script_dir / OUTPUT_FILE
    output_path = output_path.resolve()

    print(f"💾 Output file: {output_path}")

    # Load existing launches to avoid regenerating AI summaries
    existing_launches = load_existing_launches(output_path)

    # Create HTTP session with extended timeout and connection settings
    timeout = request_timeout(total=300, connect=30, sock_read=60)

    connector = aiohttp.TCPConnector(
        limit=10,
        limit_per_host=5
    )

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # Fetch upcoming launches
        launches_data = await fetch_upcoming_launches(session)

        if not launches_data:
            print("⚠️ Failed to fetch fresh data, working with existing data...")

            if existing_launches:
                print(f"📋 Working with {len(existing_launches)} existing launches")
                go_launches = list(existing_launches.values())

                if ai_summarizer and ai_summarizer.available:
                    go_launches = await enhance_all_launches_with_ai(go_launches, ai_summarizer, session, existing_launches)

                has_ai_summaries = ai_summarizer is not None and ai_summarizer.available
                success = save_launches_to_json(go_launches, output_path, HF_MODEL if has_ai_summaries else None, has_ai_summaries)

                if success:
                    print(f"🎉 Successfully processed {len(go_launches)} existing launches with potential AI enhancements!")
                    return True
                else:
                    print("❌ Failed to save enhanced existing data")
                    return False
            else:
                print("❌ No existing data to work with and fresh API data unavailable")
                return False

        # Filter for "Go" status launches and enhance with detailed information
        go_launches = await filter_and_enhance_launches(session, launches_data, existing_launches)

        if not go_launches:
            print("⚠️ No launches with 'Go' status found")
            save_launches_to_json([], output_path, None, False)
            return True

        # Add AI summaries after all launches are prepared
        print(f"🤖 Starting AI summary generation for {len(go_launches)} launches...")
        if ai_summarizer and ai_summarizer.available:
            go_launches = await enhance_all_launches_with_ai(go_launches, ai_summarizer, session, existing_launches)
        else:
            print(f"🤖 AI Summarizer is unavailable so going with empty ai_summary...")
            for launch in go_launches:
                if 'ai_summary' not in launch:
                    launch['ai_summary'] = ""

        # Save filtered data
        has_ai_summaries = ai_summarizer is not None
        success = save_launches_to_json(go_launches, output_path, HF_MODEL if has_ai_summaries else None, has_ai_summaries)

        if success:
            print(f"🎉 Successfully processed {len(go_launches)} upcoming launches!")

            # Print summary of next few launches
            print("\n📅 Next upcoming launches:")
            for i, launch in enumerate(go_launches[:3]):
                launch_time = datetime.fromisoformat(launch['net'].replace('Z', '+00:00'))
                print(f"  {i+1}. {launch['name']} - {launch_time.strftime('%Y-%m-%d %H:%M')} UTC")
                print(f"     🏢 {launch['lsp_name']} | 📍 {launch['location']}")

                if 'ai_summary' in launch:
                    if launch['ai_summary']:
                        print(f"     🤖 AI Summary: {launch['ai_summary']}")
                    else:
                        print(f"     🤖 AI Summary: [Empty - AI failed/unavailable]")
                elif launch.get('mission_description'):
                    desc = launch['mission_description'][:100] + "..." if len(launch['mission_description']) > 100 else launch['mission_description']
                    print(f"     📋 {desc}")
                print()

            return True
        else:
            print("❌ Failed to save launch data")
            return False


if __name__ == "__main__":
    success = asyncio.run(main())

    if success:
        print("\n✅ Upcoming events agent completed successfully!")
        exit(0)
    else:
        print("\n❌ Upcoming events agent failed!")
        exit(1)
