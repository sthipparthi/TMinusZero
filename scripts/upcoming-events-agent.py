#!/usr/bin/env python3
"""
Upcoming Space Launch Events Agent

This script fetches upcoming space launches from The Space Devs API,
filters for launches with status "Go", and saves them to upcoming_events.json
in the public directory for the React app to consume.
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from pathlib import Path

# AI Summarization imports
import aiohttp

# Configuration
API_URL = "https://ll.thespacedevs.com/2.0.0/launch/upcoming/"
OUTPUT_FILE = "../public/upcoming_events.json"
MAX_EVENTS = 50  # Reduced to minimize API load and avoid rate limiting

# AI Model configuration
HF_MODEL = os.getenv("HF_MODEL", "facebook/bart-large-cnn")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

AI_MODEL_NAME = None  # Will be set based on successful loading

# Configuration - Simple approach without retry logic

async def make_api_request(session, url, params=None, description="API request"):
    """
    Make a simple API request with basic error handling and rate limit retry
    
    Args:
        session: aiohttp ClientSession
        url: URL to request
        params: Optional query parameters
        description: Description for logging
    
    Returns:
        dict: JSON response or None if failed
    """
    max_retries = 2
    retry_delay = 60  # 1 minute delay for rate limit retry
    
    for attempt in range(max_retries + 1):
        try:
            print(f"📡 Making {description} to {url}")
            if attempt > 0:
                print(f"   🔄 Retry attempt {attempt}/{max_retries}")
                
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ {description} successful")
                    return data
                elif response.status == 429:
                    print(f"⚠️  {description} rate limited (429)")
                    if attempt < max_retries:
                        print(f"   ⏱️  Waiting {retry_delay} seconds before retry...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        print(f"   ❌ Max retries reached for rate limiting")
                        return None
                else:
                    print(f"❌ {description} failed with status {response.status}")
                    return None
        except Exception as e:
            print(f"❌ Error during {description}: {e}")
            if attempt < max_retries:
                print(f"   ⏱️  Waiting {retry_delay // 2} seconds before retry...")
                await asyncio.sleep(retry_delay // 2)
                continue
            return None
    
    return None

class AILaunchSummarizer:
    """
    AI-powered launch summarizer using Hugging Face API
    """
    def __init__(self):
        """Initialize the AI summarizer"""
        self.available = False
        
        # Check if HF_TOKEN is available
        if not HF_TOKEN:
            print("❌ HF_TOKEN environment variable not set")
            print("❌ AI model loading failed, continuing without AI summaries")
            return
        
        try:
            print(f"🤖 Using Hugging Face API with model: {HF_MODEL}")
            print("🔐 Using authenticated Hugging Face access")
            
            # Set AI model name for metadata
            global AI_MODEL_NAME
            AI_MODEL_NAME = HF_MODEL
            self.available = True
            print(f"✅ AI API access configured successfully!")
            
        except Exception as e:
            print(f"❌ Failed to configure AI API: {e}")
            print("❌ AI model loading failed, continuing without AI summaries")
    
    def create_launch_prompt(self, launch_data):
        """
        Create a structured prompt for the AI model to summarize launch information
        
        Args:
            launch_data: Dictionary containing launch information
        
        Returns:
            str: Formatted prompt for the model
        """
        # Extract key information
        name = launch_data.get('name', 'Unknown Launch')
        lsp_name = launch_data.get('lsp_name', 'Unknown Agency')
        lsp_description = launch_data.get('lsp_description', 'Unknown Agency')
        mission_type = launch_data.get('mission_type', '')
        mission_description = launch_data.get('mission_description', '')
        rocket_description = launch_data.get('rocket_config_description', '')
        launch_site = launch_data.get('launch_site', launch_data.get('location', ''))
        rocket_stats = f"({launch_data.get('rocket_config_successful_launches', 0)}/{launch_data.get('rocket_config_total_launch_count', 0)} successful launches)"
        
        # Additional rocket and manufacturer information
        rocket_family = launch_data.get('rocket_config_family', '')
        rocket_manufacturer_name = launch_data.get('rocket_manufacturer_name', '')
        rocket_manufacturer_description = launch_data.get('rocket_manufacturer_description', '')
        rocket_manufacturer_stats = f"({launch_data.get('rocket_manufacturer_successful_launches', 0)}/{launch_data.get('rocket_manufacturer_total_launch_count', 0)} manufacturer successful launches)"
        
        # Pad details
        pad_name = launch_data.get('pad', '')
        orbit = launch_data.get('orbit', '')
        
        # Create a more direct content-focused prompt for summarization
        # This approach provides the content to be summarized without confusing instructions
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
        """
        Generate an AI summary for a launch using Hugging Face API
        
        Args:
            launch_data: Dictionary containing launch information
            session: aiohttp ClientSession for API calls
        
        Returns:
            str: Generated summary, fallback message, or empty string if AI fails
        """
        if not self.available or not HF_TOKEN:
            # Return empty string when AI is not available (requirement 1)
            return ""
        
        try:
            # Create prompt and generate
            prompt = self.create_launch_prompt(launch_data)
            
            # Prepare API request
            payload = {"inputs": prompt, "parameters": {"max_new_tokens": 150, "min_length": 30}}
            headers = {"Authorization": f"Bearer {HF_TOKEN}", "Accept": "application/json"}
            
            # Make API request
            async with session.post(HF_API_URL, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if isinstance(result, list) and result and isinstance(result[0], dict):
                        summary = result[0].get("summary_text") or result[0].get("generated_text") or ""
                        if summary:
                            return summary.strip()
                    elif isinstance(result, dict):
                        summary = result.get("summary_text") or result.get("generated_text") or ""
                        if summary:
                            return summary.strip()
                    elif isinstance(result, str):
                        return result.strip()
                else:
                    error_text = await resp.text()
                    print(f"⚠️  HF API returned status {resp.status}: {error_text}")
                    # Return empty string when AI API fails (requirement 1)
                    return ""
            
            # Return empty string if API call didn't return a valid summary (requirement 1)
            print(f"⚠️  AI API returned no valid summary for {launch_data.get('name', 'Unknown')}")
            return ""
            
        except Exception as e:
            print(f"⚠️  AI summarization failed for {launch_data.get('name', 'Unknown')}: {e}")
            # Return empty string when AI fails (requirement 1)
            return ""

async def fetch_upcoming_launches(session, limit=MAX_EVENTS):
    """
    Fetch upcoming launches from The Space Devs API
    
    Args:
        session: aiohttp ClientSession
        limit: Maximum number of launches to fetch
    
    Returns:
        dict: API response data
    """
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

async def fetch_launch_details(session, launch_url, launch_name="Unknown"):
    """
    Fetch detailed information for a specific launch
    
    Args:
        session: aiohttp ClientSession
        launch_url: URL to fetch detailed launch information
        launch_name: Name of the launch for logging
    
    Returns:
        dict: Detailed launch data or None if failed
    """
    data = await make_api_request(
        session, 
        launch_url, 
        description=f"launch details for '{launch_name}'"
    )
    
    if not data:
        print(f"⚠️  Failed to fetch details for '{launch_name}'")
    
    return data

async def filter_and_enhance_launches(session, launches_data, existing_launches=None):
    """
    Filter launches to only include those with status "Go" and fetch detailed information
    Enhanced with robust error handling - continues with basic data if detailed fetch fails
    Now skips launch detail API calls for existing launches to avoid unnecessary API usage
    
    Args:
        session: aiohttp ClientSession
        launches_data: Raw API response data
        existing_launches: Dictionary mapping launch IDs to existing launch data (optional)
    
    Returns:
        list: Enhanced list of launches with status "Go" and available information
    """
    if not launches_data or 'results' not in launches_data:
        return []
    
    go_launches = []
    existing_launches = existing_launches or {}
    
    # First filter for "Go" status launches
    go_launch_candidates = []
    for launch in launches_data['results']:
        if (launch.get('status') and 
            isinstance(launch['status'], dict) and 
            launch['status'].get('name') == 'Go' and
            launch.get('url')):
            go_launch_candidates.append(launch)
    
    print(f"🔍 Found {len(go_launch_candidates)} launches with 'Go' status")
    
    # Separate existing launches from new launches
    existing_launch_count = 0
    new_launch_count = 0
    api_calls_saved = 0
    
    # Process each "Go" launch with smart existing launch detection
    for i, launch in enumerate(go_launch_candidates):
        launch_id = launch.get('id')
        launch_name = launch.get('name', 'Unknown')
        
        # Check if we already have this launch with complete data
        if launch_id and launch_id in existing_launches:
            existing_launch = existing_launches[launch_id]
            # If we have complete existing data (with AI summary), reuse it entirely
            if existing_launch.get('ai_summary') is not None:  # Could be empty string, that's fine
                print(f"♻️  Reusing complete existing data for: {launch_name}")
                go_launches.append(existing_launch)
                existing_launch_count += 1
                api_calls_saved += 1
                continue
        
        # This is a new launch or existing launch without complete data - process it
        print(f"📡 Processing launch {new_launch_count + 1}: {launch_name}")
        new_launch_count += 1
        
        # Add delay between requests to be respectful to the API (only for new launches)
        if new_launch_count > 1:
            await asyncio.sleep(15)  # 15 seconds delay between requests to avoid rate limiting
        
        # Try to fetch detailed launch information for new launches
        detailed_data = await fetch_launch_details(session, launch['url'], launch_name)
        
        # Always create launch data, either enhanced or basic
        try:
            if detailed_data:
                # Enhanced data path - extract all available information
                print(f"   ✅ Successfully fetched detailed data for: {launch_name}")
                
                # Get launch service provider details
                lsp_info = detailed_data.get('launch_service_provider', {})
                if not lsp_info:
                    # Try alternative key names
                    lsp_info = detailed_data.get('lsp', {})
                
                lsp_name = lsp_info.get('name', launch.get('lsp_name', 'Unknown'))
                lsp_description = lsp_info.get('description', '')
                lsp_type = lsp_info.get('type', '')
                lsp_country = lsp_info.get('country_code', '')
                lsp_logo = lsp_info.get('logo_url', '')
                
                # Get mission details
                mission_info = detailed_data.get('mission', {})
                mission_name = mission_info.get('name', launch.get('mission', 'Unknown'))
                mission_description = mission_info.get('description', '')
                mission_type = mission_info.get('type', launch.get('mission_type', ''))
                orbit_info = mission_info.get('orbit', {})
                orbit_name = orbit_info.get('name', '') if orbit_info else ''
                
                # Get pad and location details
                pad_info = detailed_data.get('pad', {})
                pad_name = pad_info.get('name', launch.get('pad', ''))
                location_info = pad_info.get('location', {}) if pad_info else {}
                location_name = location_info.get('name', launch.get('location', ''))
                
                # Get rocket information
                rocket_info = detailed_data.get('rocket', {})
                rocket_config = rocket_info.get('configuration', {}) if rocket_info else {}
                rocket_name = rocket_config.get('full_name', rocket_config.get('name', ''))
                
                # Get detailed rocket configuration information
                rocket_config_description = rocket_config.get('description', '')
                rocket_config_family = rocket_config.get('family', '')
                rocket_config_full_name = rocket_config.get('full_name', '')
                rocket_config_total_launch_count = rocket_config.get('total_launch_count', 0)
                rocket_config_successful_launches = rocket_config.get('successful_launches', 0)
                rocket_config_failed_launches = rocket_config.get('failed_launches', 0)
                rocket_config_pending_launches = rocket_config.get('pending_launches', 0)
                
                # Get rocket manufacturer information
                rocket_manufacturer = rocket_config.get('manufacturer', {}) if rocket_config else {}
                rocket_manufacturer_name = rocket_manufacturer.get('name', '')
                rocket_manufacturer_type = rocket_manufacturer.get('type', '')
                rocket_manufacturer_description = rocket_manufacturer.get('description', '')
                rocket_manufacturer_total_launch_count = rocket_manufacturer.get('total_launch_count', 0)
                rocket_manufacturer_successful_launches = rocket_manufacturer.get('successful_launches', 0)
                rocket_manufacturer_failed_launches = rocket_manufacturer.get('failed_launches', 0)
                
                # Build enhanced launch data
                cleaned_launch = {
                    'id': detailed_data.get('id', launch.get('id')),
                    'name': detailed_data.get('name', launch.get('name')),
                    'status': detailed_data.get('status', {}).get('name', 'Go'),
                    'net': detailed_data.get('net', launch.get('net')),
                    'window_start': detailed_data.get('window_start', launch.get('window_start')),
                    'window_end': detailed_data.get('window_end', launch.get('window_end')),
                    
                    # Enhanced Launch Service Provider information
                    'lsp_name': lsp_name,
                    'lsp_description': lsp_description,
                    'lsp_type': lsp_type,
                    'lsp_country': lsp_country,
                    'lsp_logo': lsp_logo,
                    
                    # Enhanced Mission information
                    'mission_name': mission_name,
                    'mission_description': mission_description,
                    'mission_type': mission_type,
                    'orbit': orbit_name,
                    
                    # Launch site information
                    'launch_site': f"{pad_name}, {location_name}" if pad_name and location_name else (location_name or pad_name or ''),
                    'pad': pad_name,
                    'location': location_name,
                    
                    # Rocket information
                    'rocket': rocket_name,
                    'rocket_config_description': rocket_config_description,
                    'rocket_config_family': rocket_config_family,
                    'rocket_config_full_name': rocket_config_full_name,
                    'rocket_config_total_launch_count': rocket_config_total_launch_count,
                    'rocket_config_successful_launches': rocket_config_successful_launches,
                    'rocket_config_failed_launches': rocket_config_failed_launches,
                    'rocket_config_pending_launches': rocket_config_pending_launches,
                    'rocket_manufacturer_name': rocket_manufacturer_name,
                    'rocket_manufacturer_type': rocket_manufacturer_type,
                    'rocket_manufacturer_description': rocket_manufacturer_description,
                    'rocket_manufacturer_total_launch_count': rocket_manufacturer_total_launch_count,
                    'rocket_manufacturer_successful_launches': rocket_manufacturer_successful_launches,
                    'rocket_manufacturer_failed_launches': rocket_manufacturer_failed_launches,
                    
                    # Media and links
                    'image': detailed_data.get('image', launch.get('image')),
                    'infographic': detailed_data.get('infographic', launch.get('infographic')),
                    'url': detailed_data.get('url', launch.get('url')),
                    
                    # Additional metadata
                    'webcast_live': detailed_data.get('webcast_live', False),
                    'probability': detailed_data.get('probability'),
                    'video_urls': detailed_data.get('vidURLs', [])
                }
                
            else:
                # Basic data path - use only what's available from the initial API call
                # This includes rate limit failures - we continue processing with basic data
                print(f"   ⚠️  Detailed fetch failed for: {launch_name}, continuing with basic data")
                cleaned_launch = {
                    'id': launch.get('id'),
                    'name': launch.get('name'),
                    'status': 'Go',
                    'net': launch.get('net'),
                    'window_start': launch.get('window_start'),
                    'window_end': launch.get('window_end'),
                    'lsp_name': launch.get('lsp_name', 'Unknown'),
                    'lsp_description': '',
                    'lsp_type': '',
                    'lsp_country': '',
                    'lsp_logo': '',
                    'mission_name': launch.get('mission', 'Unknown'),
                    'mission_description': '',
                    'mission_type': launch.get('mission_type', ''),
                    'orbit': '',
                    'launch_site': launch.get('location', ''),
                    'pad': launch.get('pad', ''),
                    'location': launch.get('location', ''),
                    'rocket': '',
                    'rocket_config_description': '',
                    'rocket_config_family': '',
                    'rocket_config_full_name': '',
                    'rocket_config_total_launch_count': 0,
                    'rocket_config_successful_launches': 0,
                    'rocket_config_failed_launches': 0,
                    'rocket_config_pending_launches': 0,
                    'rocket_manufacturer_name': '',
                    'rocket_manufacturer_type': '',
                    'rocket_manufacturer_description': '',
                    'rocket_manufacturer_total_launch_count': 0,
                    'rocket_manufacturer_successful_launches': 0,
                    'rocket_manufacturer_failed_launches': 0,
                    'image': launch.get('image'),
                    'infographic': launch.get('infographic'),
                    'url': launch.get('url'),
                    'webcast_live': False,
                    'probability': None,
                    'video_urls': []
                }
            
            # Always add the new launch data - continue processing regardless of detailed fetch success/failure
            go_launches.append(cleaned_launch)
            
        except Exception as e:
            # Even if data processing fails, create minimal launch entry - continue processing
            print(f"   ❌ Error processing launch data for {launch_name}: {e}")
            print(f"   📝 Creating minimal launch entry to ensure processing continues")
            
            minimal_launch = {
                'id': launch.get('id', f"error_{new_launch_count}"),
                'name': launch.get('name', 'Unknown Launch'),
                'status': 'Go',
                'net': launch.get('net', ''),
                'window_start': launch.get('window_start', ''),
                'window_end': launch.get('window_end', ''),
                'lsp_name': launch.get('lsp_name', 'Unknown'),
                'lsp_description': '',
                'lsp_type': '',
                'lsp_country': '',
                'lsp_logo': '',
                'mission_name': launch.get('mission', 'Unknown'),
                'mission_description': '',
                'mission_type': launch.get('mission_type', ''),
                'orbit': '',
                'launch_site': launch.get('location', ''),
                'pad': launch.get('pad', ''),
                'location': launch.get('location', ''),
                'rocket': '',
                'rocket_config_description': '',
                'rocket_config_family': '',
                'rocket_config_full_name': '',
                'rocket_config_total_launch_count': 0,
                'rocket_config_successful_launches': 0,
                'rocket_config_failed_launches': 0,
                'rocket_config_pending_launches': 0,
                'rocket_manufacturer_name': '',
                'rocket_manufacturer_type': '',
                'rocket_manufacturer_description': '',
                'rocket_manufacturer_total_launch_count': 0,
                'rocket_manufacturer_successful_launches': 0,
                'rocket_manufacturer_failed_launches': 0,
                'image': launch.get('image'),
                'infographic': launch.get('infographic'),
                'url': launch.get('url'),
                'webcast_live': False,
                'probability': None,
                'info_urls': [],
                'video_urls': []
            }
            
            go_launches.append(minimal_launch)
    
    # Report processing results with efficiency metrics
    print(f"✅ Processed {len(go_launches)} launches:")
    print(f"   ♻️  {existing_launch_count} existing launches reused (no API calls needed)")
    print(f"   🆕 {new_launch_count} new/incomplete launches processed")
    print(f"   🚀 Saved {api_calls_saved} API calls by reusing existing data")
    
    return go_launches

def load_existing_launches(output_path):
    """
    Load existing launches from the JSON file
    
    Args:
        output_path: Path to the existing JSON file
    
    Returns:
        dict: Dictionary mapping launch IDs to launch data with AI summaries
    """
    try:
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_launches = {}
                for launch in existing_data.get('launches', []):
                    if 'id' in launch:
                        existing_launches[launch['id']] = launch
                print(f"📋 Loaded {len(existing_launches)} existing launches from {output_path}")
                return existing_launches
        else:
            print(f"📋 No existing file found at {output_path}")
            return {}
    except Exception as e:
        print(f"⚠️  Error loading existing launches: {e}")
        return {}

async def enhance_all_launches_with_ai(launches, ai_summarizer, session, existing_launches=None):
    """
    Enhance launches with AI-generated summaries, only generating new summaries for launches that need them
    Enhanced with robust error handling - continues with empty AI summary if generation fails
    Now only processes launches that don't already have complete AI summaries
    
    Args:
        launches: List of launch data dictionaries
        ai_summarizer: AILaunchSummarizer instance
        session: aiohttp ClientSession for API calls
        existing_launches: Dictionary mapping launch IDs to existing launch data with AI summaries
    
    Returns:
        list: Enhanced launches with AI summaries (or empty strings if AI fails)
    """
    if not launches:
        return launches
    
    existing_launches = existing_launches or {}
    launches_needing_ai = []
    reused_summaries = 0
    new_summaries = 0
    failed_summaries = 0
    
    # Identify which launches need AI summaries (those without ai_summary field)
    for launch in launches:
        if 'ai_summary' not in launch:
            # This launch doesn't have an AI summary yet, needs processing
            launches_needing_ai.append(launch)
        else:
            # This launch already has an AI summary (reused from existing data)
            reused_summaries += 1
    
    print(f"🔍 AI Summary Status:")
    print(f"   ♻️  {reused_summaries} launches already have AI summaries (reused)")
    print(f"   🆕 {len(launches_needing_ai)} launches need new AI summaries")
    
    if launches_needing_ai:
        print(f"🤖 Generating AI summaries for {len(launches_needing_ai)} launches...")
        
        for i, launch in enumerate(launches_needing_ai):
            launch_name = launch.get('name', 'Unknown')
            print(f"🔄 Processing launch {i+1}/{len(launches_needing_ai)}: {launch_name}")
            
            # Generate AI summary for launches that need it
            if ai_summarizer and ai_summarizer.available:
                try:
                    ai_summary = await ai_summarizer.generate_summary(launch, session)
                    if ai_summary:  # Check if we got a valid summary
                        launch['ai_summary'] = ai_summary
                        new_summaries += 1
                        print(f"   🤖 AI Summary: {ai_summary}")
                    else:
                        # AI returned empty string
                        launch['ai_summary'] = ""
                        failed_summaries += 1
                        print(f"   ⚠️  AI returned empty summary, saved as empty string")
                except Exception as e:
                    print(f"   ❌ AI summarization failed: {e}")
                    # Add empty summary when AI fails
                    launch['ai_summary'] = ""
                    failed_summaries += 1
                    print(f"   📝 Saved empty AI summary due to error")
            else:
                # Add empty summary when AI is not available
                launch['ai_summary'] = ""
                failed_summaries += 1
                print(f"   📝 AI not available, saved empty summary")
    
    # Ensure all launches have ai_summary field (should already be the case now)
    for launch in launches:
        if 'ai_summary' not in launch:
            launch['ai_summary'] = ""
            failed_summaries += 1
    
    print(f"✅ AI Summary Results:")
    print(f"   ♻️ {reused_summaries} reused existing summaries")
    print(f"   🆕 {new_summaries} new AI summaries generated")
    print(f"   ⚠️ {failed_summaries} empty summaries (AI failed/unavailable)")
    return launches

def save_to_json(data, output_path, has_ai_summaries=False):
    """
    Save filtered launch data to JSON file
    Enhanced to handle cases where AI summaries might be empty strings
    
    Args:
        data: List of filtered launch data
        output_path: Path to output JSON file
        has_ai_summaries: Whether AI summaries were attempted (even if some failed)
    
    Returns:
        bool: Success status
    """
    try:
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build data includes list
        data_includes = [
            'Launch Service Provider details',
            'Mission descriptions',
            'Rocket configuration information & statistics',
            'Rocket manufacturer details & statistics',
            'Launch site details',
            'Media URLs'
        ]
        
        # Check if any launches actually have AI summaries (not just empty strings)
        ai_summary_count = 0
        empty_summary_count = 0
        for launch in data:
            if 'ai_summary' in launch:
                if launch['ai_summary']:  # Non-empty summary
                    ai_summary_count += 1
                else:  # Empty summary
                    empty_summary_count += 1
        
        # Add AI summary information to metadata
        if has_ai_summaries:
            if ai_summary_count > 0:
                data_includes.append(f'AI-generated summaries ({ai_summary_count} successful)')
            if empty_summary_count > 0:
                data_includes.append(f'Empty AI summaries ({empty_summary_count} failed/unavailable)')
        
        # Add metadata
        output_data = {
            'count': len(data),
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'source': 'The Space Devs API (Enhanced)',
            'filter_criteria': 'status.name == "Go"',
            'data_includes': data_includes,
            'launches': data
        }
        
        # Add AI model info if summaries were attempted
        if has_ai_summaries:
            output_data['ai_model'] = AI_MODEL_NAME
            output_data['ai_enhancement'] = f'AI-powered summaries using {AI_MODEL_NAME} (with robust error handling)'
            output_data['ai_summary_stats'] = {
                'successful_summaries': ai_summary_count,
                'empty_summaries': empty_summary_count,
                'total_launches': len(data)
            }
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully saved {len(data)} upcoming launches to {output_path}")
        if has_ai_summaries:
            print(f"🤖 AI summaries: {ai_summary_count} successful, {empty_summary_count} empty/failed")
        return True
        
    except Exception as e:
        print(f"❌ Error saving to file: {e}")
        return False

async def main():
    """
    Main function to fetch, filter, and save upcoming launches
    """
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
    timeout = aiohttp.ClientTimeout(
        total=300,      # Total timeout increased to 5 minutes
        connect=30,     # Connection timeout
        sock_read=60    # Socket read timeout
    )
    
    connector = aiohttp.TCPConnector(
        limit=10,       # Maximum number of connections
        limit_per_host=5  # Maximum connections per host
    )
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # Fetch upcoming launches
        launches_data = await fetch_upcoming_launches(session)
        
        if not launches_data:
            print("⚠️ Failed to fetch fresh data, working with existing data...")
            
            # If we have existing launches and fresh API data failed, work with what we have
            if existing_launches:
                print(f"📋 Working with {len(existing_launches)} existing launches")
                go_launches = list(existing_launches.values())
                
                # Add AI summaries to existing launches that don't have them
                if ai_summarizer and ai_summarizer.available:
                    go_launches = await enhance_all_launches_with_ai(go_launches, ai_summarizer, session, existing_launches)
                
                # Save updated data
                has_ai_summaries = ai_summarizer is not None and ai_summarizer.available
                success = save_to_json(go_launches, output_path, has_ai_summaries)
                
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
        # This will skip launch detail API calls and reuse data for existing launches
        go_launches = await filter_and_enhance_launches(session, launches_data, existing_launches)
        
        if not go_launches:
            print("⚠️ No launches with 'Go' status found")
            # Still save empty data with timestamp
            save_to_json([], output_path, False)
            return True
        
        # Add AI summaries after all launches are prepared
        # This will continue with empty summaries if AI fails, but proceed with all available launch data
        print(f"🤖 Starting AI summary generation for {len(go_launches)} launches...")
        if ai_summarizer and ai_summarizer.available:
            go_launches = await enhance_all_launches_with_ai(go_launches, ai_summarizer, session, existing_launches)
        else:
            print(f"🤖 AI Summarizer is unavailable so going with empty ai_summary...")
            # Ensure all launches have empty AI summaries when AI is not available
            for launch in go_launches:
                if 'ai_summary' not in launch:
                    launch['ai_summary'] = ""
        
        # Save filtered data - always attempt to save regardless of detailed fetch or AI failures
        has_ai_summaries = ai_summarizer is not None
        success = save_to_json(go_launches, output_path, has_ai_summaries)
        
        if success:
            print(f"🎉 Successfully processed {len(go_launches)} upcoming launches!")
            
            # Print summary of next few launches
            print("\n📅 Next upcoming launches:")
            for i, launch in enumerate(go_launches[:3]):  # Show first 3
                launch_time = datetime.fromisoformat(launch['net'].replace('Z', '+00:00'))
                print(f"  {i+1}. {launch['name']} - {launch_time.strftime('%Y-%m-%d %H:%M')} UTC")
                print(f"     🏢 {launch['lsp_name']} | 📍 {launch['location']}")
                
                # Show AI summary if available (including empty ones for transparency)
                if 'ai_summary' in launch:
                    if launch['ai_summary']:
                        print(f"     🤖 AI Summary: {launch['ai_summary']}")
                    else:
                        print(f"     🤖 AI Summary: [Empty - AI failed/unavailable]")
                elif launch.get('mission_description'):
                    desc = launch['mission_description'][:100] + "..." if len(launch['mission_description']) > 100 else launch['mission_description']
                    print(f"     📋 {desc}")
                print()  # Empty line for readability
            
            return True
        else:
            print("❌ Failed to save launch data")
            return False

if __name__ == "__main__":
    # Run the async main function
    success = asyncio.run(main())
    
    if success:
        print("\n✅ Upcoming events agent completed successfully!")
        exit(0)
    else:
        print("\n❌ Upcoming events agent failed!")
        exit(1)
