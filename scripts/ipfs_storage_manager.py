#!/usr/bin/env python3
"""
IPFS Storage and IPNS Publishing Script
Uploads space_news.json and upcoming_events.json to NFT.Storage
Tracks CIDs in a record file and publishes to W3Name for IPNS
"""

import os
import json
import base64
import requests
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

class W3NamePublisher:
    """W3Name IPNS publisher implementation"""
    
    def __init__(self, private_key_b64: str, w3_name: str = None):
        """Initialize with base64 encoded private key and optional W3Name"""
        try:
            # Decode the base64 private key
            self.private_key = base64.b64decode(private_key_b64)
            
            # Use provided W3Name
            if not w3_name:
                raise ValueError("W3Name is required")
            self.name_id = w3_name
            print(f"📛 Using W3Name ID: {self.name_id}")
            
        except Exception as e:
            print(f"❌ Error initializing W3Name publisher: {e}")
            raise
    
    def publish_to_w3name_api(self, cid: str) -> bool:
        """
        Publish to W3Name service via API
        Uses the actual W3Name API to publish IPNS records
        """
        try:
            # W3Name API endpoint - correct endpoint for publishing
            w3name_api_url = f"https://name.web3.storage/name/{self.name_id}"
            
            # Prepare payload according to W3Name API specification
            payload = {
                "value": f"/ipfs/{cid}"
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {base64.b64encode(self.private_key).decode()}"
            }
            
            print(f"📡 Publishing to W3Name API...")
            print(f"🎯 API URL: {w3name_api_url}")
            
            # Make API request to W3Name - using POST to create/update
            response = requests.post(w3name_api_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Successfully updated W3Name record")
                try:
                    result = response.json()
                    print(f"📋 Response: {result}")
                except:
                    print(f"📋 Response: {response.text}")
                return True
            elif response.status_code == 201:
                print(f"✅ Successfully created W3Name record")
                try:
                    result = response.json()
                    print(f"📋 Response: {result}")
                except:
                    print(f"📋 Response: {response.text}")
                return True
            elif response.status_code == 404:
                print(f"❌ W3Name not found: {self.name_id}")
                print(f"💡 You may need to create the W3Name first")
                print(f"📋 Response: {response.text}")
                return False
            elif response.status_code == 401:
                print(f"❌ Authentication failed - check your W3_KEY_BASE64")
                print(f"📋 Response: {response.text}")
                return False
            elif response.status_code == 403:
                print(f"❌ Permission denied - you don't own this W3Name")
                print(f"📋 Response: {response.text}")
                return False
            else:
                print(f"❌ W3Name API request failed: {response.status_code}")
                print(f"📋 Response: {response.text}")
                return False
            
        except requests.exceptions.Timeout:
            print(f"❌ Request timeout - W3Name API took too long to respond")
            return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error - unable to reach W3Name API")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error publishing to W3Name API: {e}")
            return False
    
    def create_ipns_link(self, cid: str) -> str:
        """Create IPNS link for the published content"""
        return f"https://ipfs.io/ipns/{self.name_id}"
    
    def publish(self, cid: str) -> bool:
        """
        Main publish method - publishes to W3Name API
        
        Args:
            cid: The IPFS CID to publish to IPNS
            
        Returns:
            True if publishing succeeded
        """
        try:
            print(f"📡 Publishing CID {cid} to IPNS name {self.name_id}")
            
            # Publish to W3Name API
            success = self.publish_to_w3name_api(cid)
            
            # Create IPNS link regardless
            ipns_url = self.create_ipns_link(cid)
            
            if success:
                print(f"✅ Successfully published to W3Name API")
                print(f"🌐 IPNS URL: {ipns_url}")
                
                return True
            else:
                print(f"❌ W3Name API publishing failed")
                print(f"🌐 IPNS URL (may not work): {ipns_url}")
                return False
                
        except Exception as e:
            print(f"❌ Error in publish method: {e}")
            return False
    
    def get_publication_info(self) -> Dict[str, Any]:
        """Get information about this W3Name publisher"""
        return {
            "name_id": self.name_id,
            "ipns_url": f"https://ipfs.io/ipns/{self.name_id}",
            "key_length": len(self.private_key),
            "created": datetime.now(timezone.utc).isoformat()
        }

