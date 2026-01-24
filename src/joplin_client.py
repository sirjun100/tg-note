"""
Joplin REST API Client
Handles all interactions with Joplin's Web Clipper API.
"""

import json
import logging
from typing import Dict, List, Optional, Any
import requests
from config import JOPLIN_WEB_CLIPPER_PORT, JOPLIN_WEB_CLIPPER_TOKEN

logger = logging.getLogger(__name__)

class JoplinClient:
    """Client for interacting with Joplin Web Clipper API"""

    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = base_url or f"http://localhost:{JOPLIN_WEB_CLIPPER_PORT}"
        self.token = token or JOPLIN_WEB_CLIPPER_TOKEN
        self.session = requests.Session()

        # Note: Joplin Web Clipper uses token as query parameter, not Authorization header

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make HTTP request to Joplin API with error handling"""
        url = f"{self.base_url}{endpoint}"

        # Add token as query parameter if available
        if self.token:
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}token={self.token}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else None
        except requests.RequestException as e:
            logger.error(f"Joplin API request failed: {method} {url} - {e}")
            return None

    def ping(self) -> bool:
        """Check if Joplin API is accessible"""
        try:
            response = self.session.get(f"{self.base_url}/ping", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def fetch_tags(self) -> List[Dict[str, Any]]:
        """Fetch all existing tags from Joplin"""
        result = self._make_request('GET', '/tags')
        if result and isinstance(result, dict) and 'items' in result:
            tags = result['items']
            logger.info(f"Fetched {len(tags)} tags from Joplin")
            return tags
        elif result and isinstance(result, list):
            logger.info(f"Fetched {len(result)} tags from Joplin")
            return result
        logger.warning("Failed to fetch tags or no tags found")
        return []

    def get_notes_with_tag(self, tag_id: str) -> List[Dict[str, Any]]:
        """Get all notes associated with a specific tag"""
        response = self._make_request("GET", f"/tags/{tag_id}/notes")
        if response and isinstance(response, dict) and 'items' in response:
            return response['items']
        return response if response is not None else []

    def create_note(self, folder_id: str, title: str, body: str) -> Optional[str]:
        """Create a new note in Joplin"""
        note_data = {
            "title": title,
            "body": body,
            "parent_id": folder_id
        }

        result = self._make_request('POST', '/notes', json=note_data)
        if result and 'id' in result:
            note_id = result['id']
            logger.info(f"Created note '{title}' with ID: {note_id}")
            return note_id

        logger.error(f"Failed to create note '{title}'")
        return None

    def update_note(self, note_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing note"""
        result = self._make_request('PUT', f'/notes/{note_id}', json=updates)
        if result:
            logger.info(f"Updated note {note_id}")
            return True

        logger.error(f"Failed to update note {note_id}")
        return False

    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific note by ID"""
        return self._make_request('GET', f'/notes/{note_id}')

    def delete_note(self, note_id: str) -> bool:
        """Delete a note"""
        result = self._make_request('DELETE', f'/notes/{note_id}')
        if result is None:  # DELETE returns no content on success
            logger.info(f"Deleted note {note_id}")
            return True

        logger.error(f"Failed to delete note {note_id}")
        return False

    def apply_tags(self, note_id: str, tag_names: List[str]) -> bool:
        """Apply tags to a note, creating tags if they don't exist"""
        success = True

        for tag_name in tag_names:
            tag_id = self._get_or_create_tag(tag_name)
            if tag_id:
                if not self._link_tag_to_note(tag_id, note_id):
                    success = False
            else:
                logger.error(f"Failed to get/create tag '{tag_name}'")
                success = False

        return success

    def apply_tags_and_track_new(self, note_id: str, tag_names: List[str]) -> Dict[str, Any]:
        """Apply tags to a note and return info about which tags are new

        Returns:
            Dict with:
            - success: bool - Whether all tags were applied successfully
            - new_tags: List[str] - Tags that were newly created
            - existing_tags: List[str] - Tags that already existed
            - all_tags: List[str] - All tags that were applied
        """
        # Get existing tags first
        existing_tag_titles = {tag.get('title') for tag in self.fetch_tags()}

        new_tags = []
        existing_tags = []
        success = True

        for tag_name in tag_names:
            # Check if tag is new before creating/getting it
            is_new = tag_name not in existing_tag_titles

            tag_id = self._get_or_create_tag(tag_name)
            if tag_id:
                if not self._link_tag_to_note(tag_id, note_id):
                    success = False

                # Track whether tag was new
                if is_new:
                    new_tags.append(tag_name)
                else:
                    existing_tags.append(tag_name)
            else:
                logger.error(f"Failed to get/create tag '{tag_name}'")
                success = False

        return {
            'success': success,
            'new_tags': new_tags,
            'existing_tags': existing_tags,
            'all_tags': tag_names
        }

    def _get_or_create_tag(self, tag_name: str) -> Optional[str]:
        """Get existing tag or create new one"""
        # First, check if tag exists
        tags = self.fetch_tags()
        for tag in tags:
            if tag.get('title') == tag_name:
                return tag['id']

        # Tag doesn't exist, create it
        tag_data = {"title": tag_name}
        result = self._make_request('POST', '/tags', json=tag_data)
        if result and 'id' in result:
            tag_id = result['id']
            logger.info(f"Created new tag '{tag_name}' with ID: {tag_id}")
            return tag_id

        logger.error(f"Failed to create tag '{tag_name}'")
        return None

    def _link_tag_to_note(self, tag_id: str, note_id: str) -> bool:
        """Link a tag to a note"""
        response = self._make_request("POST", f"tags/{tag_id}/notes", json={"id": note_id})
        return response is not None

    def rename_tag(self, tag_id: str, new_name: str) -> bool:
        """Rename an existing tag"""
        response = self._make_request("PUT", f"tags/{tag_id}", json={"title": new_name})
        return response is not None

    def append_log(self, log_entry: str) -> bool:
        """Append an entry to the AI-Decision-Log note"""
        # Load config to get log note ID
        try:
            with open('joplin_config.json', 'r') as f:
                config = json.load(f)
                log_note_id = config.get('ai_decision_log_note_id')
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            logger.error("AI-Decision-Log note ID not found in config")
            return False

        if not log_note_id:
            logger.error("AI-Decision-Log note ID not configured")
            return False

        # Get current note content
        current_note = self.get_note(log_note_id)
        if not current_note:
            logger.error("Failed to fetch AI-Decision-Log note")
            return False

        current_body = current_note.get('body', '')
        # Append new entry with timestamp
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        updated_body = f"{current_body}\n\n---\n**{timestamp}**\n{log_entry}\n"

        return self.update_note(log_note_id, {"body": updated_body})

    def get_folders(self) -> List[Dict[str, Any]]:
        """Get all folders"""
        result = self._make_request('GET', '/folders')
        if result and isinstance(result, dict) and 'items' in result:
            return result['items']
        elif result and isinstance(result, list):
            return result
        return []

    def get_folder(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific folder"""
        return self._make_request('GET', f'/folders/{folder_id}')

    def get_notes_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """Get all notes in a specific folder"""
        response = self._make_request("GET", f"folders/{folder_id}/notes")
        return response if response is not None else []

    def get_all_notes(self) -> List[Dict[str, Any]]:
        """Get all notes in the database (paginated fetch if needed)"""
        # Note: Depending on database size, this might need pagination.
        response = self._make_request("GET", "/notes", params={"limit": 1000})
        if response and isinstance(response, dict) and 'items' in response:
            return response['items']
        return response if response is not None else []

    def create_folder(self, title: str, parent_id: str = None) -> Optional[Dict[str, Any]]:
        """Create a new folder"""
        payload = {"title": title}
        if parent_id:
            payload["parent_id"] = parent_id
        
        response = self._make_request("POST", "/folders", json=payload)
        return response

    def move_note(self, note_id: str, parent_id: str) -> bool:
        """Move a note to a different folder"""
        response = self._make_request("PUT", f"/notes/{note_id}", json={"parent_id": parent_id})
        return response is not None

    def get_or_create_folder_by_path(self, path_parts: List[str]) -> Optional[str]:
        """
        Get folder ID for a path, creating folders as needed.
        Example: ["Areas", "Finance"]
        """
        current_parent_id = ""
        
        for part in path_parts:
            # Check if folder exists at this level
            folders = self.get_folders()
            target_folder = None
            
            for f in folders:
                if f.get('title') == part and f.get('parent_id', '') == current_parent_id:
                    target_folder = f
                    break
            
            if target_folder:
                current_parent_id = target_folder['id']
            else:
                # Create it
                new_folder = self.create_folder(part, parent_id=current_parent_id if current_parent_id else None)
                if not new_folder:
                    logger.error(f"Failed to create folder '{part}' during path resolution")
                    return None
                current_parent_id = new_folder['id']
                
        return current_parent_id