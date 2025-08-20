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

# Configuration
API_URL = "https://ll.thespacedevs.com/2.0.0/launch/upcoming/"
OUTPUT_FILE = "../public/upcoming_events.json"
MAX_EVENTS = 100  # Fetch more events to ensure we get 15+ with "Go" status

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
    
    try:
        async with session.get(API_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Successfully fetched {len(data.get('results', []))} upcoming launches")
                return data
            else:
                print(f"❌ API request failed with status {response.status}")
                return None
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return None

async def fetch_launch_details(session, launch_url):
    """
    Fetch detailed information for a specific launch
    
    Args:
        session: aiohttp ClientSession
        launch_url: URL to fetch detailed launch information
    
    Returns:
        dict: Detailed launch data or None if failed
    """
    try:
        async with session.get(launch_url) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"⚠️  Failed to fetch details from {launch_url} (status {response.status})")
                return None
    except Exception as e:
        print(f"⚠️  Error fetching launch details from {launch_url}: {e}")
        return None

async def filter_and_enhance_launches(session, launches_data):
    """
    Filter launches to only include those with status "Go" and fetch detailed information
    
    Args:
        session: aiohttp ClientSession
        launches_data: Raw API response data
    
    Returns:
        list: Enhanced list of launches with status "Go" and detailed information
    """
    if not launches_data or 'results' not in launches_data:
        return []
    
    go_launches = []
    
    # First filter for "Go" status launches
    go_launch_candidates = []
    for launch in launches_data['results']:
        if (launch.get('status') and 
            isinstance(launch['status'], dict) and 
            launch['status'].get('name') == 'Go' and
            launch.get('url')):
            go_launch_candidates.append(launch)
    
    print(f"🔍 Found {len(go_launch_candidates)} launches with 'Go' status, fetching detailed information...")
    
    # Fetch detailed information for each "Go" launch
    for i, launch in enumerate(go_launch_candidates):
        print(f"📡 Fetching details for launch {i+1}/{len(go_launch_candidates)}: {launch.get('name', 'Unknown')}")
        
        # Fetch detailed launch information
        detailed_data = await fetch_launch_details(session, launch['url'])
        
        # Extract enhanced information
        if detailed_data:
            # Get launch service provider details
            lsp_info = detailed_data.get('launch_service_provider', {})
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
                
                # Media and links
                'image': detailed_data.get('image', launch.get('image')),
                'infographic': detailed_data.get('infographic', launch.get('infographic')),
                'url': detailed_data.get('url', launch.get('url')),
                
                # Additional metadata
                'webcast_live': detailed_data.get('webcast_live', False),
                'probability': detailed_data.get('probability'),
                'info_urls': detailed_data.get('infoURLs', []),
                'video_urls': detailed_data.get('vidURLs', [])
            }
            
            go_launches.append(cleaned_launch)
        else:
            # Fall back to basic data if detailed fetch failed
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
                'image': launch.get('image'),
                'infographic': launch.get('infographic'),
                'url': launch.get('url'),
                'webcast_live': False,
                'probability': None,
                'info_urls': [],
                'video_urls': []
            }
            
            go_launches.append(cleaned_launch)
    
    print(f"✅ Enhanced {len(go_launches)} launches with detailed information")
    return go_launches

def save_to_json(data, output_path):
    """
    Save filtered launch data to JSON file
    
    Args:
        data: List of filtered launch data
        output_path: Path to output JSON file
    
    Returns:
        bool: Success status
    """
    try:
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Add metadata
        output_data = {
            'count': len(data),
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'source': 'The Space Devs API (Enhanced)',
            'filter_criteria': 'status.name == "Go"',
            'data_includes': [
                'Launch Service Provider details',
                'Mission descriptions',
                'Rocket information',
                'Launch site details',
                'Media URLs'
            ],
            'launches': data
        }
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully saved {len(data)} upcoming launches to {output_path}")
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
    
    # Get the absolute path for the output file
    script_dir = Path(__file__).parent
    output_path = script_dir / OUTPUT_FILE
    output_path = output_path.resolve()
    
    print(f"💾 Output file: {output_path}")
    
    # Create HTTP session with timeout
    timeout = aiohttp.ClientTimeout(total=60)  # Increased timeout for multiple requests
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Fetch upcoming launches
        launches_data = await fetch_upcoming_launches(session)
        
        if not launches_data:
            print("❌ Failed to fetch launch data")
            return False
        
        # Filter for "Go" status launches and enhance with detailed information
        go_launches = await filter_and_enhance_launches(session, launches_data)
        
        if not go_launches:
            print("⚠️  No launches with 'Go' status found")
            # Still save empty data with timestamp
            save_to_json([], output_path)
            return True
        
        # Save filtered data
        success = save_to_json(go_launches, output_path)
        
        if success:
            print(f"🎉 Successfully processed {len(go_launches)} upcoming launches!")
            
            # Print summary of next few launches
            print("\n📅 Next upcoming launches:")
            for i, launch in enumerate(go_launches[:5]):  # Show first 5
                launch_time = datetime.fromisoformat(launch['net'].replace('Z', '+00:00'))
                print(f"  {i+1}. {launch['name']} - {launch_time.strftime('%Y-%m-%d %H:%M')} UTC")
                print(f"     🏢 {launch['lsp_name']} | 📍 {launch['location']}")
                if launch.get('mission_description'):
                    desc = launch['mission_description'][:100] + "..." if len(launch['mission_description']) > 100 else launch['mission_description']
                    print(f"     📋 {desc}")
                print()  # Empty line for readability
            
            return True
        else:
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
