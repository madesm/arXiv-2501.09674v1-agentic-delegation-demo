# **Authenticated Delegation and Authorized AI Agents – Toy Demo with MCP Interaction**

![https://img.shields.io/badge/in_progress-yellow](https://img.shields.io/badge/in_progress-yellow)

> This repository is in progress

This repository demonstrates a **toy example** of **agentic delegation** and
**authorized AI agents**, inspired by
[arXiv-2501.09674](https://arxiv.org/abs/2501.09674), integrated with the
**Model Context Protocol (MCP)**.

## **Overview**

This demo showcases **AI-driven delegation**, where a **CalendarAgent** is
authorized to access a user's calendar and retrieve **available time slots**.
The **agent runs as an MCP server**, exposing an API for querying availability.

The goal is to have a user ( over something like Claude Desktop ) to be able to
authorize an agent to interact on behalf of the user.

### **Key Workflow**
1. A **Flask OAuth server** issues an **access token**, authorizing the
   **CalendarAgent** to access a user’s calendar.
2. The **CalendarAgent (MCP server)** fetches **available time slots** using the
   **delegated token**.
3. An **MCP client** interacts with the agent via **MCP APIs** to request
   available times.

This pattern enables **secure, structured, AI-driven workflows**, such as:
- AI assistants managing **personal schedules**.
- AI-powered bots handling **automated scheduling** via **MCP APIs**.

## Running 

To get started:

1. Run the oauth server

```sh
python -m uvicorn oauth_server:app --reload --port 8000
```

of if using Makefile

`make oauth_server`

2. Run the client in another terminal window:

```sh
python client_with_callback.py
```

or if using Makefile:

`make client`

3. Visit `http://localhost:9000/start` in your browser to authorize the agent.
4. Visit `http://localhost:9000/call_agent` to call the agent action and get the first time slot.

Expected Result:

```sh
{"agent_result":{"_meta":null,"content":[{"type":"text","text":"{\n  \"start\": \"2025-03-01T11:45\",\n  \"end\": \"2025-03-01T12:15\"\n}"}],"isError":false}}
```

**[Youtube Demo Here](https://www.youtube.com/embed/Xz_CiMUbik0?si=ytkHXtAfIEElHWa)**

## **Architecture**

This demo runs **two parallel servers**:

1. **Flask OAuth Server**  
   - Simulates an **OAuth-based delegation system**.
   - Issues **delegation tokens** that authorize agent access.

2. **MCP CalendarAgent**  
   - Runs as an **MCP server**, exposing an API to query **available calendar
     slots**.
   - Requires an **access token** to retrieve availability.

---

## **Sequence Diagram**

```mermaid
sequenceDiagram
  participant User
  participant FlaskOAuthServer
  actor CalendarAgent
  participant MCPClient

  User -->> FlaskOAuthServer : Requests Agent Authorization
  FlaskOAuthServer -->> User : Issues Access Token
  User -->> MCPClient : sends text to MCP Client
  MCPClient -->> CalendarAgent : Calls MCP API (find_slot) with Access Token
  CalendarAgent -->> FlaskOAuthServer : Fetches Calendar Data
  CalendarAgent -->> MCPClient : Returns Available Time Slots
```

---

## **Demo Components**

### **1. Flask OAuth Server**
- Issues **delegation tokens** that authorize the **CalendarAgent**.
- Simulates **secure access control** for AI agents.

### **2. MCP CalendarAgent**
- Runs an **MCP server** implementing:
  - **`find_slot`** – Retrieves available time slots from the user's calendar.
- Requires an **OAuth access token** for authorization.

### **3. MCP Client**
- Interacts with the **CalendarAgent** via **MCP APIs**.
- Calls **`find_slot`** to fetch available meeting times.

---

## **Limitations**

- **Single-Level Delegation:**  
  - The demo supports **direct delegation** but does not implement **multi-hop
    agent delegation**.
- **Mock Calendar Data:**  
  - The **calendar availability** is simulated with static data.
- **Simplified OAuth Flow:**  
  - No **PKCE, refresh tokens, or user account management**.
- **Access token is pushed through**: Need to think about this. There's likely a better way to do this.
- Many others...


---

## **Next Steps**
- Extend the system to support **multi-agent delegation**.
- Implement **real calendar integration** (Google Calendar, iCal, etc.).
- Expand authorization with **OAuth refresh tokens**.

---

This demo provides a **starting point** for **AI-driven delegation workflows**
using **MCP**, **OAuth**, and **agent-based automation** but much more work is
to be done to improve advance the flows. 🚀

