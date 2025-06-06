import gradio as gr
import subprocess
import time
from typing import List
import os

SERVER_CONFIGS = {
    "2XL": {"cpu_requests": "8", "cpu_limits": "8", "memory_requests": "32Gi", "memory_limits": "32Gi"},
    "XL":  {"cpu_requests": "4", "cpu_limits": "4", "memory_requests": "16Gi", "memory_limits": "16Gi"},
    "L": {"cpu_requests": "4", "cpu_limits": "4", "memory_requests": "8Gi", "memory_limits": "8Gi"},
    "M":  {"cpu_requests": "2", "cpu_limits": "2", "memory_requests": "8Gi", "memory_limits": "8Gi"},
    "S":  {"cpu_requests": "2", "cpu_limits": "2", "memory_requests": "4Gi", "memory_limits": "4Gi"},
    "XS":  {"cpu_requests": "1", "cpu_limits": "1", "memory_requests": "4Gi",  "memory_limits": "4Gi"},
    "2XS":  {"cpu_requests": "1", "cpu_limits": "1", "memory_requests": "2Gi",  "memory_limits": "2Gi"}
}

SERVER_MAPPINGS = {
    "2XL (8 CPU cores, 32Gi RAM)": "2XL",
    "XL (4 CPU cores, 16Gi RAM)": "XL",
    "L (4 CPU cores, 8Gi RAM)": "L",
    "M (2 CPU cores, 8Gi RAM)": "M",
    "S (2 CPU cores, 4Gi RAM)": "S",
    "XS (1 CPU cores, 4Gi RAM)": "XS",
    "2XS (1 CPU cores, 2Gi RAM)": "2XS"
}

SERVICE_COMMAND = {
    "http": "uvicorn app:app --host 0.0.0.0 --port 80",
    "mcp": "python app.py",
    "agent_http": "uvicorn app:app --host 0.0.0.0 --port 80",
    "agent_mcp": "python app.py"
}

SERVER_PATH = {
    "http": "src/http/",
    "mcp": "src/mcp/",
    "agent_http": "src/agent_http/",
    "agent_mcp": "src/agent_mcp/"
}

DOCKER_IMAGES = ["fastapi", "mcp", "fastapi-openai", "mcp-openai"]

TTL_LIST = ['1h', '3h', '4h', '6h', '8h', 'forever']

def execute_command(command: List[str]) -> str:
    try:
        result = subprocess.run(["bash"] + command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

def create_server(name: str, service: str, size: str, ttl: str, docker_environment: str, code: str) -> str:
    if size not in SERVER_MAPPINGS:
        return f"Invalid server size: {size}"

    with open(os.path.join("agentop-tool-v0.1.0/agentop-tool", SERVER_PATH[service], "main.py"), "w+") as f:
        f.write(code)

    config = SERVER_CONFIGS[SERVER_MAPPINGS[size]]
    size = SERVER_MAPPINGS[size]
    release_name = f"{name.lower()}-{size.lower()}"
    command = [
        "agentop.sh", "create",
        "--release-name", release_name,
        "--image", f"localhost:32000/agentop-tool",
        "--image-tag", docker_environment,
        "--command", SERVICE_COMMAND[service],
        "--port", "80",
        "--cpu-requests", config["cpu_requests"],
        "--cpu-limits", config["cpu_limits"],
        "--memory-requests", config["memory_requests"],
        "--memory-limits", config["memory_limits"],
        "--ttl", ttl,
        "--server-path", f"{SERVER_PATH[service]}*"
    ]
    return f"Server creation initiated:\n{execute_command(command)}"

def list_servers_raw() -> List[str]:
    output = execute_command(["agentop.sh", "list"])
    lines = output.strip().splitlines()
    return lines if len(lines) > 1 else []

def get_release_names() -> List[str]:
    lines = list_servers_raw()
    return [line.split()[0] for line in lines]

def restart_server(release_name: str) -> str:                                                                                 return execute_command(["agentop.sh", "restart", "--release-name", release_name]) if release_name else "Please select a release."

def delete_server(release_name: str) -> str:
    return execute_command(["agentop.sh", "delete", "--release-name", release_name]) if release_name else "Please select a release."

def check_status(release_name: str) -> str:
    return execute_command(["agentop.sh", "stat", "--release-name", release_name]) if release_name else "Please select a release."

with gr.Blocks(title="AI Pod Manager") as app:
    gr.Markdown("# AI Pod Manager")

    with gr.Tab("Create Server"):
        with gr.Row():
            name = gr.Textbox(label="Release Name")
            service = gr.Dropdown(choices=list(SERVICE_COMMAND.keys()), label="Service Type", value="http")
        with gr.Row():
            size = gr.Dropdown(choices=list(SERVER_MAPPINGS.keys()), label="Server Size", value=list(SERVER_MAPPINGS.keys())[2])
            ttl = gr.Dropdown(choices=TTL_LIST, label="Time to Live", value="8h")
        with gr.Row():
            docker_environment = gr.Dropdown(choices=DOCKER_IMAGES, label="Docker Environment", value="fastapi")
        with gr.Row():
            code = gr.Code(language="python")

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
            inputs=[name, service, size, ttl, docker_environment, code],
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
                restart_btn = '<button style="color:orange" onclick="fetch(\'gradio_api/call/restart-server\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({data:[\'' + name + '\']})}).then(res => res.json()).then(res => document.querySelector(\'#refresh-btn\').click())">Restart</button>'
                delete_btn = '<button style="color:red" onclick="fetch(\'gradio_api/call/delete-server\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({data:[\'' + name + '\']})}).then(res => res.json()).then(res => document.querySelector(\'#refresh-btn\').click())">Delete</button>'

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
