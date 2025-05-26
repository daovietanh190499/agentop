import gradio as gr
import subprocess
import time
from typing import List

SERVER_CONFIGS = {
    "XL": {"cpu_requests": "16", "cpu_limits": "16", "memory_requests": "64Gi", "memory_limits": "64Gi", "physical_gpu": "1", "gpu_memory": "140000"},
    "L":  {"cpu_requests": "8", "cpu_limits": "8", "memory_requests": "64Gi", "memory_limits": "64Gi", "physical_gpu": "1", "gpu_memory": "90000"},
    "M":  {"cpu_requests": "8", "cpu_limits": "8", "memory_requests": "32Gi", "memory_limits": "32Gi", "physical_gpu": "1", "gpu_memory": "48000"},
    "S":  {"cpu_requests": "4", "cpu_limits": "4", "memory_requests": "16Gi",  "memory_limits": "16Gi",  "physical_gpu": "1", "gpu_memory": "24000"}
}

SERVER_MAPPINGS = {
        "XL (16 CPU cores, 64Gi RAM, 1 140Gi VRAM GPU)":"XL",
        "L (8 CPU cores, 64Gi RAM, 1 90Gi VRAM GPU)":"L",
        "M (8 CPU cores, 32Gi RAM, 1 48Gi VRAM GPU)":"M",
        "S (4 CPU cores, 16Gi RAM, 1 24Gi VRAM GPU)":"S"
}

SERVICE_COMMAND = {
    "diffusion-pipe": "sleep infinity",
    "comfyui": "/opt/conda/envs/pyenv/bin/python3 main.py --port 8000 --listen 0.0.0.0 & sleep infinity"
}

SERVICE_VOLUMES = {
    "diffusion-pipe": "/home/training/diffusion-pipe/data:/diffusion-pipe/data,/home/training/diffusion-pipe/models:/diffusion-pipe/models",
    "comfyui": "/home/ai/comfy_ui0/input:/comfyui/input,/home/ai/comfy_ui0/output:/comfyui/output,/home/ai/comfy_ui0/models:/comfyui/models"
}

TTL_LIST = ['1h', '3h', '4h', '6h', '8h', 'forever']

