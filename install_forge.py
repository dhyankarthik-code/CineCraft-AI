import requests
import os
import subprocess

FORGE_VERSION = "1.20.1-47.3.0"
INSTALLER_URL = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{FORGE_VERSION}/forge-{FORGE_VERSION}-installer.jar"

def install_forge():
    print(f"Downloading Forge {FORGE_VERSION}...")
    r = requests.get(INSTALLER_URL)
    with open("server/forge-installer.jar", "wb") as f:
        f.write(r.content)
    
    print("Installing Forge Server... (This may take a minute)")
    # Run installer inside server dir
    subprocess.run(["java", "-jar", "forge-installer.jar", "--installServer"], cwd="server", check=True)
    
    # Create eula.txt
    with open("server/eula.txt", "w") as f:
        f.write("eula=true\n")
        
    print("Forge Installed!")

if __name__ == "__main__":
    if not os.path.exists("server"):
        os.makedirs("server")
    install_forge()
