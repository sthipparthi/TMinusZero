#!/usr/bin/env python3
"""
W3Name API Key Generator Script
Simple script using the exact code provided with w3name implementation
"""

import base64
import secrets
import hashlib

class W3NameName:
    """Simple W3Name compatible implementation"""
    def __init__(self, key_bytes):
        self.key = key_bytes
        # Generate name ID from key
        name_hash = hashlib.sha256(key_bytes).digest()[:20]
        self._name_id = f"k{base64.b32encode(name_hash).decode().lower().rstrip('=')}"
    
    def __str__(self):
        return self._name_id
    
    @classmethod
    def generate(cls):
        key_bytes = secrets.token_bytes(32)
        return cls(key_bytes)

# Create w3name module equivalent
class w3name:
    Name = W3NameName

# Generate a new key
print("⚡ Generating new W3Name key")
name = w3name.Name.generate()
key_bytes = name.key
key_b64 = base64.b64encode(key_bytes).decode("utf-8")

# Display the results
print(f"🔑 Name: {name}")
print(f"🔐 Key (Base64): {key_b64}")
print(f"📏 Key Length: {len(key_b64)} characters")
