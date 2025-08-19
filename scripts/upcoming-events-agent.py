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
MAX_EVENTS = 50  # Fetch more events to ensure we get 10+ with "Go" status

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

def filter_go_status_launches(launches_data):
    """
    Filter launches to only include those with status "Go"
    
    Args:
        launches_data: Raw API response data
    
    Returns:
        list: Filtered list of launches with status "Go"
    """
    if not launches_data or 'results' not in launches_data:
        return []
    
    go_launches = []
    
    for launch in launches_data['results']:
        # Check if status exists and name is "Go"
        if (launch.get('status') and 
            isinstance(launch['status'], dict) and 
            launch['status'].get('name') == 'Go'):
            
            # Clean up the launch data for frontend consumption
            cleaned_launch = {
                'id': launch.get('id'),
                'name': launch.get('name'),
                'status': launch.get('status'),
                'net': launch.get('net'),  # Launch time
                'window_start': launch.get('window_start'),
                'window_end': launch.get('window_end'),
                'lsp_name': launch.get('lsp_name'),  # Launch Service Provider
                'mission': launch.get('mission'),
                'mission_type': launch.get('mission_type'),
                'pad': launch.get('pad'),
                'location': launch.get('location'),
                'image': launch.get('image'),
                'infographic': launch.get('infographic'),
                'url': launch.get('url')
            }
            
            go_launches.append(cleaned_launch)
    
    print(f"✅ Filtered {len(go_launches)} launches with 'Go' status")
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
            'source': 'The Space Devs API',
            'filter_criteria': 'status.name == "Go"',
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
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Fetch upcoming launches
        launches_data = await fetch_upcoming_launches(session)
        
        if not launches_data:
            print("❌ Failed to fetch launch data")
            return False
        
        # Filter for "Go" status launches
        go_launches = filter_go_status_launches(launches_data)
        
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
