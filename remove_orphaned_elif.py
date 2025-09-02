#!/usr/bin/env python3

def remove_orphaned_elif():
    """Remove orphaned elif statements that are duplicates of what's in on_message function"""
    
    with open('core/api.py', 'r') as f:
        lines = f.readlines()
    
    # Find the end of on_message function
    on_message_end = None
    for i, line in enumerate(lines):
        if line.strip() == 'client.on_message = on_message':
            on_message_end = i
            break
    
    if on_message_end is None:
        print("Could not find end of on_message function")
        return
    
    # Find the start of simulate_telemetry function
    simulate_start = None
    for i in range(on_message_end, len(lines)):
        if lines[i].strip() == 'def simulate_telemetry():':
            simulate_start = i
            break
    
    if simulate_start is None:
        print("Could not find simulate_telemetry function")
        return
    
    # Create new file content
    new_lines = []
    
    # Add lines up to the end of on_message function
    new_lines.extend(lines[:on_message_end + 1])
    
    # Add a newline and client.connect line
    new_lines.append('\n')
    new_lines.append('client.connect(MQTT_HOST, 1883, 60)\n')
    new_lines.append('\n')
    
    # Add the simulate_telemetry function and everything after it
    new_lines.extend(lines[simulate_start:])
    
    # Write the fixed file
    with open('core/api.py', 'w') as f:
        f.writelines(new_lines)
    
    print(f"Removed orphaned elif statements between lines {on_message_end + 1} and {simulate_start}")

if __name__ == "__main__":
    remove_orphaned_elif()
