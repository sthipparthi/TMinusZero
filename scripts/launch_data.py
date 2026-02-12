"""Launch data transformation, filtering, and I/O."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path


async def make_api_request(session, url, params=None, description="API request"):
    """Make a simple API request with basic error handling."""
    try:
        print(f"📡 Making {description} to {url}")
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ {description} successful")
                return data
            elif response.status == 429:
                print(f"⚠️  {description} rate limited (429)")
                return None
            else:
                print(f"❌ {description} failed with status {response.status}")
                return None
    except Exception as e:
        print(f"❌ Error during {description}: {e}")
        return None


async def fetch_launch_details(session, launch_url, launch_name="Unknown"):
    """Fetch detailed information for a specific launch."""
    data = await make_api_request(
        session,
        launch_url,
        description=f"launch details for '{launch_name}'"
    )
    if not data:
        print(f"⚠️  Failed to fetch details for '{launch_name}'")
    return data


def build_launch_data(source, detailed_data=None):
    """Build a standardized launch data dictionary from source data and optional detailed data."""
    if detailed_data:
        lsp_info = detailed_data.get('launch_service_provider', {}) or detailed_data.get('lsp', {}) or {}
        mission_info = detailed_data.get('mission', {}) or {}
        orbit_info = mission_info.get('orbit', {}) or {}
        pad_info = detailed_data.get('pad', {}) or {}
        location_info = pad_info.get('location', {}) or {}
        rocket_info = detailed_data.get('rocket', {}) or {}
        rocket_config = rocket_info.get('configuration', {}) or {}
        rocket_manufacturer = rocket_config.get('manufacturer', {}) or {}

        pad_name = pad_info.get('name', source.get('pad', ''))
        location_name = location_info.get('name', source.get('location', ''))

        return {
            'id': detailed_data.get('id', source.get('id')),
            'name': detailed_data.get('name', source.get('name')),
            'status': detailed_data.get('status', {}).get('name', 'Go'),
            'net': detailed_data.get('net', source.get('net')),
            'window_start': detailed_data.get('window_start', source.get('window_start')),
            'window_end': detailed_data.get('window_end', source.get('window_end')),
            'lsp_name': lsp_info.get('name', source.get('lsp_name', 'Unknown')),
            'lsp_description': lsp_info.get('description', ''),
            'lsp_type': lsp_info.get('type', ''),
            'lsp_country': lsp_info.get('country_code', ''),
            'lsp_logo': lsp_info.get('logo_url', ''),
            'mission_name': mission_info.get('name', source.get('mission', 'Unknown')),
            'mission_description': mission_info.get('description', ''),
            'mission_type': mission_info.get('type', source.get('mission_type', '')),
            'orbit': orbit_info.get('name', '') if orbit_info else '',
            'launch_site': f"{pad_name}, {location_name}" if pad_name and location_name else (location_name or pad_name or ''),
            'pad': pad_name,
            'location': location_name,
            'rocket': rocket_config.get('full_name', rocket_config.get('name', '')),
            'rocket_config_description': rocket_config.get('description', ''),
            'rocket_config_family': rocket_config.get('family', ''),
            'rocket_config_full_name': rocket_config.get('full_name', ''),
            'rocket_config_total_launch_count': rocket_config.get('total_launch_count', 0),
            'rocket_config_successful_launches': rocket_config.get('successful_launches', 0),
            'rocket_config_failed_launches': rocket_config.get('failed_launches', 0),
            'rocket_config_pending_launches': rocket_config.get('pending_launches', 0),
            'rocket_manufacturer_name': rocket_manufacturer.get('name', ''),
            'rocket_manufacturer_type': rocket_manufacturer.get('type', ''),
            'rocket_manufacturer_description': rocket_manufacturer.get('description', ''),
            'rocket_manufacturer_total_launch_count': rocket_manufacturer.get('total_launch_count', 0),
            'rocket_manufacturer_successful_launches': rocket_manufacturer.get('successful_launches', 0),
            'rocket_manufacturer_failed_launches': rocket_manufacturer.get('failed_launches', 0),
            'image': detailed_data.get('image', source.get('image')),
            'infographic': detailed_data.get('infographic', source.get('infographic')),
            'url': detailed_data.get('url', source.get('url')),
            'webcast_live': detailed_data.get('webcast_live', False),
            'probability': detailed_data.get('probability'),
            'video_urls': detailed_data.get('vidURLs', []),
        }
    else:
        return {
            'id': source.get('id'),
            'name': source.get('name', 'Unknown Launch'),
            'status': 'Go',
            'net': source.get('net', ''),
            'window_start': source.get('window_start', ''),
            'window_end': source.get('window_end', ''),
            'lsp_name': source.get('lsp_name', 'Unknown'),
            'lsp_description': '',
            'lsp_type': '',
            'lsp_country': '',
            'lsp_logo': '',
            'mission_name': source.get('mission', 'Unknown'),
            'mission_description': '',
            'mission_type': source.get('mission_type', ''),
            'orbit': '',
            'launch_site': source.get('location', ''),
            'pad': source.get('pad', ''),
            'location': source.get('location', ''),
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
            'image': source.get('image'),
            'infographic': source.get('infographic'),
            'url': source.get('url'),
            'webcast_live': False,
            'probability': None,
            'video_urls': [],
        }


async def filter_and_enhance_launches(session, launches_data, existing_launches=None):
    """Filter launches to only include those with status "Go" and fetch detailed information.

    Skips launch detail API calls for existing launches to avoid unnecessary API usage.
    """
    if not launches_data or 'results' not in launches_data:
        return []

    go_launches = []
    existing_launches = existing_launches or {}

    go_launch_candidates = []
    for launch in launches_data['results']:
        if (launch.get('status') and
            isinstance(launch['status'], dict) and
            launch['status'].get('name') == 'Go' and
            launch.get('url')):
            go_launch_candidates.append(launch)

    print(f"🔍 Found {len(go_launch_candidates)} launches with 'Go' status")

    existing_launch_count = 0
    new_launch_count = 0
    api_calls_saved = 0

    for i, launch in enumerate(go_launch_candidates):
        launch_id = launch.get('id')
        launch_name = launch.get('name', 'Unknown')

        if launch_id and launch_id in existing_launches:
            existing_launch = existing_launches[launch_id]
            if existing_launch.get('ai_summary') is not None:
                print(f"♻️  Reusing complete existing data for: {launch_name}")
                go_launches.append(existing_launch)
                existing_launch_count += 1
                api_calls_saved += 1
                continue

        print(f"📡 Processing launch {new_launch_count + 1}: {launch_name}")
        new_launch_count += 1

        if new_launch_count > 1:
            await asyncio.sleep(1)

        detailed_data = await fetch_launch_details(session, launch['url'], launch_name)

        try:
            if detailed_data:
                print(f"   ✅ Successfully fetched detailed data for: {launch_name}")
                cleaned_launch = build_launch_data(launch, detailed_data)
            else:
                print(f"   ⚠️  Detailed fetch failed for: {launch_name}, continuing with basic data")
                cleaned_launch = build_launch_data(launch)

            go_launches.append(cleaned_launch)

        except Exception as e:
            print(f"   ❌ Error processing launch data for {launch_name}: {e}")
            print(f"   📝 Creating minimal launch entry to ensure processing continues")
            go_launches.append(build_launch_data(launch))

    print(f"✅ Processed {len(go_launches)} launches:")
    print(f"   ♻️  {existing_launch_count} existing launches reused (no API calls needed)")
    print(f"   🆕 {new_launch_count} new/incomplete launches processed")
    print(f"   🚀 Saved {api_calls_saved} API calls by reusing existing data")

    return go_launches


def load_existing_launches(output_path):
    """Load existing launches from the JSON file.

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


