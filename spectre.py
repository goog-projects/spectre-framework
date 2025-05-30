import requests
import time
import ctypes
import os
import sys
from math import sqrt, pow
import pyMeow as pm

class Offsets:
    m_pBoneArray = 0x1F0

class Settings:
    DeathMatch_mode = False

def bone_pos(mem, client, pawn_ptr, bone):
    game_scene = pm.r_int64(mem, pawn_ptr + Offsets.m_pGameSceneNode)
    bone_array_ptr = pm.r_int64(mem, game_scene + Offsets.m_pBoneArray)
    return pm.r_vec3(mem, bone_array_ptr + bone * 32)  

def initialize_offsets():
    offsets_name = ["dwViewMatrix", "dwEntityList", "dwLocalPlayerController", "dwLocalPlayerPawn", "dwViewAngles"]
    try:
        offsets = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json").json()
        [setattr(Offsets, k, offsets["client.dll"][k]) for k in offsets_name]
        
        offsets = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/buttons.json").json()
        setattr(Offsets, "dwForceJump", offsets["client.dll"]["jump"])
        
        offsets_name = ["m_iIDEntIndex", "m_hPlayerPawn", "m_fFlags", "m_iszPlayerName", "m_iHealth", 
                      "m_iTeamNum", "m_vOldOrigin", "m_pGameSceneNode", "m_entitySpottedState", 
                      "m_fFlags", "m_aimPunchAngle"]
        offsets_name2 = ["C_CSPlayerPawnBase", "CCSPlayerController", "C_BaseEntity", "CBasePlayerController", 
                        "C_BaseEntity", "C_BaseEntity", "C_BasePlayerPawn", "C_BaseEntity", 
                        "C_CSPlayerPawn", "C_BaseEntity", "C_CSPlayerPawn"]
        clientDll = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json").json()
        [setattr(Offsets, offsets_name[i], clientDll["client.dll"]["classes"][offsets_name2[i]]["fields"][offsets_name[i]]) for i in range(0, 11)]
    except Exception as e:
        print(f"Error initializing offsets: {e}")
        sys.exit(1)

def main():
    initialize_offsets()

    # Enable ANSI escape codes for Windows
    if os.name == 'nt':
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 0x0007)

    # ANSI color codes
    COLOR_RESET = "\033[0m"
    COLOR_GREEN = "\033[92m"
    COLOR_ORANGE = "\033[93m" # Often yellow, but can be used for orange-like color
    COLOR_RED = "\033[91m"
    
    try:
        mem = pm.open_process("cs2.exe")
        client = pm.get_module(mem, "client.dll")["base"]
    except Exception as e:
        print(f"Initialization error: {e}")
        sys.exit(1)
    
    while True:
        try:
            # Clear console
            os.system('cls' if os.name == 'nt' else 'clear')
            
            local_player = pm.r_int64(mem, client + Offsets.dwLocalPlayerPawn)
            if not local_player:
                time.sleep(1)
                continue
                
            local_team = pm.r_int(mem, local_player + Offsets.m_iTeamNum)
            ent_list = pm.r_int64(mem, client + Offsets.dwEntityList)
            local_pos = pm.r_vec3(mem, local_player + Offsets.m_vOldOrigin) or {'x': 0, 'y': 0, 'z': 0}
            
            print(f"Local Player Position: X={local_pos['x']:.2f}, Y={local_pos['y']:.2f}, Z={local_pos['z']:.2f}")

            allies = []
            enemies = []
            
            for i in range(1, 65):
                try:
                    entEntry = pm.r_int64(mem, ent_list + (8 * (i & 0x7FFF) >> 9) + 16)
                    entity = pm.r_int64(mem, entEntry + 120 * (i & 0x1FF))
                    if entity == pm.r_int64(mem, client + Offsets.dwLocalPlayerController):
                        continue
                        
                    controller_pawn_ptr = pm.r_int64(mem, entity + Offsets.m_hPlayerPawn)
                    list_entry_ptr = pm.r_int64(mem, ent_list + 0x8 * ((controller_pawn_ptr & 0x7FFF) >> 9) + 16)
                    pawn_ptr = pm.r_int64(mem, list_entry_ptr + 120 * (controller_pawn_ptr & 0x1FF))
                    
                    if not pawn_ptr:
                        continue
                        
                    entityTeam = pm.r_int(mem, entity + Offsets.m_iTeamNum)
                    
                    entityHealth = pm.r_int(mem, pawn_ptr + Offsets.m_iHealth)
                    entityPos = pm.r_vec3(mem, pawn_ptr + Offsets.m_vOldOrigin) or {'x': 0, 'y': 0, 'z': 0}
                    entityName = str(pm.r_string(mem, entity + Offsets.m_iszPlayerName)) or "Unknown"
                    
                    if entityHealth > 0 and entityTeam != 5:  # Skip spectator team
                        distance = sqrt(
                            pow(local_pos["x"] - entityPos["x"], 2) + 
                            pow(local_pos["y"] - entityPos["y"], 2) + 
                            pow(local_pos["z"] - entityPos["z"], 2)
                        )
                        
                        health_color = COLOR_GREEN
                        if entityHealth <= 30:
                            health_color = COLOR_RED
                        elif entityHealth <= 60:
                            health_color = COLOR_ORANGE
                        
                        pos_str = f"{entityPos.get('x', 0):.2f}, {entityPos.get('y', 0):.2f}, {entityPos.get('z', 0):.2f}"
                        
                        player_info = {
                            "name": entityName,
                            "health": entityHealth,
                            "pos_str": pos_str,
                            "distance": distance,
                            "color": health_color
                        }

                        if local_team == entityTeam:
                            allies.append(player_info)
                        else:
                            enemies.append(player_info)
                            
                except Exception as e:
                    # Skip any errors with individual entities
                    continue

            # --- Allies Tab ---
            print("\n--- Allies ---")
            print("-" * 60)
            print(f"{'Name':<20} {'Health':<6} {'Position (X, Y, Z)':<30} {'Distance':<10}")
            print("-" * 60)
            if not allies:
                print("No allies found.")
            else:
                for ally in allies:
                    print(f"{ally['color']}{ally['name']:<20} {ally['health']:<6} {ally['pos_str']:<30} {ally['distance']:.2f}{COLOR_RESET}")

            # --- Enemies Tab ---
            print("\n--- Enemies ---")
            print("-" * 60)
            print(f"{'Name':<20} {'Health':<6} {'Position (X, Y, Z)':<30} {'Distance':<10}")
            print("-" * 60)
            if not enemies:
                print("No enemies found.")
            else:
                for enemy in enemies:
                    print(f"{enemy['color']}{enemy['name']:<20} {enemy['health']:<6} {enemy['pos_str']:<30} {enemy['distance']:.2f}{COLOR_RESET}")
            
            time.sleep(0.5)  # Update rate
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