def execute_command(command: List[str]) -> str:
    try:
        result = subprocess.run(["bash"] + command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

def create_server(name: str, service: str, size: str, ttl: str, username: str, password: str) -> str:
    if size not in SERVER_MAPPINGS:
        return f"Invalid server size: {size}"
    if service not in SERVICE_VOLUMES:
        return f"Invalid service: {service}"

    config = SERVER_CONFIGS[SERVER_MAPPINGS[size]]
    size = SERVER_MAPPINGS[size]
    release_name = f"{name.lower()}-{size.lower()}"
    command = [
        "aipod.sh", "create",
        "--release-name", release_name,
        "--image", f"localhost:32000/aipod-{service}",
        "--image-tag", "latest",
        "--command", SERVICE_COMMAND[service],
        "--volumes", SERVICE_VOLUMES[service],
        "--port", "8000",
        "--cpu-requests", config["cpu_requests"],
        "--cpu-limits", config["cpu_limits"],
        "--memory-requests", config["memory_requests"],
        "--memory-limits", config["memory_limits"],
        "--physical-gpu", config["physical_gpu"],
        "--gpu-memory", config["gpu_memory"],
        "--username", username,
        "--password", password,
        "--ttl", ttl
    ]
    return f"Server creation initiated:\n{execute_command(command)}"

def list_servers_raw() -> List[str]:
    output = execute_command(["aipod.sh", "list"])
    lines = output.strip().splitlines()
    return lines if len(lines) > 1 else []

def get_release_names() -> List[str]:
    lines = list_servers_raw()
    return [line.split()[0] for line in lines]

def restart_server(release_name: str) -> str:                                                                                 return execute_command(["aipod.sh", "restart", "--release-name", release_name]) if release_name else "Please select a release."

def delete_server(release_name: str) -> str:
    return execute_command(["aipod.sh", "delete", "--release-name", release_name]) if release_name else "Please select a release."

def check_status(release_name: str) -> str:
    return execute_command(["aipod.sh", "stat", "--release-name", release_name]) if release_name else "Please select a release."

with gr.Blocks(title="AI Pod Manager") as app:
    gr.Markdown("# AI Pod Manager")

    with gr.Tab("Create Server"):
        with gr.Row():
            name = gr.Textbox(label="Release Name")
            service = gr.Dropdown(choices=list(SERVICE_VOLUMES.keys()), label="Service Type", value="diffusion-pipe")
        with gr.Row():
            size = gr.Dropdown(choices=list(SERVER_MAPPINGS.keys()), label="Server Size", value=list(SERVER_MAPPINGS.keys())[2])
            ttl = gr.Dropdown(choices=TTL_LIST, label="Time to Live", value="8h")
        with gr.Row():
            username = gr.Textbox(label="Username", value="default")
            password = gr.Textbox(label="Password", value="default", type="password")

        create_btn = gr.Button("Create Server")
        create_output = gr.HTML(label="Creation Status")

        def format_create_output(raw_text):
            import re
            url_match = re.search(r'(https?://[^\s]+)', raw_text)
            url = url_match.group(1) if url_match else ""
            url_html = f'<a href="{url}" target="_blank">{url}</a>' if url else ""

            html = f"<pre>{raw_text.strip()}</pre>"

            if url_html:
                html += f"<br><strong>App URL:</strong> {url_html}"

            return html

        create_btn.click(
            fn=lambda *args: format_create_output(create_server(*args)),
            inputs=[name, service, size, ttl, username, password],
            outputs=create_output
        )


    with gr.Tab("List Servers") as list_tab:
        list_output = gr.HTML(label="Active Servers")

        def update_list_output():
            lines = list_servers_raw()
            if not lines or len(lines) < 3:
                return "<p>No active servers.</p>"

            headers = lines[0].split()
            html = """
            <style>
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th, td {
                    border: 1px solid #ccc;
                    padding: 6px 8px;
                    text-align: left;
                    font-family: monospace;
                }
                button {
                    padding: 4px 8px;
                    font-size: 0.9em;
                    cursor: pointer;
                }
            </style>
            <table>
                <tr>
                    <th>NAME</th>
                    <th>IMAGE</th>
                    <th>READY</th>
                    <th>LAST DEPLOYED</th>
                    <th>URL</th>
                    <th>SCHEDULE</th>
                    <th>EXPIRED DATETIME</th>
                    <th>REMAIN (m)</th>
                    <th>RESTART</th>
                    <th>DELETE</th>
                </tr>
            """

            for line in lines[2:]:
                parts = line.split()
                if len(parts) < 9:
                    continue

                name = parts[0]
                image = parts[1]
                ready = parts[2]
                last_deployed = parts[3] + " " + parts[4]
                url = parts[5]
                schedule = parts[6]
                expired_datetime = parts[7] + " " + parts[8]
                remain = parts[9]

                url_html = f'<a href="http://{url}" target="_blank">🔗</a>' if url else ""
                restart_btn = '<button style="color:orange" onclick="fetch(\'https://skynetwork-gputest.vshosting.cz/gradio_api/call/restart-server\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({data:[\'' + name + '\']})}).then(res => res.json()).then(res => document.querySelector(\'#refresh-btn\').click())">Restart</button>'
                delete_btn = '<button style="color:red" onclick="fetch(\'https://skynetwork-gputest.vshosting.cz/gradio_api/call/delete-server\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({data:[\'' + name + '\']})}).then(res => res.json()).then(res => document.querySelector(\'#refresh-btn\').click())">Delete</button>'

                html += f"""
                <tr>
                    <td>{name}</td>
                    <td>{image}</td>
                    <td>{ready}</td>
                    <td>{last_deployed}</td>
                    <td>{url_html}</td>
                    <td>{schedule}</td>
                    <td>{expired_datetime}</td>
                    <td>{remain}</td>
                    <td>{restart_btn}</td>
                    <td>{delete_btn}</td>
                </tr>
                """

            html += "</table>"
            return html

        refresh_btn = gr.Button(visible=False, elem_id="refresh-btn")
        refresh_btn.click(fn=update_list_output, outputs=[list_output])

        list_tab.select(fn=update_list_output, outputs=[list_output])

    gr.api(delete_server, api_name="delete-server")
    gr.api(restart_server, api_name="restart-server")

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=8000)