def save_launches_to_json(data, output_path, ai_model_name=None, has_ai_summaries=False):
    """Save filtered launch data to JSON file.

    Args:
        data: List of filtered launch data
        output_path: Path to output JSON file
        ai_model_name: Name of the AI model used (e.g. "facebook/bart-large-cnn")
        has_ai_summaries: Whether AI summaries were attempted
    """
    try:
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        data_includes = [
            'Launch Service Provider details',
            'Mission descriptions',
            'Rocket configuration information & statistics',
            'Rocket manufacturer details & statistics',
            'Launch site details',
            'Media URLs'
        ]

        ai_summary_count = 0
        empty_summary_count = 0
        for launch in data:
            if 'ai_summary' in launch:
                if launch['ai_summary']:
                    ai_summary_count += 1
                else:
                    empty_summary_count += 1

        if has_ai_summaries:
            if ai_summary_count > 0:
                data_includes.append(f'AI-generated summaries ({ai_summary_count} successful)')
            if empty_summary_count > 0:
                data_includes.append(f'Empty AI summaries ({empty_summary_count} failed/unavailable)')

        output_data = {
            'count': len(data),
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'source': 'The Space Devs API (Enhanced)',
            'filter_criteria': 'status.name == "Go"',
            'data_includes': data_includes,
            'launches': data
        }

        if has_ai_summaries:
            output_data['ai_model'] = ai_model_name
            output_data['ai_enhancement'] = f'AI-powered summaries using {ai_model_name} (with robust error handling)'
            output_data['ai_summary_stats'] = {
                'successful_summaries': ai_summary_count,
                'empty_summaries': empty_summary_count,
                'total_launches': len(data)
            }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Successfully saved {len(data)} upcoming launches to {output_path}")
        if has_ai_summaries:
            print(f"🤖 AI summaries: {ai_summary_count} successful, {empty_summary_count} empty/failed")
        return True

    except Exception as e:
        print(f"❌ Error saving to file: {e}")
        return False