class IPFSStorageManager:
    """Manages IPFS storage via NFT.Storage and IPNS publishing via W3Name"""
    
    def __init__(self, nft_storage_token: str, w3_key_base64: str, w3_name: str = None):
        self.nft_storage_token = nft_storage_token
        self.nft_storage_url = "https://api.nft.storage"
        self.records_file = "public/ipfs_records.json"
        
        # Initialize W3Name publisher
        self.w3name = W3NamePublisher(w3_key_base64, w3_name)
        
        # Headers for NFT.Storage
        self.headers = {
            "Authorization": f"Bearer {nft_storage_token}"
        }
        print("🔧 IPFS Storage Manager initialized")
    
    def upload_to_nft_storage(self, file_path: str, file_name: str) -> Optional[str]:
        """
        Upload file to NFT.Storage and return CID
        
        Args:
            file_path: Path to the file to upload
            file_name: Name of the file
            
        Returns:
            CID string if successful, None if failed
        """
        try:
            print(f"📤 Uploading {file_name} to NFT.Storage...")
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Prepare file for upload
            files = {
                'file': (file_name, file_content, 'application/json')
            }
            
            # Upload to NFT.Storage
            response = requests.post(
                f"{self.nft_storage_url}/upload",
                headers=self.headers,
                files=files,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                cid = result.get('value', {}).get('cid')
                
                if cid:
                    print(f"✅ Successfully uploaded {file_name}")
                    print(f"🔗 CID: {cid}")
                    print(f"🌐 IPFS URL: https://ipfs.io/ipfs/{cid}")
                    print(f"🔗 NFT.Storage URL: https://{cid}.ipfs.nftstorage.link")
                    return cid
                else:
                    print(f"❌ No CID returned for {file_name}")
                    return None
            else:
                print(f"❌ Upload failed for {file_name}: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error uploading {file_name}: {str(e)}")
            return None
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information including size and hash"""
        try:
            # File size
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            # File hash
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            return {
                "size_bytes": file_size,
                "sha256_hash": file_hash
            }
        except Exception as e:
            print(f"⚠️ Error getting file info for {file_path}: {e}")
            return {"size_bytes": 0, "sha256_hash": ""}
    
    def load_records(self) -> Dict[str, Any]:
        """Load existing IPFS records"""
        try:
            if os.path.exists(self.records_file):
                with open(self.records_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "created": datetime.now(timezone.utc).isoformat(),
                    "records": [],
                    "latest_cids": {},
                    "w3name_id": self.w3name.name_id,
                    "stats": {
                        "total_uploads": 0,
                        "space_news_uploads": 0,
                        "upcoming_events_uploads": 0
                    }
                }
        except Exception as e:
            print(f"⚠️ Error loading records: {e}")
            return {
                "created": datetime.now(timezone.utc).isoformat(),
                "records": [],
                "latest_cids": {},
                "w3name_id": self.w3name.name_id,
                "stats": {
                    "total_uploads": 0,
                    "space_news_uploads": 0,
                    "upcoming_events_uploads": 0
                }
            }
    
    def save_records(self, records: Dict[str, Any]) -> bool:
        """Save IPFS records to JSON file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.records_file), exist_ok=True)
            
            # Update metadata
            records["last_modified"] = datetime.now(timezone.utc).isoformat()
            records["w3name_id"] = self.w3name.name_id
            
            # Save to file
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Records saved to {self.records_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving records: {e}")
            return False
    
    def upload_file_and_record(self, file_path: str, file_type: str) -> Optional[Dict[str, Any]]:
        """Upload file to IPFS and create record entry"""
        
        if not os.path.exists(file_path):
            print(f"⚠️ File not found: {file_path}")
            return None
        
        file_name = os.path.basename(file_path)
        file_info = self.get_file_info(file_path)
        
        print(f"\n📁 Processing {file_name} ({file_type})...")
        print(f"📊 File size: {file_info['size_bytes']} bytes")
        
        # Upload to NFT.Storage
        cid = self.upload_to_nft_storage(file_path, file_name)
        
        if not cid:
            return None
        
        # Create record entry
        record_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filename": file_name,
            "file_type": file_type,
            "file_path": file_path,
            "cid": cid,
            "ipfs_url": f"https://ipfs.io/ipfs/{cid}",
            "nft_storage_url": f"https://{cid}.ipfs.nftstorage.link",
            "file_size_bytes": file_info["size_bytes"],
            "file_sha256": file_info["sha256_hash"],
            "upload_success": True
        }
        
        print(f"✅ {file_type} uploaded successfully")
        return record_entry
    
    def upload_all_files(self) -> bool:
        """Upload space_news.json and upcoming_events.json to IPFS"""
        try:
            print("🚀 Starting IPFS upload process...")
            
            # Load existing records
            records = self.load_records()
            
            # Files to upload
            files_to_upload = [
                ("public/space_news.json", "space_news"),
                ("public/upcoming_events.json", "upcoming_events")
            ]
            
            upload_results = []
            latest_cids = {}
            
            # Upload each file
            for file_path, file_type in files_to_upload:
                record_entry = self.upload_file_and_record(file_path, file_type)
                
                if record_entry:
                    # Add to records
                    records["records"].append(record_entry)
                    latest_cids[file_type] = record_entry["cid"]
                    records["stats"]["total_uploads"] += 1
                    records["stats"][f"{file_type}_uploads"] += 1
                    
                    upload_results.append(record_entry)
                    
            if not upload_results:
                print("❌ No files were uploaded successfully")
                return False
            
            # Update latest CIDs
            records["latest_cids"] = latest_cids
            
            # Save updated records
            self.save_records(records)
            
            # Upload records file itself to IPFS
            print(f"\n📋 Uploading records file to IPFS...")
            records_record = self.upload_file_and_record(self.records_file, "ipfs_records")
            
            if records_record:
                records_cid = records_record["cid"]
                print(f"📋 Records file CID: {records_cid}")
                
                # Publish to IPNS
                print(f"\n🌐 Publishing to IPNS...")
                ipns_success = self.w3name.publish(records_cid)
                
                if ipns_success:
                    # Update records with IPNS info
                    records["ipns_info"] = {
                        "name_id": self.w3name.name_id,
                        "current_cid": records_cid,
                        "ipns_url": f"https://ipfs.io/ipns/{self.w3name.name_id}",
                        "last_published": datetime.now(timezone.utc).isoformat()
                    }
                    self.save_records(records)
                return True
            else:
                print("❌ Failed to upload records file")
                return False
                
        except Exception as e:
            print(f"❌ Error in upload process: {e}")
            return False
    
def main():
    """Main function to run the IPFS storage and IPNS publishing process"""
    try:
        print("🌟 Space News IPFS Storage & IPNS Publishing")
        print("="*60)
        
        # Get environment variables
        #nft_storage_token = os.getenv("NFT_STORAGE_TOKEN")
        #w3_key_base64 = os.getenv("W3_KEY_BASE64")
        #w3_name = os.getenv("W3_NAME")
        
        nft_storage_token = "94124595.492e63afb6b54b17844f9a9b97775bfb"
        w3_key_base64 = "LMc6D/ZloBqEijcA5bMl5uJ/iakvo4I9MOGGtvhd21M="
        w3_name = "kqleyhr4xy5bucxueqdzynaemna2civzo"
        

        # Initialize storage manager
        storage_manager = IPFSStorageManager(nft_storage_token, w3_key_base64, w3_name)
        
        # Upload all files
        success = storage_manager.upload_all_files()
        
        if success:
            print("\n🎉 IPFS upload and IPNS publishing completed successfully!")
            return True
        else:
            print("\n❌ Process failed")
            return False
            
    except Exception as e:
        print(f"❌ Error in main function: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
