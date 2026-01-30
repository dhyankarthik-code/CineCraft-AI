import requests
import os

MODS = [
    ("citadel", "model-libs", "Citadel (Dependency)"),
    ("titans-world", "mod", "Titans World (Titan Mod Request)")
]

VERSION = "1.20.1"

def download_file(project_slug, project_type, label):
    print(f"Searching for {label}...")
    
    # 1. Search (using slug directly if accurate, or query)
    # Modrinth slugs are usually accurate.
    # Get version for slug directly.
    
    # Try getting project first to confirm
    r_proj = requests.get(f"https://api.modrinth.com/v2/project/{project_slug}")
    if r_proj.status_code != 200:
        # Fallback to search if slug is wrong
        search_url = f"https://api.modrinth.com/v2/search?query={project_slug}&facets=[[\"project_type:mod\"]]&limit=1"
        r = requests.get(search_url)
        if r.status_code != 200 or not r.json()['hits']:
            print(f"❌ {label} not found.")
            return
        project_id = r.json()['hits'][0]['project_id']
    else:
        project_id = r_proj.json()['id']
        
    # 2. Get Version
    versions_url = f"https://api.modrinth.com/v2/project/{project_id}/version?game_versions=[\"{VERSION}\"]&loaders=[\"forge\"]"
    r_ver = requests.get(versions_url)
    versions = r_ver.json()
    
    if not versions:
        print(f"❌ No {VERSION} Forge version for {label}.")
        return

    file_obj = versions[0]['files'][0]
    url = file_obj['url']
    filename = file_obj['filename']
    
    # 3. Download
    print(f"⬇️ Downloading {filename}...")
    dest = os.path.join("server", "mods", filename)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    
    r_file = requests.get(url)
    with open(dest, 'wb') as f:
        f.write(r_file.content)
    print(f"✅ Installed {label}")

if __name__ == "__main__":
    for slug, ptype, name in MODS:
        download_file(slug, ptype, name)
